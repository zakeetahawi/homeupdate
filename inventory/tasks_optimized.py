"""
مهام Celery المحسّنة للمخزون - نظام ذكي يمنع التكرارات
"""

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
import logging
import pandas as pd
from io import BytesIO

User = get_user_model()
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
    from .models import (BulkUploadLog, Product, Category, Warehouse, 
                         StockTransaction, BulkUploadError)
    from .smart_upload_logic import (smart_update_product, clean_start_reset,
                                     add_stock_transaction, delete_empty_warehouses)
    
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
        upload_log.total_rows = total
        upload_log.save(update_fields=['total_rows'])
        
        logger.info(f"📋 {total} صف للمعالجة")
        
        # تهيئة كاملة إذا طُلب
        if upload_mode == 'clean_start':
            logger.warning("⚠️ وضع المسح الكامل")
            reset_stats = clean_start_reset()
            upload_log.summary = f"مسح كامل: {reset_stats['deleted_products']} منتج، {reset_stats['deleted_transactions']} معاملة"
            upload_log.save(update_fields=['summary'])
        
        # تنظيف البيانات
        df = df.dropna(subset=['اسم المنتج', 'السعر']).fillna('')
        
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
        
        # معالجة بدفعات سريعة
        batch_size = 100
        errors_batch = []  # لحفظ الأخطاء بالدفعة
        
        for batch_start in range(0, len(df), batch_size):
            batch_end = min(batch_start + batch_size, len(df))
            batch = df.iloc[batch_start:batch_end]
            
            with transaction.atomic():
                for idx, row in batch.iterrows():
                    try:
                        # استخراج البيانات
                        name = str(row['اسم المنتج']).strip()
                        code = str(row.get('الكود', '')).strip() or None
                        price = float(row['السعر']) if row['السعر'] else 0
                        quantity = float(row.get('الكمية', 0)) if pd.notna(row.get('الكمية')) else 0
                        
                        if not name or price <= 0:
                            stats['errors'] += 1
                            errors_batch.append(BulkUploadError(
                                upload_log=upload_log,
                                row_number=idx + 2,
                                error_type='missing_data',
                                result_status='failed',
                                error_message='اسم المنتج أو السعر مفقود أو غير صالح',
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
                        target_wh = warehouse
                        
                        if wh_name:
                            if wh_name in warehouses_cache:
                                target_wh = warehouses_cache[wh_name]
                            else:
                                target_wh = Warehouse.objects.create(
                                    name=wh_name,
                                    code=f"WH{len(warehouses_cache)+1:03d}",
                                    is_active=True,
                                    created_by=user
                                )
                                warehouses_cache[wh_name] = target_wh
                        
                        # استخدام المنطق الذكي
                        product_data = {
                            'name': name,
                            'code': code,
                            'price': price,
                            'category': category,
                            'quantity': quantity,
                            'currency': row.get('العملة', 'EGP'),
                            'unit': row.get('الوحدة', 'piece')
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
                        
                        # تتبع تحديثات أوامر التقطيع 🔥
                        if 'cutting_orders_updated' in result:
                            stats['cutting_updated'] += result['cutting_orders_updated']
                        if 'cutting_orders_split' in result:
                            stats['cutting_split'] += result['cutting_orders_split']
                        
                        # إضافة الكمية إذا كانت موجودة (فقط إذا لم يتم النقل)
                        if quantity > 0 and result['product'] and target_wh and result['action'] != 'moved':
                            add_stock_transaction(result['product'], target_wh, quantity, user, 'رفع من Excel')
                    
                    except Exception as e:
                        logger.error(f"خطأ صف {idx}: {e}")
                        stats['errors'] += 1
                        errors_batch.append(BulkUploadError(
                            upload_log=upload_log,
                            row_number=idx + 2,
                            error_type='processing',
                            result_status='failed',
                            error_message=str(e),
                            row_data=row.to_dict() if hasattr(row, 'to_dict') else {}
                        ))
            
            # حفظ الأخطاء بالدفعة
            if errors_batch:
                BulkUploadError.objects.bulk_create(errors_batch)
                errors_batch = []
            
            # تحديث التقدم
            processed = batch_end
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
            percent = int((processed / total) * 100)
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': processed,
                    'total': total,
                    'percent': percent,
                    'created': stats['created'],
                    'updated': stats['updated'],
                    'skipped': stats['skipped'],
                    'errors': stats['errors']
                }
            )
            
            logger.info(f"✅ {percent}% - {processed}/{total}")
        
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
