"""
كشف الحساب الشجري للعميل - Account Statement
"""
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.db.models import Q, Sum, Case, When, DecimalField

from accounting.models import Account, Transaction, TransactionLine
from customers.models import Customer


@login_required
def customer_account_statement(request, customer_id):
    """
    كشف حساب تفصيلي شجري للعميل
    يعرض جميع القيود المحاسبية مع تفاصيلها الكاملة
    """
    customer = get_object_or_404(Customer, pk=customer_id)
    
    # البحث عن حساب العميل المحاسبي
    customer_account = Account.objects.filter(
        customer=customer,
        is_customer_account=True
    ).first()
    
    # جلب نطاق التاريخ من GET parameters
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    # جلب جميع القيود المرتبطة بالعميل (المرحلة فقط)
    transactions = Transaction.objects.filter(
        Q(customer=customer) | 
        Q(lines__account=customer_account),
        status='posted'
    ).distinct().select_related(
        'order', 'customer'
    ).prefetch_related(
        'lines__account'
    ).order_by('date', 'created_at')
    
    # تطبيق فلاتر التاريخ
    if from_date:
        transactions = transactions.filter(date__gte=from_date)
    if to_date:
        transactions = transactions.filter(date__lte=to_date)
    
    # إعداد البيانات الشجرية
    statement_data = []
    running_balance = Decimal('0.00')
    opening_balance = Decimal('0.00')
    
    # حساب الرصيد الافتتاحي إذا كان هناك فلتر تاريخ
    if from_date and customer_account:
        opening_transactions = Transaction.objects.filter(
            Q(customer=customer) | Q(lines__account=customer_account),
            date__lt=from_date,
            status='posted'
        ).distinct()
        
        for txn in opening_transactions:
            for line in txn.lines.all():
                if line.account == customer_account:
                    opening_balance += line.debit - line.credit
        
        running_balance = opening_balance
    
    # معالجة القيود
    for txn in transactions:
        # جمع جميع السطور في هذا القيد
        lines = txn.lines.all().select_related('account')
        
        # حساب مدين/دائن العميل في هذا القيد
        customer_debit = Decimal('0.00')
        customer_credit = Decimal('0.00')
        other_lines = []
        
        for line in lines:
            if line.account == customer_account or (not customer_account and line.account.code == '1121'):
                # سطر حساب العميل
                customer_debit = line.debit
                customer_credit = line.credit
            else:
                # السطور الأخرى (المقابلة)
                other_lines.append({
                    'account': line.account,
                    'debit': line.debit,
                    'credit': line.credit,
                    'description': line.description
                })
        
        # حساب الرصيد الجاري
        movement = customer_debit - customer_credit
        running_balance += movement
        
        statement_data.append({
            'transaction': txn,
            'customer_debit': customer_debit,
            'customer_credit': customer_credit,
            'movement': movement,
            'balance': running_balance,
            'other_lines': other_lines,
            'line_count': len(other_lines)
        })
    
    # الإحصائيات
    total_debit = sum(item['customer_debit'] for item in statement_data)
    total_credit = sum(item['customer_credit'] for item in statement_data)
    final_balance = running_balance
    
    context = {
        'customer': customer,
        'customer_account': customer_account,
        'statement_data': statement_data,
        'opening_balance': opening_balance,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'final_balance': final_balance,
        'from_date': from_date,
        'to_date': to_date,
        'has_transactions': len(statement_data) > 0,
    }
    
    return render(request, 'accounting/customer_account_statement.html', context)
