from django.urls import path

from . import views

urlpatterns = (
    path('explore/', views.PublicRoomExplorerAPIView.as_view(), name='joined-cmty-public-rooms'),
    path('my-rooms/', views.MyRoomListAPIView.as_view(), name='my-rooms'),

    path('<id>/add', views.MakeRoomsAndMatesAPIView.as_view(), name='make-room'),
    path('<id>/save-public', views.SavePublicRoomAPIView.as_view(), name='save-public-room'),

    path('<id>', views.RoomDetailAPIView.as_view(), name='get-thread'),
    path('<id>/history/', views.RetrieveMessagesAPIView.as_view(), name='thread-history'),
    
    path('<id>/roommates/', views.RoommateListAPIView.as_view(), name='list-mates'),
    path('<id>/roommates/__self', views.MyRoommateInfoAPIView.as_view(), name='edit-self'),
    path('<id>/roommates/<username>', views.RoommateEditAPIView.as_view(), name='edit-role'),
)