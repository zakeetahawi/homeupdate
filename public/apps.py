from django.apps import AppConfig


class PublicConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "public"
    verbose_name = "الصفحات العامة"

    def ready(self):
        """Register signals for automatic product pipeline + Cloudflare sync"""
        from django.db.models.signals import post_delete, post_save

        from inventory.models import BaseProduct, Product

        from . import signals

        # ===== Product (النظام القديم) =====
        # عند حفظ منتج: ترحيل تلقائي + QR + مزامنة Cloudflare
        post_save.connect(
            self._on_product_save,
            sender=Product,
            dispatch_uid="auto_pipeline_product_save",
        )

        # عند حذف منتج: حذف من Cloudflare
        post_delete.connect(
            self._on_product_delete,
            sender=Product,
            dispatch_uid="auto_pipeline_product_delete",
        )

        # ===== BaseProduct (النظام الجديد) =====
        # عند تعديل BaseProduct مباشرة: مزامنة Cloudflare
        post_save.connect(
            self._on_base_product_save,
            sender=BaseProduct,
            dispatch_uid="auto_pipeline_base_product_save",
        )

    def _on_product_save(self, sender, instance, created, **kwargs):
        """
        عند حفظ منتج في النظام القديم:
        1. ترحيل تلقائي (إنشاء BaseProduct + ProductVariant)
        2. توليد QR
        3. مزامنة Cloudflare
        كل شيء يتم في الخلفية بدون تأثير على الأداء
        """
        # تخطي إذا كان Pipeline معطل (أثناء الرفع الجماعي مثلاً)
        if getattr(instance, "_skip_auto_pipeline", False):
            return

        if instance.code:
            from django.db import transaction

            update_fields = kwargs.get("update_fields")

            transaction.on_commit(
                lambda: self._trigger_product_pipeline(
                    instance.pk, created, update_fields
                )
            )

    def _trigger_product_pipeline(self, product_id, created, update_fields):
        """تشغيل خط الإنتاج التلقائي"""
        try:
            from inventory.auto_product_pipeline import on_product_saved

            on_product_saved(
                product_id,
                created=created,
                update_fields=update_fields,
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Auto pipeline trigger error: {e}")

    def _on_product_delete(self, sender, instance, **kwargs):
        """Handle product delete - remove from Cloudflare"""
        if instance.code:
            try:
                from inventory.auto_product_pipeline import on_product_deleted

                on_product_deleted(instance.code)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Auto pipeline delete error: {e}")

    def _on_base_product_save(self, sender, instance, created, **kwargs):
        """
        عند حفظ BaseProduct مباشرة (من الأدمن أو البرمجة):
        مزامنة Cloudflare تلقائياً
        """
        # تخطي إذا كان Pipeline معطل
        if getattr(instance, "_skip_auto_pipeline", False):
            return
        # تخطي أثناء الترحيل (سيتم بعدها)
        if getattr(instance, "_skip_cloudflare_sync", False):
            return

        if instance.code and instance.is_active:
            from django.db import transaction

            update_fields = kwargs.get("update_fields")
            bp_id = instance.pk

            transaction.on_commit(
                lambda: self._trigger_base_product_sync(bp_id, update_fields)
            )

    def _trigger_base_product_sync(self, base_product_id, update_fields):
        """تشغيل مزامنة BaseProduct"""
        try:
            from inventory.auto_product_pipeline import on_base_product_saved

            on_base_product_saved(base_product_id, update_fields=update_fields)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"BaseProduct sync trigger error: {e}")
