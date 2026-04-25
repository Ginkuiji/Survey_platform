from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "admin"
        )

class IsOrganizerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ["organizer", "admin"]
        )

class IsOrganizer(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj.owners.filter(id=request.user.id).exists()
