from decimal import Decimal

from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from installations.models import InstallationSchedule

from .models import InstallationAccountingSettings, InstallationCard, TechnicianShare


@receiver(post_save, sender=InstallationSchedule)
def create_installation_accounting_card(sender, instance, created, **kwargs):
    """
    بمجرد تحويل حالة التركيب إلى 'completed' أو 'modification_completed'، يتم إنشاء بطاقة المحاسبة تلقائياً
    """
    if instance.status in ["completed", "modification_completed"]:
        # Create or get card
        card, created = InstallationCard.objects.get_or_create(
            installation_schedule=instance,
            defaults={
                "windows_count": instance.windows_count or 0,
                "completion_date": instance.completion_date or instance.updated_at,
                "status": "new",
            },
        )

        # If not created now, update windows count if it changed
        if not created and instance.windows_count:
            card.windows_count = instance.windows_count
            card.save(update_fields=["windows_count"])

        # Recalculate and create shares
        sync_technician_shares(card)


def sync_technician_shares(card):
    """
    توزيع عدد الشبابيك والمستحقات على الفنيين المذكورين في الجدولة
    """
    installation = card.installation_schedule
    technicians = list(installation.technicians.all())

    if not technicians:
        return

    # Calculate share
    total_windows = Decimal(str(card.windows_count))
    num_techs = Decimal(len(technicians))

    # Check settings for price
    settings = InstallationAccountingSettings.get_settings()

    # للملفات غير المدفوعة، نستخدم السعر الحالي من الإعدادات دائماً
    if card.status != "paid":
        price_per_window = settings.default_price_per_window
        card.price_per_window = price_per_window
        card.total_cost = total_windows * price_per_window
        card.save(update_fields=["price_per_window", "total_cost"])
    else:
        price_per_window = card.price_per_window or settings.default_price_per_window

    share_windows = total_windows / num_techs
    share_amount = (total_windows * price_per_window) / num_techs

    # Update or create shares for existing technicians
    existing_tech_ids = []
    for tech in technicians:
        share, created = TechnicianShare.objects.update_or_create(
            card=card,
            technician=tech,
            defaults={"assigned_windows": share_windows, "amount": share_amount},
        )
        existing_tech_ids.append(tech.id)

    # Remove shares for technicians no longer in the list (if they haven't been paid)
    TechnicianShare.objects.filter(card=card, is_paid=False).exclude(
        technician_id__in=existing_tech_ids
    ).delete()


@receiver(m2m_changed, sender=InstallationSchedule.technicians.through)
def update_shares_on_tech_change(sender, instance, action, **kwargs):
    """
    تحديث الحصص إذا تغير قائمة الفنيين في الجدولة
    """
    if action in ["post_add", "post_remove", "post_clear"]:
        if hasattr(instance, "accounting_card"):
            sync_technician_shares(instance.accounting_card)


@receiver(post_save, sender=InstallationAccountingSettings)
def update_all_unpaid_cards_price(sender, instance, **kwargs):
    """
    تحديث جميع البطاقات غير المدفوعة عند تغيير سعر الشباك الافتراضي في الإعدادات
    """
    cards = InstallationCard.objects.exclude(status="paid")
    for card in cards:
        sync_technician_shares(card)
