"""Вьюхи корзины. См. _scratch/PLAN_CART.md, п.4, п.6, п.7.

Корзина — «синглтон на субъекта»: в URL её id не светим, всегда работаем с «моей текущей
корзиной» (резолв по аккаунту или по токену гостя). Адресуемы только строки — по их id.

Все операции доступны и гостю (AllowAny), кроме слияния (нужен залогиненный аккаунт).
"""

from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Cart, CartItem
from .serializers import (
    AddCartItemSerializer,
    CartSerializer,
    UpdateCartItemSerializer,
)

# Заголовок с токеном гостевой корзины — для неавторизованных запросов.
# Описываем его в схеме, чтобы в Swagger можно было ввести токен и протестировать гостя.
CART_TOKEN_PARAM = OpenApiParameter(
    "X-Cart-Token",
    OpenApiTypes.UUID,
    OpenApiParameter.HEADER,
    required=False,
    description="Токен гостевой корзины (для неавторизованных). "
    "Возвращается в поле token при первом добавлении.",
)

# Представление пустой корзины, когда строки в БД ещё нет (гость без токена на GET).
# Не создаём строку Cart ради чтения — бережём БД от мусора (см. resolve(create=False)).
EMPTY_CART = {
    "token": None,
    "items": [],
    "total": "0.00",
    "count": 0,
    "has_unavailable_items": False,
}


def _load_cart(pk):
    """Перечитать корзину с префетчем строк/вариантов/товаров/фото — без N+1.

    Живые расчёты (total/count/доступность) и сериализация ходят по этим объектам в памяти.
    """
    items_qs = (
        CartItem.objects.select_related("variant", "variant__product")
        .prefetch_related("variant__product__images")
        .order_by("added_at", "id")
    )
    return Cart.objects.prefetch_related(Prefetch("items", queryset=items_qs)).get(pk=pk)


def _cart_response(cart, request, http_status=status.HTTP_200_OK):
    """Единый ответ: сериализованная корзина (или пустое представление, если корзины нет)."""
    if cart is None:
        return Response(EMPTY_CART, status=http_status)
    cart = _load_cart(cart.pk)
    data = CartSerializer(cart, context={"request": request}).data
    return Response(data, status=http_status)


class CartView(APIView):
    """GET — показать корзину; DELETE — очистить (удалить все строки, корзину оставить)."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["cart"],
        parameters=[CART_TOKEN_PARAM],
        responses=CartSerializer,
        description="Показать текущую корзину (по аккаунту или токену гостя).",
    )
    def get(self, request):
        cart = Cart.objects.resolve(request, create=False)
        return _cart_response(cart, request)

    @extend_schema(
        tags=["cart"],
        parameters=[CART_TOKEN_PARAM],
        responses=CartSerializer,
        description="Очистить корзину: удалить все строки (саму корзину сохраняем).",
    )
    def delete(self, request):
        cart = Cart.objects.resolve(request, create=False)
        if cart is not None:
            cart.items.all().delete()
        return _cart_response(cart, request)


class CartItemView(APIView):
    """POST — добавить вариант в корзину (если уже есть — увеличить количество)."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["cart"],
        parameters=[CART_TOKEN_PARAM],
        request=AddCartItemSerializer,
        responses=CartSerializer,
        description="Добавить вариант в корзину. Если вариант уже есть — увеличить количество. "
        "Класть можно только доступные варианты (активные и в наличии).",
    )
    def post(self, request):
        serializer = AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        variant = serializer.validated_data["variant"]
        quantity = serializer.validated_data["quantity"]

        # create=True: для гостя при необходимости создаётся корзина с новым токеном,
        # который вернётся в ответе (CartSerializer.token) — клиент его сохранит.
        cart = Cart.objects.resolve(request, create=True)
        item, created = cart.items.get_or_create(
            variant=variant, defaults={"quantity": quantity}
        )
        if not created:
            item.quantity += quantity  # повторное добавление → увеличиваем количество
            item.save(update_fields=["quantity", "updated_at"])

        return _cart_response(cart, request, http_status=status.HTTP_201_CREATED)


class CartItemDetailView(APIView):
    """PATCH — изменить количество строки; DELETE — удалить строку.

    Строку ищем ТОЛЬКО внутри корзины запросившего — чужую строку тронуть нельзя.
    """

    permission_classes = [AllowAny]

    def _get_item_or_404(self, request, pk):
        cart = Cart.objects.resolve(request, create=False)
        if cart is None:
            # Нет корзины — значит и этой строки у запросившего нет.
            raise Http404("Корзина не найдена.")
        return cart, get_object_or_404(cart.items, pk=pk)

    @extend_schema(
        tags=["cart"],
        parameters=[CART_TOKEN_PARAM],
        request=UpdateCartItemSerializer,
        responses=CartSerializer,
        description="Изменить количество строки корзины.",
    )
    def patch(self, request, pk):
        cart, item = self._get_item_or_404(request, pk)
        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item.quantity = serializer.validated_data["quantity"]
        item.save(update_fields=["quantity", "updated_at"])
        return _cart_response(cart, request)

    @extend_schema(
        tags=["cart"],
        parameters=[CART_TOKEN_PARAM],
        responses=CartSerializer,
        description="Удалить строку из корзины.",
    )
    def delete(self, request, pk):
        cart, item = self._get_item_or_404(request, pk)
        item.delete()
        return _cart_response(cart, request)


class CartMergeView(APIView):
    """POST — слить гостевую корзину (по токену из X-Cart-Token) в корзину пользователя.

    Вызывается фронтом сразу после логина. Гостю сливать не во что → нужен залогиненный.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["cart"],
        parameters=[CART_TOKEN_PARAM],
        request=None,
        responses=CartSerializer,
        description="Слить гостевую корзину (токен в X-Cart-Token) в корзину пользователя. "
        "Совпавшие варианты — количества суммируются. Вызывать после логина.",
    )
    def post(self, request):
        token = request.headers.get("X-Cart-Token")
        guest_cart = None
        if token:
            try:
                guest_cart = Cart.objects.filter(
                    token=token, user__isnull=True
                ).first()
            except (ValueError, ValidationError):
                guest_cart = None  # битый токен в заголовке — сливать нечего

        if guest_cart is not None:
            cart = Cart.objects.merge_guest_into_user(guest_cart, request.user)
        else:
            # Нечего сливать — просто отдаём (создав при отсутствии) корзину пользователя.
            cart = Cart.objects.resolve(request, create=True)

        return _cart_response(cart, request)
