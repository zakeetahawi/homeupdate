#!/usr/bin/env python3
"""
Comprehensive codebase analyzer for Django project
Analyzes for:
- Unused imports
- Unused functions/classes
- N+1 query patterns
- Missing select_related/prefetch_related
- Query optimization opportunities
"""

import ast
import os
import re
from collections import defaultdict
from pathlib import Path


class CodeAnalyzer(ast.NodeVisitor):
    """AST-based code analyzer"""

    def __init__(self, filepath):
        self.filepath = filepath
        self.imports = {}
        self.used_names = set()
        self.functions = {}
        self.classes = {}
        self.function_calls = set()
        self.django_queries = []
        self.n_plus_one_patterns = []

    def visit_Import(self, node):
        """Track imports"""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name.split(".")[0]
            self.imports[name] = {
                "full_name": alias.name,
                "line": node.lineno,
                "used": False,
            }
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Track from imports"""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            full_name = f"{node.module}.{alias.name}" if node.module else alias.name
            self.imports[name] = {
                "full_name": full_name,
                "line": node.lineno,
                "used": False,
            }
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        """Track function definitions"""
        self.functions[node.name] = {
            "line": node.lineno,
            "called": False,
            "is_method": False,
            "decorators": [
                d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list
            ],
        }
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """Track class definitions"""
        self.classes[node.name] = {"line": node.lineno, "used": False, "methods": []}

        # Mark methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                self.functions[item.name] = {
                    "line": item.lineno,
                    "called": False,
                    "is_method": True,
                    "class": node.name,
                    "decorators": [
                        d.id if isinstance(d, ast.Name) else str(d)
                        for d in item.decorator_list
                    ],
                }
                self.classes[node.name]["methods"].append(item.name)

        self.generic_visit(node)

    def visit_Name(self, node):
        """Track name usage"""
        self.used_names.add(node.id)
        if node.id in self.imports:
            self.imports[node.id]["used"] = True
        if node.id in self.classes:
            self.classes[node.id]["used"] = True
        self.generic_visit(node)

    def visit_Call(self, node):
        """Track function calls and Django ORM patterns"""
        # Track function calls
        if isinstance(node.func, ast.Name):
            self.function_calls.add(node.func.id)
            if node.func.id in self.functions:
                self.functions[node.func.id]["called"] = True
        elif isinstance(node.func, ast.Attribute):
            # Track Django ORM queries
            if isinstance(node.func.value, ast.Name):
                if node.func.attr in ["filter", "all", "get", "create", "update"]:
                    self.django_queries.append(
                        {
                            "type": node.func.attr,
                            "line": node.lineno,
                            "model": node.func.value.id,
                        }
                    )

        self.generic_visit(node)

    def visit_For(self, node):
        """Detect potential N+1 queries in loops"""
        # Look for foreign key access in loops
        for child in ast.walk(node):
            if isinstance(child, ast.Attribute):
                # Pattern: for item in items: item.foreign_key.attribute
                self.n_plus_one_patterns.append(
                    {
                        "line": node.lineno,
                        "context": (
                            ast.unparse(node.target)
                            if hasattr(ast, "unparse")
                            else "loop"
                        ),
                    }
                )
                break
        self.generic_visit(node)


def analyze_file(filepath):
    """Analyze a single Python file"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filepath)
        analyzer = CodeAnalyzer(filepath)
        analyzer.visit(tree)

        return {
            "filepath": filepath,
            "unused_imports": {
                k: v for k, v in analyzer.imports.items() if not v["used"]
            },
            "unused_functions": {
                k: v
                for k, v in analyzer.functions.items()
                if not v["called"]
                and not v["is_method"]
                and not any(
                    d in ["property", "cached_property", "classmethod", "staticmethod"]
                    for d in v["decorators"]
                )
            },
            "unused_classes": {
                k: v for k, v in analyzer.classes.items() if not v["used"]
            },
            "django_queries": analyzer.django_queries,
            "n_plus_one_patterns": analyzer.n_plus_one_patterns,
        }
    except SyntaxError as e:
        return {
            "filepath": filepath,
            "error": f"Syntax error: {e}",
            "unused_imports": {},
            "unused_functions": {},
            "unused_classes": {},
            "django_queries": [],
            "n_plus_one_patterns": [],
        }
    except Exception as e:
        return {
            "filepath": filepath,
            "error": f"Error: {e}",
            "unused_imports": {},
            "unused_functions": {},
            "unused_classes": {},
            "django_queries": [],
            "n_plus_one_patterns": [],
        }


