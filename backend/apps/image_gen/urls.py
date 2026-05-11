from django.urls import path
from . import views

urlpatterns = [
    path('generations/', views.ImageGenerationView.as_view(), name='image_generations'),
    path('generations/<int:pk>/', views.ImageGenerationDetailView.as_view(), name='image_generation_detail'),
]
