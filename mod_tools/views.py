from rest_framework import (
    mixins,
    generics,
    status,
    views
)
from rest_framework.exceptions import APIException
from rest_framework.response import Response

from posts.models import Content, PinnedPost
from accounts.models import User
from communities.models import Membership
from reacts.models import Icon
from chat.models import PublicRoom
# from notification.models import Notification

from . import serializers
from reacts.serializers import IconCreateSerializer

from .permissions import (
    IsAdmin,
    IsMod,
)

from communities.views import GetCommunityMixin


class FetusDeletusAPIView(mixins.UpdateModelMixin, generics.DestroyAPIView):
    permission_classes = (IsMod,)

    def get_object(self):
        try:
            obj = Content.objects.get(id=self.kwargs['content_id'])
        except Content.DoesNotExist:
            raise APIException("No content found", status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(self.request, obj.allocated_to)
        return obj

    # def delete(self, request, *args, **kwargs): # todo archive post maybe
    #     Notification.objects.create(
    #         actor = self.request.user,
    #         action = Notification.MOD_SAID,
    #     )


class BanHammerAPIView(GetCommunityMixin, mixins.DestroyModelMixin, generics.UpdateAPIView):
    serializer_class = serializers.MemberManageSerializer
    permission_classes = (IsAdmin, IsMod)
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

    def check_object_permissions(self, request, obj):
        self.admin_request = False
        for permission in self.get_permissions():
            if not permission.has_object_permission(request, self, obj):
                self.permission_denied(
                    request, message=getattr(permission, 'message', None)
                )
            elif permission.__class__.__name__ == 'IsAdmin':
                self.admin_request = True

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['admin'] = self.admin_request
        return context
    
    def get_object(self):
        user = User.objects.get_by_username(self.kwargs['username'])
        community = self.get_community_obj()
        try:
            obj = Membership.objects.get(community=community, user=user)
        except Membership.DoesNotExist:
            raise APIException("No membership found", status.HTTP_404_NOT_FOUND)
        
        obj_role = obj.role
        if not self.admin_request:
            if obj_role in (Membership.MODERATOR, Membership.ADMINISTRATOR):
                raise APIException("Can't demote this person", status.HTTP_403_FORBIDDEN)
        else:
            if obj_role == Membership.ADMINISTRATOR and \
            Membership.objects.filter(community=community, role=Membership.ADMINISTRATOR).count() < 2:
                raise APIException("You are the only admin left", status.HTTP_412_PRECONDITION_FAILED)
        return obj

    def delete(self, request, *args, **kwargs):
        pass
        # return self.destroy(request, *args, **kwargs)



class IconCreateAPIView(GetCommunityMixin, generics.CreateAPIView):
    serializer_class = IconCreateSerializer
    permission_classes = (IsAdmin,)
    def perform_create(self, serializer):
        serializer.save(belongs_to = self.get_community_obj(), uploader=self.request.user)

class IconEditAPIView(GetCommunityMixin, mixins.UpdateModelMixin, generics.DestroyAPIView):
    serializer_class = serializers.IconEditSerializer
    permission_classes = (IsAdmin,)
    def get_object(self):
        obj = Icon.objects.filter(belongs_to=self.get_community_obj())
        url_val = self.kwargs['name']
        try:
            obj = obj.get(id = self.kwargs['name']) if url_val.isdigit() \
                else obj.get(name = self.kwargs['name'])
        except Icon.DoesNotExist:
            raise APIException("No icon found", status.HTTP_404_NOT_FOUND)
        return obj
    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class ChatRoomCreateAPIView(GetCommunityMixin, generics.CreateAPIView):
    serializer_class = serializers.PublicRoomCreateSerializer
    permission_classes = (IsAdmin,)
    def perform_create(self, serializer):
        serializer.save(creator=self.request.user, community=self.get_community_obj())

class ChatRoomEditAPIView(GetCommunityMixin, mixins.UpdateModelMixin, generics.DestroyAPIView):
    serializer_class = serializers.PublicRoomCreateSerializer
    permission_classes = (IsAdmin,)
        
    def get_object(self):
        try:
            obj = PublicRoom.objects.get(associated_with=self.get_community_obj(), room_id=self.kwargs['room_id'])
        except PublicRoom.DoesNotExist:
            raise APIException("No room found", status.HTTP_404_NOT_FOUND)
        return obj
    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)
    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


class AnouncementsCreateAPIView(GetCommunityMixin, generics.CreateAPIView):
    serializer_class = serializers.PinnedPostCreateSerializer
    permission_classes = (IsMod,)
    def perform_create(self, serializer):
        serializer.save(author=self.request.user, allocated_to=self.get_community_obj())
        
        
class AnouncementSwapAPIView(GetCommunityMixin, generics.GenericAPIView):
    serializer_class = serializers.OrderSwapSerializer
    permission_classes = (IsMod,)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['fields'] = {
            'group_fld': "allocated_to",
            'order_fld': "order",
            'id_fld': "content_id",
            'group': self.get_community_obj(),
            'model_cls': PinnedPost
        }
        return context
    
    def put(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_206_PARTIAL_CONTENT)

class ChatRoomSwapAPIView(AnouncementSwapAPIView):
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['fields'] = {
            'group_fld': "associated_with",
            'order_fld': "order",
            'id_fld': "room_id",
            'group': self.get_community_obj(),
            'model_cls': PublicRoom
        }
        return context
