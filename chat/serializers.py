from rest_framework import serializers
from django.db.models import Prefetch

from .models import Message, Room, PublicRoom, Roommate
from relationships.models import Block
from communities.models import Community
 
from accounts.serializers import UserPeakSerializer
from communities.serializers import CommunityPeakSerializer

from bubblyb.utils import NestedFlattenerMixin


from django.db.models import Max

import json
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
def signal_to_consumer(msg_obj):
    response = {
        "msg_data": MessageSerializer(
            msg_obj,
            context = {'profile_flds': ('profile_pic', 'fave_color')}
        ).data,
    }
    async_to_sync(get_channel_layer().group_send)(
        msg_obj.thread.channels_layer_name,
        {
            "type": "chat_message",
            "text": json.dumps(response)
        }
    )


class MessageSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    class Meta:
        model = Message
        fields = (
            'id',
            'author',
            'timestamp',
            'msg_type',
            'content',
        )
    def get_author(self, obj):
        return UserPeakSerializer(obj.author, context=self.context).data



class RoomDetailSerializer(NestedFlattenerMixin, serializers.ModelSerializer):
    roommate_info = serializers.SerializerMethodField()
    meta_data = serializers.SerializerMethodField()
    class Meta:
        model = Room
        fields = (
            'id',
            'name',
            'bg_img',
            'roommate_info',
            'meta_data',
        )
        read_only_fields=(
            'id',
        )
    def get_roommate_info(self, obj):
        try:
            for info in obj.my_info:
                return MyRoommateInfoSerializer(info).data
        except AttributeError:
            print("my roommate info NO PREFETCH")
            try:
                return MyRoommateInfoSerializer(
                    obj.roommate_set.get(identity=self.context['request'].user)
                ).data
            except Roommate.DoesNotExist:
                return None
        

    def get_meta_data(self, obj): # todo refactor
        self.to_flatten = 'meta_data'
        roomType = ""
        data = {}

        if hasattr(obj, 'direct'):
            roomType = "direct"
            dr = obj.direct
            other_u = dr.u2 if dr.u1 == self.context['request'].user else dr.u1
            data = UserPeakSerializer(other_u, context=self.context).data

        elif hasattr(obj, 'publicroom'):
            roomType = "public"
            data = {
                'community': CommunityPeakSerializer(obj.publicroom.associated_with).data,
                'order': obj.publicroom.order
            }

        else:
            roomType = "group"
            try:
                count = obj.roommate__count
            except AttributeError:
                print("rommate count NO PREFETCH")
                count = obj.roommate_set.count()
            data = {"roommate_count" : count}

        return {
            "room_type" : roomType,
            "room_type_data" : data
        }

    def validate_name(self, value):
        signal_to_consumer( # wierd flex but ok
            Message.objects.create(
                thread = self.instance,
                author = self.context['request'].user,
                msg_type = 6,
                content = value,
            )
        )
        return value
    def validate_bg_img(self, value):
        signal_to_consumer(Message.objects.create(
            thread = self.instance,
            author = self.context['request'].user,
            msg_type = 7,
            content = value,
        ))
        return value


class MyRoommateInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Roommate
        fields = (
            'is_admin',
            'enable_noti',
            'last_seen',
        )
        read_only_fields = (
            'is_admin',
            'last_seen',
        )
        

class RoommateListSerializer(NestedFlattenerMixin, serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.to_flatten = 'identity'
        context= kwargs.get('context')
        if context:
            if context.get('custom_fields') == 'to_patch':
                self.fields.pop('identity')
            else:
                self.fields['identity'] = UserPeakSerializer(context=context)
    class Meta:
        model = Roommate
        fields = (
            'identity',
            'is_admin',
        )


class RoomCreateSerializer(serializers.Serializer):
    participants = RoommateListSerializer(many=True)

    def to_representation(self, obj):
        return RoomDetailSerializer(obj, context={'request': self.context['request']}).data
        return {"id": obj.id}

    def create(self, validated_data):
        you = self.context['request'].user
        them = validated_data['participants']
        room = self.context.get('add_to')
        
        if room:
            if hasattr(room, 'direct'):
                room.direct.delete()
                # raise serializers.ValidationError("Can't do that to a direct")
        else:
            if len(them) == 1:
                them_id = them[0]['identity']
                direct = Room.get_direct(you, them_id)
                if direct: return direct.room
                else:
                    if Block.blocked(them_id, you):
                        raise serializers.ValidationError("You are blocked")
                    return Room.objects.create_direct(you, them_id)
            else:
                room = Room.objects.create_room(creator = you)

        new = 0
        for buddy in them:
            if buddy['identity'] != you:
                if not Block.blocked(buddy['identity'], you):
                    _, created = Roommate.objects.get_or_create(room=room, **buddy)
                    if created: new +=1
        if new:
            signal_to_consumer(Message.objects.create(
                thread = room,
                author = you,
                msg_type = 5,
                content = new,
            ))
        return room



class PeakMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = (
            'author',
            'timestamp',
            'msg_type',
            'content',
        )
class RoomListSerializer(RoomDetailSerializer):
    last_msg = serializers.SerializerMethodField()
    class Meta:
        model = Room
        fields = (
            'id',
            'name',
            'bg_img',
            'roommate_info',
            'last_msg',
            'meta_data',
        )
    def get_last_msg(self, obj):
        return PeakMessageSerializer(
            obj.message_set.first() ).data



class SmolRoomListSerializer(RoomListSerializer):
    last_msg = serializers.SerializerMethodField()
    class Meta:
        model = Room
        fields = (
            'id',
            'name',
            'bg_img',
            'last_msg',
        )
class PublicRoomsSerializer(RoomListSerializer, NestedFlattenerMixin):
    ''' list PARTICULAR community's public rooms '''
    to_flatten = 'room'
    room = SmolRoomListSerializer()
    class Meta:
        model = PublicRoom
        fields = (
            'room',
            'description',
            'order',
        )


class MyPublicRoomsSerializer(CommunityPeakSerializer):
    ''' list JOINED communities' public rooms '''
    class Meta:
        model = Community
        fields = (
            'id',
            'name',
            'icon_img',
            'theme_color',
            'recently_active'
        )
    recently_active = serializers.SerializerMethodField()
    def get_recently_active(self, obj):
        return PublicRoomsSerializer(
            obj.publicroom_set,
            many = True
        ).data
