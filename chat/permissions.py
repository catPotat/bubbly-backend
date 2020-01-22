from rest_framework import permissions

class IsAdminOrBasicPerms(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS: #GET, HEAD or OPTIONS
            return obj.has_room_perm(request.user, basic_perms=True)
        return obj.has_room_perm(request.user)
        