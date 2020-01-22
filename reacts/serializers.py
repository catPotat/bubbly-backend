from rest_framework import serializers
# from generic_relations.relations import GenericRelatedField
# from django.contrib.contenttypes.fields import GenericRelation

from .models import Reaction, Icon
from communities.models import Community
# from notification.models import Notification

from django.db.models import Count

'''
#################
# CUSTOM FIELDS #
class IncludedpostRelatedField(serializers.RelatedField):
    def to_internal_value(self, data):
        post_data = data.get('includedposts')

        # Perform the data validation.
        if not post_data:
            raise serializers.ValidationError({
                'score': 'This field is required.'
            })
        # if len(player_name) > 10:
        #     raise serializers.ValidationError({
        #         'player_name': 'May not be more than 10 characters.'
        #     })
        
        # Return the validated values. This will be available as
        # the `.validated_data` property.
        return {
            'title': post_data,
        }
    
    def to_representation(self, value):
        if isinstance(value, Community):
            serializer = CommunityPostCreateSerializer(value)
        elif isinstance(value, Post):
            serializer = PostCreateSerializer(value)
        else:
            raise Exception('Unexpected type of tagged object')

        return serializer.data
# END OF CUSTOM FIELDS #
########################
'''


class IconCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Icon
        fields = (
            'img_src',
            'name',
        )

    def create(self, validated_data):
        instance, _ = Icon.objects.get_or_create(**validated_data)
        return instance
        

class IconListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Icon
        fields = (
            'id',
            'img_src',
            'name',
            'active',
        )

class MyIconsSerializer(serializers.ModelSerializer):
    icons = serializers.SerializerMethodField()
    class Meta:
        model = Community
        fields = (
            'id',
            'name',
            'icons',
        )
    def get_icons(self, cmty):
        return IconListSerializer(cmty.icon_set.filter(active=True), many=True).data


class ReactionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reaction
        fields = (
            'icon',
        )
    def to_representation(self, obj):
        return { 
            'reactions': obj.to.reaction_set.values('icon_id').annotate(count=Count('icon_id'))
        }
    def validate_icon(self, value):
        if not (value.belongs_to == self.context['content'].allocated_to or value.belongs_to==None):
            raise serializers.ValidationError("Icon not in this community")

        if not value.active:
            raise serializers.ValidationError("Icon already disabled")
        return value