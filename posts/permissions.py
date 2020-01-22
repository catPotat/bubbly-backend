from rest_framework import permissions

from relationships.models import Block

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # print(request.__dir__())
        # print('----------------bruh')
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.author == request.user

class IsNotBlocked(permissions.BasePermission):
    """
    If blocked then cannot interact
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return not Block.blocked(
            obj.author,
            request.user
        )

class IsMemberOrPublicPostsOnly(permissions.BasePermission):
    """ If not publicly available, check if member """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return obj.allocated_to.has_cmty_perm(request.user, read_only=True)
        return obj.allocated_to.has_cmty_perm(request.user)