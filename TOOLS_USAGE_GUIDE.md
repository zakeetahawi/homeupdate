# Optimization Tools Usage Guide

## Overview

Three powerful automation tools have been created to help you optimize the codebase:

1. **analyze_codebase.py** - Complete codebase analyzer
2. **remove_unused_imports.py** - Safe unused import remover
3. **apply_query_optimizations.py** - Query optimization analyzer

---

## Tool 1: analyze_codebase.py

### Purpose
Complete analysis of the codebase to identify:
- Unused imports
- Unused functions and classes
- N+1 query patterns
- Missing select_related/prefetch_related

### Usage

```bash
# Analyze entire project
python analyze_codebase.py . CODEBASE_ANALYSIS_REPORT.md

# Analyze specific directory
python analyze_codebase.py accounts/ analysis_accounts.md

# Analyze single file
python analyze_codebase.py orders/views.py analysis_orders.md
```

### Output
- Generates comprehensive Markdown report
- Shows unused code with line numbers
- Identifies query optimization opportunities
- Provides statistics and metrics

### Example Output
```
Analyzing project in: .
This may take a few minutes...

✅ Analysis complete!
📊 Report saved to: CODEBASE_ANALYSIS_REPORT.md

📈 Summary:
  - Files analyzed: 432
  - Files with issues: 359
  - Unused imports: 516
  - Unused functions: 2336
  - Query issues: 1423
```

### When to Use
- Before major refactoring
- Monthly code quality checks
- After large feature additions
- To track improvement over time

---

## Tool 2: remove_unused_imports.py

### Purpose
Safely removes unused imports with:
- Automatic backups before changes
- False positive detection
- Dry-run mode for preview
- Detailed change reports

### Usage

```bash
# DRY RUN (preview only - no changes)
python remove_unused_imports.py --dry-run .
python remove_unused_imports.py --dry-run accounts/admin.py

# LIVE RUN (actually removes imports)
python remove_unused_imports.py .
python remove_unused_imports.py accounts/

# Custom report location
python remove_unused_imports.py --report my_report.md accounts/
```

### Safety Features

1. **Automatic Backups**
   - Creates `.backups/` directory
   - Timestamped backups of all modified files
   - Easy rollback if needed

2. **False Positive Detection**
   Skips removing:
   - Django signal imports
   - Decorator imports
   - Admin auto-registration imports
   - Type hint imports
   - Star imports (too risky)

3. **Dry Run Mode**
   - Preview what would be removed
   - No files modified
   - Generate report to review

### Example Workflow

```bash
# Step 1: Dry run to see what would be removed
python remove_unused_imports.py --dry-run .

# Step 2: Review the report
cat unused_imports_removal_report.md

# Step 3: If satisfied, run for real
python remove_unused_imports.py .

# Step 4: Test your application
python manage.py test

# Step 5: If tests fail, restore from backups
# Backups are in .backups/ directories
```

### Example Output
```
🔍 DRY RUN MODE
Processing: .

📊 Results:
  - Files with unused imports: 45
  - Total imports identified: 156

⚠️  DRY RUN - No files were modified
Run without --dry-run to actually remove imports

📄 Report saved to: unused_imports_removal_report.md
```

### Report Format
```markdown
# Unused Imports Removal Report

## Summary
- Files Processed: 45
- Imports Removed: 156
- Errors: 0

## Details

### accounts/admin.py
**Removed Imports** (7):
- Line 8: `format_html` (from `django.utils.html.format_html`)
- Line 12: `ActivityLog` (from `models.ActivityLog`)
...
```

### Restoring from Backup
```bash
# Find backup
ls accounts/.backups/

# Restore specific file
cp accounts/.backups/admin.py.20240101_120000.bak accounts/admin.py
```

---

## Tool 3: apply_query_optimizations.py

### Purpose
Analyzes Django code for query optimization opportunities:
- Missing select_related()
- Missing prefetch_related()
- N+1 queries in loops
- Admin classes without get_queryset()
- List comprehensions with foreign key access

