from django.urls import path

from . import views

urlpatterns = (
    path('get-upload-url', views.CreatePresignedS3UrlAPIView.as_view()),
)