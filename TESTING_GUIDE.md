# Testing Guide - Fabric Cutting System Features

## Overview
This guide provides step-by-step instructions for testing the newly implemented features.

---

## Part 1: Installation Orders - Window Count Field

### Test 1: Create New Installation Schedule
**Steps:**
1. Navigate to the installations section
2. Click on "Schedule Installation" or create a new installation order
3. Fill in the required fields
4. Locate the "عدد الشبابيك" (Number of Windows) field
5. Enter a number (e.g., 5)
6. Submit the form

**Expected Results:**
- ✅ The windows count field should be visible in the form
- ✅ The field should accept positive integers only
- ✅ The form should save successfully
- ✅ No validation errors should occur

### Test 2: Edit Existing Installation Schedule
**Steps:**
1. Navigate to an existing installation schedule
2. Click "Edit" or "تعديل"
3. Locate the "عدد الشبابيك" field
4. Change the value (or add a value if empty)
5. Save the changes

**Expected Results:**
- ✅ The windows count field should be visible and editable
- ✅ Changes should save successfully
- ✅ The new value should persist after saving

### Test 3: View Installation Details
**Steps:**
1. Navigate to an installation detail page
2. Look for the "عدد الشبابيك" field in the details section

**Expected Results:**
- ✅ If windows count is set, it should display as a badge with the number
- ✅ If not set, it should show "غير محدد" (Not specified)
- ✅ The field should be clearly labeled

### Test 4: Daily Schedule View
**Steps:**
1. Navigate to the daily installation schedule view
2. Check the table for the windows count column

**Expected Results:**
- ✅ Windows count should display for each installation
- ✅ Empty values should show "غير محدد"
- ✅ The column should be properly aligned

---

## Part 2: Warehouse Staff Role and Permissions System

### Test 5: Create Warehouse Staff User
**Steps:**
1. Login as admin/superuser
2. Navigate to Django Admin: `/admin/`
3. Go to Users section
4. Click "Add User" or select an existing user
5. Scroll to "أدوار المستودع" (Warehouse Roles) section
6. Check "موظف مستودع" (is_warehouse_staff)
7. Select a warehouse from "المستودع المخصص" (assigned_warehouse) dropdown
8. Save the user

**Expected Results:**
- ✅ The warehouse roles section should be visible
- ✅ Both fields should be present and functional
- ✅ User should save successfully
- ✅ In the user list, the new columns should show the warehouse staff status

### Test 6: Warehouse Staff User Without Assigned Warehouse (Validation Test)
**Steps:**
1. In Django Admin, create or edit a user
2. Check "موظف مستودع" (is_warehouse_staff)
3. Leave "المستودع المخصص" (assigned_warehouse) empty
4. Try to save

**Expected Results:**
- ✅ Validation error should appear
- ✅ Error message: "يجب تحديد مستودع مخصص لموظف المستودع"
- ✅ User should NOT save until warehouse is assigned

### Test 7: Warehouse Staff Login and Navigation
**Steps:**
1. Logout from admin account
2. Login as the warehouse staff user created in Test 5
3. Check the navigation menu

**Expected Results:**
- ✅ Navigation should show ONLY:
  - الرئيسية (Home)
  - نظام التقطيع (Cutting System)
  - [Warehouse Name] (Their assigned warehouse)
  - أوامر التقطيع المجمعة (Completed Cutting Orders)
- ✅ Should NOT see:
  - العملاء (Customers)
  - الطلبات (Orders)
  - المخزون (Full Inventory)
  - المعاينات (Inspections)
  - التركيبات (Installations)
  - المصنع (Manufacturing)
  - الشكاوى (Complaints)
  - التقارير (Reports)
  - إدارة البيانات (Database Management)

### Test 8: Warehouse Staff - Cutting Orders Access
**Steps:**
1. As warehouse staff user, click on "نظام التقطيع"
2. Observe the cutting orders displayed

**Expected Results:**
- ✅ Should see only orders from their assigned warehouse
- ✅ Should see only INCOMPLETE orders (pending, in_progress)
- ✅ Should NOT see completed orders on this page
- ✅ All filters should work correctly

### Test 9: Warehouse Staff - Assigned Warehouse View
**Steps:**
1. As warehouse staff user, click on their warehouse name in navigation
2. Observe the orders displayed

**Expected Results:**
- ✅ Should see only orders from their assigned warehouse
- ✅ Should see only incomplete orders
- ✅ URL should be: `/cutting/orders/warehouse/{warehouse_id}/`

### Test 10: Warehouse Staff - Completed Orders Page
**Steps:**
1. As warehouse staff user, click on "أوامر التقطيع المجمعة"
2. Test the filters:
   - Select different warehouses (should only see their warehouse)
   - Filter by status: completed, incomplete, partially completed
   - Search by cutting code, contract number, customer name
3. Check pagination if there are many orders

**Expected Results:**
- ✅ Page should load successfully
- ✅ Warehouse filter should only show their assigned warehouse
- ✅ Status filters should work correctly:
  - "مكتملة" shows only completed orders
  - "غير مكتملة" shows only incomplete orders
  - "مكتملة جزئياً" shows partially completed orders
- ✅ Search should filter results correctly
- ✅ Table should display all order details clearly
- ✅ Progress bars should show correct percentages
- ✅ Status badges should have correct colors
- ✅ Pagination should work if applicable

### Test 11: Warehouse Staff - Access Restrictions
**Steps:**
1. As warehouse staff user, try to access restricted URLs directly:
   - `/customers/`
   - `/orders/`
   - `/inventory/`
   - `/inspections/`
   - `/installations/`
   - `/manufacturing/`
   - `/complaints/`
   - `/reports/list/`