### Usage

```bash
# Quick check (just counts)
python apply_query_optimizations.py --check .
python apply_query_optimizations.py --check orders/views.py

# Full analysis with report
python apply_query_optimizations.py .
python apply_query_optimizations.py manufacturing/

# Custom report location
python apply_query_optimizations.py --report my_report.md views/
```

### What It Detects

1. **Missing select_related()**
   ```python
   # ❌ Bad - N+1 queries
   orders = Order.objects.filter(status='pending')
   
   # ✅ Good - Single query
   orders = Order.objects.select_related('customer', 'salesperson').filter(status='pending')
   ```

2. **N+1 in Loops**
   ```python
   # ❌ Bad
   for order in orders:
       print(order.customer.name)  # New query each time!
   
   # ✅ Good
   orders = orders.select_related('customer')
   for order in orders:
       print(order.customer.name)  # Already loaded
   ```

3. **Admin Without get_queryset()**
   ```python
   # ❌ Bad
   class OrderAdmin(admin.ModelAdmin):
       list_display = ['order_number', 'customer', 'salesperson']
       # N+1 on list page!
   
   # ✅ Good
   class OrderAdmin(admin.ModelAdmin):
       list_display = ['order_number', 'customer', 'salesperson']
       
       def get_queryset(self, request):
           qs = super().get_queryset(request)
           return qs.select_related('customer', 'salesperson')
   ```

### Example Output
```
🔍 Analyzing query patterns...

📊 Results:
  - Files with issues: 28
  - Total issues: 187
  - High severity: 142

🎯 Top Files to Optimize:
  - manufacturing/views.py: 65 issues
  - orders/views.py: 48 issues
  - installations/views.py: 42 issues
  - inventory/views.py: 35 issues
  - accounts/admin.py: 25 issues

📄 Detailed report saved to: query_optimization_report.md
```

### Report Format
```markdown
## Detailed Findings

### orders/views.py

**Issues Found**: 48

#### Missing Select Related (35 instances)

**Line 80** - high severity
```python
orders = Order.objects.filter(branch__id=branch_filter)
```

💡 **Suggestion**: Add .select_related('related_field') after Order.objects

...
```

---

## Recommended Workflow

### Phase 1: Analysis (Week 1)

```bash
# 1. Run complete analysis
python analyze_codebase.py . CODEBASE_ANALYSIS_REPORT.md

# 2. Run query optimization analysis
python apply_query_optimizations.py . query_optimization_report.md

# 3. Review reports
cat CODEBASE_ANALYSIS_REPORT.md | less
cat query_optimization_report.md | less
```

### Phase 2: Code Cleanup (Week 2)

```bash
# 1. Dry run to see what would be removed
python remove_unused_imports.py --dry-run .

# 2. Review the report carefully
cat unused_imports_removal_report.md

# 3. If satisfied, remove unused imports
python remove_unused_imports.py .

# 4. Run tests to verify
python manage.py test

# 5. If issues, restore from .backups/
```

### Phase 3: Query Optimization (Week 3-4)

```bash
# 1. Check specific files
python apply_query_optimizations.py orders/views.py
python apply_query_optimizations.py manufacturing/views.py

# 2. Manually apply optimizations from report
# See QUERY_OPTIMIZATION_GUIDE.md for examples

# 3. Test each change
python manage.py test

# 4. Measure performance improvement
# Use Django Debug Toolbar to verify query counts
```

### Phase 4: Continuous Monitoring (Monthly)

```bash
# Run analysis monthly
python analyze_codebase.py . monthly_report_$(date +%Y%m).md

# Compare with previous month
diff monthly_report_202410.md monthly_report_202411.md
```

---

## Safety Best Practices

### Before Running Any Tool

1. **Commit Current Changes**
   ```bash
   git add .
   git commit -m "Before optimization"
   ```

2. **Create a Branch**
   ```bash
   git checkout -b optimization-$(date +%Y%m%d)
   ```

