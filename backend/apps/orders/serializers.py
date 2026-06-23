"""Сериализаторы заказа. См. _scratch/PLAN_ORDER.md, п.10.

Вход (OrderCreateSerializer) — только ВАЛИДАЦИЯ данных покупателя и способа доставки;
саму сборку заказа из корзины (заморозка цен, расчёт доставки, транзакция) делает вьюха
(как в корзине: сериализатор валидирует, вьюха оркеструет). Вывод — заказ и его позиции
из снимка (живой каталог не трогаем). Плюс сериализаторы превью оформления (суммы + опции
доставки) — для типизированной схемы Swagger.
"""

from rest_framework import serializers

from apps.core.models import DeliveryMethod
from apps.users.serializers import normalize_phone

from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    """Позиция заказа из снимка: название, форма продажи, замороженная цена, сумма строки."""

    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product_name",
            "variant_label",
            "unit_price",
            "quantity",
            "subtotal",
        )


class OrderSerializer(serializers.ModelSerializer):
    """Полное представление заказа для покупателя и владельца (всё из снимка заказа)."""

    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    payment_status_display = serializers.CharField(
        source="get_payment_status_display", read_only=True
    )
    delivery_method_display = serializers.CharField(
        source="get_delivery_method_display", read_only=True
    )

    class Meta:
        model = Order
        fields = (
            "number",
            "access_token",
            "customer_name",
            "customer_phone",
            "email",
            "delivery_method",
            "delivery_method_display",
            "delivery_address",
            "wanted_time",
            "comment",
            "goods_total",
            "delivery_cost",
            "total",
            "status",
            "status_display",
            "payment_status",
            "payment_status_display",
            "created_at",
            "items",
        )


class OrderCreateSerializer(serializers.Serializer):
    """Вход при оформлении: данные покупателя + способ доставки.

    Только валидация (корзина, заморозка цен и суммы — во вьюхе). Имя и телефон обязательны;
    телефон нормализуется к каноническому +7XXXXXXXXXX. Адрес обязателен лишь при доставке.
    """

    customer_name = serializers.CharField(max_length=255)
    customer_phone = serializers.CharField(max_length=32)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    delivery_method = serializers.ChoiceField(choices=DeliveryMethod.choices)
    delivery_address = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    wanted_time = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    comment = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_customer_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Укажите имя.")
        return value

    def validate_customer_phone(self, value):
        # Переиспользуем нормализацию из регистрации: принимаем 8…/7…/+7… и приводим к +7XXXXXXXXXX.
        return normalize_phone(value)

    def validate(self, attrs):
        # Адрес обязателен только при доставке по Иглино. При самовывозе адрес не нужен —
        # на всякий случай обнуляем, чтобы в заказ не попал случайный текст.
        if attrs["delivery_method"] == DeliveryMethod.LOCAL:
            if not (attrs.get("delivery_address") or "").strip():
                raise serializers.ValidationError(
                    {"delivery_address": "При доставке укажите адрес."}
                )
        else:
            attrs["delivery_address"] = ""
        return attrs


# --- Превью оформления (п.5): суммы + опции доставки по текущей корзине ---


class DeliveryOptionSerializer(serializers.Serializer):
    """Одна опция доставки с посчитанной для текущей корзины ценой."""

    method = serializers.ChoiceField(choices=DeliveryMethod.choices)
    label = serializers.CharField()
    cost = serializers.DecimalField(max_digits=12, decimal_places=2)
    is_free = serializers.BooleanField()


class CheckoutPreviewSerializer(serializers.Serializer):
    """Сводка для экрана оформления: сумма товаров, порог и подсказка про бесплатную доставку."""

    goods_total = serializers.DecimalField(max_digits=12, decimal_places=2)
    free_delivery_threshold = serializers.DecimalField(max_digits=10, decimal_places=2)
    amount_until_free_delivery = serializers.DecimalField(
        max_digits=10, decimal_places=2
    )
    delivery_options = DeliveryOptionSerializer(many=True)
