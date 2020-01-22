from rest_framework import (
    mixins,
    generics,
    permissions,
    status,
    filters,
)
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from rest_framework.views import APIView
from django.db.models import Q, Prefetch, Count, Max

from .models import User
from posts.models import Post, Comment, Content
from communities.models import Membership
from relationships.models import Block
from chat.models import Room

from . import serializers
from posts.serializers import (
    PostSerializer,
    CommentSerializer,
)
from communities.serializers import MembershipSerializer
from chat.serializers import RoomDetailSerializer
from reacts.models import Reaction

from .permissions import IsSelfOrReadOnly

from posts.views import sort_posts, posts_aggregate

from bubblyb.utils import (
    PaginationMixin,
    SrchCompatiblePgnationMixin,
    count_db_hits,
    perf_timer
)


class UserListAPIView(SrchCompatiblePgnationMixin, generics.ListAPIView):
    serializer_class = serializers.UserPeakSerializer
    paginate_kwargs = ('-date_joined',)
    search_fields = ('username', 'alias', '=email')
    filter_backends = (filters.SearchFilter,)
    queryset = User.objects.all().filter(is_active=True)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.query_params.get('minimal') == "1":
            to_show = ('profile_pic',)
        else:
            to_show = ('profile_pic', 'you_follow', 'fave_color', 'bio')
        context['profile_flds'] = to_show
        return context


class UserObjectMixin(object):
    def get_user_object(self):
        user = User.objects.get_by_username(self.kwargs['username'])
        if not user:
            raise APIException("No user found", status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(self.request, user)
        return user


class UserCreateAPIView(generics.CreateAPIView):
    serializer_class = serializers.UserCreateSerializer
    permission_classes = (permissions.AllowAny,)


class PasswordUpdateAPIView(APIView):
    serializer_class = serializers.PasswordUpdateSerializer
    permission_classes = (permissions.IsAuthenticated,)
    def put(self, request, *args, **kwargs):
        instance = request.user
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_202_ACCEPTED)

class EmailUpdateAPIView(PasswordUpdateAPIView):
    serializer_class = serializers.EmailSerializer
    def get(self, request, *args, **kwargs):
        serializer = serializers.EmailSerializer(request.user, context={'request': self.request})
        return Response(serializer.data, status.HTTP_200_OK)


class ProfileDetailAPIView(UserObjectMixin, mixins.UpdateModelMixin, generics.RetrieveAPIView):
    serializer_class = serializers.UserDetailSerializer
    permission_classes = (IsSelfOrReadOnly,)
    def get_object(self):
        return self.get_user_object()
    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class GetDirectAPIView(UserObjectMixin, APIView):
    permission_classes = (permissions.IsAuthenticated,)
    def get(self, request, *args, **kwargs):
        me = self.request.user
        them = self.get_user_object()
        if Block.blocked(them, me):
            return Response({"detail":"Your blockt"}, status.HTTP_412_PRECONDITION_FAILED)
        direct = Room.get_direct(self.request.user, self.get_user_object())
        if direct:
            # serializer = RoomDetailSerializer(direct.room, context={'request': self.request})
            return Response({"room_id": direct.room_id}, status.HTTP_206_PARTIAL_CONTENT)
        return Response({"room_id": None}, status.HTTP_200_OK)


class MembershipListAPIView(UserObjectMixin, PaginationMixin, generics.ListAPIView):
    serializer_class = MembershipSerializer
    permission_classes = (permissions.AllowAny,)
    paginate_kwargs = ('-reputation_point', '-date_joined',)
    paginate_limit = 15
    offset_prop = 'community'
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['memb_fields'] = ('community',)
        context['cmty_fields'] = ('cover_img',)
        return context

    def get_big_queryset(self):
        qs = Membership.objects.all()
        qs = qs.select_related('community')
        you = '0' if self.request.user.is_anonymous else self.request.user
        if self.kwargs['username'] == '__self':
            qs = qs.filter(user=you)
            self.paginate_limit = 69 # be careful
        else:
            them = self.get_user_object()
            q = Q(community__is_secret=False
                    ) | Q(community__in=Membership.get_mutual_communities(you, them))
            qs = qs.filter(q, user=them)

        qs = qs.filter(role__gte=Membership.MEMBER)
        return qs