**Expected Results:**
- ✅ Should be redirected or see "Permission Denied"
- ✅ Should not be able to access these sections

### Test 12: Regular Staff User - Full Access
**Steps:**
1. Logout from warehouse staff account
2. Login as a regular staff user (is_staff=True, is_warehouse_staff=False)
3. Check navigation and access

**Expected Results:**
- ✅ Should see full navigation menu
- ✅ Should have access to all sections
- ✅ In cutting system, should see all warehouses
- ✅ Should see both complete and incomplete orders
- ✅ Completed orders page should show all warehouses

### Test 13: Cutting Order Cards - Compact Design
**Steps:**
1. Login as any user with cutting system access
2. Navigate to cutting orders page: `/cutting/orders/`
3. Observe the card layout

**Expected Results:**
- ✅ Cards should be more compact than before
- ✅ Should display 2 cards per row (on large screens)
- ✅ All important information should still be visible:
  - Cutting code
  - Customer name
  - Contract number
  - Invoice number
  - Warehouse name
  - Branch (if applicable)
  - Salesperson (if applicable)
  - Order type/destination badge
  - Status badge
  - Progress circle with percentage
  - Item statistics (total, completed, pending)
  - Creation date
  - Assigned person
  - Action buttons
- ✅ Cards should have proper spacing and alignment
- ✅ Hover effect should work
- ✅ Cards should be responsive on mobile devices

### Test 14: Admin Interface - Warehouse Staff Management
**Steps:**
1. Login as admin
2. Go to Django Admin: `/admin/`
3. Navigate to Users
4. Check the list view

**Expected Results:**
- ✅ List should show "is_warehouse_staff" column
- ✅ List should show "assigned_warehouse" column
- ✅ Filter sidebar should include "is_warehouse_staff" filter
- ✅ Clicking filter should show only warehouse staff users

**Steps (continued):**
5. Click on a user to edit
6. Scroll to "أدوار المستودع" section

**Expected Results:**
- ✅ Section should be clearly visible (not collapsed)
- ✅ Should contain both fields with proper labels
- ✅ Description should be present
- ✅ Warehouse dropdown should show all active warehouses

---

## Edge Cases and Error Handling

### Test 15: Warehouse Staff with Deleted Warehouse
**Steps:**
1. Create a warehouse staff user with assigned warehouse
2. In admin, deactivate or delete the assigned warehouse
3. Login as that warehouse staff user

**Expected Results:**
- ✅ System should handle gracefully (no crashes)
- ✅ User should see empty results or appropriate message
- ✅ No server errors should occur

### Test 16: Multiple Warehouse Staff Users
**Steps:**
1. Create multiple warehouse staff users
2. Assign different warehouses to each
3. Login as each user and verify they only see their warehouse

**Expected Results:**
- ✅ Each user should only see their assigned warehouse
- ✅ No data leakage between warehouse staff users

### Test 17: Warehouse Staff Promotion to Regular Staff
**Steps:**
1. Take a warehouse staff user
2. In admin, uncheck "is_warehouse_staff"
3. Check "is_staff" instead
4. Save and login as that user

**Expected Results:**
- ✅ User should now see full navigation
- ✅ User should have access to all sections
- ✅ No errors should occur

---

## Performance Testing

### Test 18: Large Dataset Performance
**Steps:**
1. Ensure there are many cutting orders (100+)
2. Login as warehouse staff
3. Navigate through pages
4. Test filters and search

**Expected Results:**
- ✅ Pages should load quickly (< 2 seconds)
- ✅ Pagination should work smoothly
- ✅ Filters should respond quickly
- ✅ No database query timeouts

---

## Browser Compatibility

### Test 19: Cross-Browser Testing
**Browsers to Test:**
- Chrome
- Firefox
- Safari
- Edge

**Steps:**
1. Test all features in each browser
2. Check responsive design on mobile browsers

**Expected Results:**
- ✅ All features should work in all browsers
- ✅ Layout should be consistent
- ✅ No JavaScript errors in console
- ✅ Mobile responsive design should work properly

---

## Checklist Summary

### Part 1 - Installation Orders:
- [ ] Create new installation with windows count
- [ ] Edit existing installation windows count
- [ ] View installation details with windows count
- [ ] Check daily schedule display

### Part 2 - Warehouse Staff:
- [ ] Create warehouse staff user in admin
- [ ] Test validation (warehouse staff without warehouse)
- [ ] Login as warehouse staff and check navigation
- [ ] Verify cutting orders access (incomplete only)
- [ ] Test assigned warehouse view
- [ ] Test completed orders page with all filters
- [ ] Verify access restrictions
- [ ] Test regular staff full access
- [ ] Check compact card design
- [ ] Verify admin interface updates
- [ ] Test edge cases
- [ ] Performance testing
- [ ] Cross-browser testing

---

## Reporting Issues

If you encounter any issues during testing:

1. **Document the issue:**
   - What were you trying to do?
   - What did you expect to happen?
   - What actually happened?
   - Steps to reproduce

2. **Check browser console:**
   - Are there any JavaScript errors?
   - Are there any network errors?

3. **Check server logs:**
   - Are there any Python exceptions?
   - Are there any database errors?

4. **Provide screenshots:**
   - Screenshot of the issue
   - Screenshot of browser console (if applicable)

---

## Success Criteria

All tests should pass with:
- ✅ No server errors (500 errors)
- ✅ No database errors
- ✅ No JavaScript console errors
- ✅ Proper validation messages
- ✅ Correct permission enforcement
- ✅ Responsive design working
- ✅ All features functioning as specified

---

## Post-Testing

After successful testing:
1. Document any issues found and fixed
2. Update user documentation if needed
3. Train warehouse staff users on new features
4. Monitor system for any issues in production
5. Gather user feedback for future improvements

