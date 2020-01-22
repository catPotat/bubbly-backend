from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.db.models import Q

from .models import Relationship, Block
from chat.models import Room
from accounts.views import UserObjectMixin

class FollowEditAPIView(UserObjectMixin, APIView):
    permission_classes = (IsAuthenticated,)
    def post(self, request, **kwargs):
        you = request.user
        them = self.get_user_object()
        if you == them:
            return Response({'detail': "Can't follow yourself!"}, status=status.HTTP_403_FORBIDDEN)
        if Block.blocked(them, you):
            return Response({'detail': "You are blocked"}, status=status.HTTP_403_FORBIDDEN)

        instance, _ = Relationship.objects.get_or_create(
            from_user = you,
            to_user = them
        )
        return Response(status=status.HTTP_201_CREATED)
    def delete(self, request, **kwargs):
        pact = Relationship.objects.filter(
            from_user = request.user,
            to_user__username = kwargs['username']
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class BlockEditAPIView(UserObjectMixin, APIView):
    permission_classes = (IsAuthenticated,)
    def post(self, request, **kwargs):
        you = request.user
        the_1_u_h8 = self.get_user_object()
        
        if you == the_1_u_h8:
            return Response({'detail': "Can't block yourself!"}, status=status.HTTP_403_FORBIDDEN)

        Relationship.objects.filter(
            Q(from_user = you) | Q(from_user = the_1_u_h8),
            Q(to_user = you) | Q(to_user = the_1_u_h8),
        ).delete()
        dm = Room.get_direct(you, the_1_u_h8)
        if dm: dm.room.delete()

        instance, _ = Block.objects.get_or_create(
            blocker = you,
            got_blokt = the_1_u_h8
        )
        return Response(status=status.HTTP_201_CREATED)
    def delete(self, request, **kwargs):
        Block.objects.filter(
            blocker = request.user,
            got_blokt__username = kwargs['username']
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