def find_query_optimizations(filepath):
    """Find Django query optimization opportunities"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        issues = []

        # Pattern 1: .filter() without select_related
        if re.search(r"\.filter\([^)]*\)(?!.*\.select_related)", content):
            for i, line in enumerate(content.split("\n"), 1):
                if (
                    ".filter(" in line
                    and "select_related" not in line
                    and "prefetch_related" not in line
                ):
                    if (
                        "__" in line or "ForeignKey" in line
                    ):  # Likely foreign key access
                        issues.append(
                            {
                                "line": i,
                                "type": "missing_select_related",
                                "snippet": line.strip()[:80],
                            }
                        )

        # Pattern 2: for loop with foreign key access
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "for " in line and " in " in line:
                # Check next few lines for foreign key access
                for j in range(i + 1, min(i + 10, len(lines))):
                    if "." in lines[j] and "__" not in lines[j]:
                        issues.append(
                            {
                                "line": i + 1,
                                "type": "potential_n_plus_one",
                                "snippet": line.strip()[:80],
                            }
                        )
                        break

        return issues
    except:
        return []


def analyze_project(base_dir):
    """Analyze entire project"""
    base_path = Path(base_dir)
    results = {
        "total_files": 0,
        "files_with_issues": 0,
        "total_unused_imports": 0,
        "total_unused_functions": 0,
        "total_unused_classes": 0,
        "total_query_issues": 0,
        "files": [],
    }

    # Find all Python files
    for py_file in base_path.rglob("*.py"):
        # Skip venv, migrations, __pycache__
        if any(
            skip in str(py_file)
            for skip in ["venv", "migrations", "__pycache__", ".git"]
        ):
            continue

        results["total_files"] += 1

        # Analyze file
        analysis = analyze_file(str(py_file))
        query_issues = find_query_optimizations(str(py_file))

        has_issues = (
            analysis["unused_imports"]
            or analysis["unused_functions"]
            or analysis["unused_classes"]
            or query_issues
        )

        if has_issues:
            results["files_with_issues"] += 1
            results["total_unused_imports"] += len(analysis["unused_imports"])
            results["total_unused_functions"] += len(analysis["unused_functions"])
            results["total_unused_classes"] += len(analysis["unused_classes"])
            results["total_query_issues"] += len(query_issues)

            analysis["query_optimizations"] = query_issues
            analysis["relative_path"] = str(py_file.relative_to(base_path))
            results["files"].append(analysis)

    return results


def generate_report(results, output_file):
    """Generate detailed report"""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# Codebase Analysis Report\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"- Total Files Analyzed: {results['total_files']}\n")
        f.write(f"- Files with Issues: {results['files_with_issues']}\n")
        f.write(f"- Total Unused Imports: {results['total_unused_imports']}\n")
        f.write(f"- Total Unused Functions: {results['total_unused_functions']}\n")
        f.write(f"- Total Unused Classes: {results['total_unused_classes']}\n")
        f.write(
            f"- Total Query Optimization Issues: {results['total_query_issues']}\n\n"
        )

        f.write("## Detailed Findings\n\n")

        for file_data in sorted(
            results["files"], key=lambda x: len(x["unused_imports"]), reverse=True
        ):
            if file_data.get("error"):
                f.write(f"### {file_data['relative_path']}\n\n")
                f.write(f"**Error**: {file_data['error']}\n\n")
                continue

            f.write(f"### {file_data['relative_path']}\n\n")

            if file_data["unused_imports"]:
                f.write(f"#### Unused Imports ({len(file_data['unused_imports'])})\n\n")
                for name, info in file_data["unused_imports"].items():
                    f.write(
                        f"- Line {info['line']}: `{name}` (from `{info['full_name']}`)\n"
                    )
                f.write("\n")

            if file_data["unused_functions"]:
                f.write(
                    f"#### Unused Functions ({len(file_data['unused_functions'])})\n\n"
                )
                for name, info in file_data["unused_functions"].items():
                    f.write(f"- Line {info['line']}: `{name}()`\n")
                f.write("\n")

            if file_data["unused_classes"]:
                f.write(f"#### Unused Classes ({len(file_data['unused_classes'])})\n\n")
                for name, info in file_data["unused_classes"].items():
                    f.write(f"- Line {info['line']}: `{name}`\n")
                f.write("\n")

            if file_data.get("query_optimizations"):
                f.write(
                    f"#### Query Optimization Opportunities ({len(file_data['query_optimizations'])})\n\n"
                )
                for issue in file_data["query_optimizations"]:
                    f.write(f"- Line {issue['line']}: {issue['type']}\n")
                    f.write(f"  ```python\n  {issue['snippet']}\n  ```\n")
                f.write("\n")


if __name__ == "__main__":
    import sys

    base_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    output_file = sys.argv[2] if len(sys.argv) > 2 else "CODEBASE_ANALYSIS_REPORT.md"

    print(f"Analyzing project in: {base_dir}")
    print("This may take a few minutes...")

    results = analyze_project(base_dir)
    generate_report(results, output_file)

    print(f"\n✅ Analysis complete!")
    print(f"📊 Report saved to: {output_file}")
    print(f"\n📈 Summary:")
    print(f"  - Files analyzed: {results['total_files']}")
    print(f"  - Files with issues: {results['files_with_issues']}")
    print(f"  - Unused imports: {results['total_unused_imports']}")
    print(f"  - Unused functions: {results['total_unused_functions']}")
    print(f"  - Query issues: {results['total_query_issues']}")
