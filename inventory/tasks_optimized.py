"""
مهام Celery المحسّنة للمخزون - نظام ذكي يمنع التكرارات
"""

from celery import shared_task
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
import logging
import pandas as pd
from io import BytesIO

logger = logging.getLogger(__name__)


@shared_task(bind=True, time_limit=600, soft_time_limit=540, rate_limit=None)
def bulk_upload_products_fast(self, upload_log_id, file_content, warehouse_id, upload_mode, user_id, auto_delete_empty=False):
    """
    رفع المنتجات بالجملة - نظام ذكي محسّن
    الأوضاع:
    - smart_update: تحديث ذكي مع نقل للمستودع الصحيح
    - merge_warehouses: دمج الأصناف المكررة  
    - add_only: إضافة الجديد فقط
    - clean_start: مسح كامل وبدء من جديد
    
    Args:
        auto_delete_empty: حذف المستودعات الفارغة بعد الانتهاء
    """
    from django.contrib.auth import get_user_model
    from .models import (BulkUploadLog, Product, Category, Warehouse, 
                         StockTransaction, BulkUploadError)
    from .smart_upload_logic import (smart_update_product, clean_start_reset,
                                     add_stock_transaction, delete_empty_warehouses)
    
    User = get_user_model()
    logger.info(f"🚀 بدء الرفع الذكي - Log: {upload_log_id} - الوضع: {upload_mode}")
    
    try:
        # تحميل البيانات الأساسية (بدون select_for_update)
        upload_log = BulkUploadLog.objects.get(id=upload_log_id)
        user = User.objects.get(id=user_id)
        warehouse = Warehouse.objects.get(id=warehouse_id) if warehouse_id else None
        
        upload_log.status = 'processing'
        upload_log.save(update_fields=['status'])
        
        # قراءة Excel بسرعة
        logger.info("📊 قراءة Excel...")
        df = pd.read_excel(BytesIO(file_content), engine='openpyxl')
        total = len(df)
        
        # تحديث total_rows مباشرة بعد القراءة - مهم للـ API!
        upload_log.total_rows = total
        upload_log.save(update_fields=['total_rows'])
        
        logger.info(f"📋 {total} صف للمعالجة")
        
        # تهيئة كاملة إذا طُلب
        if upload_mode == 'clean_start':
            logger.warning("⚠️ وضع المسح الكامل")
            reset_stats = clean_start_reset()
            upload_log.summary = f"مسح كامل: {reset_stats['deleted_products']} منتج، {reset_stats['deleted_transactions']} معاملة"
            upload_log.save(update_fields=['summary'])
        
        # تنظيف البيانات - فقط الاسم مطلوب (السعر اختياري للمنتجات الموجودة)
        df = df.dropna(subset=['اسم المنتج']).fillna('')
        
        # تحميل البيانات المسبقة
        categories_cache = {c.name: c for c in Category.objects.all()}
        warehouses_cache = {w.name: w for w in Warehouse.objects.filter(is_active=True)}
        
        stats = {
            'created': 0, 
            'updated': 0, 
            'moved': 0, 
            'merged': 0, 
            'skipped': 0, 
            'errors': 0,
            'cutting_updated': 0,
            'cutting_split': 0
        }
        
        # معالجة بدفعات سريعة جداً - 10x أسرع!
        batch_size = 1000  # زيادة من 100 إلى 1000
        errors_batch = []
        last_progress_update = 0  # لتحديث التقدم كل 5%
        
        logger.info(f"🔄 بدء معالجة {len(df)} صف في دفعات بحجم {batch_size}")
        
        for batch_start in range(0, len(df), batch_size):
            batch_end = min(batch_start + batch_size, len(df))
            batch = df.iloc[batch_start:batch_end]
            
            logger.info(f"📦 معالجة الدفعة {batch_start}-{batch_end} ({len(batch)} صف)")
            
            # معالجة الصفوف بسرعة - بدون atomic لكل صف
            for idx, row in batch.iterrows():
                try:
                    logger.info(f"🔍 معالجة الصف {idx + 2}")
                    
                    # استخراج البيانات من جميع الأعمدة
                    name = str(row['اسم المنتج']).strip()
                    code = str(row.get('الكود', '')).strip() or None
                    
                    # تنظيف الكود: إزالة الأصفار البادئة لأن Excel يحذفها تلقائياً
                    # مثال: 010100100730 في النظام → 10100100730 في Excel
                    if code and code.isdigit():
                        code = code.lstrip('0') or '0'  # إزالة الأصفار البادئة، لكن احتفظ بـ '0' إذا كان الكود كله أصفار
                    
                    # معالجة السعر بشكل آمن
                    try:
                        price_value = row.get('السعر', '')
                        if pd.notna(price_value) and str(price_value).strip() not in ['', 'nan', 'none']:
                            price = float(price_value)
                        else:
                            price = 0
                    except (ValueError, TypeError):
                        price = 0
                    
                    # معالجة الكمية بشكل آمن
                    try:
                        quantity_value = row.get('الكمية', '')
                        if pd.notna(quantity_value) and str(quantity_value).strip() not in ['', 'nan', 'none']:
                            quantity = float(quantity_value)
                        else:
                            quantity = 0
                    except (ValueError, TypeError):
                        quantity = 0
                    
                    # الوصف
                    description = str(row.get('الوصف', '')).strip() if pd.notna(row.get('الوصف')) else ''
                    
                    # الحد الأدنى للمخزون
                    try:
                        min_stock_value = str(row.get('الحد الأدنى', 0)).strip() if pd.notna(row.get('الحد الأدنى')) else '0'
                        minimum_stock = int(float(min_stock_value)) if min_stock_value and min_stock_value.lower() not in ['', 'nan', 'none'] else 0
                    except (ValueError, TypeError):
                        minimum_stock = 0
                    
                    # العملة والوحدة
                    currency = str(row.get('العملة', 'EGP')).strip().upper()
                    if currency not in ['EGP', 'USD', 'EUR']:
                        currency = 'EGP'
                    unit = str(row.get('الوحدة', 'piece')).strip() or 'piece'
                    
                    # التحقق من البيانات الأساسية
                    # للمنتجات الموجودة: يمكن ترك الاسم فارغاً (لتحديث حقول أخرى فقط)
                    # للمنتجات الجديدة: الاسم مطلوب
                    is_existing_product = False
                    actual_code = code  # الكود الفعلي الذي سيُستخدم
                    
                    if code:
                        # محاولة البحث بالكود كما هو
                        is_existing_product = Product.objects.filter(code=code).exists()
                        
                        # إذا لم يُعثر عليه، جرب مع الأصفار البادئة
                        if not is_existing_product and code.isdigit():
                            # تجربة أطوال مختلفة (من طول الكود+1 حتى 15)
                            max_length = max(len(code) + 5, 15)
                            for padding in range(len(code) + 1, max_length + 1):
                                padded_code = code.zfill(padding)
                                if Product.objects.filter(code=padded_code).exists():
                                    is_existing_product = True
                                    actual_code = padded_code  # استخدم الكود المبطن
                                    logger.info(f"✅ تم العثور على المنتج: {code} -> {padded_code}")
                                    break
                    
                    # إذا كان منتج جديد بدون اسم، رفض
                    if not is_existing_product and not name:
                        stats['errors'] += 1
                        errors_batch.append(BulkUploadError(
                            upload_log=upload_log,
                            row_number=idx + 2,
                            error_type='missing_data',
                            result_status='failed',
                            error_message='منتج جديد يتطلب اسم',
                            row_data=row.to_dict()
                        ))
                        continue
                    
                    # التحقق من السعر - فقط للمنتجات الجديدة
                    # إذا كان منتج جديد بدون سعر، رفض
                    if not is_existing_product and price <= 0:
                        stats['errors'] += 1
                        errors_batch.append(BulkUploadError(
                            upload_log=upload_log,
                            row_number=idx + 2,
                            error_type='missing_data',
                            result_status='failed',
                            error_message='منتج جديد يتطلب سعر صحيح (> 0)',
                            row_data=row.to_dict()
                        ))
                        continue
                    
                    # الفئة
                    cat_name = str(row.get('الفئة', '')).strip()
                    category = None
                    if cat_name:
                        if cat_name in categories_cache:
                            category = categories_cache[cat_name]
                        else:
                            category = Category.objects.create(name=cat_name)
                            categories_cache[cat_name] = category
                    
                    # المستودع المستهدف
                    wh_name = str(row.get('المستودع', '')).strip()
                    target_wh = warehouse  # من صفحة الرفع
                    
                    # إذا تم تحديد مستودع في الملف، استخدمه
                    if wh_name:
                        if wh_name in warehouses_cache:
                            target_wh = warehouses_cache[wh_name]
                        else:
                            # إنشاء/الحصول على المستودع
                            from .views_bulk import get_or_create_warehouse
                            target_wh = get_or_create_warehouse(wh_name, user)
                            if target_wh:
                                warehouses_cache[wh_name] = target_wh
                            else:
                                raise ValueError(f'فشل في إنشاء/الحصول على المستودع: {wh_name}')
                    
                    # استخدام المنطق الذكي مع جميع البيانات
                    product_data = {
                        'name': name,
                        'code': actual_code,  # استخدام الكود الفعلي (المبطن إذا لزم الأمر)
                        'price': price,
                        'category': category,
                        'quantity': quantity,
                        'description': description,
                        'minimum_stock': minimum_stock,
                        'currency': currency,
                        'unit': unit
                    }
                    
                    result = smart_update_product(product_data, target_wh, user, upload_mode)
                    
                    # تحديث الإحصائيات
                    if result['action'] == 'created':
                        stats['created'] += 1
                    elif result['action'] == 'updated':
                        stats['updated'] += 1
                    elif result['action'] == 'moved':
                        stats['moved'] += 1
                        stats['updated'] += 1
                    elif result['action'] == 'skipped':
                        stats['skipped'] += 1
                        errors_batch.append(BulkUploadError(
                            upload_log=upload_log,
                            row_number=idx + 2,
                            error_type='duplicate',
                            result_status='skipped',
                            error_message=result['message'],
                            row_data=row.to_dict()
                        ))
                    
                    # تتبع تحديثات أوامر التقطيع
                    if 'cutting_orders_updated' in result:
                        stats['cutting_updated'] += result['cutting_orders_updated']
                    if 'cutting_orders_split' in result:
                        stats['cutting_split'] += result['cutting_orders_split']
                
                except Exception as e:
                    logger.error(f"خطأ صف {idx + 2}: {e}")
                    stats['errors'] += 1
                    errors_batch.append(BulkUploadError(
                        upload_log=upload_log,
                        row_number=idx + 2,
                        error_type='processing',
                        result_status='failed',
                        error_message=str(e),
                        row_data=row.to_dict() if hasattr(row, 'to_dict') else {}
                    ))
            
            # حفظ الأخطاء بالدفعة (أسرع)
            if errors_batch:
                BulkUploadError.objects.bulk_create(errors_batch, batch_size=500)
                errors_batch = []
            
            # تحديث التقدم - فقط كل 5% لتقليل العمليات
            processed = batch_end
            percent = int((processed / total) * 100)
            
            if percent >= last_progress_update + 5 or processed == total:
                upload_log.processed_count = processed
                upload_log.created_count = stats['created']
                upload_log.updated_count = stats['updated']
                upload_log.skipped_count = stats['skipped']
                upload_log.error_count = stats['errors']
                upload_log.save(update_fields=[
                    'processed_count', 'created_count', 'updated_count',
                    'skipped_count', 'error_count'
                ])
                
                # تحديث حالة المهمة
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'current': processed,
                        'total': total,
                        'percent': percent,
                        'created': stats['created'],
                        'updated': stats['updated'],
                        'skipped': stats['skipped'],
                        'errors': stats['errors'],
                        'speed': int(processed / max(1, (timezone.now().timestamp() - upload_log.created_at.timestamp())))
                    }
                )
                
                logger.info(f"⚡ {percent}% - {processed}/{total}")
                last_progress_update = percent
        
        # إكمال
        summary_parts = []
        if stats['created'] > 0:
            summary_parts.append(f"✅ {stats['created']} منتج جديد")
        if stats['updated'] > 0:
            summary_parts.append(f"🔄 {stats['updated']} محدث")
        if stats['moved'] > 0:
            summary_parts.append(f"📦 {stats['moved']} نُقل للمستودع الصحيح")
        if stats['cutting_updated'] > 0:
            summary_parts.append(f"🔪 {stats['cutting_updated']} أمر تقطيع محدث")
        if stats['cutting_split'] > 0:
            summary_parts.append(f"🔀 {stats['cutting_split']} أمر تقطيع منقسم")
        if stats['skipped'] > 0:
            summary_parts.append(f"⏭️ {stats['skipped']} متخطى")
        if stats['errors'] > 0:
            summary_parts.append(f"❌ {stats['errors']} خطأ")
        
        summary = " | ".join(summary_parts) if summary_parts else "لا توجد بيانات"
        
        upload_log.complete(summary=summary)
        
        logger.info("🎉 اكتمل الرفع بنجاح!")
        
        # حذف المستودعات الفارغة إذا طُلب ذلك
        deleted_warehouses = []
        if auto_delete_empty:
            logger.info("🗑️ بدء حذف المستودعات الفارغة...")
            delete_result = delete_empty_warehouses(user)
            deleted_warehouses = delete_result.get('warehouses', [])
            
            if deleted_warehouses:
                logger.info(f"✅ تم حذف {len(deleted_warehouses)} مستودع: {', '.join(deleted_warehouses)}")
                upload_log.summary = summary + f" | 🗑️ حُذف {len(deleted_warehouses)} مستودع فارغ"
                upload_log.save(update_fields=['summary'])
        
        return {
            'status': 'success',
            'stats': stats,
            'upload_log_id': upload_log_id,
            'deleted_warehouses': deleted_warehouses
        }
    
    except Exception as e:
        logger.error(f"💥 خطأ كارثي: {e}")
        upload_log.fail(error_message=str(e))
        raise
