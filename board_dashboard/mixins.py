from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


class BoardAccessMixin(UserPassesTestMixin):
    """
    Mixin to restrict access to the Executive Board Dashboard.
    Only active superusers are allowed.
    """
    
    def test_func(self):
        return self.request.user.is_active and self.request.user.is_superuser

    def handle_no_permission(self):
        # Redirect generic users to 404 to hide existence, 
        # or just raise standard 403.
        # Implementation Plan said "Redirect to 404 (Security by Obscurity) or 403 Forbidden"
        # Let's start with 403 for clarity during dev, but maybe 404 is safer?
        # User request said: "Strict UI Restriction... completely hidden"
        # Raising PermissionDenied triggers 403.
        raise PermissionDenied
