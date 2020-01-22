from rest_framework import permissions

from communities.models import Membership

class IsAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return Membership.check_member(obj, request.user, Membership.ADMINISTRATOR)
        
class IsMod(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return Membership.check_member(obj, request.user, Membership.MODERATOR)