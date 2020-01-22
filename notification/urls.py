from django.urls import path

from . import views

urlpatterns = (
    path('all/', views.NotificationListAPIView.as_view(), name='noti-list' ),
)
