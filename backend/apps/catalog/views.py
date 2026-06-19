"""Вьюхи каталога (только чтение). См. _scratch/PLAN_API.md, п.2–5."""

from django.db.models import Exists, Min, OuterRef, Prefetch, Subquery
from mptt.templatetags.mptt_tags import cache_tree_children
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Category, Product, ProductVariant
from .serializers import (
    CategoryTreeSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
)


class CatalogPagination(PageNumberPagination):
    """Пагинация только для списка товаров. По 20 на страницу (?page=2)."""

    page_size = 20


class ProductViewSet(ReadOnlyModelViewSet):
    """Только чтение: список товаров и карточка одного товара.

    ReadOnlyModelViewSet даёт ровно list + retrieve (без записи).
    Витрина публичная (AllowAny). Только опубликованные товары.
    """

    permission_classes = [AllowAny]
    pagination_class = CatalogPagination
    filter_backends = [SearchFilter]
    search_fields = ["name_ru", "name_lat", "cultivar"]
    # Подсказка роутеру/спектакуляру; реальный набор строит get_queryset().
    queryset = Product.objects.all()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProductDetailSerializer
        return ProductListSerializer

    def get_queryset(self):
        # Только опубликованные. Категория сразу подтянута (select_related).
        qs = Product.objects.filter(is_published=True).select_related("category")

        # price_from / is_available — коррелированными подзапросами по активным
        # вариантам: без JOIN-размножения строк и без N+1 (один SQL на список).
        active_variants = ProductVariant.objects.filter(
            product=OuterRef("pk"), is_active=True
        )
        price_subquery = (
            active_variants.values("product").annotate(m=Min("price")).values("m")[:1]
        )
        in_stock = active_variants.filter(
            availability_status=ProductVariant.Availability.IN_STOCK
        )
        qs = qs.annotate(
            price_from=Subquery(price_subquery),
            is_available=Exists(in_stock),
        )

        # Фильтр по категории — ВКЛЮЧАЯ подкатегории (mptt get_descendants).
        category_id = self.request.query_params.get("category")
        if category_id:
            try:
                category = Category.objects.get(pk=category_id)
            except (Category.DoesNotExist, ValueError):
                return qs.none()
            branch = category.get_descendants(include_self=True)
            qs = qs.filter(category__in=branch)

        # Префетч под действие: для карточки — фото + ТОЛЬКО активные варианты;
        # для списка — только фото (первое идёт в thumbnail).
        if self.action == "retrieve":
            qs = qs.prefetch_related(
                "images",
                Prefetch(
                    "variants",
                    queryset=ProductVariant.objects.filter(is_active=True),
                ),
            )
        else:
            qs = qs.prefetch_related("images")
        return qs


class CategoryTreeView(ListAPIView):
    """Дерево категорий целиком (только активные узлы), без пагинации.

    cache_tree_children() вытягивает дерево ОДНИМ запросом и собирает вложенность
    в памяти; рекурсивный сериализатор затем читает детей из кэша (нет N+1).
    """

    permission_classes = [AllowAny]
    serializer_class = CategoryTreeSerializer
    pagination_class = None  # дерево должно прийти целиком
    queryset = Category.objects.filter(is_active=True)

    def list(self, request, *args, **kwargs):
        roots = cache_tree_children(self.get_queryset())
        serializer = self.get_serializer(roots, many=True)
        return Response(serializer.data)
