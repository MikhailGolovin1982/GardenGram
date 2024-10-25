from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()
router.register(r'', views.ProductDetailView, basename='product')

urlpatterns = [
    # Маршруты для категорий
    path('categories/', views.CategoryListCreateView.as_view(), name='category-list-create'),
    path('categories/<int:pk>/', views.CategoryDetailView.as_view(), name='category-detail'),

    # Маршруты для товаров
    path('', include(router.urls)),

    # Маршруты для наличия товаров
    path('stocks/', views.StockListCreateView.as_view(), name='stock-list-create'),
    path('stocks/<int:pk>/', views.StockDetailView.as_view(), name='stock-detail'),

    # Маршруты для изображений товаров
    path('product-images/', views.ProductImageListCreateView.as_view(), name='product-image-list-create'),
    path('product-images/<int:pk>/', views.ProductImageDetailView.as_view(), name='product-image-detail'),
]
