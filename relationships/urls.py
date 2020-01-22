from django.urls import path

from . import views

urlpatterns = (
    path('follow/<username>', views.FollowEditAPIView.as_view(), name='follow-edit' ),
    path('block/<username>', views.BlockEditAPIView.as_view(), name='block-edit' ),
)