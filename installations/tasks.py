"""
مهام Celery لإدارة المديونيات
"""

import logging

from celery import shared_task
from django.core.management import call_command
from django.db.models import F, Sum
from django.utils import timezone

from orders.models import Order

from .models import CustomerDebt

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="sync_customer_debts")
def sync_customer_debts_task(self):
    """
    مهمة مزامنة المديونيات مع الطلبات
    تعمل كل ساعة لضمان دقة البيانات
    """
    try:
        logger.info("🔄 بدء مزامنة المديونيات...")

        # تشغيل أمر المزامنة
        call_command("sync_debts", verbosity=0)

        # الحصول على إحصائيات محدثة
        stats = {
            "total_debts": CustomerDebt.objects.filter(is_paid=False).count(),
            "total_amount": CustomerDebt.objects.filter(is_paid=False).aggregate(
                total=Sum("debt_amount")
            )["total"]
            or 0,
            "sync_time": timezone.now().isoformat(),
        }

        logger.info(
            f"✅ تمت مزامنة المديونيات - {stats['total_debts']} مديونية بمبلغ {stats['total_amount']:.2f} ج.م"
        )

        return {
            "status": "success",
            "message": "تمت مزامنة المديونيات بنجاح",
            "stats": stats,
        }

    except Exception as e:
        logger.error(f"❌ خطأ في مزامنة المديونيات: {str(e)}")
        return {"status": "error", "message": f"خطأ في مزامنة المديونيات: {str(e)}"}


@shared_task(bind=True, name="create_debt_records")
def create_debt_records_task(self):
    """
    مهمة إنشاء سجلات المديونيات للطلبات الجديدة
    تعمل كل 30 دقيقة
    """
    try:
        logger.info("📝 بدء إنشاء سجلات المديونيات...")

        # البحث عن الطلبات التي عليها مديونية وليس لها سجل
        debt_orders = (
            Order.objects.filter(total_amount__gt=F("paid_amount"))
            .annotate(debt_amount=F("total_amount") - F("paid_amount"))
            .exclude(customerdebt__isnull=False)
        )

        created_count = 0
        for order in debt_orders:
            debt_amount = float(order.debt_amount)

            CustomerDebt.objects.create(
                customer=order.customer,
                order=order,
                debt_amount=debt_amount,
                notes=f"مديونية تلقائية للطلب {order.order_number} - مهمة دورية",
                is_paid=False,
            )
            created_count += 1

        logger.info(f"✅ تم إنشاء {created_count} سجل مديونية جديد")

        return {
            "status": "success",
            "message": f"تم إنشاء {created_count} سجل مديونية",
            "created_count": created_count,
        }

    except Exception as e:
        logger.error(f"❌ خطأ في إنشاء سجلات المديونيات: {str(e)}")
        return {
            "status": "error",
            "message": f"خطأ في إنشاء سجلات المديونيات: {str(e)}",
        }


@shared_task(bind=True, name="update_overdue_debts")
def update_overdue_debts_task(self):
    """
    مهمة تحديث المديونيات المتأخرة
    تعمل يومياً في منتصف الليل
    """
    try:
        logger.info("⏰ بدء تحديث المديونيات المتأخرة...")

        # تحديد المديونيات المتأخرة (أكثر من 30 يوم)
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        overdue_debts = CustomerDebt.objects.filter(
            is_paid=False, created_at__lt=thirty_days_ago
        )

        overdue_count = overdue_debts.count()
        total_overdue_amount = (
            overdue_debts.aggregate(total=Sum("debt_amount"))["total"] or 0
        )

        # يمكن إضافة إشعارات أو إجراءات أخرى هنا

        logger.info(
            f"⚠️ تم العثور على {overdue_count} مديونية متأخرة بمبلغ {total_overdue_amount:.2f} ج.م"
        )

        return {
            "status": "success",
            "message": f"تم تحديث {overdue_count} مديونية متأخرة",
            "overdue_count": overdue_count,
            "total_overdue_amount": float(total_overdue_amount),
        }

    except Exception as e:
        logger.error(f"❌ خطأ في تحديث المديونيات المتأخرة: {str(e)}")
        return {
            "status": "error",
            "message": f"خطأ في تحديث المديونيات المتأخرة: {str(e)}",
        }


@shared_task(bind=True, name="generate_debt_report")
def generate_debt_report_task(self):
    """
    مهمة إنشاء تقرير المديونيات الأسبوعي
    تعمل كل أسبوع يوم الأحد
    """
    try:
        logger.info("📊 بدء إنشاء تقرير المديونيات...")

        # إحصائيات شاملة
        total_debts = CustomerDebt.objects.filter(is_paid=False).count()
        total_amount = (
            CustomerDebt.objects.filter(is_paid=False).aggregate(
                total=Sum("debt_amount")
            )["total"]
            or 0
        )

        # المديونيات المتأخرة
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        overdue_count = CustomerDebt.objects.filter(
            is_paid=False, created_at__lt=thirty_days_ago
        ).count()

        # المديونيات المدفوعة هذا الأسبوع
        week_ago = timezone.now() - timezone.timedelta(days=7)
        paid_this_week = CustomerDebt.objects.filter(
            is_paid=True, payment_date__gte=week_ago
        ).count()

        report_data = {
            "total_debts": total_debts,
            "total_amount": float(total_amount),
            "overdue_count": overdue_count,
            "paid_this_week": paid_this_week,
            "report_date": timezone.now().isoformat(),
        }

        logger.info(
            f"📈 تقرير المديونيات: {total_debts} مديونية، {total_amount:.2f} ج.م، {overdue_count} متأخرة"
        )

        return {
            "status": "success",
            "message": "تم إنشاء تقرير المديونيات",
            "report": report_data,
        }

    except Exception as e:
        logger.error(f"❌ خطأ في إنشاء تقرير المديونيات: {str(e)}")
        return {
            "status": "error",
            "message": f"خطأ في إنشاء تقرير المديونيات: {str(e)}",
        }
