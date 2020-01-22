from rest_framework import (
    generics,
    mixins,
    status,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import APIView

from django.db.models import Prefetch, Count, Max
from django.utils.timezone import now

from .models import Message, Room, Roommate, PublicRoom
from communities.models import Membership
from accounts.models import User

from . import serializers

from .permissions import IsAdminOrBasicPerms

from bubblyb.utils import PaginationMixin, count_db_hits


class GetRoomMixin(object):
    def get_room_object(self):
        try:
            obj = Room.objects.get(id = self.kwargs['id'])
        except Room.DoesNotExist:
            raise APIException("No room found", status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(self.request, obj)
        return obj


class RetrieveMessagesAPIView(GetRoomMixin, PaginationMixin, generics.ListAPIView):
    serializer_class = serializers.MessageSerializer
    permission_classes = (IsAdminOrBasicPerms,)
    paginate_kwargs = ('-timestamp',)
    paginate_limit = 20

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['profile_flds'] = ('profile_pic', 'fave_color')
        return context

    def get_big_queryset(self):
        qs = Message.objects.all()
        qs = qs.filter(thread = self.get_room_object())
        qs = qs.select_related('author')
        return qs



class RoomDetailAPIView(GetRoomMixin, mixins.UpdateModelMixin, generics.RetrieveAPIView):
    serializer_class = serializers.RoomDetailSerializer
    permission_classes = (IsAdminOrBasicPerms,)
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['profile_flds'] = ('profile_pic', 'fave_color')
        return context
        
    def get_object(self):
        return self.get_room_object()

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class RoommateListAPIView(GetRoomMixin, PaginationMixin, generics.ListAPIView):
    serializer_class = serializers.RoommateListSerializer
    permission_classes = (IsAdminOrBasicPerms,)
    paginate_kwargs = ('-joined_at', '-is_admin')
    paginate_limit = 20
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['profile_flds'] = ('profile_pic', 'fave_color')
        return context
    
    def get_big_queryset(self):
        qs = Roommate.objects.all()
        qs = qs.select_related('identity')
        qs = qs.filter(room = self.get_room_object())
        return qs


class RoommateEditAPIView(GetRoomMixin, generics.UpdateAPIView):
    serializer_class = serializers.RoommateListSerializer
    permission_classes = (IsAdminOrBasicPerms,)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['custom_fields'] = 'to_patch'
        return context

    def get_object(self):
        user = User.objects.get_by_username(self.kwargs['username'])
        if user == self.request.user:
            raise APIException("Not here", status.HTTP_406_NOT_ACCEPTABLE)
        try:
            obj = Roommate.objects.get(room=self.get_room_object(), identity= user)
        except Roommate.DoesNotExist:
            raise APIException("No roomate found", status.HTTP_404_NOT_FOUND)
        return obj

    def delete(self, request, **kwargs):
        mate_obj = self.get_object()
        if hasattr(mate_obj.room, 'direct'):
            raise APIException("Not here", status.HTTP_406_NOT_ACCEPTABLE)
        mate_obj.delete()
        serializers.signal_to_consumer(
            Message.objects.create(
            thread = mate_obj.room,
            author = request.user,
            msg_type = 9,
            content = mate_obj.identity.alias,
        ))
        return Response(status = status.HTTP_204_NO_CONTENT)


class MakeRoomsAndMatesAPIView(GetRoomMixin, generics.CreateAPIView):
    serializer_class = serializers.RoomCreateSerializer
    permission_classes = (IsAuthenticated, IsAdminOrBasicPerms)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.kwargs['id'] != '__new_or_direct':
            context['add_to'] = self.get_room_object()
        return context
class SavePublicRoomAPIView(GetRoomMixin, APIView):
    def post(self, request, **kwargs):
        room = self.get_room_object()
        user = request.user
        if hasattr(room, 'publicroom'):
            if Membership.check_member(
                room.publicroom.associated_with,
                user
            ):
                mate, _ = Roommate.objects.get_or_create(room=room, identity=user)
                if self.request.query_params.get('as-mod') == "1":
                    if Membership.check_member(
                        room.publicroom.associated_with,
                        user, checkRole = Membership.MODERATOR
                    ):
                        mate.is_admin = True
                        mate.save()
                return Response(
                    serializers.MyRoommateInfoSerializer(mate).data,
                    status = status.HTTP_201_CREATED
                )
        return Response(status = status.HTTP_403_FORBIDDEN)



class MyRoommateInfoAPIView(GetRoomMixin, mixins.UpdateModelMixin, generics.RetrieveAPIView):
    serializer_class = serializers.MyRoommateInfoSerializer

    def get_object(self):
        try:
            obj = Roommate.objects.get(room=self.get_room_object(), identity=self.request.user)
        except Roommate.DoesNotExist:
            raise APIException("Not in this room", status.HTTP_404_NOT_FOUND)
        return obj

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)
    def put(self, request, **kwargs):
        me = self.get_object()
        me.last_seen = now()
        me.save()
        return Response(status = status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        mate_obj = self.get_object()
        room = mate_obj.room
        if not hasattr(room, 'publicroom'):
            if hasattr(room, 'direct'):
                room.direct.delete()
            else:
                mates = Roommate.objects.filter(
                    room=room
                ).exclude(identity = self.request.user)
                if mates.count() == 0:
                    room.delete()
                else:
                    admins = mates.filter(is_admin=True)
                    if not admins.exists():  # auto assign oldest member as new admin
                        mates.earliest('timestamp').is_admin = True
            serializers.signal_to_consumer(
                Message.objects.create(
                thread = room,
                author = request.user,
                msg_type = 9,
                content = "",
            ))
        mate_obj.delete()
        return Response(status = status.HTTP_204_NO_CONTENT)


class MyRoomListAPIView(PaginationMixin, generics.ListAPIView): 
    serializer_class = serializers.RoomListSerializer
    permission_classes = (IsAuthenticated,)
    paginate_kwargs = ('-message__timestamp',)
    paginate_limit = 15
    
    # @count_db_hits
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['profile_flds'] = ('profile_pic', 'fave_color')
        return context

    def get_big_queryset(self):
        user = self.request.user
        qs = Room.objects.filter(roommate__identity = user)
        qs = qs.select_related('publicroom__associated_with', 'direct__u1', 'direct__u2')
        qs = qs.prefetch_related(
            Prefetch('message_set',
                queryset=Message.objects.order_by('-timestamp')),
            Prefetch(
                'roommate_set',
                queryset=Roommate.objects.filter(identity = user),
                to_attr="my_info"
            )
        )
        qs = qs.annotate(
            Count('roommate'),
            message__timestamp = Max('message__timestamp')
        )
        return qs

class PublicRoomExplorerAPIView(PaginationMixin, generics.ListAPIView):
    serializer_class = serializers.MyPublicRoomsSerializer
    permission_classes = (IsAuthenticated,)
    paginate_kwargs = ('-membership__reputation_point',)
    paginate_limit = 5
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['cmty_fields'] = ('cover_img',)
        return context
    def get_big_queryset(self):
        qs = Membership.get_joined_communities(self.request.user)
        qs = qs.filter(publicroom__isnull=False).distinct()
        qs = qs.annotate(
            membership__reputation_point = Max('membership__reputation_point')
        )
        qs = qs.prefetch_related(
            Prefetch(
                'publicroom_set',
                queryset = PublicRoom.objects.select_related('room') \
                .prefetch_related(
                    Prefetch(
                        'room__message_set',
                        queryset=Message.objects.order_by('-timestamp')
                    )
                ).annotate(
                    room__message__timestamp = Max('room__message__timestamp')
                ).order_by('-room__message__timestamp'),
                # to_attr = 'publicroom_set'
            )
        )
        return qs