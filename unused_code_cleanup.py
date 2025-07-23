#!/usr/bin/env python3
"""
سكريبت تنظيف الأكواد غير المستخدمة
يحدد ويحذف الأكواد والملفات غير المستخدمة في النظام
"""

import os
import re
from pathlib import Path
import ast
import json

class UnusedCodeDetector:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.unused_items = {
            'files': [],
            'functions': [],
            'classes': [],
            'variables': [],
            'imports': []
        }
    
    def scan_unused_files(self):
        """فحص الملفات غير المستخدمة"""
        print("🔍 فحص الملفات غير المستخدمة...")
        
        # ملفات مشكوك في عدم استخدامها
        suspicious_files = [
            "crm/middleware/performance.py",
            "crm/middleware/lazy_load.py", 
            "orders/services/google_drive_service.py",
            "inspections/services/google_drive_service.py",
            "advanced_test_scenarios.py",
            "comprehensive_system_test.py",
            "comprehensive_status_consistency_test.py",
            "fix_customer_creation_date.py",
            "fix_existing_orders.py",
            "fix_inspection_dates_postgres.py",
            "fix_inspection_expected_date.py",
            "fix_inspection_status_display.py",
            "fix_phone.py",
            "fix_restore_now.py",
            "fix_sequence.py",
            "fix_system_issues.py",
            "quick_diagnosis.py",
            "quick_fix_restore.html",
            "reset_db_local.sh",
            "reset_tables.py",
            "run_admin_dashboard.sh",
            "run_installation_test.sh",
            "run_status_consistency_test.py",
            "run_system_fixes.py",
            "run_updated_test.py",
            "test_*.py",  # ملفات الاختبار المؤقتة
            "debug_*.py",  # ملفات التصحيح
            "temp/*",  # مجلد مؤقت
            ".qodo/*",  # مجلد qodo
            ".ropeproject/*",  # مجلد rope
        ]
        
        for pattern in suspicious_files:
            if '*' in pattern:
                # استخدام glob للأنماط
                for file_path in self.project_root.glob(pattern):
                    if file_path.is_file():
                        self.unused_items['files'].append(str(file_path.relative_to(self.project_root)))
            else:
                file_path = self.project_root / pattern
                if file_path.exists():
                    self.unused_items['files'].append(pattern)
    
    def scan_unused_functions(self):
        """فحص الدوال غير المستخدمة"""
        print("🔍 فحص الدوال غير المستخدمة...")
        
        # دوال مشكوك في عدم استخدامها
        suspicious_functions = {
            'orders/models.py': [
                'upload_contract_to_google_drive',
                'notify_status_change', 
                'send_status_notification',
                'get_scheduling_date',
                'get_scheduling_date_display'
            ],
            'inspections/models.py': [
                'upload_to_google_drive_async',
                'generate_drive_filename',
                '_clean_filename'
            ],
            'installations/models.py': [
                'can_change_status_to',
                'get_next_possible_statuses',
                'requires_scheduling_settings'
            ],
            'manufacturing/models.py': [
                'get_absolute_url',
                'get_delete_url'
            ]
        }
        
        for file_path, functions in suspicious_functions.items():
            full_path = self.project_root / file_path
            if full_path.exists():
                content = full_path.read_text(encoding='utf-8')
                for func_name in functions:
                    # البحث عن استخدام الدالة في الملف نفسه أو ملفات أخرى
                    if self._is_function_unused(func_name, content):
                        self.unused_items['functions'].append(f"{file_path}::{func_name}")
    
    def scan_unused_classes(self):
        """فحص الكلاسات غير المستخدمة"""
        print("🔍 فحص الكلاسات غير المستخدمة...")
        
        # كلاسات مشكوك في عدم استخدامها
        suspicious_classes = {
            'installations/models.py': [
                'ModificationErrorAnalysis',
                'InstallationAnalytics',
                'ModificationErrorType',
                'InstallationEventLog'
            ],
            'inspections/models.py': [
                'InspectionEvaluation',
                'InspectionNotification', 
                'InspectionReport'
            ],
            'orders/models.py': [
                'ManufacturingDeletionLog'
            ]
        }
        
        for file_path, classes in suspicious_classes.items():
            full_path = self.project_root / file_path
            if full_path.exists():
                for class_name in classes:
                    if self._is_class_unused(class_name, full_path):
                        self.unused_items['classes'].append(f"{file_path}::{class_name}")
    
    def scan_unused_imports(self):
        """فحص الاستيرادات غير المستخدمة"""
        print("🔍 فحص الاستيرادات غير المستخدمة...")
        
        python_files = list(self.project_root.glob("**/*.py"))
        
        for file_path in python_files:
            if file_path.is_file() and 'migrations' not in str(file_path):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    unused_imports = self._find_unused_imports(content)
                    if unused_imports:
                        for imp in unused_imports:
                            self.unused_items['imports'].append(f"{file_path.relative_to(self.project_root)}::{imp}")
                except Exception as e:
                    print(f"خطأ في فحص {file_path}: {e}")
    
    def _is_function_unused(self, func_name, content):
        """فحص ما إذا كانت الدالة غير مستخدمة"""
        # البحث عن استدعاءات الدالة
        patterns = [
            rf"\.{func_name}\(",  # استدعاء كmethod
            rf"{func_name}\(",    # استدعاء مباشر
            rf"'{func_name}'",    # كstring
            rf'"{func_name}"',    # كstring
        ]
        
        for pattern in patterns:
            if re.search(pattern, content):
                return False
        return True
    
    def _is_class_unused(self, class_name, file_path):
        """فحص ما إذا كانت الكلاس غير مستخدمة"""
        # البحث في جميع ملفات Python
        python_files = list(self.project_root.glob("**/*.py"))
        
        for py_file in python_files:
            if py_file != file_path and py_file.is_file():
                try:
                    content = py_file.read_text(encoding='utf-8')
                    if class_name in content:
                        return False
                except:
                    continue
        return True
    
    def _find_unused_imports(self, content):
        """البحث عن الاستيرادات غير المستخدمة"""
        try:
            tree = ast.parse(content)
            imports = []
            used_names = set()
            
            # جمع جميع الاستيرادات
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.Name):
                    used_names.add(node.id)
            
            # البحث عن الاستيرادات غير المستخدمة
            unused = []
            for imp in imports:
                if imp not in used_names and imp != '*':
                    unused.append(imp)
            
            return unused
        except:
            return []
    
    def scan_large_files(self):
        """فحص الملفات الكبيرة التي قد تحتاج تحسين"""
        print("🔍 فحص الملفات الكبيرة...")
        
        large_files = []
        python_files = list(self.project_root.glob("**/*.py"))
        
        for file_path in python_files:
            if file_path.is_file():
                size = file_path.stat().st_size
                if size > 50000:  # أكبر من 50KB
                    lines = len(file_path.read_text(encoding='utf-8').splitlines())
                    large_files.append({
                        'file': str(file_path.relative_to(self.project_root)),
                        'size': size,
                        'lines': lines
                    })
        
        # ترتيب حسب الحجم
        large_files.sort(key=lambda x: x['size'], reverse=True)
        
        print("📊 أكبر 10 ملفات:")
        for i, file_info in enumerate(large_files[:10], 1):
            print(f"{i}. {file_info['file']} - {file_info['size']/1024:.1f}KB ({file_info['lines']} سطر)")
    
    def scan_complex_functions(self):
        """فحص الدوال ��لمعقدة التي تحتاج تبسيط"""
        print("🔍 فحص الدوال المعقدة...")
        
        complex_functions = []
        python_files = list(self.project_root.glob("**/*.py"))
        
        for file_path in python_files:
            if file_path.is_file() and 'migrations' not in str(file_path):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    functions = self._find_complex_functions(content)
                    for func in functions:
                        complex_functions.append({
                            'file': str(file_path.relative_to(self.project_root)),
                            'function': func['name'],
                            'lines': func['lines'],
                            'complexity': func['complexity']
                        })
                except Exception as e:
                    continue
        
        # ترتيب حسب التعقيد
        complex_functions.sort(key=lambda x: x['complexity'], reverse=True)
        
        print("📊 أكثر 10 دوال تعقيداً:")
        for i, func_info in enumerate(complex_functions[:10], 1):
            print(f"{i}. {func_info['file']}::{func_info['function']} - {func_info['lines']} سطر (تعقيد: {func_info['complexity']})")
    
    def _find_complex_functions(self, content):
        """البحث عن الدوال المعقدة"""
        functions = []
        lines = content.splitlines()
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('def '):
                func_name = line.split('(')[0].replace('def ', '').strip()
                func_lines = 1
                complexity = 1
                indent_level = len(lines[i]) - len(lines[i].lstrip())
                
                i += 1
                while i < len(lines):
                    current_line = lines[i]
                    current_indent = len(current_line) - len(current_line.lstrip())
                    
                    if current_line.strip() and current_indent <= indent_level:
                        break
                    
                    func_lines += 1
                    
                    # حساب التعقيد
                    if any(keyword in current_line for keyword in ['if ', 'elif ', 'for ', 'while ', 'try:', 'except']):
                        complexity += 1
                    
                    i += 1
                
                if func_lines > 20 or complexity > 5:  # دوال كبيرة أو معقدة
                    functions.append({
                        'name': func_name,
                        'lines': func_lines,
                        'complexity': complexity
                    })
            else:
                i += 1
        
        return functions
    
    def generate_cleanup_script(self):
        """إنشاء سكريبت تنظيف الأكواد غير المستخدمة"""
        print("📝 إنشاء سكريبت التنظيف...")
        
        script_content = f'''#!/usr/bin/env python3
"""
سكريبت تنظيف الأكواد غير المستخدمة - تم إنشاؤه تلقائياً
"""

import os
import shutil
from pathlib import Path

def cleanup_unused_code():
    """حذف الأكواد غير المستخدمة"""
    project_root = Path("{self.project_root}")
    
    print("🗑️ بدء تنظيف الأكواد غير المستخدمة...")
    
    # حذف الملفات غير المستخدمة
    files_to_remove = {json.dumps(self.unused_items['files'], indent=4, ensure_ascii=False)}
    
    for file_path in files_to_remove:
        full_path = project_root / file_path
        if full_path.exists():
            if full_path.is_file():
                full_path.unlink()
                print(f"🗑️ حذف ملف: {{file_path}}")
            elif full_path.is_dir():
                shutil.rmtree(full_path)
                print(f"🗑️ حذف مجلد: {{file_path}}")
    
    print("✅ تم تنظيف الأكواد غير المستخدمة")

if __name__ == "__main__":
    cleanup_unused_code()
'''
        
        script_file = self.project_root / "cleanup_unused_code.py"
        script_file.write_text(script_content, encoding='utf-8')
        
        print(f"✅ تم إنشاء سكريبت التنظيف: {script_file}")
    
    def generate_report(self):
        """إنشاء تقرير شامل عن الأكواد غير المستخدمة"""
        print("📊 إنشاء تقرير الأكواد غير المستخدمة...")
        
        report = {
            'summary': {
                'unused_files': len(self.unused_items['files']),
                'unused_functions': len(self.unused_items['functions']),
                'unused_classes': len(self.unused_items['classes']),
                'unused_imports': len(self.unused_items['imports'])
            },
            'details': self.unused_items
        }
        
        # حفظ التقرير كJSON
        report_file = self.project_root / "unused_code_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=4, ensure_ascii=False)
        
        # إنشاء تقرير نصي
        text_report = f"""# تقرير الأكواد غير المستخدمة

## ملخص:
- ملفات غير مستخدمة: {report['summary']['unused_files']}
- دوال غير مستخدمة: {report['summary']['unused_functions']}
- كلاسات غير مستخدمة: {report['summary']['unused_classes']}
- استيرادات غير مستخدمة: {report['summary']['unused_imports']}

## الملفات غير المستخدمة:
"""
        
        for file_path in self.unused_items['files']:
            text_report += f"- {file_path}\n"
        
        text_report += "\n## الدوال غير المستخدمة:\n"
        for func in self.unused_items['functions']:
            text_report += f"- {func}\n"
        
        text_report += "\n## الكلاسات غير المستخدمة:\n"
        for cls in self.unused_items['classes']:
            text_report += f"- {cls}\n"
        
        text_report_file = self.project_root / "unused_code_report.md"
        text_report_file.write_text(text_report, encoding='utf-8')
        
        print(f"✅ تم إنشاء التقرير: {report_file}")
        print(f"✅ تم إنشاء التقرير النصي: {text_report_file}")
    
    def run_analysis(self):
        """تشغيل التحليل الشامل"""
        print("🔍 بدء تحليل الأكواد غير المستخدمة...")
        print("=" * 50)
        
        self.scan_unused_files()
        self.scan_unused_functions()
        self.scan_unused_classes()
        self.scan_unused_imports()
        self.scan_large_files()
        self.scan_complex_functions()
        
        self.generate_cleanup_script()
        self.generate_report()
        
        print("=" * 50)
        print("✅ تم إكمال التحليل!")
        print(f"📊 تم العثور على:")
        print(f"   - {len(self.unused_items['files'])} ملف غير مستخدم")
        print(f"   - {len(self.unused_items['functions'])} دالة غير مستخدمة")
        print(f"   - {len(self.unused_items['classes'])} كلاس غير مستخدم")
        print(f"   - {len(self.unused_items['imports'])} استيراد غير مستخدم")
        print("\n📁 الملفات المُنشأة:")
        print("   - unused_code_report.json")
        print("   - unused_code_report.md")
        print("   - cleanup_unused_code.py")

if __name__ == "__main__":
    project_root = "/home/zakee/homeupdate"
    detector = UnusedCodeDetector(project_root)
    detector.run_analysis()