#!/usr/bin/env python3
"""
Query Optimization Application Tool

This script helps apply query optimizations to Django views and admin classes.
It analyzes files and suggests specific optimizations with code examples.

Usage:
    python apply_query_optimizations.py [file_or_directory]
    python apply_query_optimizations.py --check  # Just analyze, don't suggest
"""

import ast
import re
from pathlib import Path
import argparse
from collections import defaultdict


class QueryOptimizationAnalyzer:
    """Analyzes Django code for query optimization opportunities"""
    
    def __init__(self, filepath, content):
        self.filepath = filepath
        self.content = content
        self.lines = content.split('\n')
        self.issues = []
        
    def analyze(self):
        """Run all analysis checks"""
        self._check_queryset_without_select_related()
        self._check_loops_with_foreign_keys()
        self._check_admin_get_queryset()
        self._check_list_comprehensions_with_fks()
        return self.issues
    
    def _check_queryset_without_select_related(self):
        """Find queryset operations without select_related"""
        for i, line in enumerate(self.lines, 1):
            # Pattern: .objects.filter(...) or .objects.all()
            if re.search(r'\.objects\.(filter|all|get|exclude)\(', line):
                # Check if select_related or prefetch_related nearby
                context = '\n'.join(self.lines[max(0, i-3):min(len(self.lines), i+3)])
                
                if 'select_related' not in context and 'prefetch_related' not in context:
                    # Check if it looks like it might access foreign keys
                    if any(indicator in line for indicator in ['__', 'customer', 'order', 'user', 'branch']):
                        self.issues.append({
                            'line': i,
                            'type': 'missing_select_related',
                            'severity': 'high',
                            'code': line.strip(),
                            'suggestion': self._suggest_select_related(line)
                        })
    
    def _check_loops_with_foreign_keys(self):
        """Find for loops that likely access foreign keys"""
        in_loop = False
        loop_start = 0
        
        for i, line in enumerate(self.lines, 1):
            if re.match(r'\s*for\s+\w+\s+in\s+', line):
                in_loop = True
                loop_start = i
                loop_var = re.search(r'for\s+(\w+)\s+in\s+', line)
                if loop_var:
                    var_name = loop_var.group(1)
                    # Check next 10 lines for foreign key access
                    for j in range(i, min(i + 10, len(self.lines) + 1)):
                        if j >= len(self.lines):
                            break
                        next_line = self.lines[j - 1]
                        # Pattern: item.foreign_key or item.foreign_key.attribute
                        if re.search(rf'{var_name}\.\w+\.\w+', next_line):
                            self.issues.append({
                                'line': loop_start,
                                'type': 'n_plus_one_loop',
                                'severity': 'high',
                                'code': line.strip(),
                                'suggestion': 'Add select_related() or prefetch_related() before the loop'
                            })
                            break
            elif not line.strip() or not line[0].isspace():
                in_loop = False
    
    def _check_admin_get_queryset(self):
        """Check if admin classes override get_queryset"""
        content = self.content
        
        # Find admin classes
        admin_classes = re.finditer(r'class\s+(\w+)\(.*admin\.ModelAdmin.*\):', content)
        
        for match in admin_classes:
            class_name = match.group(1)
            class_start = content[:match.start()].count('\n') + 1
            
            # Find the class body
            class_end = class_start + 100  # Check next 100 lines
            class_content = '\n'.join(self.lines[class_start-1:class_end])
            
            # Check for list_display with foreign keys
            list_display_match = re.search(r'list_display\s*=\s*\[(.*?)\]', class_content, re.DOTALL)
            
            if list_display_match:
                fields = list_display_match.group(1)
                # Check if get_queryset is defined
                if 'def get_queryset' not in class_content:
                    self.issues.append({
                        'line': class_start,
                        'type': 'admin_missing_get_queryset',
                        'severity': 'high',
                        'code': f'class {class_name}',
                        'suggestion': f'Add get_queryset() override to {class_name} with select_related()'
                    })
    
    def _check_list_comprehensions_with_fks(self):
        """Find list comprehensions that access foreign keys"""
        for i, line in enumerate(self.lines, 1):
            # Pattern: [item.fk for item in queryset]
            if re.search(r'\[.*?\..*?\s+for\s+.*?\s+in\s+.*?\]', line):
                if not any(opt in line for opt in ['select_related', 'prefetch_related']):
                    self.issues.append({
                        'line': i,
                        'type': 'list_comp_fk_access',
                        'severity': 'medium',
                        'code': line.strip(),
                        'suggestion': 'Ensure queryset uses select_related() before list comprehension'
                    })
    
    def _suggest_select_related(self, line):
        """Generate specific select_related suggestion"""
        # Extract model name if possible
        model_match = re.search(r'(\w+)\.objects', line)
        if model_match:
            model = model_match.group(1)
            return f"Add .select_related('related_field') after {model}.objects"
        return "Add .select_related('related_field') to the queryset"


