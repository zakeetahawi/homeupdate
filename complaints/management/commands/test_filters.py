#!/usr/bin/env python3
"""
أداة اختبار شاملة لنظام فلاتر الشكاوى
"""

from django.core.management.base import BaseCommand
from django.http import QueryDict
from complaints.forms import ComplaintFilterForm
from complaints.models import Complaint, ComplaintType
from accounts.models import User, Department
from django.db.models import Q


class Command(BaseCommand):
    help = 'اختبار نظام فلاتر الشكاوى وإصلاح المشاكل'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-form',
            action='store_true',
            help='اختبار نموذج الفلترة'
        )
        parser.add_argument(
            '--test-queries',
            action='store_true',
            help='اختبار استعلامات الفلترة'
        )
        parser.add_argument(
            '--test-all',
            action='store_true',
            help='اختبار جميع الوظائف'
        )
        parser.add_argument(
            '--create-test-data',
            action='store_true',
            help='إنشاء بيانات اختبار'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔍 بدء اختبار نظام فلاتر الشكاوى...')
        )

        if options['create_test_data']:
            self.create_test_data()

        if options['test_form'] or options['test_all']:
            self.test_filter_form()

        if options['test_queries'] or options['test_all']:
            self.test_filter_queries()

        if options['test_all']:
            self.test_complete_filtering()

        self.stdout.write(
            self.style.SUCCESS('✅ انتهى اختبار نظام الفلاتر')
        )

    def create_test_data(self):
        """إنشاء بيانات اختبار للفلاتر"""
        self.stdout.write('📝 إنشاء بيانات اختبار...')
        
        # إحصائيات قبل الإنشاء
        initial_count = Complaint.objects.count()
        self.stdout.write(f'عدد الشكاوى الحالية: {initial_count}')

    def test_filter_form(self):
        """اختبار نموذج الفلترة"""
        self.stdout.write('🧪 اختبار نموذج الفلترة...')

        # اختبار 1: نموذج فارغ
        form = ComplaintFilterForm()
        self.stdout.write(f'✓ النموذج الفارغ صالح: {form.is_valid()}')

        # اختبار 2: بيانات صحيحة
        test_data = QueryDict('status=new&priority=high')
        form = ComplaintFilterForm(test_data)
        is_valid = form.is_valid()
        self.stdout.write(f'✓ النموذج مع بيانات صحيحة: {is_valid}')
        
        if is_valid:
            self.stdout.write('البيانات المنظفة:')
            for field, value in form.cleaned_data.items():
                if value:
                    self.stdout.write(f'  - {field}: {value}')
        else:
            self.stdout.write('أخطاء النموذج:')
            for field, errors in form.errors.items():
                self.stdout.write(f'  - {field}: {errors}')

        # اختبار 3: تواريخ غير صحيحة
        invalid_dates = QueryDict('date_from=2024-12-31&date_to=2024-01-01')
        form = ComplaintFilterForm(invalid_dates)
        is_valid = form.is_valid()
        self.stdout.write(f'✓ النموذج مع تواريخ غير صحيحة: {not is_valid}')

    def test_filter_queries(self):
        """اختبار استعلامات الفلترة"""
        self.stdout.write('🔍 اختبار استعلامات الفلترة...')

        # الاستعلام الأساسي
        base_queryset = Complaint.objects.all()
        total_complaints = base_queryset.count()
        self.stdout.write(f'إجمالي الشكاوى: {total_complaints}')

        if total_complaints == 0:
            self.stdout.write(
                self.style.WARNING('⚠️ لا توجد شكاوى للاختبار')
            )
            return

        # اختبار فلترة الحالة
        new_complaints = base_queryset.filter(status='new').count()
        self.stdout.write(f'الشكاوى الجديدة: {new_complaints}')

        # اختبار فلترة الأولوية
        high_priority = base_queryset.filter(priority='high').count()
        self.stdout.write(f'الشكاوى عالية الأولوية: {high_priority}')

        # اختبار البحث
        search_results = base_queryset.filter(
            Q(title__icontains='test') |
            Q(description__icontains='test')
        ).count()
        self.stdout.write(f'نتائج البحث عن "test": {search_results}')

    def test_complete_filtering(self):
        """اختبار الفلترة الكاملة"""
        self.stdout.write('🎯 اختبار الفلترة الكاملة...')

        # محاكاة طلب GET مع فلاتر متعددة
        test_params = QueryDict('status=new&priority=high&search=test')
        form = ComplaintFilterForm(test_params)

        if form.is_valid():
            queryset = Complaint.objects.all()
            
            # تطبيق الفلاتر
            if form.cleaned_data.get('status'):
                queryset = queryset.filter(status=form.cleaned_data['status'])
                self.stdout.write(f'بعد فلترة الحالة: {queryset.count()}')

            if form.cleaned_data.get('priority'):
                queryset = queryset.filter(priority=form.cleaned_data['priority'])
                self.stdout.write(f'بعد فلترة الأولوية: {queryset.count()}')

            if form.cleaned_data.get('search'):
                search_term = form.cleaned_data['search']
                search_query = (
                    Q(complaint_number__icontains=search_term) |
                    Q(customer__name__icontains=search_term) |
                    Q(title__icontains=search_term) |
                    Q(description__icontains=search_term)
                )
                queryset = queryset.filter(search_query)
                self.stdout.write(f'بعد البحث: {queryset.count()}')

            self.stdout.write(f'النتيجة النهائية: {queryset.count()} شكوى')

        # اختبار الخيارات المتاحة
        self.stdout.write('\n📋 الخيارات المتاحة:')
        self.stdout.write(f'أنواع الشكاوى النشطة: {ComplaintType.objects.filter(is_active=True).count()}')
        self.stdout.write(f'المستخدمون النشطون: {User.objects.filter(is_active=True).count()}')
        self.stdout.write(f'الأقسام النشطة: {Department.objects.filter(is_active=True).count()}')

        # اختبار حالات الشكاوى
        status_counts = {}
        for status_code, status_name in Complaint.STATUS_CHOICES:
            count = Complaint.objects.filter(status=status_code).count()
            status_counts[status_name] = count
            self.stdout.write(f'{status_name}: {count}')

        # اختبار أولويات الشكاوى
        priority_counts = {}
        for priority_code, priority_name in Complaint.PRIORITY_CHOICES:
            count = Complaint.objects.filter(priority=priority_code).count()
            priority_counts[priority_name] = count
            self.stdout.write(f'{priority_name}: {count}')
