"""Роуты корзины. База подключается как api/v1/cart/ в config/urls.py."""

from django.urls import path

from .views import CartItemDetailView, CartItemView, CartMergeView, CartView

urlpatterns = [
    path("", CartView.as_view(), name="cart"),
    path("items/", CartItemView.as_view(), name="cart-items"),
    path("items/<int:pk>/", CartItemDetailView.as_view(), name="cart-item-detail"),
    path("merge/", CartMergeView.as_view(), name="cart-merge"),
]
