#!/usr/bin/env python
"""
اختبار تحويل الأرقام العربية إلى إنجليزية
Test Arabic to English number conversion
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from core.utils.general import convert_arabic_numbers_to_english, convert_model_arabic_numbers

def test_conversion():
    """اختبار دوال التحويل"""
    print("=" * 60)
    print("🧪 اختبار تحويل الأرقام العربية إلى إنجليزية")
    print("=" * 60)
    
    test_cases = [
        ("رقم الطلب: ١٢٣٤٥", "رقم الطلب: 12345"),
        ("المبلغ: ٥٠٠٠ جنيه", "المبلغ: 5000 جنيه"),
        ("الرقم المرجعي: ٩٨٧٦٥٤٣٢١٠", "الرقم المرجعي: 9876543210"),
        ("كود الحساب: ١١٠١", "كود الحساب: 1101"),
        ("No Arabic numbers", "No Arabic numbers"),
        ("", ""),
        (None, None),
    ]
    
    all_passed = True
    
    for i, (input_text, expected) in enumerate(test_cases, 1):
        result = convert_arabic_numbers_to_english(input_text)
        passed = result == expected
        all_passed = all_passed and passed
        
        status = "✅" if passed else "❌"
        print(f"\n{status} Test {i}:")
        print(f"   Input:    {repr(input_text)}")
        print(f"   Expected: {repr(expected)}")
        print(f"   Got:      {repr(result)}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ جميع الاختبارات نجحت!")
        print("✅ All tests passed!")
    else:
        print("❌ بعض الاختبارات فشلت")
        print("❌ Some tests failed")
    print("=" * 60)
    
    return all_passed


def test_model_conversion():
    """اختبار التحويل على Model"""
    print("\n" + "=" * 60)
    print("🧪 اختبار تحويل الأرقام في Models")
    print("=" * 60)
    
    # Create mock object
    class MockModel:
        def __init__(self):
            self.code = "١٢٣٤"
            self.name = "حساب رقم ٥٦٧٨"
            self.reference = "REF-٩٩٩"
    
    obj = MockModel()
    print(f"\n📝 Before conversion:")
    print(f"   code: {obj.code}")
    print(f"   name: {obj.name}")
    print(f"   reference: {obj.reference}")
    
    convert_model_arabic_numbers(obj, ['code', 'name', 'reference'])
    
    print(f"\n✨ After conversion:")
    print(f"   code: {obj.code}")
    print(f"   name: {obj.name}")
    print(f"   reference: {obj.reference}")
    
    passed = (
        obj.code == "1234" and 
        obj.name == "حساب رقم 5678" and 
        obj.reference == "REF-999"
    )
    
    print("\n" + "=" * 60)
    if passed:
        print("✅ تحويل Model نجح!")
        print("✅ Model conversion passed!")
    else:
        print("❌ تحويل Model فشل")
        print("❌ Model conversion failed")
    print("=" * 60)
    
    return passed


if __name__ == "__main__":
    test1 = test_conversion()
    test2 = test_model_conversion()
    
    print("\n" + "=" * 60)
    print("📊 النتيجة النهائية / Final Result")
    print("=" * 60)
    
    if test1 and test2:
        print("✅ جميع الاختبارات نجحت - النظام جاهز!")
        print("✅ All tests passed - System ready!")
        exit(0)
    else:
        print("❌ بعض الاختبارات فشلت")
        print("❌ Some tests failed")
        exit(1)
