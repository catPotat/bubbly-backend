from rest_framework import (
    mixins,
    generics,
    status,
    filters,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import APIException

from django.db.models import Count, Prefetch, F, Max

from django.utils.timezone import now
from datetime import  timedelta

from .models import Post, Comment, Content
from communities.models import Membership
from reacts.models import Reaction
from accounts.models import User

from .permissions import (
    IsOwnerOrReadOnly,
    IsNotBlocked,
    IsMemberOrPublicPostsOnly
)

from . import serializers
from accounts.serializers import UserPeakSerializer

from bubblyb.utils import (
    PaginationMixin,
    SrchCompatiblePgnationMixin,
    count_db_hits,
    perf_timer
)


def sort_posts(get_filtered):
    def sorter(self, *args, **kwargs):
        qs = get_filtered(self)
        sort_by = self.request.query_params.get('sort_by', "")
        if sort_by:
            if sort_by == "new":
                self.paginate_kwargs = ('-content__timestamp',)
            elif sort_by == "best":
                last = self.request.query_params.get('last_x_days', "")
                if last:
                    last = int(last) if last.isdigit() else 0
                    qs = qs.filter(content__timestamp__gte = now()-timedelta(days=last))
                self.paginate_kwargs = ('-content__reaction__count', '-content__timestamp')
        return qs
    return sorter

def posts_aggregate(get_qs): # for comment and post qs
    def aggregator(self, *args, **kwargs):
        qs = get_qs(self)
        qs = qs.select_related('content__author').defer( # TODO make it work with only() instead
            'content__author__bio',
            'content__author__location',
            'content__author__email',
            'content__author__password',
            'content__author__cover_photo',
            'content__author__date_joined',
            'content__author__is_active',
            'content__author__last_login',
            'content__author__is_superuser',
            'content__author__is_staff',
        )
        qs = qs.select_related('allocated_to').defer(
            'allocated_to__moto',
            'allocated_to__cover_img',
            'allocated_to__background_img',
            'allocated_to__invite_code',
            'allocated_to__date_created',
        )
        qs = qs.prefetch_related(
            'content__attachment_set',
            # Prefetch(
            #     'content__reaction_set',
            #     queryset=Reaction.objects.all().values(),
            #     to_attr = "reactions"
            # ),

            Prefetch(
                'content__reaction_set',
                queryset = Reaction.objects.filter(
                    user = '0' if self.request.user.is_anonymous else self.request.user
                ),
                to_attr = "my_react"
            ),
        )
        qs = qs.annotate(
            Count('comment', distinct=True),
            Count('content__reaction', distinct=True),
        )
        return qs
    return aggregator

class PostFeedAPIView(PaginationMixin, generics.ListAPIView):
    serializer_class = serializers.PostSerializer
    permission_classes = (IsAuthenticated,)
    paginate_kwargs = ('-hot_score', '-content__timestamp')

    # @count_db_hits
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['post_fields'] = ('allocated_to', 'content', 'total_reacts', 'reply_count')
        context['content_flds'] = ('author', 'attachments_preview', 'text', )
        context['profile_flds'] = ('fave_color',)
        return context

    # @perf_timer
    @sort_posts
    @posts_aggregate
    def get_big_queryset(self):
        qs = Post.objects.all()
        qs = qs.filter(
            allocated_to__in = Membership.get_joined_communities(self.request.user)
        )
        return qs


class PostSearchAPIView(SrchCompatiblePgnationMixin, PostFeedAPIView):
    permission_classes = ()
    serializer_class = serializers.PostSerializer
    search_fields = ('title', 'content__author__alias', 'content__author__username',)
    filter_backends = (filters.SearchFilter,)

    @posts_aggregate
    def get_big_queryset(self):
        return Post.objects.all().filter(allocated_to__is_secret=False)


class GetPostMixin(object):
    def get_post_object(self):
        url_val = self.kwargs['content_id']
        try:
            obj = Post.objects.get(content_id = url_val) if url_val.isdigit() else \
                Post.objects.get(slug = url_val)
        except Post.DoesNotExist:
            raise APIException("No post found", status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(self.request, obj)
        return obj

    def get_comment_object(self):
        try:
            obj = Comment.objects.get(content_id = self.kwargs['content_id'])
        except Comment.DoesNotExist:
            raise APIException("No comment found", status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(self.request, obj)
        return obj

    def get_content_object(self):
        try:
            obj = Content.objects.get(id=self.kwargs['content_id'])
        except Content.DoesNotExist:
            raise APIException("No content found", status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(self.request, obj)
        return obj


class PostDetailAPIView(GetPostMixin, generics.RetrieveUpdateAPIView):
    serializer_class = serializers.PostSerializer
    permission_classes = (IsOwnerOrReadOnly, IsMemberOrPublicPostsOnly)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.method=='GET':
            context['post_fields'] = ('slug', 'allocated_to', 'content', 'reply_count')
            context['content_flds'] = ('author', 'attachments', 'reactions', 'total_reacts')
            context['profile_flds'] = ('profile_pic', 'fave_color', 'you_follow', 'you_block')
        return context

    def get_object(self):
        return self.get_post_object()



class ContentEditAPIView(GetPostMixin, mixins.UpdateModelMixin, generics.DestroyAPIView):
    serializer_class = serializers.ContentSerializer
    permission_classes = (IsOwnerOrReadOnly,)
    def get_object(self):
        return self.get_content_object()
    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)



class CommentListAPIView(PaginationMixin, GetPostMixin, generics.ListAPIView):
    serializer_class = serializers.CommentSerializer
    permission_classes = (IsMemberOrPublicPostsOnly,)
    paginate_kwargs = ('-content__timestamp',)
    
    # @count_db_hits
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['post_fields'] = ('content', 'reply_count')
        context['content_flds'] = ('author', 'attachments', 'reactions')
        context['profile_flds'] = ('profile_pic', )
        return context

    # @perf_timer
    @sort_posts
    def get_big_queryset(self):
        qs = Comment.objects.all()

        # todo optimize aggragate
        qs = qs.select_related('content__author').defer(
            'content__author__bio',
            'content__author__location',
            'content__author__email',
            'content__author__password',
            'content__author__cover_photo',
            'content__author__date_joined',
            'content__author__is_active',
            'content__author__last_login',
            'content__author__is_superuser',
            'content__author__is_staff',
        )
        qs = qs.prefetch_related(
            'content__attachment_set',
            # Prefetch(
            #     'content__reaction_set',
            #     queryset=Reaction.objects.all().values(),
            #     to_attr = "reactions"
            # ),
            Prefetch(
                'content__reaction_set',
                queryset = Reaction.objects.filter(
                    user = '0' if self.request.user.is_anonymous else self.request.user
                ),
                to_attr = "my_react"
            ),
        )
        qs = qs.annotate(
            Count('comment', distinct=True),
            Count('content__reaction', distinct=True),
        )

        get_replies = self.request.query_params.get('is_reply')
        if get_replies == "1":
            qs = qs.filter(reply_to = self.get_comment_object())
            # self.paginate_kwargs = ('-content__timestamp',)
        else:
            qs = qs.filter(on = self.get_post_object(), reply_to = None)
        return qs


class CommentDetailAPIView(GetPostMixin, generics.RetrieveAPIView):
    serializer_class = serializers.CommentSerializer
    permission_classes = (IsMemberOrPublicPostsOnly,)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['post_fields'] = ('allocated_to', 'content', 'reply_count', 'reply_to', 'on')
        context['content_flds'] = ('author', 'attachments', 'reactions')
        context['profile_flds'] = ('profile_pic', 'fave_color')
        return context

    def get_object(self):
        return self.get_comment_object()


class CommentCreateAPIView(GetPostMixin, generics.CreateAPIView):
    serializer_class = serializers.CommentCreateSerializer
    permission_classes = (IsNotBlocked, IsMemberOrPublicPostsOnly)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user, on=self.get_post_object())



class ReactionListAPIView(PaginationMixin, GetPostMixin, generics.ListAPIView):
    serializer_class = UserPeakSerializer
    permission_classes = (IsMemberOrPublicPostsOnly,)
    paginate_kwargs = ('-reaction__timestamp',)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['profile_flds'] = ('profile_pic', 'you_follow', 'fave_color')
        return context

    def get_big_queryset(self):
        qs = User.objects.all()
        qs = qs.annotate(
            reaction__timestamp = Max('reaction__timestamp')
        )
        my_filter = {}
        my_filter['reaction__to'] = self.get_content_object()

        emote_id = self.request.query_params.get('emote')
        if emote_id:
            my_filter['reaction__icon_id'] = emote_id
        qs = qs.filter(**my_filter)
        # https://docs.djangoproject.com/en/2.2/topics/db/queries/#spanning-multi-valued-relationships
        return qs
