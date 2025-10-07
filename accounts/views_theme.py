"""
عروض تخصيص الثيمات
Theme Customization Views
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext_lazy as _
from .theme_customization import ThemeCustomization
from .forms_theme import ThemeCustomizationForm
import json


@login_required
def theme_customization_view(request):
    """
    صفحة تخصيص الثيم
    """
    # جلب أو إنشاء تخصيص الثيم للمستخدم
    customization, created = ThemeCustomization.objects.get_or_create(
        user=request.user,
        defaults={'base_theme': request.user.default_theme}
    )
    
    if request.method == 'POST':
        form = ThemeCustomizationForm(request.POST, instance=customization)
        if form.is_valid():
            saved_customization = form.save(commit=False)
            # تأكد من وجود قيمة لـ base_theme
            if not saved_customization.base_theme:
                saved_customization.base_theme = request.user.default_theme or 'default'
            saved_customization.save()
            messages.success(request, _('✅ تم حفظ تخصيصات الثيم بنجاح!'))
            return redirect('accounts:theme_customization')
        else:
            # طباعة الأخطاء للتشخيص
            error_messages = []
            for field, errors in form.errors.items():
                for error in errors:
                    error_messages.append(f'{field}: {error}')
            
            error_text = ' | '.join(error_messages) if error_messages else 'حدث خطأ غير معروف'
            messages.error(request, f'❌ خطأ في الحفظ: {error_text}')
            print(f"Form errors: {form.errors}")  # للتشخيص في الـ logs
    else:
        form = ThemeCustomizationForm(instance=customization)
    
    # الثيمات المتاحة
    available_themes = [
        {'value': 'default', 'label': '🏠 الكلاسيكي'},
        {'value': 'custom', 'label': '🌟 مخصص'},
        {'value': 'modern-black', 'label': '🌙 أسود عصري'},
        {'value': 'mocha-mousse', 'label': '🍫 موكا موس'},
        {'value': 'warm-earth', 'label': '🌍 أرض دافئة'},
        {'value': 'coffee-elegance', 'label': '☕ أناقة القهوة'},
    ]
    
    context = {
        'form': form,
        'customization': customization,
        'available_themes': available_themes,
        'current_theme': request.user.default_theme,
    }
    
    return render(request, 'accounts/theme_customization.html', context)


@login_required
@require_http_methods(["POST"])
def theme_customization_reset(request):
    """
    إعادة تعيين التخصيصات للقيم الافتراضية
    """
    try:
        customization = ThemeCustomization.objects.get(user=request.user)
        customization.reset_to_defaults()
        
        return JsonResponse({
            'status': 'success',
            'message': _('تم إعادة تعيين التخصيصات بنجاح! 🔄')
        })
    except ThemeCustomization.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': _('لم يتم العثور على تخصيصات.')
        }, status=404)


@login_required
def theme_customization_export(request):
    """
    تصدير التخصيصات كـ JSON
    """
    try:
        customization = ThemeCustomization.objects.get(user=request.user)
        data = customization.to_json()
        
        return JsonResponse({
            'status': 'success',
            'data': json.loads(data)
        })
    except ThemeCustomization.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': _('لم يتم العثور على تخصيصات.')
        }, status=404)


@login_required
@require_http_methods(["POST"])
def theme_customization_update_live(request):
    """
    تحديث التخصيصات مباشرة (AJAX)
    """
    try:
        customization = ThemeCustomization.objects.get(user=request.user)
        
        data = json.loads(request.body)
        field_name = data.get('field')
        field_value = data.get('value')
        
        if hasattr(customization, field_name):
            setattr(customization, field_name, field_value)
            customization.save()
            
            return JsonResponse({
                'status': 'success',
                'message': _('تم التحديث')
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': _('حقل غير صحيح')
            }, status=400)
            
    except ThemeCustomization.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': _('لم يتم العثور على تخصيصات.')
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': _('بيانات غير صحيحة')
        }, status=400)
