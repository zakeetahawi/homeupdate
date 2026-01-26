from rest_framework import permissions


class IsBoardMember(permissions.BasePermission):
    """
    Allows access only to superusers (Board Members).
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_active and request.user.is_superuser)
