#!/usr/bin/env python3
"""
Test script to verify decimal value handling improvements for mobile order creation.
This script tests the server-side decimal processing improvements.
"""

import os
import sys
import django
import json
from decimal import Decimal, InvalidOperation

# Setup Django environment
sys.path.append('/home/xhunterx/homeupdate')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')
django.setup()

from orders.models import Order, OrderItem
from inventory.models import Product
from customers.models import Customer
from accounts.models import User, Branch


def test_decimal_conversion():
    """Test decimal conversion logic similar to the server-side processing"""
    print("🧪 اختبار تحويل القيم العشرية...")
    
    test_cases = [
        # (input_value, expected_output, description)
        ("4.25", Decimal("4.25"), "قيمة عشرية صحيحة"),
        ("4.250", Decimal("4.25"), "قيمة عشرية مع أصفار زائدة"),
        ("4", Decimal("4"), "قيمة صحيحة"),
        ("0.001", Decimal("0.001"), "قيمة عشرية صغيرة"),
        ("999.999", Decimal("999.999"), "قيمة عشرية كبيرة"),
        (4.25, Decimal("4.25"), "رقم float"),
        (4, Decimal("4"), "رقم integer"),
    ]
    
    invalid_cases = [
        ("abc", "قيمة نصية غير صالحة"),
        ("", "قيمة فارغة"),
        (None, "قيمة None"),
        ("4.25.5", "قيمة بنقطتين عشريتين"),
        ("-5", "قيمة سالبة"),
    ]
    
    print("\n✅ اختبار القيم الصحيحة:")
    for input_val, expected, description in test_cases:
        try:
            result = Decimal(str(input_val))
            if result == expected:
                print(f"   ✓ {description}: {input_val} → {result}")
            else:
                print(f"   ✗ {description}: {input_val} → {result} (متوقع: {expected})")
        except Exception as e:
            print(f"   ✗ {description}: {input_val} → خطأ: {e}")
    
    print("\n❌ اختبار القيم غير الصحيحة:")
    for input_val, description in invalid_cases:
        try:
            result = Decimal(str(input_val))
            print(f"   ⚠️  {description}: {input_val} → {result} (كان يجب أن يفشل)")
        except (InvalidOperation, ValueError, TypeError) as e:
            print(f"   ✓ {description}: {input_val} → خطأ متوقع: {type(e).__name__}")


def test_json_processing():
    """Test JSON processing similar to the order creation view"""
    print("\n🧪 اختبار معالجة JSON...")
    
    # محاكاة البيانات المرسلة من JavaScript
    test_json_data = json.dumps([
        {
            "product_id": 1,
            "quantity": 4.25,
            "unit_price": 150.50,
            "discount_percentage": 5.0,
            "notes": "اختبار القيم العشرية"
        },
        {
            "product_id": 2,
            "quantity": 1.5,
            "unit_price": 200.00,
            "discount_percentage": 0,
            "notes": ""
        }
    ])
    
    print(f"JSON البيانات: {test_json_data}")
    
    try:
        selected_products = json.loads(test_json_data)
        print(f"\n✅ تم تحليل JSON بنجاح: {len(selected_products)} عنصر")
        
        for i, product_data in enumerate(selected_products, 1):
            print(f"\n📦 العنصر {i}:")
            
            # معالجة الكمية
            try:
                quantity = Decimal(str(product_data['quantity']))
                print(f"   الكمية: {product_data['quantity']} → {quantity}")
            except Exception as e:
                print(f"   ❌ خطأ في الكمية: {e}")
                continue
            
            # معالجة السعر
            try:
                unit_price = Decimal(str(product_data['unit_price']))
                print(f"   السعر: {product_data['unit_price']} → {unit_price}")
            except Exception as e:
                print(f"   ❌ خطأ في السعر: {e}")
                continue
            
            # معالجة الخصم
            try:
                discount = Decimal(str(product_data.get('discount_percentage', 0)))
                print(f"   الخصم: {product_data.get('discount_percentage', 0)}% → {discount}%")
            except Exception as e:
                print(f"   ❌ خطأ في الخصم: {e}")
                discount = Decimal('0')
            
            # حساب الإجمالي
            total = quantity * unit_price
            discount_amount = total * (discount / Decimal('100'))
            final_total = total - discount_amount
            
            print(f"   الإجمالي قبل الخصم: {total}")
            print(f"   مبلغ الخصم: {discount_amount}")
            print(f"   الإجمالي بعد الخصم: {final_total}")
            
    except Exception as e:
        print(f"❌ خطأ في معالجة JSON: {e}")


def test_mobile_scenarios():
    """Test specific mobile scenarios that might cause decimal truncation"""
    print("\n🧪 اختبار سيناريوهات الهواتف المحمولة...")
    
    # سيناريوهات قد تحدث على الهواتف المحمولة
    mobile_scenarios = [
        # (description, quantity_from_js, expected_result)
        ("إدخال عادي", "4.25", Decimal("4.25")),
        ("إدخال بأصفار زائدة", "4.250", Decimal("4.25")),
        ("إدخال بدون جزء عشري", "4", Decimal("4")),
        ("إدخال بجزء عشري صغير", "0.5", Decimal("0.5")),
        ("إدخال بثلاث منازل عشرية", "4.125", Decimal("4.125")),
        ("إدخال كبير", "999.999", Decimal("999.999")),
    ]
    
    print("\n📱 اختبار سيناريوهات الهواتف المحمولة:")
    for description, js_value, expected in mobile_scenarios:
        try:
            # محاكاة ما يحدث في JavaScript
            js_number = float(js_value)  # parseFloat في JavaScript
            
            # محاكاة ما يحدث في JSON
            json_data = json.dumps({"quantity": js_number})
            parsed_data = json.loads(json_data)
            
            # محاكاة المعالجة في الخادم
            server_decimal = Decimal(str(parsed_data["quantity"]))
            
            if server_decimal == expected:
                print(f"   ✓ {description}: {js_value} → JS:{js_number} → JSON → Server:{server_decimal}")
            else:
                print(f"   ✗ {description}: {js_value} → JS:{js_number} → JSON → Server:{server_decimal} (متوقع: {expected})")
                
        except Exception as e:
            print(f"   ❌ {description}: خطأ - {e}")


def main():
    """Run all tests"""
    print("🚀 بدء اختبار معالجة القيم العشرية المحسنة")
    print("=" * 60)
    
    test_decimal_conversion()
    test_json_processing()
    test_mobile_scenarios()
    
    print("\n" + "=" * 60)
    print("✅ انتهى الاختبار")
    print("\n💡 ملاحظات:")
    print("   - تأكد من أن جميع القيم العشرية تُعالج بشكل صحيح")
    print("   - تحقق من عدم فقدان الدقة أثناء التحويل")
    print("   - اختبر على أجهزة محمولة مختلفة للتأكد من التوافق")


if __name__ == "__main__":
    main()
