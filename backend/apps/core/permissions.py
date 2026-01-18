from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """Permission check for object ownership."""

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Allow read access to anyone, but only owner can modify."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user


class IsAdminOrReadOnly(permissions.BasePermission):
    """Allow read access to anyone, but only admin can modify."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff


class IsMasterOrReadOnly(permissions.BasePermission):
    """Allow read access to anyone, but only master can modify their own data."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and request.user.role == 'master'


class IsMasterOwner(permissions.BasePermission):
    """Check if the user is the master who owns the object."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        # Check if obj has master attribute and it matches current user's master profile
        if hasattr(obj, 'master'):
            return obj.master.user == request.user
        return False
