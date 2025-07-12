from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import CompanyInfo, SystemSettings, UnifiedSystemSettings


class Command(BaseCommand):
    help = 'ترحيل إعدادات النظام إلى النموذج الموحد'

    def handle(self, *args, **options):
        self.stdout.write('بدء ترحيل إعدادات النظام...')
        
        try:
            # التحقق من وجود إعدادات موحدة
            if UnifiedSystemSettings.objects.exists():
                self.stdout.write(
                    self.style.WARNING('الإعدادات الموحدة موجودة بالفعل. سيتم تحديثها.')
                )
                unified_settings = UnifiedSystemSettings.objects.first()
            else:
                self.stdout.write('إنشاء إعدادات موحدة جديدة...')
                unified_settings = UnifiedSystemSettings.objects.create()
            
            # ترحيل CompanyInfo
            company_info = CompanyInfo.objects.first()
            if company_info:
                self.stdout.write('ترحيل معلومات الشركة...')
                unified_settings.company_name = company_info.name
                unified_settings.company_logo = company_info.logo
                unified_settings.company_address = company_info.address
                unified_settings.company_phone = company_info.phone
                unified_settings.company_email = company_info.email
                unified_settings.company_website = company_info.website
                unified_settings.tax_number = company_info.tax_number
                unified_settings.commercial_register = company_info.commercial_register
                unified_settings.working_hours = company_info.working_hours
                unified_settings.about_text = company_info.about
                unified_settings.vision_text = company_info.vision
                unified_settings.mission_text = company_info.mission
                unified_settings.facebook_url = company_info.facebook
                unified_settings.twitter_url = company_info.twitter
                unified_settings.instagram_url = company_info.instagram
                unified_settings.linkedin_url = company_info.linkedin
                unified_settings.primary_color = company_info.primary_color
                unified_settings.secondary_color = company_info.secondary_color
                unified_settings.accent_color = company_info.accent_color
                unified_settings.copyright_text = company_info.copyright_text
                self.stdout.write(
                    self.style.SUCCESS('تم ترحيل معلومات الشركة بنجاح')
                )
            
            # ترحيل SystemSettings
            system_settings = SystemSettings.objects.first()
            if system_settings:
                self.stdout.write('ترحيل إعدادات النظام...')
                unified_settings.currency = system_settings.currency
                unified_settings.enable_notifications = system_settings.enable_notifications
                unified_settings.enable_email_notifications = system_settings.enable_email_notifications
                unified_settings.items_per_page = system_settings.items_per_page
                unified_settings.low_stock_threshold = system_settings.low_stock_threshold
                unified_settings.enable_analytics = system_settings.enable_analytics
                unified_settings.maintenance_mode = system_settings.maintenance_mode
                unified_settings.maintenance_message = system_settings.maintenance_message
                self.stdout.write(
                    self.style.SUCCESS('تم ترحيل إعدادات النظام بنجاح')
                )
            
            # حفظ الإعدادات
            unified_settings.save()
            
            self.stdout.write(
                self.style.SUCCESS('تم ترحيل جميع الإعدادات بنجاح!')
            )
            
            # عرض ملخص الإعدادات
            self.stdout.write('\nملخص الإعدادات المحدثة:')
            self.stdout.write(f'اسم الشركة: {unified_settings.company_name}')
            self.stdout.write(f'العملة: {unified_settings.currency}')
            self.stdout.write(f'تفعيل الإشعارات: {unified_settings.enable_notifications}')
            self.stdout.write(f'عدد العناصر في الصفحة: {unified_settings.items_per_page}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'حدث خطأ أثناء الترحيل: {str(e)}')
            )
            raise 