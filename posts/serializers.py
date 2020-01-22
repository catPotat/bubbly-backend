from rest_framework import serializers
from django.db.models import F

from .models import Content, Attachment, Post, Comment
from reacts.models import Icon, Reaction
from relationships.models import Block

from accounts.serializers import UserPeakSerializer
from communities.serializers import CommunityPeakSerializer
from reacts.serializers import IconListSerializer

from django.db.models import Count

from django.utils.timezone import now

from bubblyb.utils import (
    NestedFlattenerMixin,
    DynamicFieldsMixin,
    LoggedInExclsvFldsMixin,
)

class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = (
            'type',
            'content',
            'order',
        )


class ContentSerializer(
    DynamicFieldsMixin,LoggedInExclsvFldsMixin,NestedFlattenerMixin, serializers.ModelSerializer):
    ''' 
        OPTIONAL FIELDS: author, attachments_preview, 'text', attachments,
        post_or_comment_data, reactions, total_reacts, reacted_with
    '''
    dyna_fld_kwarg = 'content_flds'
    logged_in_flds = ('my_react',)
    '''
    # TODO performance benchmark these mixins
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ctx = kwargs.get('context')
        if ctx:
            if not ctx['request'].user.is_anonymous:
                self.fields['my_react'] = serializers.SerializerMethodField()
            fields = ctx.get('content_flds', ())
            for field in fields:
                self.fields[field] = serializers.SerializerMethodField()
    '''
    
    def get_author(self, obj):
        return UserPeakSerializer(
            obj.author,
            context = self.context
        ).data
    def get_text(self, obj):
        return obj.text if len(obj.text)<690 else obj.text[:690]+"... Read more"
    def get_attachments_preview(self, obj):
        atchs = obj.attachment_set.all()
        return {
            "atchs": AttachmentSerializer(atchs[:3], many=True).data,
            "count": atchs.count()
        }
    def get_attachments(self, obj):
        return AttachmentSerializer(
            obj.attachment_set.all()[:20],
            many=True
        ).data
    def get_post_or_comment_data(self, obj):
        self.to_flatten = 'post_or_comment_data'
        if hasattr(self, 'post'):
            return PostSerializer(
                obj.post,
                context = self.context
            ).data
        elif hasattr(self, 'comment'):
            return CommentSerializer(
                obj.comment,
                context = self.context
            ).data
        return {}
    def get_reacted_with(self, obj):
        return None # todo get a user's reaction in there profile page
    def get_reactions(self, obj): # n+1 query
        # https://code.djangoproject.com/ticket/26565
        # Todo grow and make good
        return obj.reaction_set.values(
                'icon_id',
                name = F('icon__name'),
                img_src = F('icon__img_src')
            ).annotate(count=Count('icon_id'))
    def get_total_reacts(self, obj):
        return obj.reaction_set.count()
    def get_my_react(self, obj):
        try:
            for r in obj.my_react:
                return r.icon_id
        except AttributeError:
            print("my_react NO PREFETCH")
            try:
                return obj.reaction_set.get(user=self.context['request'].user).icon_id
            except Reaction.DoesNotExist:
                return None

    new_attachments = AttachmentSerializer(many=True, write_only=True, required=False)
    class Meta:
        model = Content
        fields = (
            'id',
            'timestamp',
            'edited',

            'text',
            'new_attachments',
        )
        read_only_fields = (
            'id',
            'timestamp',
            'edited',
        )
    def update(self, instance, validated_data):
        attachments_data = validated_data.get('new_attachments')
        if attachments_data:
            instance.attachment_set.delete()
            Content.objects.create_attachments(
                content = instance,
                attachments_data = attachments_data
            )
        instance.text = validated_data.get('text', instance.text)
        
        instance.edited = now()
        instance.save()
        return instance



class PostAndCommentSerializer(NestedFlattenerMixin, DynamicFieldsMixin, serializers.ModelSerializer):
    ''' Sole purpose: to be inherited '''
    dyna_fld_kwarg = 'post_fields'
    def get_content(self, obj):
        self.to_flatten = 'content'
        return ContentSerializer(
            obj.content,
            context = self.context
        ).data
    def get_reply_count(self, obj):
        try: return obj.comment__count
        except AttributeError:
            print("reply_count NO PREFETCH")
            return obj.comment_set.count()
    def get_allocated_to(self, obj):
        return CommunityPeakSerializer(obj.allocated_to, context=self.context).data
    def get_total_reacts(self, obj):
        try: return obj.content__reaction__count
        except AttributeError: return "USE PREFETCH PLS"
        

class PostSerializer(PostAndCommentSerializer):
    ''' OPTIONAL FIELDS: allocated_to, reply_count, slug, content '''
    def get_slug(self, obj):
        return obj.slug
    class Meta:
        model = Post
        fields = (
            'title',
            'is_nsfw',
        )
    def update(self, instance, validated_data):
        instance.update(**validated_data)
        instance.content.update(edited = now())
        return instance


class CommentSerializer(PostAndCommentSerializer):
    ''' optional fields: allocated_to, reply_count, reply_to, on, content '''
    def get_reply_to(self, obj):
        return obj.reply_to_id
    def get_on(self, obj):
        return obj.on_id
    def get_allocated_to(self, obj):
        return obj.allocated_to.id
    class Meta:
        model = Comment
        fields = ()



class CommonContentCreateSerializer(serializers.Serializer):
    attachments = AttachmentSerializer(many=True, required=False)
    text = serializers.CharField(trim_whitespace=False, required=False)
    def create(self, validated_data):
        content = Content.objects.create(
            author = validated_data.pop('author'), # from perform_create
            text = validated_data.pop('text', ""),
        )
        Content.objects.create_attachments(content,
            validated_data.pop('attachments', ())
        )
        return content


class PostCreateSerializer(CommonContentCreateSerializer):
    title = serializers.CharField(required=False)
    
    def to_representation(self, obj):
        return {
            "id": obj.content_id,
            # "title": obj.title,
            # "cont3nt": ContentSerializer(obj.content).data
        }
    def create(self, validated_data):
        content = super().create(validated_data)
        post = Post.objects.create(**validated_data, content=content)
        return post
    

class CommentCreateSerializer(CommonContentCreateSerializer):
    reply_to = serializers.PrimaryKeyRelatedField(queryset=Comment.objects.all(), required=False)

    def to_representation(self, obj):
        return ContentSerializer(obj.content, context={'content_flds':('attachments',)}).data
        
    def validate_reply_to(self, value):
        if Block.blocked(value.content.author, self.context['request'].user):
            raise serializers.ValidationError("Your blokt")
        return value

    def create(self, validated_data):
        content = super().create(validated_data)
        comment = Comment.objects.create(**validated_data, content=content)
        return comment
