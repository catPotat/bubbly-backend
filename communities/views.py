from rest_framework import (
    generics,
    mixins,
    filters,
    status,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import APIException
from rest_framework.response import Response

from django.db.models import Prefetch, Count, Q

from .models import Community, Membership
from posts.models import Post, Content
from reacts.models import Icon, Reaction
from chat.models import Room, PublicRoom, Message

from . import serializers
from chat.serializers import PublicRoomsSerializer
from posts.serializers import (
    PostCreateSerializer,
    PostSerializer,
    ContentSerializer )
from reacts.serializers import IconListSerializer

from .permissions import IsCommunityMemberOrPublicOnly
from mod_tools.permissions import IsAdmin, IsMod

from bubblyb.utils import PaginationMixin, SrchCompatiblePgnationMixin
from posts.views import sort_posts, posts_aggregate

from django.utils.timezone import now
from datetime import timedelta

from django.core.cache import caches
from rest_framework.throttling import UserRateThrottle



class CommunityListAPIView(SrchCompatiblePgnationMixin, generics.ListAPIView):
    serializer_class = serializers.CommunityPeakSerializer
    # permission_classes = (IsAuthenticated,)
    search_fields = ('name', 'id', 'moto',)
    filter_backends = (filters.SearchFilter,)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['cmty_fields'] = ['cover_img', 'moto', 'visibility']
        if not self.request.user.is_anonymous:
            context['cmty_fields'].append('membership_info')
        return context
        
    def get_big_queryset(self):
        qs = Community.objects.all()
        
        sortby = self.request.query_params.get('sortby', "")
        if sortby == "most_mems":
            qs = qs.annotate(most_members=Count('membership', filter=Q(membership__role__gte=Membership.MEMBER)))
            self.paginate_kwargs = ('-most_members',)
        elif sortby == "growing":
            qs = qs.annotate(most_members=Count('membership', filter=Q(
                membership__role__gte = Membership.MEMBER,
                membership__date_joined__gte = now() - timedelta(days=90)
            )))
            self.paginate_kwargs = ('-most_members',)
        else:
            self.paginate_kwargs = ('date_created',)

        qs = qs.filter(is_secret=False)
        return qs


class GetCommunityMixin(object):
    def get_community_obj(self):
        try:
            obj = Community.objects.get(id = self.kwargs['id'])
        except Community.DoesNotExist:
            raise APIException("No community found", status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(self.request, obj)
        return obj


class CommunityDetailAPIView(GetCommunityMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, generics.RetrieveAPIView):
    serializer_class = serializers.CommunityDetailSerializer

    def get_permissions(self):
        if self.request.method=='GET':
            return (IsCommunityMemberOrPublicOnly(),)
        elif self.request.method=='POST':
            return (IsAuthenticated(),)
        return (IsAdmin(),) # PATCH
    
    def get_object(self):
        # return None
        return self.get_community_obj()
        
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)
    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class PostCreateAPIView(GetCommunityMixin, generics.CreateAPIView):
    serializer_class = PostCreateSerializer
    permission_classes = (IsCommunityMemberOrPublicOnly,)
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user, allocated_to=self.get_community_obj())



class CommunityMemberListAPIView(GetCommunityMixin, PaginationMixin, generics.ListAPIView):
    serializer_class = serializers.MembershipSerializer
    paginate_kwargs = ('-role', '-date_joined')
    paginate_limit = 20
    offset_prop = 'user'
    def get_permissions(self):
        if self.request.query_params.get("filter_by") == "banned":
            return (IsMod(),)
        else:
            return (IsCommunityMemberOrPublicOnly(),)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['memb_fields'] = ('user',)
        context['profile_flds'] = ('profile_pic', 'fave_color', 'you_follow')
        return context

    def get_big_queryset(self):
        qs = Membership.objects.all()
        qs = qs.select_related('user')
        qs = qs.filter(community = self.get_community_obj())
        role_filter = self.request.query_params.get("filter_by")
        if role_filter == "mod_team":
            qs = qs.filter(role__gte = Membership.MODERATOR)
        elif role_filter == "banned":
            qs = qs.filter(role = Membership.BANNED)
        else:
            qs = qs.filter(role__gte = Membership.MEMBER)
        return qs


class MembershipCreateDestroyAPIView(GetCommunityMixin, generics.CreateAPIView):
    serializer_class = serializers.MembershipCreateSerializer
    # throttle_classes = (UserRateThrottle, )
    permission_classes = (IsAuthenticated,)
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['community'] = self.get_community_obj()
        return context
    def delete(self, request, **kwargs):
        try:
            mem_obj = Membership.objects.get(
                community = self.get_community_obj(),
                user = request.user,
            )
            mem_obj.role = Membership.VISITANT
            mem_obj.save()
            return Response(status=status.HTTP_200_OK)
        except Membership.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)




class CmtyRoomListAPIView(GetCommunityMixin, PaginationMixin, generics.ListAPIView):
    serializer_class = PublicRoomsSerializer
    permission_classes = (IsCommunityMemberOrPublicOnly,)
    paginate_kwargs = ('order',)
    paginate_limit = 6

    def get_big_queryset(self):
        qs = PublicRoom.objects.all()
        qs = qs.select_related('room')
        qs = qs.prefetch_related( Prefetch('room__message_set',
            queryset=Message.objects.order_by('-timestamp')) )
        qs = qs.filter(associated_with = self.get_community_obj())
        return qs


class CmtyPostFeedAPIView(GetCommunityMixin, PaginationMixin, generics.ListAPIView):
    permission_classes = (IsCommunityMemberOrPublicOnly,)
    serializer_class = PostSerializer
    paginate_kwargs = ('-hot_score', '-content__timestamp')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['post_fields'] = ('content', 'total_reacts', 'reply_count')
        context['content_flds'] = ('author', 'attachments_preview', 'text')
        context['profile_flds'] = ('profile_pic',)
        return context

    @sort_posts
    @posts_aggregate
    def get_big_queryset(self):
        qs = Post.objects.all()
        qs = qs.filter(allocated_to=self.get_community_obj())
        return qs


class CmtyEmoteListAPIView(GetCommunityMixin, PaginationMixin, generics.ListAPIView):
    serializer_class = IconListSerializer
    permission_classes = (IsCommunityMemberOrPublicOnly,)
    paginate_kwargs = ('-active', '-uploaded_on')
    
    def get_big_queryset(self):
        qs = Icon.objects.all()
        qs = qs.filter(belongs_to = self.get_community_obj())
        # if self.request.query_params.get('get_inactive', "") != "1":
        #     my_filter['active'] = True
        return qs


class CmtyAnouncementListAPIView(GetCommunityMixin, PaginationMixin, generics.ListAPIView):
    serializer_class = ContentSerializer
    permission_classes = (IsCommunityMemberOrPublicOnly,)
    paginate_kwargs = ('pinnedpost__order',)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['content_flds'] = ('author', 'attachments')
        return context
    
    def get_big_queryset(self):
        qs = Content.objects.all()
        qs = qs.select_related('pinnedpost', 'author')
        user = '0' if self.request.user.is_anonymous else self.request.user
        qs = qs.prefetch_related(
            'attachment_set',
            Prefetch(
                'reaction_set',
                queryset=Reaction.objects.filter(user=user),
                to_attr="my_react"
            ),
        )
        qs = qs.filter(pinnedpost__allocated_to=self.get_community_obj())
        return qs 
