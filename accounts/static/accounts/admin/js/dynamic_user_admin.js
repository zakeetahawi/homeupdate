/**
 * نظام الأقسام الديناميكية في نموذج المستخدم - Django Admin
 * Dynamic Department Sections for User Admin Form
 *
 * يُظهر/يُخفي أقسام الأدوار بناءً على اختيار القسم الوظيفي
 * ويُظهر الحقول المرتبطة بكل دور تلقائياً عند تفعيله
 */
(function($) {
    'use strict';

    // ─── تعريف الأقسام وحقولها ───────────────────────────────────
    const DEPARTMENT_SECTIONS = {
        sales: {
            label: 'المبيعات والإدارة',
            icon: '🏪',
            fieldsetIndex: null, // سيتم تحديده ديناميكياً
            headerText: 'أدوار المبيعات والإدارة',
            roleFields: [
                'is_salesperson', 'is_branch_manager', 'is_region_manager',
                'is_sales_manager', 'is_traffic_manager'
            ],
            // حقول تظهر فقط عند تفعيل دور معين
            conditionalFields: {
                'is_branch_manager': ['managed_branches'],
                'is_region_manager': ['managed_branches'],
                'is_sales_manager': ['managed_branches'],
            }
        },
        factory: {
            label: 'المصنع',
            icon: '🏭',
            fieldsetIndex: null,
            headerText: 'أدوار المصنع',
            roleFields: [
                'is_factory_manager', 'is_factory_accountant', 'is_factory_receiver'
            ],
            conditionalFields: {}
        },
        inspections: {
            label: 'المعاينات والتركيبات',
            icon: '🔍',
            fieldsetIndex: null,
            headerText: 'أدوار المعاينات والتركيبات',
            roleFields: [
                'is_inspection_technician', 'is_inspection_manager', 'is_installation_manager'
            ],
            conditionalFields: {}
        },
        warehouse: {
            label: 'المستودع',
            icon: '📦',
            fieldsetIndex: null,
            headerText: 'أدوار المستودع',
            roleFields: ['is_warehouse_staff'],
            conditionalFields: {
                'is_warehouse_staff': ['assigned_warehouse', 'assigned_warehouses']
            }
        },
        external_sales: {
            label: 'المبيعات الخارجية',
            icon: '🏗️',
            fieldsetIndex: null,
            headerText: 'المبيعات الخارجية',
            roleFields: [
                'is_decorator_dept_manager', 'is_decorator_dept_staff'
            ],
            conditionalFields: {}
        }
    };

    // أقسام تظهر دائماً (ليست أدوار وظيفية)
    const ALWAYS_VISIBLE_HEADERS = [
        'معلومات شخصية',
        'الحالة والنظام',
        'تواريخ مهمة'
    ];

    // أقسام ثانوية (تظهر أسفل الصفحة، مطوية)
    const SECONDARY_HEADERS = [
        'صلاحيات إضافية',
        'المجموعات والصلاحيات المتقدمة',
        'الأجهزة المصرح بها'
    ];

    // ─── دوال مساعدة ─────────────────────────────────────────────

    /**
     * البحث عن fieldset بواسطة عنوان h2
     */
    function findFieldsetByHeader(text) {
        var result = null;
        $('fieldset').each(function() {
            var $h2 = $(this).find('h2:first');
            if ($h2.length && $h2.text().trim().indexOf(text) !== -1) {
                result = $(this);
                return false;
            }
        });
        return result;
    }

    /**
     * البحث عن div.form-row لحقل معين
     */
    function findFieldRow(fieldName) {
        return $('.form-row.field-' + fieldName);
    }

    /**
     * فحص هل حقل checkbox مفعّل
     */
    function isFieldChecked(fieldName) {
        var $el = $('#id_' + fieldName);
        return $el.length && $el.is(':checked');
    }

    /**
     * فحص هل يوجد أي دور مفعّل في قسم معين
     */
    function hasActiveRoleInSection(sectionKey) {
        var section = DEPARTMENT_SECTIONS[sectionKey];
        for (var i = 0; i < section.roleFields.length; i++) {
            if (isFieldChecked(section.roleFields[i])) {
                return true;
            }
        }
        return false;
    }

    /**
     * جمع كل الأقسام التي لديها أدوار مفعّلة
     */
    function getActiveDepartments() {
        var active = [];
        for (var key in DEPARTMENT_SECTIONS) {
            if (hasActiveRoleInSection(key)) {
                active.push(key);
            }
        }
        return active;
    }

    // ─── بناء واجهة اختيار الأقسام ──────────────────────────────

    function buildDepartmentChooser() {
        var activeDepts = getActiveDepartments();

        var html = '<fieldset id="dept-chooser-fieldset" class="module aligned dept-chooser">';
        html += '<h2>🎯 اختيار القسم الوظيفي</h2>';
        html += '<div class="description help">اختر الأقسام لعرض الأدوار المتاحة فيها — يمكنك اختيار أكثر من قسم</div>';
        html += '<div class="dept-chooser-grid">';

        for (var key in DEPARTMENT_SECTIONS) {
            var dept = DEPARTMENT_SECTIONS[key];
            var isActive = activeDepts.indexOf(key) !== -1;
            var checkedAttr = isActive ? ' checked' : '';
            var activeClass = isActive ? ' active' : '';

            html += '<label class="dept-chip' + activeClass + '" data-dept="' + key + '">';
            html += '<input type="checkbox" class="dept-toggle" value="' + key + '"' + checkedAttr + '>';
            html += '<span class="dept-icon">' + dept.icon + '</span>';
            html += '<span class="dept-label">' + dept.label + '</span>';
            html += '</label>';
        }

        html += '</div>';
        html += '</fieldset>';

        return html;
    }

    // ─── ربط الـ fieldsets بالأقسام ──────────────────────────────

    function mapFieldsetsToSections() {
        for (var key in DEPARTMENT_SECTIONS) {
            var section = DEPARTMENT_SECTIONS[key];
            var $fs = findFieldsetByHeader(section.headerText);
            if ($fs) {
                $fs.attr('data-dept-section', key);
                section.$fieldset = $fs;
            }
        }
    }

    // ─── إظهار/إخفاء الأقسام ────────────────────────────────────

    function toggleDepartmentSection(deptKey, show) {
        var section = DEPARTMENT_SECTIONS[deptKey];
        if (!section || !section.$fieldset) return;

        if (show) {
            section.$fieldset
                .slideDown(250)
                .removeClass('collapsed dept-hidden');
            // فتح الـ fieldset إذا كان مطوياً
            section.$fieldset.find('h2 a.collapse-toggle').each(function() {
                if ($(this).text().indexOf('إظهار') !== -1 || $(this).text().indexOf('Show') !== -1) {
                    $(this).trigger('click');
                }
            });
        } else {
            // لا تخفي إذا فيه أدوار مفعّلة
            if (hasActiveRoleInSection(deptKey)) {
                return;
            }
            section.$fieldset
                .slideUp(250)
                .addClass('dept-hidden');
        }
    }

    function refreshAllSections() {
        for (var key in DEPARTMENT_SECTIONS) {
            var section = DEPARTMENT_SECTIONS[key];
            if (!section.$fieldset) continue;

            var $toggle = $('.dept-toggle[value="' + key + '"]');
            var isChecked = $toggle.is(':checked');
            var hasActive = hasActiveRoleInSection(key);

            if (hasActive || isChecked) {
                section.$fieldset.slideDown(250).removeClass('collapsed dept-hidden');
            } else {
                section.$fieldset.slideUp(250).addClass('dept-hidden');
            }
        }

        // تحديث الحقول الشرطية
        refreshConditionalFields();
    }

    // ─── الحقول الشرطية (تظهر عند تفعيل دور) ────────────────────

    function refreshConditionalFields() {
        for (var key in DEPARTMENT_SECTIONS) {
            var section = DEPARTMENT_SECTIONS[key];
            var conditionalFields = section.conditionalFields;
            if (!conditionalFields) continue;

            for (var roleField in conditionalFields) {
                var dependentFields = conditionalFields[roleField];
                var isActive = isFieldChecked(roleField);

                for (var i = 0; i < dependentFields.length; i++) {
                    var $row = findFieldRow(dependentFields[i]);
                    if ($row.length) {
                        if (isActive) {
                            $row.slideDown(200);
                        } else {
                            $row.slideUp(200);
                        }
                    }
                }
            }
        }

        // wholesale/retail تظهر فقط إذا أحد أدوار المبيعات مفعل
        var hasSalesRole = false;
        var salesFields = DEPARTMENT_SECTIONS.sales.roleFields;
        for (var j = 0; j < salesFields.length; j++) {
            if (isFieldChecked(salesFields[j])) {
                hasSalesRole = true;
                break;
            }
        }
        var $wholesaleRow = findFieldRow('is_wholesale');
        var $retailRow = findFieldRow('is_retail');
        if ($wholesaleRow.length) {
            hasSalesRole ? $wholesaleRow.slideDown(200) : $wholesaleRow.slideUp(200);
        }
        if ($retailRow.length) {
            hasSalesRole ? $retailRow.slideDown(200) : $retailRow.slideUp(200);
        }
    }

    // ─── ملخص الأدوار المفعّلة ──────────────────────────────────

    function buildRoleSummary() {
        var $summary = $('#role-summary');
        if (!$summary.length) return;

        var activeRoles = [];
        for (var key in DEPARTMENT_SECTIONS) {
            var section = DEPARTMENT_SECTIONS[key];
            for (var i = 0; i < section.roleFields.length; i++) {
                var field = section.roleFields[i];
                if (isFieldChecked(field)) {
                    var $label = $('label[for="id_' + field + '"]');
                    var labelText = $label.length ? $label.text().trim() : field;
                    activeRoles.push({
                        dept: section.label,
                        icon: section.icon,
                        role: labelText
                    });
                }
            }
        }

        if (activeRoles.length === 0) {
            $summary.html('<div class="summary-empty">لم يتم تعيين أي دور وظيفي بعد</div>');
            return;
        }

        var html = '<div class="summary-roles">';
        for (var r = 0; r < activeRoles.length; r++) {
            html += '<span class="role-badge">';
            html += '<span class="badge-icon">' + activeRoles[r].icon + '</span>';
            html += activeRoles[r].role;
            html += '</span>';
        }
        html += '</div>';
        $summary.html(html);
    }

    // ─── التهيئة الرئيسية ────────────────────────────────────────

    $(document).ready(function() {
        // تأكد نحن في صفحة change (تعديل) وليس add (إضافة)
        if ($('#user_form').length === 0 && $('form#user_form').length === 0) {
            // فحص بديل: هل يوجد حقل is_salesperson؟
            if ($('#id_is_salesperson').length === 0) {
                return;
            }
        }

        // ربط الـ fieldsets
        mapFieldsetsToSections();

        // التأكد من وجود fieldsets مرتبطة
        var hasMappedSections = false;
        for (var k in DEPARTMENT_SECTIONS) {
            if (DEPARTMENT_SECTIONS[k].$fieldset) {
                hasMappedSections = true;
                break;
            }
        }
        if (!hasMappedSections) return;

        // إدراج واجهة اختيار الأقسام بعد fieldset "الحالة والنظام"
        var $statusFieldset = findFieldsetByHeader('الحالة والنظام');
        if ($statusFieldset) {
            var chooserHtml = buildDepartmentChooser();
            // إضافة ملخص الأدوار
            chooserHtml += '<div id="role-summary" class="role-summary-bar"></div>';
            $statusFieldset.after(chooserHtml);
        }

        // إخفاء الأقسام غير المختارة مبدئياً (بدون animation)
        for (var key in DEPARTMENT_SECTIONS) {
            var section = DEPARTMENT_SECTIONS[key];
            if (!section.$fieldset) continue;

            var hasActive = hasActiveRoleInSection(key);
            if (!hasActive) {
                section.$fieldset.hide().addClass('dept-hidden');
            } else {
                // إزالة collapse class للأقسام المفعّلة
                section.$fieldset.removeClass('collapsed');
            }
        }

        // إخفاء الحقول الشرطية مبدئياً
        refreshConditionalFields();

        // بناء ملخص الأدوار
        buildRoleSummary();

        // ─── ربط الأحداث ─────────────────────────────────────

        // تبديل أقسام الأدوار
        $(document).on('change', '.dept-toggle', function() {
            var deptKey = $(this).val();
            var isChecked = $(this).is(':checked');

            $(this).closest('.dept-chip').toggleClass('active', isChecked);
            toggleDepartmentSection(deptKey, isChecked);
        });

        // مراقبة تغييرات checkboxes الأدوار
        var allRoleFields = [];
        for (var dk in DEPARTMENT_SECTIONS) {
            allRoleFields = allRoleFields.concat(DEPARTMENT_SECTIONS[dk].roleFields);
        }

        var roleSelectors = allRoleFields.map(function(f) {
            return '#id_' + f;
        }).join(',');

        $(document).on('change', roleSelectors, function() {
            var fieldName = $(this).attr('id').replace('id_', '');
            var isChecked = $(this).is(':checked');

            // تحديث chips
            for (var dk2 in DEPARTMENT_SECTIONS) {
                var sectionFields = DEPARTMENT_SECTIONS[dk2].roleFields;
                if (sectionFields.indexOf(fieldName) !== -1) {
                    var $chip = $('.dept-toggle[value="' + dk2 + '"]');
                    if (isChecked && !$chip.is(':checked')) {
                        $chip.prop('checked', true);
                        $chip.closest('.dept-chip').addClass('active');
                    }
                    break;
                }
            }

            // تحديث الحقول الشرطية والملخص
            refreshConditionalFields();
            buildRoleSummary();
        });

        // أيضاً: wholesale/retail تستجيب لأدوار المبيعات
        $(document).on('change', '#id_is_wholesale, #id_is_retail', function() {
            buildRoleSummary();
        });
    });

})(django.jQuery);
