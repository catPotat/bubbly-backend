from django.urls import path

from . import views

urlpatterns = (
    path('<id>/posts/<content_id>', views.FetusDeletusAPIView.as_view(), name='mod-delete'),
    path('<id>/members/<username>', views.BanHammerAPIView.as_view(), name='ban-hammer'),

    path('<id>/anouncements', views.AnouncementsCreateAPIView.as_view(), name='anouncements'),
    path('<id>/anouncements/swap', views.AnouncementSwapAPIView.as_view(), name='anouncements-swap'),

    path('<id>/chat', views.ChatRoomCreateAPIView.as_view(), name='pub-chat-create'),
    path('<id>/chat/swap', views.ChatRoomSwapAPIView.as_view(), name='pub-chat-swap'),
    path('<id>/chat/<room_id>', views.ChatRoomEditAPIView.as_view(), name='pub-chat'),

    path('<id>/icons', views.IconCreateAPIView.as_view(), name='community-icons-create'),
    path('<id>/icons/<name>', views.IconEditAPIView.as_view(), name='community-icons-edit'),
)