from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import ManufacturingOrder

@login_required
def dashboard(request):
    orders = ManufacturingOrder.objects.all()
    context = {
        'orders': orders,
        'page_title': 'لوحة تحكم المصنع',
    }
    return render(request, 'factory/dashboard.html', context)
