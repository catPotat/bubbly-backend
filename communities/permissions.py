from rest_framework import permissions

from .models import Membership

class IsCommunityMemberOrPublicOnly(permissions.BasePermission):
    """ If not publicly available, check if member """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return obj.has_cmty_perm(request.user, read_only=True)
        return obj.has_cmty_perm(request.user)
