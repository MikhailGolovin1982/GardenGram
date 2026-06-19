"""URL каталога: роутер для товаров + отдельный path для дерева категорий."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CategoryTreeView, ProductViewSet

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")

urlpatterns = [
    path("categories/", CategoryTreeView.as_view(), name="category-tree"),
]
urlpatterns += router.urls
