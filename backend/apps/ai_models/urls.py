from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AIModelViewSet, ModelProviderViewSet, ModelCategoryViewSet

router = DefaultRouter()
router.register(r'models', AIModelViewSet, basename='aimodels')
router.register(r'providers', ModelProviderViewSet, basename='providers')
router.register(r'categories', ModelCategoryViewSet, basename='modelcategories')

urlpatterns = [
    path('', include(router.urls)),
]
