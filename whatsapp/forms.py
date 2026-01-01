from django import forms
from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import WhatsAppSettings
from .services import WhatsAppService


class TestMessageForm(forms.Form):
    """نموذج إرسال رسالة اختبار"""
    phone_number = forms.CharField(
        label='رقم الهاتف',
        max_length=15,
        help_text='مثال: 01119238775',
        widget=forms.TextInput(attrs={'placeholder': '01119238775'})
    )
    template_name = forms.ChoiceField(
        label='القالب',
        choices=[
            ('hello_world', 'Hello World (معتمد ✅)'),
        ],
        initial='hello_world',
        help_text='قالب order_confirmation قيد المراجعة من Meta'
    )
    
    def clean_phone_number(self):
        phone = self.cleaned_data['phone_number']
        # إزالة المسافات والرموز
        phone = phone.replace(' ', '').replace('-', '').replace('+', '')
        
        # التحقق من أنه رقم
        if not phone.isdigit():
            raise forms.ValidationError('رقم الهاتف يجب أن يحتوي على أرقام فقط')
        
        # التحقق من الطول
        if len(phone) < 10 or len(phone) > 15:
            raise forms.ValidationError('رقم الهاتف غير صحيح')
        
        return phone
