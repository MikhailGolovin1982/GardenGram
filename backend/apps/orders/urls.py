"""Роуты заказа. База подключается как api/v1/orders/ в config/urls.py.

`preview/` — литеральный путь, не конфликтует с конвертером <uuid:access_token>.
"""

from django.urls import path

from .views import CheckoutPreviewView, OrderDetailView, OrderListCreateView

urlpatterns = [
    path("", OrderListCreateView.as_view(), name="orders"),
    path("preview/", CheckoutPreviewView.as_view(), name="order-preview"),
    path("<uuid:access_token>/", OrderDetailView.as_view(), name="order-detail"),
]
