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

    // ─── Department double-click → expand/collapse pages ───
    document.querySelectorAll('.dept-header').forEach(header => {
        header.addEventListener('dblclick', function(e) {
            // تجاهل النقر على الـ checkbox نفسه
            if (e.target.closest('.form-check-input')) return;
            const rootId = this.dataset.root;
            toggleDeptPanel(rootId);
        });
        // أيضاً النقر على السهم
        const chevron = header.querySelector('.dept-chevron');
        if (chevron) {
            chevron.addEventListener('click', function(e) {
                e.stopPropagation();
                const rootId = header.dataset.root;
                toggleDeptPanel(rootId);
            });
        }
    });

    function toggleDeptPanel(rootId) {
        const panel = document.querySelector(`.dept-pages-panel[data-root="${rootId}"]`);
        const chevron = document.querySelector(`.dept-header[data-root="${rootId}"] .dept-chevron`);
        if (!panel) return;
        const isHidden = panel.style.display === 'none';
        panel.style.display = isHidden ? '' : 'none';
        if (chevron) {
            chevron.style.transform = isHidden ? 'rotate(180deg)' : '';
        }
    }

    // Auto-expand departments that have assigned children
    document.querySelectorAll('.dept-pages-panel').forEach(panel => {
        const rootId = panel.dataset.root;
        const hasChecked = panel.querySelector('.dept-child-cb:checked');
        if (hasChecked) {
            panel.style.display = '';
            const chevron = document.querySelector(`.dept-header[data-root="${rootId}"] .dept-chevron`);
            if (chevron) chevron.style.transform = 'rotate(180deg)';
        }
    });

    // ─── Department root checkboxes → toggle all children ───
    document.querySelectorAll('.dept-root-cb').forEach(rootCb => {
        rootCb.addEventListener('change', function() {
            const rootId = this.dataset.root;
            const children = document.querySelectorAll(`.dept-child-cb[data-root="${rootId}"]`);
            children.forEach(cb => { cb.checked = this.checked; });
            // Auto-expand when root is checked
            if (this.checked) {
                const panel = document.querySelector(`.dept-pages-panel[data-root="${rootId}"]`);
                const chevron = document.querySelector(`.dept-header[data-root="${rootId}"] .dept-chevron`);
                if (panel && panel.style.display === 'none') {
                    panel.style.display = '';
                    if (chevron) chevron.style.transform = 'rotate(180deg)';
                }
            }
            updateDeptCount();
        });
    });
    // Child checkbox → update root state
    document.querySelectorAll('.dept-child-cb').forEach(childCb => {
        childCb.addEventListener('change', function() {
            const rootId = this.dataset.root;
            const rootCb = document.querySelector(`.dept-root-cb[data-root="${rootId}"]`);
            const siblings = document.querySelectorAll(`.dept-child-cb[data-root="${rootId}"]`);
            const allChecked = Array.from(siblings).every(cb => cb.checked);
            const someChecked = Array.from(siblings).some(cb => cb.checked);
            if (rootCb) {
                rootCb.checked = allChecked;
                rootCb.indeterminate = someChecked && !allChecked;
            }
            updateDeptCount();
        });
    });
    function updateDeptCount() {
        const el = document.getElementById('dept-count');
        if (el) {
            const count = document.querySelectorAll('input[name="departments"]:checked').length;
            el.textContent = count;
        }
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

    // ─── Django permissions accordion (event delegation) ───
    const permsContainer = document.getElementById('django-perms-container');
    if (permsContainer) {
        permsContainer.addEventListener('click', function(e) {
            const header = e.target.closest('.perm-app-header');
            if (!header) return;
            // Don't toggle if clicking a checkbox
            if (e.target.closest('input')) return;
            const group = header.closest('.perm-app-group');
            const body = group ? group.querySelector('.perm-app-body') : null;
            const chevron = header.querySelector('.perm-app-chevron');
            if (!body) return;
            const isHidden = body.style.display === 'none';
            body.style.display = isHidden ? '' : 'none';
            if (chevron) chevron.style.transform = isHidden ? 'rotate(-90deg)' : '';
        });
    }

    // Auto-expand groups that have checked permissions
    document.querySelectorAll('.perm-app-group').forEach(group => {
        const hasChecked = group.querySelector('.django-perm-cb:checked');
        if (hasChecked) {
            const body = group.querySelector('.perm-app-body');
            const chevron = group.querySelector('.perm-app-chevron');
            if (body) body.style.display = '';
            if (chevron) chevron.style.transform = 'rotate(-90deg)';
        }
    });

    // ─── Django permissions search filter ───
    const permSearchInput = document.getElementById('perm-search-input');
    if (permSearchInput) {
        permSearchInput.addEventListener('input', function() {
            const query = this.value.trim().toLowerCase();
            document.querySelectorAll('.perm-app-group').forEach(group => {
                const items = group.querySelectorAll('.perm-item');
                let groupHasMatch = false;
                items.forEach(item => {
                    const codename = (item.dataset.codename || '').toLowerCase();
                    const name = (item.dataset.name || '').toLowerCase();
                    const full = (item.dataset.full || '').toLowerCase();
                    const match = !query || codename.includes(query) || name.includes(query) || full.includes(query);
                    item.style.display = match ? '' : 'none';
                    if (match) groupHasMatch = true;
                });
                group.style.display = groupHasMatch ? '' : 'none';
                // Auto-expand when searching
                if (query && groupHasMatch) {
                    const body = group.querySelector('.perm-app-body');
                    const chevron = group.querySelector('.perm-app-chevron');
                    if (body) body.style.display = '';
                    if (chevron) chevron.style.transform = 'rotate(-90deg)';
                }
            });
        });
    }

    // ─── Direct perms count + sidebar live update ───
    document.querySelectorAll('.django-perm-cb').forEach(cb => {
        cb.addEventListener('change', function() {
            const countEl = document.getElementById('direct-perms-count');
            if (countEl) {
                countEl.textContent = document.querySelectorAll('.django-perm-cb:checked').length;
            }

            const permItem = this.closest('.perm-item');
            const fullPerm = permItem ? permItem.dataset.full : '';
            const tbody = document.getElementById('perms-table-body');
            const permsCount = document.getElementById('perms-count');
            if (!tbody || !fullPerm) return;

            // Remove "no perms" placeholder if exists
            const noPermsRow = document.getElementById('no-perms-row');
            if (noPermsRow) noPermsRow.remove();

            if (this.checked) {
                // Add to sidebar
                const tr = document.createElement('tr');
                tr.dataset.directPerm = fullPerm;
                tr.innerHTML = `<td class="px-3 py-1">
                    <div class="d-flex align-items-start gap-2">
                        <i class="fas fa-check-circle text-success mt-1" style="font-size:11px"></i>
                        <div>
                            <code class="perm-code">${escapeHtml(fullPerm)}</code>
                            <br><small class="text-success">صلاحية فردية</small>
                        </div>
                    </div>
                </td>`;
                tbody.appendChild(tr);
            } else {
                // Remove from sidebar
                const existing = tbody.querySelector(`tr[data-direct-perm="${CSS.escape(fullPerm)}"]`);
                if (existing) existing.remove();
            }

            // Update total permissions count
            if (permsCount) {
                permsCount.textContent = tbody.querySelectorAll('tr').length;
            }
        });
    });
}
