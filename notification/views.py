from rest_framework import (
    filters,
    generics,
    status
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import (
    NotificationListSerializer,
)

from .models import Notification

from bubblyb.utils import PaginationMixin

class NotificationListAPIView(PaginationMixin, generics.ListAPIView):
    serializer_class = NotificationListSerializer
    permission_classes = (IsAuthenticated,)
    paginate_kwargs = ('-timestamp',)
        
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['profile_flds'] = ['profile_pic', 'fave_color']
        return context
    
    def get_big_queryset(self):
        qs = Notification.objects.all()
        qs = qs.filter(receiver=self.request.user)
        return qs
        
    def delete(self, request, *args, **kwargs):
        qs = self.get_big_queryset()
        qs.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)