from rest_framework import serializers

from rest_framework.fields import CurrentUserDefault
from django.utils.timezone import now
from string import ascii_lowercase

from .models import Community, Membership

from bubblyb.utils import (
    NestedFlattenerMixin,
    DynamicFieldsMixin,
    LoggedInExclsvFldsMixin
)


class GetMembershipMixin(serializers.ModelSerializer):
    def get_membership_info(self, obj):
        try:
            return MembershipSerializer(
                Membership.objects.get(community=obj, user=self.context['request'].user)
            ).data
        except Membership.DoesNotExist:
            return None
            
class CommunityPeakSerializer(DynamicFieldsMixin, GetMembershipMixin):
    dyna_fld_kwarg = 'cmty_fields'
    class Meta:
        model = Community
        fields = ( # TODO dynamic fields from front end request maybe
            'id',
            'name',
            'icon_img',
            'theme_color',
        )
    def get_cover_img(self, obj):
        return obj.cover_img
    def get_moto(self, obj):
        return obj.moto
    def get_visibility(self, obj):
        return obj.visibility


class MembershipSerializer(NestedFlattenerMixin, DynamicFieldsMixin, serializers.ModelSerializer):
    ''' optional fields: user, community '''
    dyna_fld_kwarg = 'memb_fields'
    role = serializers.CharField(source='get_role_display')
    class Meta:
        model = Membership
        fields = (
            'date_joined',
            'role',
            'reputation_point',
        )
    def get_community(self, obj):
        self.to_flatten = 'community'
        return CommunityPeakSerializer(obj.community, context=self.context).data
    def get_user(self, obj):
        self.to_flatten = 'user'
        return UserPeakSerializer(obj.user, context=self.context).data


from accounts.serializers import UserPeakSerializer


class CommunityDetailSerializer(LoggedInExclsvFldsMixin, GetMembershipMixin):
    logged_in_flds = ('membership_info',)
    total_members = serializers.SerializerMethodField()
    def get_total_members(self, obj):
        return obj.member_count
    class Meta:
        model = Community
        fields = (
            'id',
            'visibility',
            'name',
            'moto',
            'icon_img',
            'cover_img',
            'theme_color',
            'background_img',
            'total_members',
            # write only below
            'is_secret',
            'invite_code',
        )
        extra_kwargs = {
            'id': {'required': False},
            'is_secret': {'write_only': True},
            'invite_code': {'write_only': True},
        }

    def validate_id(self, value):
        if self.context['request'].method != 'POST':
            raise serializers.ValidationError("Cannot change id")
        if not all(c in '1234567890_ '+ascii_lowercase for c in value):
            raise serializers.ValidationError("ASCII lower letter, numb3rs and _underscore only please. No spaces")
        return value
    def create(self, *args, **kwargs):
        cmtyObj = super().create(*args, **kwargs)
        Membership.objects.create(
            community = cmtyObj,
            user = self.context['request'].user,
            role = Membership.ADMINISTRATOR
        )
        return cmtyObj


class MembershipCreateSerializer(serializers.Serializer):
    invite_code = serializers.CharField(required=False)

    def to_representation(self, obj):
        return MembershipSerializer(obj).data

    def validate(self, data):
        cmty = self.context['community']
        
        if cmty.visibility == 'top secret?':
            raise serializers.ValidationError("Not supported yet maybe")
        code = cmty.invite_code
        if code and data.get('invite_code') != code:
            raise serializers.ValidationError("Wrong code")
        return data

    def create(self, validated_data):
        instance, created = Membership.objects.get_or_create(
            community = self.context['community'],
            user = self.context['request'].user,
        )
        if not created:
            instance.role = Membership.MEMBER
            instance.date_joined = now()
            instance.save()
        return instance