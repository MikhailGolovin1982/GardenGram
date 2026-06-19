"""Сериализаторы каталога (только чтение).

Список и карточка товара — РАЗНЫЕ сериализаторы:
- список лёгкий (плитка: название, фото-превью, цена «от», наличие);
- карточка подробная (описание, все фото, все активные варианты).
Почему так — см. _scratch/PLAN_API.md, п.1.
"""

from rest_framework import serializers

from .models import Category, Product, ProductImage, ProductVariant


class CategoryTreeSerializer(serializers.ModelSerializer):
    """Узел дерева категорий с рекурсивной вложенностью.

    `children` читаются из кэша, который заранее построила cache_tree_children()
    во вьюхе, поэтому рекурсия НЕ ходит в БД на каждом узле (нет N+1).
    """

    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "children")

    def get_children(self, obj):
        # get_children() у mptt возвращает кэшированных детей (из cache_tree_children),
        # если кэш есть. Контекст пробрасываем дальше — пригодится для request.
        children = obj.get_children()
        return CategoryTreeSerializer(children, many=True, context=self.context).data


class CategoryShortSerializer(serializers.ModelSerializer):
    """Короткая ссылка на категорию — чтобы вложить в товар без всего дерева."""

    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class ProductImageSerializer(serializers.ModelSerializer):
    """Фото товара. `image` отдаётся абсолютным URL (есть request в контексте)."""

    class Meta:
        model = ProductImage
        fields = ("id", "image", "alt", "position")


class ProductVariantSerializer(serializers.ModelSerializer):
    """Вариант товара: цена, наличие, форма продажи.

    Отдаём и готовые подписи (form_label/short_label — это @property модели),
    и «сырые» поля формы продажи (пригодятся фронту для фильтров/отображения).
    """

    is_available = serializers.ReadOnlyField()
    form_label = serializers.ReadOnlyField()
    short_label = serializers.ReadOnlyField()

    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "price",
            "availability_status",
            "is_available",
            "quantity",
            "form_label",
            "short_label",
            # «сырые» поля формы продажи
            "root_system",
            "volume_l",
            "size_label",
            "age_note",
        )


class ProductListSerializer(serializers.ModelSerializer):
    """КРАТКО — строка/плитка списка. Без описания, всех фото и всех вариантов.

    `price_from` и `is_available` приходят аннотацией из queryset вьюхи (один SQL,
    без N+1) — здесь только объявляем их типы для вывода и схемы.
    """

    display_name = serializers.ReadOnlyField()
    category = CategoryShortSerializer(read_only=True)
    thumbnail = serializers.SerializerMethodField()
    price_from = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True, allow_null=True
    )
    is_available = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "display_name",
            "name_ru",
            "name_lat",
            "cultivar",
            "kind",
            "category",
            "thumbnail",
            "price_from",
            "is_available",
        )

    def get_thumbnail(self, obj):
        # obj.images — префетчены и упорядочены по position (Meta модели),
        # поэтому первое фото = главное. Срез [:1] по готовому списку, без доп. запроса.
        images = list(obj.images.all()[:1])
        if not images:
            return None
        url = images[0].image.url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url


class ProductDetailSerializer(serializers.ModelSerializer):
    """ПОДРОБНО — карточка товара: описание, все фото, все активные варианты.

    `images` и `variants` приходят префетченными из вьюхи; варианты уже отфильтрованы
    по is_active=True (фильтр живёт в Prefetch вьюхи, не здесь).
    """

    display_name = serializers.ReadOnlyField()
    category = CategoryShortSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "display_name",
            "name_ru",
            "name_lat",
            "cultivar",
            "kind",
            "category",
            "description",
            "images",
            "variants",
        )
