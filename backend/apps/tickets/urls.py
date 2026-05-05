from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TicketCategoryViewSet, TicketViewSet

router = DefaultRouter()
router.register(r'categories', TicketCategoryViewSet, basename='ticket-categories')
router.register(r'', TicketViewSet, basename='tickets')

urlpatterns = [
    path('', include(router.urls)),
]
