from django.urls import path

from . import views

urlpatterns = (
    path('icons/all/', views.IconListAPIView.as_view(), name='icon-list'),
    
    path('<content_id>', views.ReactionCreateAPIView.as_view(), name='react-to'),
)
