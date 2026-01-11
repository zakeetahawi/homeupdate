"""
تحميل إشارات تطبيق الحسابات
"""

from accounts.signals.device_signals import (
    authorize_device_for_branch_users,
    track_branch_change,
    update_user_devices_on_branch_change,
    validate_authorized_devices_limit,
)
from accounts.signals.post_migrate import create_core_departments_after_migrate
