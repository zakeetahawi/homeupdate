#!/usr/bin/env python3
"""
Safe Unused Import Removal Tool

This script removes unused imports from Python files with safety checks:
- Creates backups before modification
- Only removes clearly unused imports
- Skips common false positives (decorators, signals, etc.)
- Generates a report of changes

Usage:
    python remove_unused_imports.py [file_or_directory]
    python remove_unused_imports.py --dry-run [file_or_directory]
"""

import ast
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
import argparse


class SafeImportRemover(ast.NodeVisitor):
    """Safely identifies and removes unused imports"""
    
    # Known false positives - imports that may be used indirectly
    FALSE_POSITIVES = {
        # Django imports that register automatically
        'signals', 'receivers', 'admin', 'apps',
        # Common decorators
        'login_required', 'permission_required', 'csrf_exempt',
        'cache_page', 'require_POST', 'require_http_methods',
        # Type hints
        'typing', 'Type', 'Optional', 'List', 'Dict', 'Union',
        # Django models that may be used in migrations
        'models', 'migrations',
    }
    
    def __init__(self, content):
        self.content = content
        self.lines = content.split('\n')
        self.imports_to_remove = []
        self.imports = {}
        self.used_names = set()
        
    def analyze(self):
        """Analyze the file and find unused imports"""
        try:
            tree = ast.parse(self.content)
            self.visit(tree)
            return self._identify_unused()
        except SyntaxError:
            return []
    
    def visit_Import(self, node):
        """Track import statements"""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name.split('.')[0]
            self.imports[name] = {
                'line': node.lineno - 1,
                'full_name': alias.name,
                'type': 'import',
                'statement': self.lines[node.lineno - 1]
            }
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Track from...import statements"""
        for alias in node.names:
            if alias.name == '*':
                # Never remove star imports (too risky)
                continue
            name = alias.asname if alias.asname else alias.name
            self.imports[name] = {
                'line': node.lineno - 1,
                'module': node.module,
                'full_name': f'{node.module}.{alias.name}' if node.module else alias.name,
                'type': 'from',
                'statement': self.lines[node.lineno - 1]
            }
        self.generic_visit(node)
    
    def visit_Name(self, node):
        """Track name usage"""
        self.used_names.add(node.id)
        self.generic_visit(node)
    
    def visit_Attribute(self, node):
        """Track attribute access"""
        if isinstance(node.value, ast.Name):
            self.used_names.add(node.value.id)
        self.generic_visit(node)
    
    def _identify_unused(self):
        """Identify truly unused imports"""
        unused = []
        
        for name, info in self.imports.items():
            # Skip if used
            if name in self.used_names:
                continue
            
            # Skip false positives
            if name in self.FALSE_POSITIVES:
                continue
            
            # Skip if module name suggests it's a false positive
            if 'full_name' in info:
                full = info['full_name'].lower()
                if any(fp in full for fp in self.FALSE_POSITIVES):
                    continue
            
            # Skip __future__ imports
            if info.get('module') == '__future__':
                continue
            
            unused.append({
                'name': name,
                'line': info['line'],
                'statement': info['statement'],
                'full_name': info.get('full_name', name)
            })
        
        return sorted(unused, key=lambda x: x['line'], reverse=True)


def create_backup(filepath):
    """Create a backup of the file"""
    backup_dir = Path(filepath).parent / '.backups'
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = backup_dir / f"{Path(filepath).name}.{timestamp}.bak"
    
    shutil.copy2(filepath, backup_path)
    return backup_path


def remove_unused_imports(filepath, dry_run=False):
    """Remove unused imports from a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Analyze
        analyzer = SafeImportRemover(content)
        unused = analyzer.analyze()
        
        if not unused:
            return None
        
        if dry_run:
            return {
                'filepath': filepath,
                'unused': unused,
                'dry_run': True
            }
        
        # Create backup
        backup_path = create_backup(filepath)
        
        # Remove unused imports (in reverse order to maintain line numbers)
        lines = content.split('\n')
        removed_lines = []
        
        for imp in unused:
            line_idx = imp['line']
            removed_lines.append(lines[line_idx])
            lines[line_idx] = ''  # Remove the line
        
        # Remove consecutive empty lines created by removal
        new_content = '\n'.join(lines)
        
        # Clean up multiple consecutive blank lines
        while '\n\n\n' in new_content:
            new_content = new_content.replace('\n\n\n', '\n\n')
        
        # Write back
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return {
            'filepath': filepath,
            'unused': unused,
            'backup': backup_path,
            'dry_run': False
        }
        
    except Exception as e:
        return {
            'filepath': filepath,
            'error': str(e)
        }


