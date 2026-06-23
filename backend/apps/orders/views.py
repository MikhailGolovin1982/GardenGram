"""Вьюхи заказа. См. _scratch/PLAN_ORDER.md, п.8, п.9, п.12.

Оформление доступно гостю и юзеру: корзина резолвится тем же механизмом, что в apps.cart
(по аккаунту или по заголовку X-Cart-Token). Просмотр одного заказа — по секретному
access_token; список — только свои (залогиненному). Стиль — явные APIView, как в корзине.

Создание заказа целиком в transaction.atomic: либо создаются заказ + позиции и чистится
корзина, либо при сбое не остаётся ничего (полузаказов не бывает).
"""

from decimal import Decimal

from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cart.models import Cart
# Переиспользуем описание заголовка X-Cart-Token и префетч корзины из приложения корзины,
# чтобы не дублировать схему и запрос (резолв/расчёты идут по объектам в памяти, без N+1).
from apps.cart.views import CART_TOKEN_PARAM, _load_cart
from apps.core.models import DeliveryMethod, ShopSettings

from .models import Order, OrderItem
from .serializers import (
    CheckoutPreviewSerializer,
    OrderCreateSerializer,
    OrderSerializer,
)


def _resolve_cart_with_items(request):
    """Текущая корзина запроса с префетчем строк/вариантов/товаров (или None, если её нет)."""
    cart = Cart.objects.resolve(request, create=False)
    if cart is None:
        return None
    return _load_cart(cart.pk)


class OrderListCreateView(APIView):
    """POST — оформить заказ из текущей корзины (гость или юзер);
    GET — список СВОИХ заказов (только залогиненному)."""

    def get_permissions(self):
        # Оформлять может любой (гость/юзер); список своих заказов — только залогиненный.
        if self.request.method == "POST":
            return [AllowAny()]
        return [IsAuthenticated()]

    @extend_schema(
        tags=["orders"],
        parameters=[CART_TOKEN_PARAM],
        request=OrderCreateSerializer,
        responses=OrderSerializer,
        description="Оформить заказ из текущей корзины. В заказ идут только доступные позиции; "
        "цены замораживаются, корзина очищается. Гостю в ответе вернутся number и access_token.",
    )
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        cart = _resolve_cart_with_items(request)
        if cart is None or not cart.items.all():
            return Response(
                {"detail": "Корзина пуста."}, status=status.HTTP_400_BAD_REQUEST
            )

        active_items = cart.active_items  # вычисляется по префетченным строкам, без N+1
        if not active_items:
            return Response(
                {"detail": "Нет доступных позиций для заказа."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order = self._create_order(request, data, cart, active_items)
        return Response(
            OrderSerializer(order, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @transaction.atomic
    def _create_order(self, request, data, cart, active_items):
        """Собрать заказ: заморозить цены, посчитать доставку, создать Order+позиции, очистить корзину."""
        shop = ShopSettings.load()
        goods_total = sum(
            (item.subtotal for item in active_items), start=Decimal("0")
        )
        delivery_method = data["delivery_method"]
        delivery_cost = shop.delivery_cost(delivery_method, goods_total)

        user = request.user if request.user.is_authenticated else None
        # Лёгкая подстраховка (открытый вопрос 4): у залогиненного без введённого email
        # подставляем email из профиля. Имя/телефон всегда из формы (обязательны).
        email = data.get("email") or ""
        if not email and user is not None:
            email = user.email

        order = Order.objects.create(
            user=user,
            customer_name=data["customer_name"],
            customer_phone=data["customer_phone"],
            email=email,
            delivery_method=delivery_method,
            delivery_address=data.get("delivery_address", ""),
            wanted_time=data.get("wanted_time", ""),
            comment=data.get("comment", ""),
            goods_total=goods_total,
            delivery_cost=delivery_cost,
            total=goods_total + delivery_cost,
        )

        # Замораживаем позиции: копируем название/форму/цену из варианта в снимок заказа.
        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    variant=item.variant,
                    product_name=item.variant.product.display_name,
                    variant_label=item.variant.form_label,
                    unit_price=item.variant.price,
                    quantity=item.quantity,
                )
                for item in active_items
            ]
        )

        # Очищаем корзину (удаляем строки, сам контейнер оставляем — как DELETE /cart/).
        cart.items.all().delete()
        return order

    @extend_schema(
        tags=["orders"],
        responses=OrderSerializer(many=True),
        description="Список своих заказов (для залогиненного пользователя).",
    )
    def get(self, request):
        orders = (
            Order.objects.filter(user=request.user)
            .prefetch_related("items")
            .order_by("-created_at")
        )
        return Response(
            OrderSerializer(orders, many=True, context={"request": request}).data
        )


class CheckoutPreviewView(APIView):
    """GET — превью оформления по текущей корзине: суммы, порог и опции доставки с ценами."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["orders"],
        parameters=[CART_TOKEN_PARAM],
        responses=CheckoutPreviewSerializer,
        description="Сводка для экрана оформления: сумма товаров, порог бесплатной доставки, "
        "сколько добрать до бесплатной, и стоимость каждого способа доставки.",
    )
    def get(self, request):
        cart = _resolve_cart_with_items(request)
        goods_total = cart.total if cart is not None else Decimal("0")
        shop = ShopSettings.load()

        local_cost = shop.delivery_cost(DeliveryMethod.LOCAL, goods_total)
        data = {
            "goods_total": goods_total,
            "free_delivery_threshold": shop.free_delivery_threshold,
            "amount_until_free_delivery": shop.amount_until_free_delivery(goods_total),
            "delivery_options": [
                {
                    "method": DeliveryMethod.PICKUP,
                    "label": DeliveryMethod.PICKUP.label,
                    "cost": Decimal("0"),
                    "is_free": True,
                },
                {
                    "method": DeliveryMethod.LOCAL,
                    "label": DeliveryMethod.LOCAL.label,
                    "cost": local_cost,
                    "is_free": local_cost == 0,
                },
            ],
        }
        return Response(CheckoutPreviewSerializer(data).data)


class OrderDetailView(APIView):
    """GET — посмотреть один заказ по секретному токену доступа (модель «секретной ссылки»)."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["orders"],
        responses=OrderSerializer,
        description="Посмотреть заказ по секретному access_token (его получает покупатель при оформлении).",
    )
    def get(self, request, access_token):
        order = get_object_or_404(
            Order.objects.prefetch_related("items"), access_token=access_token
        )
        # Доп. защита (открытый вопрос 6): заказ, привязанный к аккаунту, не отдаём другому
        # залогиненному пользователю, даже если он как-то узнал токен.
        if (
            order.user_id
            and request.user.is_authenticated
            and request.user.id != order.user_id
        ):
            raise Http404("Заказ не найден.")
        return Response(OrderSerializer(order, context={"request": request}).data)
