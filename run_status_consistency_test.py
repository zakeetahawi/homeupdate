#!/usr/bin/env python
"""
تشغيل الاختبار الشامل لتطابق الحالات
"""

import sys
import subprocess


def run_test():
    """تشغيل الاختبار الشامل"""
    print("🚀 تشغيل الاختبار الشامل لتطابق الحالات في النظام")
    print("=" * 60)
    
    try:
        # تشغيل الاختبار
        result = subprocess.run([
            sys.executable, 
            'comprehensive_status_consistency_test.py'
        ], capture_output=True, text=True, encoding='utf-8')
        
        # عرض النتائج
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print("⚠️ تحذيرات/أخطاء:")
            print(result.stderr)
        
        # حالة الخروج
        if result.returncode == 0:
            print("\n✅ تم إنجاز الاختبار بنجاح!")
        else:
            print("\n❌ فشل الاختبار!")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ خطأ في تشغيل الاختبار: {str(e)}")
        return False


if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1) 