3. **Run in Dry-Run Mode First**
   ```bash
   python remove_unused_imports.py --dry-run .
   ```

4. **Review Reports Thoroughly**
   - Check for false positives
   - Verify suggestions make sense
   - Plan implementation order

### After Running Tools

1. **Run Tests**
   ```bash
   python manage.py test
   ```

2. **Check for Syntax Errors**
   ```bash
   python manage.py check
   ```

3. **Manual Review**
   ```bash
   git diff
   ```

4. **Test Critical Features**
   - Login/logout
   - Create order
   - View dashboard
   - Run reports

5. **Commit Changes**
   ```bash
   git add .
   git commit -m "Remove unused imports - batch 1"
   ```

---

## Troubleshooting

### Tool Fails with Syntax Error

```bash
# Check which file has syntax error
python -m py_compile path/to/file.py

# Fix syntax error first
# Then re-run tool
```

### Too Many False Positives

Edit the tool's FALSE_POSITIVES list:

```python
# In remove_unused_imports.py
FALSE_POSITIVES = {
    'signals', 'receivers', 'admin',
    # Add your project-specific names
    'my_custom_decorator',
    'my_signal_handler',
}
```

### Backup Not Created

Check permissions:
```bash
ls -la .backups/
chmod 755 .backups/
```

### Report Too Large

Filter to specific directory:
```bash
# Analyze just one app
python analyze_codebase.py orders/ orders_analysis.md
```

---

## Performance Tips

### For Large Projects

```bash
# Analyze in batches
for app in accounts orders manufacturing; do
    python analyze_codebase.py $app/ ${app}_analysis.md
done

# Remove imports in batches (safer)
python remove_unused_imports.py accounts/
# Test
python remove_unused_imports.py orders/
# Test
```

### Speed Up Analysis

```bash
# Skip test files
python analyze_codebase.py . --exclude tests/

# Skip migrations (already excluded by default)
```

---

## Integration with CI/CD

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
python remove_unused_imports.py --dry-run . > /dev/null
if [ $? -ne 0 ]; then
    echo "Unused imports detected! Review report."
    exit 1
fi
```

### Monthly Cron Job

```bash
# crontab -e
0 0 1 * * cd /path/to/project && python analyze_codebase.py . monthly_report.md
```

---

## Advanced Usage

### Combine Tools

```bash
# Complete optimization pipeline
python analyze_codebase.py . analysis.md
python remove_unused_imports.py --dry-run .
python apply_query_optimizations.py .

# Review all reports
ls -lh *report*.md *analysis*.md
```

### Custom Scripts

Create your own based on the tools:

```python
from remove_unused_imports import SafeImportRemover

# Custom analysis
with open('myfile.py') as f:
    analyzer = SafeImportRemover(f.read())
    unused = analyzer.analyze()
    print(f"Found {len(unused)} unused imports")
```

---

## Summary

| Tool | Purpose | Safety | Speed | Output |
|------|---------|--------|-------|--------|
| analyze_codebase.py | Complete analysis | Read-only | Slow (~2 min) | Detailed MD |
| remove_unused_imports.py | Remove imports | Auto-backup | Fast (<30s) | Simple MD |
| apply_query_optimizations.py | Find N+1 queries | Read-only | Fast (<30s) | Detailed MD |

### Quick Reference

```bash
# Analysis
python analyze_codebase.py .

# Cleanup (with safety)
python remove_unused_imports.py --dry-run .
python remove_unused_imports.py .

# Optimization hints
python apply_query_optimizations.py .

# Always test after changes!
python manage.py test
```

---

## Support

For issues or questions:
1. Check the tool's help: `python tool_name.py --help`
2. Review generated reports
3. Check `.backups/` for file restoration
4. Review `QUERY_OPTIMIZATION_GUIDE.md` for implementation details

---

*Tools created as part of comprehensive codebase optimization project*  
*All tools include safety features and detailed reporting*  
*Use with confidence but always test after changes!*
