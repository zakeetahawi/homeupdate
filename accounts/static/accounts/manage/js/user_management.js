/**
 * User Management — Dynamic role toggling and permissions refresh
 */
function initUserManagement(config) {
    const { toggleUrl, permissionsUrl, csrfToken } = config;

    // Role chip click handlers
    document.querySelectorAll('.role-chip').forEach(chip => {
        chip.addEventListener('click', function(e) {
            e.preventDefault();
            const checkbox = this.querySelector('.role-checkbox');
            const icon = this.querySelector('.role-icon');
            const fieldName = this.dataset.field;

            // Toggle checkbox
            checkbox.checked = !checkbox.checked;

            // Toggle visual state
            this.classList.toggle('role-chip-active', checkbox.checked);
            icon.classList.toggle('fa-check-circle', checkbox.checked);
            icon.classList.toggle('fa-circle', !checkbox.checked);

            // Show/hide conditional fields
            handleConditionalFields(fieldName, checkbox.checked);

            // Update section badge
            updateSectionBadge(this.closest('.role-section'));
        });
    });

    // Conditional field visibility
    function handleConditionalFields(fieldName, isActive) {
        if (fieldName === 'is_warehouse_staff') {
            const el = document.querySelector('.warehouse-fields');
            if (el) el.style.display = isActive ? '' : 'none';
        }
        if (fieldName === 'is_region_manager') {
            const el = document.querySelector('.managed-branches-field');
            if (el) el.style.display = isActive ? '' : 'none';
        }
    }

    // Update section active badge
    function updateSectionBadge(section) {
        if (!section) return;
        const hasActive = section.querySelectorAll('.role-chip-active').length > 0;
        let badge = section.querySelector('.card-header .badge');
        if (hasActive && !badge) {
            badge = document.createElement('span');
            badge.className = 'badge bg-success ms-1';
            badge.style.fontSize = '10px';
            badge.textContent = 'فعّال';
            section.querySelector('.card-header h6').appendChild(badge);
        } else if (!hasActive && badge) {
            badge.remove();
        }
    }

    // Refresh permissions panel after form submit
    function refreshPermissions() {
        fetch(permissionsUrl, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(r => r.json())
        .then(data => {
            const tbody = document.getElementById('perms-table-body');
            const countEl = document.getElementById('perms-count');
            const noMsg = document.getElementById('no-perms-msg');

            if (data.permissions && data.permissions.length > 0) {
                if (noMsg) noMsg.style.display = 'none';
                if (countEl) countEl.textContent = data.permissions.length;
                if (tbody) {
                    tbody.innerHTML = data.permissions.map(p => `
                        <tr>
                            <td>
                                <code class="small">${p.permission}</code><br>
                                <small class="${p.type === 'direct' ? 'text-success' : 'text-muted'}">
                                    <i class="fas ${p.type === 'direct' ? 'fa-check' : 'fa-arrow-alt-circle-down'} me-1"></i>${p.source}
                                </small>
                            </td>
                        </tr>
                    `).join('');
                }
            } else {
                if (countEl) countEl.textContent = '0';
                if (tbody) tbody.innerHTML = '';
                if (noMsg) noMsg.style.display = '';
            }
        })
        .catch(err => console.error('Error refreshing permissions:', err));
    }

    // Update roles summary badge
    function updateRolesSummary() {
        const activeChips = document.querySelectorAll('.role-chip-active');
        const summary = document.getElementById('roles-summary');
        if (summary) {
            const names = Array.from(activeChips).map(c => c.textContent.trim());
            summary.textContent = names.length > 0 ? names.join('، ') : 'مستخدم عادي';
        }
    }

    // Observe form changes to update summary
    document.querySelectorAll('.role-checkbox').forEach(cb => {
        cb.addEventListener('change', () => {
            updateRolesSummary();
        });
    });
}
