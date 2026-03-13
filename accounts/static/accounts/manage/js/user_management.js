/**
 * User Management — Dynamic AJAX role toggling and live permissions refresh
 */
function initUserManagement(config) {
    const { toggleUrl, permissionsUrl, csrfToken } = config;
    let isToggling = false;

    // ─── Role chip click → AJAX toggle ───
    document.querySelectorAll('.role-chip').forEach(chip => {
        chip.addEventListener('click', function(e) {
            e.preventDefault();
            if (isToggling) return;
            const fieldName = this.dataset.field;
            toggleRole(this, fieldName);
        });
        // Keyboard support
        chip.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.click();
            }
        });
    });

    async function toggleRole(chip, fieldName) {
        isToggling = true;
        const cb = chip.querySelector('.role-checkbox');
        const indicator = chip.querySelector('.role-chip-indicator');
        const icon = indicator ? indicator.querySelector('i') : null;

        // Optimistic UI
        const wasActive = cb.checked;
        cb.checked = !wasActive;
        chip.classList.toggle('role-chip-active', cb.checked);
        if (indicator) indicator.classList.toggle('active', cb.checked);
        if (icon) {
            icon.className = cb.checked ? 'fas fa-spinner fa-spin' : 'fas fa-spinner fa-spin';
        }

        try {
            const resp = await fetch(toggleUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: 'role_field=' + encodeURIComponent(fieldName)
            });
            const data = await resp.json();

            if (data.success) {
                // Update icon to final state
                if (icon) icon.className = data.value ? 'fas fa-check' : 'fas fa-plus';

                // Conditional fields
                handleConditionalFields(fieldName, data.value);

                // Update section badge
                updateSectionBadge(chip.closest('.role-section'));

                // Update summary badge at top
                updateRolesSummary(data.active_roles_display);

                // Refresh permissions panel
                refreshPermissions();

                showToast(data.value
                    ? 'تم تفعيل: ' + (chip.dataset.display || fieldName)
                    : 'تم إلغاء: ' + (chip.dataset.display || fieldName), 'success');
            } else {
                // Revert on failure
                cb.checked = wasActive;
                chip.classList.toggle('role-chip-active', wasActive);
                if (indicator) indicator.classList.toggle('active', wasActive);
                if (icon) icon.className = wasActive ? 'fas fa-check' : 'fas fa-plus';
                showToast(data.error || 'حدث خطأ', 'danger');
            }
        } catch (err) {
            // Revert on network error
            cb.checked = wasActive;
            chip.classList.toggle('role-chip-active', wasActive);
            if (indicator) indicator.classList.toggle('active', wasActive);
            if (icon) icon.className = wasActive ? 'fas fa-check' : 'fas fa-plus';
            showToast('خطأ في الاتصال', 'danger');
        } finally {
            isToggling = false;
        }
    }

    // ─── Conditional field visibility ───
    function handleConditionalFields(fieldName, isActive) {
        if (fieldName === 'is_warehouse_staff') {
            const el = document.querySelector('.warehouse-fields');
            if (el) {
                el.style.display = isActive ? '' : 'none';
                if (isActive) el.classList.add('fade-in');
            }
        }
        if (fieldName === 'is_region_manager') {
            const el = document.querySelector('.managed-branches-field');
            if (el) {
                el.style.display = isActive ? '' : 'none';
                if (isActive) el.classList.add('fade-in');
            }
        }
    }

    // ─── Section badge update ───
    function updateSectionBadge(section) {
        if (!section) return;
        const sectionKey = section.dataset.section;
        const badge = document.getElementById('badge-' + sectionKey);
        const activeCount = section.querySelectorAll('.role-chip-active').length;
        if (badge) {
            if (activeCount > 0) {
                badge.className = 'badge section-badge-' + sectionKey;
                badge.textContent = activeCount + ' دور';
            } else {
                badge.className = 'badge bg-light text-muted';
                badge.textContent = 'غير مفعّل';
            }
        }
    }

    // ─── Roles summary badge ───
    function updateRolesSummary(displayText) {
        const el = document.getElementById('roles-summary');
        if (el && displayText !== undefined) {
            el.textContent = displayText || 'مستخدم عادي';
        } else if (el) {
            const active = document.querySelectorAll('.role-chip-active');
            const names = Array.from(active).map(c => {
                const lbl = c.querySelector('.role-chip-label');
                return lbl ? lbl.textContent.trim() : c.textContent.trim();
            });
            el.textContent = names.length > 0 ? names.join('، ') : 'مستخدم عادي';
        }
    }

    // ─── Permissions refresh ───
    function refreshPermissions() {
        const loading = document.getElementById('perms-loading');
        const table = document.getElementById('perms-table');
        const countEl = document.getElementById('perms-count');

        if (loading) loading.style.display = '';
        if (table) table.style.opacity = '0.5';

        fetch(permissionsUrl, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(r => r.json())
        .then(data => {
            if (loading) loading.style.display = 'none';
            if (table) table.style.opacity = '1';
            if (countEl) countEl.textContent = data.permissions ? data.permissions.length : 0;

            const tbody = document.getElementById('perms-table-body');
            if (!tbody) return;

            if (data.permissions && data.permissions.length > 0) {
                tbody.innerHTML = data.permissions.map(p => `
                    <tr>
                        <td class="px-3 py-1">
                            <div class="d-flex align-items-start gap-2">
                                <i class="fas ${p.type === 'direct' ? 'fa-check-circle text-success' : 'fa-arrow-circle-down text-muted'} mt-1" style="font-size:11px"></i>
                                <div>
                                    <code class="perm-code">${escapeHtml(p.permission)}</code>
                                    <br>
                                    <small class="${p.type === 'direct' ? 'text-success' : 'text-muted'}">
                                        ${escapeHtml(p.source)} ${p.type === 'inherited' ? '(موروث)' : ''}
                                    </small>
                                </div>
                            </div>
                        </td>
                    </tr>
                `).join('');
            } else {
                tbody.innerHTML = `<tr><td class="text-center text-muted py-4">
                    <i class="fas fa-lock fa-2x mb-2 d-block"></i>
                    لا توجد صلاحيات — فعّل دوراً أولاً
                </td></tr>`;
            }
        })
        .catch(() => {
            if (loading) loading.style.display = 'none';
            if (table) table.style.opacity = '1';
        });
    }

    // Manual refresh button
    const refreshBtn = document.getElementById('refresh-perms-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function(e) {
            e.preventDefault();
            refreshPermissions();
        });
    }

    // ─── Toast notification ───
    function showToast(message, type) {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'position-fixed bottom-0 start-50 translate-middle-x p-3';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-bg-' + type + ' border-0 show';
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${escapeHtml(message)}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>`;
        container.appendChild(toast);
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 2500);
    }

    // ─── XSS safety ───
    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}
