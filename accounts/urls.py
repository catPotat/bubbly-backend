from django.urls import path

from rest_framework_jwt.views import obtain_jwt_token, refresh_jwt_token
from . import views

urlpatterns = (
    path('', views.UserListAPIView.as_view(), name='user-list'),

    path('existance-check', views.ExistanceCheckAPIView.as_view(), name='pre-register'),
    path('register', views.UserCreateAPIView.as_view(), name='register'),
    path('get-jwt', obtain_jwt_token),
    path('refresh-jwt', refresh_jwt_token),

    path('__self/update-pw', views.PasswordUpdateAPIView.as_view(), name='password-update'),
    path('__self/update-email', views.EmailUpdateAPIView.as_view(), name='email-update'),
    path('__self/badge-count', views.AccountHeadsUp.as_view()),

    path('<username>', views.ProfileDetailAPIView.as_view(), name='user-profile'),
    path('<username>/posts/', views.UserPostsAPIView.as_view(), name='user-posts'),
    path('<username>/communities/', views.MembershipListAPIView.as_view(), name='user-community-list'),
    path('<username>/circles/', views.FollowListAPIView.as_view(), name='user-follows'),
    path('<username>/comments/', views.UserCommentAPIView.as_view()),
    path('<username>/chat-to', views.GetDirectAPIView.as_view()),
    # path('<username>/reacted-posts/', views.ReactedToAPIView.as_view(), name='user-reacted'),
)