class UserPostsAPIView(UserObjectMixin, PaginationMixin, generics.ListAPIView):
    serializer_class = PostSerializer
    paginate_kwargs = ('-content__timestamp',)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['post_fields'] = ('allocated_to', 'content', 'total_reacts', 'reply_count')
        context['content_flds'] = ('attachments_preview', 'text')
        context['cmty_fields'] = ('visibility',)
        return context

    # @count_db_hits
    @sort_posts
    @posts_aggregate
    def get_big_queryset(self):
        qs = Post.objects.all()
        them = self.get_user_object()
        q = Q(allocated_to__is_secret=False
                ) | Q(allocated_to__in=Membership.get_mutual_communities(self.request.user, them))
        qs = qs.filter(q, content__author=them)
        return qs


class UserCommentAPIView(UserPostsAPIView):
    serializer_class = CommentSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['post_fields'] = ('on', 'reply_to', 'content', 'reply_count')
        context['content_flds'] = ('attachments',)
        return context

    def get_big_queryset(self):
        qs = Comment.objects.all()
        them = self.get_user_object()
        q = Q(allocated_to__is_secret=False
                ) | Q(allocated_to__in=Membership.get_mutual_communities(self.request.user, them))
        qs = qs.filter(q, content__author=them)
        return qs


class PostsReactedToAPIView(UserObjectMixin, PaginationMixin, generics.ListAPIView):
    # serializer_class = ReactedToSerializer # todo later maybe
    paginate_kwargs = ('timestamp',)
    def get_big_queryset(self):
        qs = self.get_user_object().reaction_set

        return qs


class FollowListAPIView(UserObjectMixin, UserListAPIView):
    paginate_limit = 20
    
    def get_big_queryset(self):
        qs = User.objects.all()

        if self.request.query_params.get('get_followers') == "1":
            kwarg = 'from_user__timestamp'
            fltrkw = 'from_user__to_user'
        else:
            kwarg = 'follows__timestamp'
            fltrkw = 'follows__from_user'

        qs = qs.filter(**{fltrkw: self.get_user_object()})
        qs = qs.annotate(**{kwarg: Max(kwarg)})
        self.paginate_kwargs = (f"-{kwarg}",)

        return qs


class ExistanceCheckAPIView(APIView):
    permission_classes = (permissions.AllowAny,)
    def get(self, request, *args, **kwargs):
        exists = None
        # big walrus candidate
        email = request.query_params.get('email')
        if email:
            exists = User.objects.all().filter(email=email).exists()
        else:
            username = request.query_params.get('username')
            if username:
                exists = User.objects.all().filter(username=username).exists()
        return Response({"presence": exists}, status.HTTP_200_OK)


class AccountHeadsUp(APIView):
    def get(self, request, *args, **kwargs):
        def get_first_time(set_):
            first_obj = set_.first()
            return first_obj.timestamp if first_obj else 0

        user = request.user
        if user.is_anonymous:
            return Response({"detail": "Authentication credentials were not provided."},
                status.HTTP_401_UNAUTHORIZED)

        mate_obj = user.joined_chats.order_by('room__message__timestamp').last()
        has_unread = False
        if mate_obj:
            mate_obj__time = mate_obj.last_seen
            msg_obj__time = get_first_time(mate_obj.room.message_set)
            has_unread = mate_obj__time < msg_obj__time

        data = {
            "lastest_noti": get_first_time(user.noti_receiver.all()),
            "has_unread_msg": has_unread
        }
        return Response(data, status.HTTP_200_OK)