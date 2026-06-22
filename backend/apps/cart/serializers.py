"""Сериализаторы корзины.

Чтение: корзина → строки → краткое описание варианта (с контекстом товара), плюс
живые суммы и пометки доступности. Запись: добавление варианта и изменение количества
с валидацией (добавлять можно только доступные варианты).
См. _scratch/PLAN_CART.md, п.5.
"""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.catalog.models import ProductVariant

from .models import Cart, CartItem


class CartLineVariantSerializer(serializers.ModelSerializer):
    """Краткое описание варианта для строки корзины: чем он является и почём.

    Цена живая (берётся из варианта). Добавляем контекст товара (имя, превью-фото),
    чтобы фронт показал «что это», не таща карточку целиком.
    """

    # Типизированные read-only поля — чтобы spectacular знал типы в схеме.
    is_available = serializers.BooleanField(read_only=True)
    form_label = serializers.CharField(read_only=True)
    short_label = serializers.CharField(read_only=True)
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    product_name = serializers.CharField(source="product.display_name", read_only=True)
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "product_id",
            "product_name",
            "price",
            "availability_status",
            "is_available",
            "form_label",
            "short_label",
            "thumbnail",
        )

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_thumbnail(self, obj):
        # Первое фото товара = главное (images упорядочены по position в модели).
        # Срез по префетченному списку — без доп. запроса (префетч во вьюхе).
        images = list(obj.product.images.all()[:1])
        if not images:
            return None
        url = images[0].image.url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url


class CartItemSerializer(serializers.ModelSerializer):
    """Строка корзины: вариант, количество, живая сумма и флаг доступности."""

    variant = CartLineVariantSerializer(read_only=True)
    subtotal = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    is_available_now = serializers.BooleanField(read_only=True)

    class Meta:
        model = CartItem
        fields = ("id", "variant", "quantity", "subtotal", "is_available_now")


class CartSerializer(serializers.ModelSerializer):
    """Вся корзина: строки, итог по доступным, счётчик, признак недоступных позиций.

    `token` отдаём, чтобы гость сохранил его и слал в X-Cart-Token. Для пользовательской
    корзины токен не используется (резолв идёт по аккаунту), но возвращать его безопасно:
    доступ по токену даётся только к гостевым корзинам.
    """

    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    count = serializers.IntegerField(read_only=True)
    has_unavailable_items = serializers.BooleanField(read_only=True)

    class Meta:
        model = Cart
        fields = ("token", "items", "total", "count", "has_unavailable_items")


class AddCartItemSerializer(serializers.Serializer):
    """Вход для добавления: какой вариант и сколько. Кладём только доступные варианты."""

    variant = serializers.PrimaryKeyRelatedField(queryset=ProductVariant.objects.all())
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate_variant(self, variant):
        # Требование №4: в корзину можно класть только доступный вариант
        # (не скрытый и в наличии). Уже лежащий и ставший недоступным — отдельная история,
        # он остаётся с пометкой (см. is_available_now), это не про добавление.
        if not variant.is_active or not variant.is_available:
            raise serializers.ValidationError(
                "Этот вариант сейчас недоступен для добавления."
            )
        return variant


class UpdateCartItemSerializer(serializers.Serializer):
    """Вход для изменения количества строки. Наличием количество не ограничиваем."""

    quantity = serializers.IntegerField(min_value=1)
