from django.urls import path

from . import views

urlpatterns = (
    path('search/', views.PostSearchAPIView.as_view(), name='post-search'),
    path('feed/', views.PostFeedAPIView.as_view(), name='post-feed'),
    path('following/', views.PostFeedAPIView.as_view(), name='following-feed'),

    path('comment/<content_id>', views.CommentDetailAPIView.as_view(), name='comment-detail'),
    path('<content_id>', views.PostDetailAPIView.as_view(), name='post-detail'),
    path('<content_id>/reacts/', views.ReactionListAPIView.as_view(), name='content-reacts'),

    path('<content_id>/comments/', views.CommentListAPIView.as_view(), name='content-comments'),
    path('<content_id>/comments/create', views.CommentCreateAPIView.as_view(), name='comment-create'),
    
    path('<content_id>/edit', views.ContentEditAPIView.as_view(), name='content-edit'),
)