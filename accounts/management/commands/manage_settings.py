from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from accounts.models import UnifiedSystemSettings
import json


class Command(BaseCommand):
    help = 'إدارة إعدادات النظام الموحدة'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['list', 'create', 'update', 'delete', 'duplicate', 'reset', 'export'],
            help='الإجراء المطلوب'
        )
        parser.add_argument(
            '--id',
            type=int,
            help='معرف الإعدادات'
        )
        parser.add_argument(
            '--name',
            type=str,
            help='اسم الشركة'
        )
        parser.add_argument(
            '--phone',
            type=str,
            help='رقم الهاتف'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='البريد الإلكتروني'
        )
        parser.add_argument(
            '--currency',
            type=str,
            choices=['SAR', 'EGP', 'USD', 'EUR', 'AED', 'KWD', 'QAR', 'BHD', 'OMR'],
            help='العملة'
        )
        parser.add_argument(
            '--file',
            type=str,
            help='ملف JSON للاستيراد/التصدير'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'list':
            self.list_settings()
        elif action == 'create':
            self.create_settings(options)
        elif action == 'update':
            self.update_settings(options)
        elif action == 'delete':
            self.delete_settings(options)
        elif action == 'duplicate':
            self.duplicate_settings(options)
        elif action == 'reset':
            self.reset_settings(options)
        elif action == 'export':
            self.export_settings(options)

    def list_settings(self):
        """عرض جميع الإعدادات"""
        settings = UnifiedSystemSettings.objects.all()
        
        if not settings.exists():
            self.stdout.write(
                self.style.WARNING('لا توجد إعدادات في النظام')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(f'تم العثور على {settings.count()} إعدادات:')
        )
        
        for setting in settings:
            self.stdout.write(
                f'ID: {setting.id} | '
                f'الشركة: {setting.company_name} | '
                f'الهاتف: {setting.company_phone} | '
                f'العملة: {setting.currency} | '
                f'تاريخ الإنشاء: {setting.created_at.strftime("%Y-%m-%d %H:%M")}'
            )

    def create_settings(self, options):
        """إنشاء إعدادات جديدة"""
        try:
            settings = UnifiedSystemSettings.objects.create(
                company_name=options.get('name', 'شركة جديدة'),
                company_phone=options.get('phone', ''),
                company_email=options.get('email', ''),
                currency=options.get('currency', 'SAR')
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'تم إنشاء إعدادات جديدة برقم: {settings.id}')
            )
        except Exception as e:
            raise CommandError(f'خطأ في إنشاء الإعدادات: {str(e)}')

    def update_settings(self, options):
        """تحديث الإعدادات"""
        setting_id = options.get('id')
        if not setting_id:
            raise CommandError('يجب تحديد معرف الإعدادات باستخدام --id')
        
        try:
            settings = UnifiedSystemSettings.objects.get(id=setting_id)
            
            if options.get('name'):
                settings.company_name = options['name']
            if options.get('phone'):
                settings.company_phone = options['phone']
            if options.get('email'):
                settings.company_email = options['email']
            if options.get('currency'):
                settings.currency = options['currency']
            
            settings.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'تم تحديث الإعدادات برقم: {settings.id}')
            )
        except UnifiedSystemSettings.DoesNotExist:
            raise CommandError(f'الإعدادات برقم {setting_id} غير موجودة')
        except Exception as e:
            raise CommandError(f'خطأ في تحديث الإعدادات: {str(e)}')

    def delete_settings(self, options):
        """حذف الإعدادات"""
        setting_id = options.get('id')
        if not setting_id:
            raise CommandError('يجب تحديد معرف الإعدادات باستخدام --id')
        
        try:
            settings = UnifiedSystemSettings.objects.get(id=setting_id)
            company_name = settings.company_name
            settings.delete()
            
            self.stdout.write(
                self.style.SUCCESS(f'تم حذف إعدادات الشركة: {company_name}')
            )
        except UnifiedSystemSettings.DoesNotExist:
            raise CommandError(f'الإعدادات برقم {setting_id} غير موجودة')
        except Exception as e:
            raise CommandError(f'خطأ في حذف الإعدادات: {str(e)}')

    def duplicate_settings(self, options):
        """تكرار الإعدادات"""
        setting_id = options.get('id')
        if not setting_id:
            raise CommandError('يجب تحديد معرف الإعدادات باستخدام --id')
        
        try:
            original = UnifiedSystemSettings.objects.get(id=setting_id)
            
            # إنشاء نسخة جديدة
            new_settings = UnifiedSystemSettings.objects.create(
                company_name=f"{original.company_name} - نسخة",
                company_logo=original.company_logo,
                company_address=original.company_address,
                company_phone=original.company_phone,
                company_email=original.company_email,
                company_website=original.company_website,
                working_hours=original.working_hours,
                about_text=original.about_text,
                vision_text=original.vision_text,
                mission_text=original.mission_text,
                description=original.description,
                tax_number=original.tax_number,
                commercial_register=original.commercial_register,
                facebook_url=original.facebook_url,
                twitter_url=original.twitter_url,
                instagram_url=original.instagram_url,
                linkedin_url=original.linkedin_url,
                social_links=original.social_links,
                currency=original.currency,
                enable_notifications=original.enable_notifications,
                enable_email_notifications=original.enable_email_notifications,
                items_per_page=original.items_per_page,
                low_stock_threshold=original.low_stock_threshold,
                enable_analytics=original.enable_analytics,
                primary_color=original.primary_color,
                secondary_color=original.secondary_color,
                accent_color=original.accent_color,
                default_theme=original.default_theme,
                copyright_text=original.copyright_text,
                maintenance_mode=original.maintenance_mode,
                maintenance_message=original.maintenance_message
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'تم تكرار الإعدادات برقم: {new_settings.id}')
            )
        except UnifiedSystemSettings.DoesNotExist:
            raise CommandError(f'الإعدادات برقم {setting_id} غير موجودة')
        except Exception as e:
            raise CommandError(f'خطأ في تكرار الإعدادات: {str(e)}')

    def reset_settings(self, options):
        """إعادة تعيين الإعدادات إلى القيم الافتراضية"""
        setting_id = options.get('id')
        if not setting_id:
            raise CommandError('يجب تحديد معرف الإعدادات باستخدام --id')
        
        try:
            settings = UnifiedSystemSettings.objects.get(id=setting_id)
            
            # إعادة تعيين إلى القيم الافتراضية
            settings.company_name = 'Elkhawaga'
            settings.company_phone = ''
            settings.company_email = ''
            settings.company_website = ''
            settings.working_hours = ''
            settings.about_text = ''
            settings.vision_text = ''
            settings.mission_text = ''
            settings.description = ''
            settings.tax_number = ''
            settings.commercial_register = ''
            settings.facebook_url = ''
            settings.twitter_url = ''
            settings.instagram_url = ''
            settings.linkedin_url = ''
            settings.social_links = None
            settings.currency = 'SAR'
            settings.enable_notifications = True
            settings.enable_email_notifications = False
            settings.items_per_page = 20
            settings.low_stock_threshold = 20
            settings.enable_analytics = True
            settings.primary_color = ''
            settings.secondary_color = ''
            settings.accent_color = ''
            settings.default_theme = 'default'
            settings.copyright_text = 'جميع الحقوق محفوظة لشركة الخواجة للستائر والمفروشات تطوير zakee tahawi'
            settings.maintenance_mode = False
            settings.maintenance_message = ''
            
            settings.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'تم إعادة تعيين الإعدادات برقم: {settings.id}')
            )
        except UnifiedSystemSettings.DoesNotExist:
            raise CommandError(f'الإعدادات برقم {setting_id} غير موجودة')
        except Exception as e:
            raise CommandError(f'خطأ في إعادة تعيين الإعدادات: {str(e)}')

    def export_settings(self, options):
        """تصدير الإعدادات إلى ملف JSON"""
        setting_id = options.get('id')
        file_path = options.get('file', 'settings_export.json')
        
        try:
            if setting_id:
                settings = UnifiedSystemSettings.objects.get(id=setting_id)
                data = [self.serialize_settings(settings)]
            else:
                settings_list = UnifiedSystemSettings.objects.all()
                data = [self.serialize_settings(s) for s in settings_list]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.stdout.write(
                self.style.SUCCESS(f'تم تصدير الإعدادات إلى: {file_path}')
            )
        except UnifiedSystemSettings.DoesNotExist:
            raise CommandError(f'الإعدادات برقم {setting_id} غير موجودة')
        except Exception as e:
            raise CommandError(f'خطأ في تصدير الإعدادات: {str(e)}')

    def serialize_settings(self, settings):
        """تحويل الإعدادات إلى قاموس"""
        return {
            'id': settings.id,
            'company_name': settings.company_name,
            'company_phone': settings.company_phone,
            'company_email': settings.company_email,
            'company_website': settings.company_website,
            'company_address': settings.company_address,
            'working_hours': settings.working_hours,
            'about_text': settings.about_text,
            'vision_text': settings.vision_text,
            'mission_text': settings.mission_text,
            'description': settings.description,
            'tax_number': settings.tax_number,
            'commercial_register': settings.commercial_register,
            'facebook_url': settings.facebook_url,
            'twitter_url': settings.twitter_url,
            'instagram_url': settings.instagram_url,
            'linkedin_url': settings.linkedin_url,
            'social_links': settings.social_links,
            'currency': settings.currency,
            'enable_notifications': settings.enable_notifications,
            'enable_email_notifications': settings.enable_email_notifications,
            'items_per_page': settings.items_per_page,
            'low_stock_threshold': settings.low_stock_threshold,
            'enable_analytics': settings.enable_analytics,
            'primary_color': settings.primary_color,
            'secondary_color': settings.secondary_color,
            'accent_color': settings.accent_color,
            'default_theme': settings.default_theme,
            'copyright_text': settings.copyright_text,
            'maintenance_mode': settings.maintenance_mode,
            'maintenance_message': settings.maintenance_message,
            'created_at': settings.created_at.isoformat(),
            'updated_at': settings.updated_at.isoformat()
        } 