from django.urls import path

from . import views

urlpatterns = (
    path('', views.CommunityListAPIView.as_view(), name='community-list'),
    path('create', views.CommunityDetailAPIView.as_view(), name='community-create'),

    path('<id>', views.CommunityDetailAPIView.as_view(), name='community-detail'),
    path('<id>/members/', views.CommunityMemberListAPIView.as_view(), name='community-members'),
    path('<id>/members/__self', views.MembershipCreateDestroyAPIView.as_view(), name='membership-create'),
    path('<id>/icons/', views.CmtyEmoteListAPIView.as_view(), name='community-react-icons'),
    path('<id>/public-rooms/', views.CmtyRoomListAPIView.as_view(), name='public-rooms'),
    path('<id>/anouncements/', views.CmtyAnouncementListAPIView.as_view(), name='public-anouncements'),

    path('<id>/posts/', views.CmtyPostFeedAPIView.as_view(), name='community-posts'),
    path('<id>/posts/create', views.PostCreateAPIView.as_view(), name='cmty-posts-create'),
)