def process_directory(directory, dry_run=False):
    """Process all Python files in a directory"""
    results = []
    
    directory = Path(directory)
    
    for py_file in directory.rglob('*.py'):
        # Skip venv, migrations, __pycache__
        if any(skip in str(py_file) for skip in ['venv', 'migrations', '__pycache__', '.git', '.backups']):
            continue
        
        result = remove_unused_imports(str(py_file), dry_run)
        if result:
            results.append(result)
    
    return results


def generate_report(results, output_file='unused_imports_removal_report.md'):
    """Generate a report of removed imports"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Unused Imports Removal Report\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        total_files = len(results)
        total_removed = sum(len(r['unused']) for r in results if 'unused' in r)
        errors = [r for r in results if 'error' in r]
        
        f.write("## Summary\n\n")
        f.write(f"- **Files Processed**: {total_files}\n")
        f.write(f"- **Imports Removed**: {total_removed}\n")
        f.write(f"- **Errors**: {len(errors)}\n\n")
        
        if results[0].get('dry_run'):
            f.write("**Mode**: DRY RUN (no files modified)\n\n")
        else:
            f.write("**Mode**: LIVE (files modified, backups created)\n\n")
        
        f.write("## Details\n\n")
        
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
            
            if result.get('backup'):
                f.write(f"**Backup**: {result['backup']}\n\n")
            
            f.write(f"**Removed Imports** ({len(result['unused'])}):\n\n")
            
            for imp in result['unused']:
                f.write(f"- Line {imp['line'] + 1}: `{imp['name']}` (from `{imp['full_name']}`)\n")
                f.write(f"  ```python\n  {imp['statement']}\n  ```\n")
            
            f.write("\n")
        
        if errors:
            f.write("## Errors\n\n")
            for error in errors:
                f.write(f"- {error['filepath']}: {error['error']}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Safely remove unused imports from Python files'
    )
    parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='File or directory to process (default: current directory)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be removed without modifying files'
    )
    parser.add_argument(
        '--report',
        default='unused_imports_removal_report.md',
        help='Output report file (default: unused_imports_removal_report.md)'
    )
    
    args = parser.parse_args()
    
    path = Path(args.path)
    
    if not path.exists():
        print(f"Error: Path '{path}' does not exist")
        sys.exit(1)
    
    print(f"{'🔍 DRY RUN MODE' if args.dry_run else '🔧 LIVE MODE'}")
    print(f"Processing: {path}")
    print()
    
    if path.is_file():
        result = remove_unused_imports(str(path), args.dry_run)
        results = [result] if result else []
    else:
        results = process_directory(path, args.dry_run)
    
    if not results:
        print("✅ No unused imports found!")
        return
    
    # Generate report
    generate_report(results, args.report)
    
    # Summary
    total_files = len(results)
    total_removed = sum(len(r['unused']) for r in results if 'unused' in r)
    
    print(f"📊 Results:")
    print(f"  - Files with unused imports: {total_files}")
    print(f"  - Total imports identified: {total_removed}")
    
    if args.dry_run:
        print(f"\n⚠️  DRY RUN - No files were modified")
        print(f"Run without --dry-run to actually remove imports")
    else:
        print(f"\n✅ Imports removed successfully!")
        print(f"📁 Backups created in .backups/ directories")
    
    print(f"\n📄 Report saved to: {args.report}")


if __name__ == '__main__':
    main()
