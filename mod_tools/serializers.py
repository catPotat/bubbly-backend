from rest_framework import serializers
from django.db.models import Max

from communities.models import Membership
from posts.models import PinnedPost, Content
from chat.models import PublicRoom
from reacts.models import Icon

from posts.serializers import CommonContentCreateSerializer


class MemberManageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = (
            'role',
        )

    def validate_role(self, value):
        if self.context['admin']:
            allowed_vals = (Membership.BANNED, Membership.MEMBER, Membership.MODERATOR, Membership.ADMINISTRATOR)
        else:
            allowed_vals = (Membership.BANNED, Membership.MEMBER)
        if value not in allowed_vals:
            raise serializers.ValidationError("Nuh uh")
        return value


class PublicRoomCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicRoom
        fields = (
            'description',
        )
    def to_representation(self, obj):
        return {"id": obj.room_id}
        
    def create(self, validated_data):
        return PublicRoom.objects.create_public(**validated_data)


class PinnedPostCreateSerializer(CommonContentCreateSerializer):
    def to_representation(self, obj):
        return {
            "id": obj.content_id,
            # "cont3nt": ContentSerializer(obj.content).data
        }
    def create(self, validated_data):
        content = super().create(validated_data)
        current_big = PinnedPost.objects.filter(allocated_to=validated_data.get('allocated_to')).aggregate(Max('order'))['order__max']
        new_order = current_big+1 if current_big else 1
        pinned = PinnedPost.objects.create(**validated_data, order=new_order, content=content)
        return pinned


class OrderSwapSerializer(serializers.Serializer):
    ''' pass in group_fld, order_fld, id_fld, group and model_cls for this to work '''
    first = serializers.CharField()
    second = serializers.CharField()

    def save(self):
        fields = self.context.get('fields')
        if fields: # walrus candidate
            class_ = fields['model_cls']
            id_ = fields['id_fld']
            order = fields['order_fld']
            qs = class_.objects.filter(**{fields['group_fld']:fields['group']})
            try:
                first = qs.get(**{id_:self.validated_data['first']})
                second = qs.get(**{id_:self.validated_data['second']})
            except class_.DoesNotExist:
                raise serializers.ValidationError("Not found")
            
            print(first)
            print(second)
            
            plc_holder = getattr(first, order)
            setattr(first, order, getattr(second, order))
            setattr(second, order, plc_holder)
            first.save()
            second.save()
            # cannot use unique constraint


class IconEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Icon
        fields = (
            'name',
            'active',
        )