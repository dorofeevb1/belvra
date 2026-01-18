from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, MasterServiceViewSet, PortfolioItemViewSet, ServiceViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("items", ServiceViewSet, basename="service")
router.register("master-services", MasterServiceViewSet, basename="master-service")
router.register("portfolio", PortfolioItemViewSet, basename="portfolio")

urlpatterns = [
    path("", include(router.urls)),
]
