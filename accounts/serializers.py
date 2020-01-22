from rest_framework import serializers

from .models import User
from relationships.models import Block
from communities.models import Membership

from communities.serializers import MembershipSerializer

from bubblyb.utils import DynamicFieldsMixin, LoggedInExclsvFldsMixin, NestedFlattenerMixin

class UserCreateSerializer(serializers.ModelSerializer):
    superuser = serializers.BooleanField(label='superuser bruh')
    class Meta:
        model = User
        fields = (
            'superuser',
            'username',
            'alias',
            'email',
            'password',
            'fave_color'
        )
        extra_kwargs = {
            'password': {'write_only': True},
            'alias': {'required': False},
            'superuser': {'required': False},
        }
    def to_representation(self, obj):
        return {
            'username': obj.username,
            'email': obj.email,
        }

    def validate(self, data):
        username = User.objects.filter(username=data['username'])
        email = User.objects.filter(email=data['email'])
        if username.exists() or email.exists():
            raise serializers.ValidationError("This user has already registered.")
        return data
    def validate_superuser(self, value):
        if value:
            raise serializers.ValidationError("We see you have taken interest in our API suite. Wanna work with us?")
        return False

    def create(self, validated_data):
        if validated_data.pop('superuser', False):
            # created = User.objects.create_superuser(**validated_data)
            created = None
        else:
            created = User.objects.create_user(**validated_data)
        return created
        

class PasswordUpdateSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=False)
    reset_code = serializers.CharField(required=False)
    new_password = serializers.CharField()
    def validate(self, data):
        if data.get('old_password') or data.get('reset_code'):
            return data
        raise serializers.ValidationError("No auth data provided")
    def validate_old_password(self, value):
        if self.instance.check_password(value):
            return value
        raise serializers.ValidationError("Wrong password")
    def validate_reset_code(self, value):
        if value == self.instance.pw_reset_code:
            return value
        raise serializers.ValidationError("Wrong reset code")

    def update(self, instance, validated_data):
        instance.set_password(validated_data['new_password'])
        instance.save()
        return instance

class EmailSerializer(serializers.ModelSerializer, PasswordUpdateSerializer):
    class Meta:
        model = User
        fields = (
            'old_password',
            'email',
        )



class UserPeakSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    '''
        Custom fields: FAVE_COLOR, PROFILE_PIC, COVER_PHOTO, BIO,
        BLOCKED, FOLLOWS_YOU, YOU_FOLLOW
    '''
    dyna_fld_kwarg = 'profile_flds'

    def get_fave_color(self, obj):
        return obj.fave_color
    def get_profile_pic(self, obj):
        return obj.profile_pic
    def get_cover_photo(self, obj):
        return obj.cover_photo
    def get_bio(self, obj):
        return obj.bio

    def get_blocks_you(self, obj):
        return Block.blocked(obj, self.context['request'].user)
    def get_you_block(self, obj):
        return Block.blocked(self.context['request'].user, obj)
    def get_follows_you(self, obj):
        return obj.from_user.filter(to_user=self.context['request'].user).exists()
    def get_you_follow(self, obj):
        try:
            return obj.follows.filter(from_user=self.context['request'].user).exists()
        except TypeError:
            return "_"

    class Meta:
        model = User
        fields = (
            'username',
            'alias',
        )


class UserDetailSerializer(LoggedInExclsvFldsMixin, UserPeakSerializer):
    logged_in_flds = ('blocks_you', 'you_block', 'you_follow', 'follows_you')#, 'mutual_communities')

    following_count = serializers.SerializerMethodField()
    def get_following_count(self, obj):
        return obj.from_user.count()
    follower_count = serializers.SerializerMethodField()
    def get_follower_count(self, obj):
        return obj.follows.count()

    # def get_mutuals(self, obj): # TODO
    def get_mutual_communities(self, obj):
        return MembershipSerializer(
            obj.membership_set.select_related('community').filter(
                community__in=Membership.get_mutual_communities(self.context['request'].user, obj)
            )[:5],
            context = {'memb_fields': ('community',)},
            many = True
        ).data

    class Meta:
        model = User
        fields = (
            'username',
            'alias',
            'fave_color',
            'profile_pic',
            'cover_photo',
            'bio',
            'location',

            'following_count',
            'follower_count',
        )
        read_only_fields = (
            'username',
        )