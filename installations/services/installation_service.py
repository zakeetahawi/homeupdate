from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
from ..models import InstallationSchedule, InstallationTeam, InstallationArchive


class InstallationService:
    """خدمة إدارة التركيبات"""
    
    @staticmethod
    def get_dashboard_stats():
        """الحصول على إحصائيات لوحة التحكم"""
        today = timezone.now().date()
        
        return {
            'total': InstallationSchedule.objects.count(),
            'pending': InstallationSchedule.objects.filter(status='pending').count(),
            'scheduled': InstallationSchedule.objects.filter(status='scheduled').count(),
            'in_progress': InstallationSchedule.objects.filter(status='in_progress').count(),
            'completed': InstallationSchedule.objects.filter(status='completed').count(),
            'today': InstallationSchedule.objects.filter(scheduled_date=today).count(),
        }
    
    @staticmethod
    def get_today_installations():
        """الحصول على تركيبات اليوم"""
        today = timezone.now().date()
        return InstallationSchedule.objects.filter(
            scheduled_date=today,
            status__in=['scheduled', 'in_progress']
        ).select_related('order', 'order__customer', 'team').order_by('scheduled_time')
    
    @staticmethod
    def get_upcoming_installations(limit=10):
        """الحصول على التركيبات القادمة"""
        today = timezone.now().date()
        return InstallationSchedule.objects.filter(
            scheduled_date__gt=today,
            status='scheduled'
        ).select_related('order', 'order__customer', 'team').order_by('scheduled_date', 'scheduled_time')[:limit]
    
    @staticmethod
    def get_team_stats():
        """الحصول على إحصائيات الفرق"""
        return InstallationTeam.objects.filter(is_active=True).annotate(
            installations_count=Count('installationschedule')
        )
    
    @staticmethod
    def schedule_installation(installation_id, team_id, scheduled_date, scheduled_time, notes=None):
        """جدولة تركيب"""
        try:
            installation = InstallationSchedule.objects.get(id=installation_id)
            team = InstallationTeam.objects.get(id=team_id)
            
            installation.team = team
            installation.scheduled_date = scheduled_date
            installation.scheduled_time = scheduled_time
            installation.status = 'scheduled'
            if notes:
                installation.notes = notes
            installation.save()
            
            return True, "تم جدولة التركيب بنجاح"
        except InstallationSchedule.DoesNotExist:
            return False, "التركيب غير موجود"
        except InstallationTeam.DoesNotExist:
            return False, "الفريق غير موجود"
        except Exception as e:
            return False, f"حدث خطأ: {str(e)}"
    
    @staticmethod
    def update_installation_status(installation_id, new_status):
        """تحديث حالة التركيب"""
        try:
            installation = InstallationSchedule.objects.get(id=installation_id)
            installation.status = new_status
            installation.save()
            
            # إذا تم إكمال التركيب، إنشاء أرشيف
            if new_status == 'completed':
                InstallationArchive.objects.get_or_create(
                    installation=installation
                )
            
            return True, "تم تحديث الحالة بنجاح"
        except InstallationSchedule.DoesNotExist:
            return False, "التركيب غير موجود"
        except Exception as e:
            return False, f"حدث خطأ: {str(e)}"
    
    @staticmethod
    def get_daily_schedule(date, team_id=None):
        """الحصول على الجدول اليومي"""
        installations = InstallationSchedule.objects.filter(
            scheduled_date=date,
            status__in=['scheduled', 'in_progress']
        ).select_related('order', 'order__customer', 'team')
        
        if team_id:
            installations = installations.filter(team_id=team_id)
        
        return installations.order_by('scheduled_time')
    
    @staticmethod
    def search_installations(query, filters=None):
        """البحث في التركيبات"""
        installations = InstallationSchedule.objects.select_related(
            'order', 'order__customer', 'team'
        )
        
        if query:
            installations = installations.filter(
                Q(order__order_number__icontains=query) |
                Q(order__customer__name__icontains=query) |
                Q(order__customer__phone__icontains=query)
            )
        
        if filters:
            if filters.get('status'):
                installations = installations.filter(status=filters['status'])
            if filters.get('team'):
                installations = installations.filter(team=filters['team'])
            if filters.get('date_from'):
                installations = installations.filter(scheduled_date__gte=filters['date_from'])
            if filters.get('date_to'):
                installations = installations.filter(scheduled_date__lte=filters['date_to'])
        
        return installations.order_by('-created_at')
    
    @staticmethod
    def get_archived_installations():
        """الحصول على التركيبات المؤرشفة"""
        return InstallationArchive.objects.select_related(
            'installation', 'installation__order', 'installation__order__customer'
        ).order_by('-completion_date')
    
    @staticmethod
    def auto_schedule_installations():
        """الجدولة التلقائية للتركيبات"""
        # خوارزمية بسيطة للجدولة التلقائية
        pending_installations = InstallationSchedule.objects.filter(
            status='pending'
        ).select_related('order', 'order__customer')
        
        available_teams = InstallationTeam.objects.filter(is_active=True)
        
        if not available_teams.exists():
            return False, "لا توجد فرق متاحة"
        
        today = timezone.now().date()
        current_time = timezone.now().time()
        
        for installation in pending_installations:
            # تخصيص فريق عشوائي (يمكن تحسين هذه الخوارزمية)
            team = available_teams.first()
            
            # جدولة في اليوم التالي في الساعة 9 صباحاً
            tomorrow = today + timedelta(days=1)
            scheduled_time = datetime.strptime('09:00', '%H:%M').time()
            
            installation.team = team
            installation.scheduled_date = tomorrow
            installation.scheduled_time = scheduled_time
            installation.status = 'scheduled'
            installation.save()
        
        return True, f"تم جدولة {pending_installations.count()} تركيب تلقائياً" 