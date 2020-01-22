from rest_framework import (
    mixins,
    generics,
    status,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import APIException

from django.db.models import Count

from . import serializers

from communities.models import Membership
from .models import Reaction


from posts.views import GetPostMixin
from posts.permissions import (
    IsNotBlocked,
    IsMemberOrPublicPostsOnly
)

from bubblyb.utils import PaginationMixin


class IconListAPIView(PaginationMixin, generics.ListAPIView):
    serializer_class = serializers.MyIconsSerializer
    permission_classes = (IsAuthenticated,)
    paginate_kwargs = ('id',)
    paginate_limit = 6
    def get_big_queryset(self):
        qs = Membership.get_joined_communities(self.request.user)
        qs = qs.prefetch_related('icon_set')
        return qs



class ReactionCreateAPIView(GetPostMixin, generics.CreateAPIView):
    serializer_class = serializers.ReactionCreateSerializer
    permission_classes = (IsNotBlocked, IsMemberOrPublicPostsOnly,)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['content'] = self.get_content_object()
        return context
    def perform_create(self, serializer):
        u = self.request.user
        to = serializer.context['content']
        Reaction.objects.filter(user=u, to=to).delete()
        serializer.save(user=u, to=to)

    def get(self, request, **kwargs):
        return Response(
            {'reactions': self.get_content_object().reaction_set.values('icon_id').annotate(count=Count('icon_id'))},
            status = status.HTTP_200_OK
        )

    def delete(self, request, **kwargs):
        Reaction.objects.filter(user=request.user, to=self.get_content_object()).delete()
        return Response(status = status.HTTP_204_NO_CONTENT)