def analyze_file(filepath):
    """Analyze a single file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        analyzer = QueryOptimizationAnalyzer(str(filepath), content)
        issues = analyzer.analyze()
        
        return {
            'filepath': filepath,
            'issues': issues
        }
    except Exception as e:
        return {
            'filepath': filepath,
            'error': str(e)
        }


def analyze_directory(directory):
    """Analyze all Python files in directory"""
    results = []
    
    for py_file in Path(directory).rglob('*.py'):
        if any(skip in str(py_file) for skip in ['venv', 'migrations', '__pycache__', '.git']):
            continue
        
        result = analyze_file(py_file)
        if result.get('issues'):
            results.append(result)
    
    return results


def generate_optimization_report(results, output_file='query_optimization_report.md'):
    """Generate detailed optimization report"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Query Optimization Report\n\n")
        
        # Summary
        total_files = len(results)
        total_issues = sum(len(r['issues']) for r in results if 'issues' in r)
        high_severity = sum(
            sum(1 for issue in r['issues'] if issue['severity'] == 'high')
            for r in results if 'issues' in r
        )
        
        f.write("## Summary\n\n")
        f.write(f"- **Files with Issues**: {total_files}\n")
        f.write(f"- **Total Issues**: {total_issues}\n")
        f.write(f"- **High Severity**: {high_severity}\n\n")
        
        # Priority recommendations
        f.write("## Priority Files (Most Issues)\n\n")
        sorted_results = sorted(
            [r for r in results if 'issues' in r],
            key=lambda x: len(x['issues']),
            reverse=True
        )[:10]
        
        for r in sorted_results:
            rel_path = Path(r['filepath']).relative_to(Path.cwd())
            f.write(f"- **{rel_path}**: {len(r['issues'])} issues\n")
        
        f.write("\n## Detailed Findings\n\n")
        
        # Details
        for result in results:
            if 'error' in result:
                f.write(f"### {result['filepath']}\n\n")
                f.write(f"**Error**: {result['error']}\n\n")
                continue
            
            try:
                rel_path = Path(result['filepath']).relative_to(Path.cwd())
            except ValueError:
                rel_path = Path(result['filepath']).resolve().relative_to(Path.cwd())
            f.write(f"### {rel_path}\n\n")
            f.write(f"**Issues Found**: {len(result['issues'])}\n\n")
            
            # Group by type
            by_type = defaultdict(list)
            for issue in result['issues']:
                by_type[issue['type']].append(issue)
            
            for issue_type, issues in by_type.items():
                type_name = issue_type.replace('_', ' ').title()
                f.write(f"#### {type_name} ({len(issues)} instances)\n\n")
                
                for issue in issues[:5]:  # Show first 5
                    f.write(f"**Line {issue['line']}** - {issue['severity']} severity\n\n")
                    f.write(f"```python\n{issue['code']}\n```\n\n")
                    f.write(f"💡 **Suggestion**: {issue['suggestion']}\n\n")
                
                if len(issues) > 5:
                    f.write(f"*... and {len(issues) - 5} more*\n\n")
            
            f.write("---\n\n")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze Django code for query optimization opportunities'
    )
    parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='File or directory to analyze (default: current directory)'
    )
    parser.add_argument(
        '--report',
        default='query_optimization_report.md',
        help='Output report file'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Just check and count issues, no detailed report'
    )
    
    args = parser.parse_args()
    
    path = Path(args.path)
    
    if not path.exists():
        print(f"Error: Path '{path}' does not exist")
        return
    
    print("🔍 Analyzing query patterns...")
    print()
    
    if path.is_file():
        result = analyze_file(path)
        results = [result] if result.get('issues') else []
    else:
        results = analyze_directory(path)
    
    if not results:
        print("✅ No query optimization issues found!")
        return
    
    total_issues = sum(len(r['issues']) for r in results if 'issues' in r)
    high_severity = sum(
        sum(1 for issue in r['issues'] if issue['severity'] == 'high')
        for r in results if 'issues' in r
    )
    
    print(f"📊 Results:")
    print(f"  - Files with issues: {len(results)}")
    print(f"  - Total issues: {total_issues}")
    print(f"  - High severity: {high_severity}")
    
    if not args.check:
        generate_optimization_report(results, args.report)
        print(f"\n📄 Detailed report saved to: {args.report}")
    
    # Show top 5 files
    print(f"\n🎯 Top Files to Optimize:")
    sorted_results = sorted(results, key=lambda x: len(x['issues']), reverse=True)[:5]
    for r in sorted_results:
        try:
            rel_path = Path(r['filepath']).relative_to(Path.cwd())
        except ValueError:
            rel_path = Path(r['filepath']).resolve().relative_to(Path.cwd())
        print(f"  - {rel_path}: {len(r['issues'])} issues")


if __name__ == '__main__':
    main()
