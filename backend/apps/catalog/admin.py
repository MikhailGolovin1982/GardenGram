"""Админка каталога GardenGram.

Цель — чтобы Людмила (эксперт по растениям) наполняла каталог сама, без программиста:
- дерево категорий с отступами и перетаскиванием (DraggableMPTTAdmin);
- карточка товара с вариантами и фото прямо на одной странице (инлайны);
- выбор категории — выпадающий список с отступами (видно вложенность).
"""

from django.contrib import admin
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from mptt.admin import DraggableMPTTAdmin, TreeRelatedFieldListFilter
from mptt.forms import TreeNodeChoiceField

from .models import Category, Product, ProductImage, ProductVariant


@admin.register(Category)
class CategoryAdmin(DraggableMPTTAdmin):
    """Дерево категорий: отступы по уровням + перетаскивание мышкой."""

    # Колонки списка: индикатор дерева (от DraggableMPTTAdmin) + наши поля.
    list_display = ("tree_actions", "indented_title", "is_active", "slug")
    list_display_links = ("indented_title",)
    list_filter = ("is_active",)
    search_fields = ("name",)
    # Slug заполняется автоматически из названия — Людмиле о нём думать не нужно.
    prepopulated_fields = {"slug": ("name",)}


class ProductImageInline(admin.TabularInline):
    """Фото товара прямо на странице товара, с превью-миниатюрой и порядком."""

    model = ProductImage
    extra = 1
    fields = ("preview", "image", "position", "alt")
    readonly_fields = ("preview",)
    ordering = ("position", "id")

    @admin.display(description="Превью")
    def preview(self, obj):
        if obj.pk and obj.image:
            return format_html(
                '<img src="{}" style="max-height:80px;max-width:120px;'
                'border-radius:4px;" />',
                obj.image.url,
            )
        return "—"


class ProductVariantInline(admin.StackedInline):
    """Варианты товара на странице товара. Stacked — у варианта много необязательных полей."""

    model = ProductVariant
    extra = 1
    # Группируем поля по смыслу: сначала цена/наличие (у всех), затем форма продажи.
    fieldsets = (
        (
            "Цена и наличие",
            {
                "fields": (
                    "variant_label",
                    "price",
                    "availability_status",
                    "quantity",
                    "is_active",
                ),
            },
        ),
        (
            "Форма продажи",
            {
                "fields": ("root_system", "volume_l", "size_label", "age_note"),
                "description": (
                    "Поля «Корневая система» и «Возраст» — только для растений. "
                    "Для сопутствующих товаров (торф, грунт, горшки) их оставляйте пустыми, "
                    "а форму задавайте объёмом или текстовым размером."
                ),
            },
        ),
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Карточка товара: всё для одной позиции на одной странице (варианты + фото инлайнами)."""

    inlines = (ProductVariantInline, ProductImageInline)

    list_display = ("display_name", "cultivar", "category", "kind", "variants_summary", "is_published")
    list_display_links = ("display_name",)
    list_filter = ("kind", ("category", TreeRelatedFieldListFilter), "is_published")
    search_fields = ("name_ru", "name_lat", "cultivar")
    list_select_related = ("category",)

    fieldsets = (
        ("Основное", {"fields": ("name_ru", "description")}),
        (
            "Латынь и сорт",
            {
                "fields": ("name_lat", "cultivar"),
                "description": (
                    "Необязательно. Если задано латинское имя — в каталоге показывается "
                    "как «Русское (Латинское)»."
                ),
            },
        ),
        ("Категория и тип", {"fields": ("category", "kind")}),
        ("Публикация и продавец", {"fields": ("is_published", "seller")}),
    )

    def get_queryset(self, request):
        # Подгружаем варианты одним запросом — иначе сводка делает по запросу на строку.
        return super().get_queryset(request).prefetch_related("variants")

    @admin.display(description="Варианты")
    def variants_summary(self, obj):
        """Сводка по вариантам прямо в списке товаров: число + форма продажи и цена построчно.

        short_label уже даёт «ОКС — 600 ₽» / «ЗКС 5 л — 800 ₽». Данные наши собственные
        (не пользовательский ввод), поэтому format_html_join с <br> здесь безопасен.
        """
        variants = list(obj.variants.all())
        if not variants:
            return "—"
        rows = format_html_join(
            mark_safe("<br>"), "{}", ((v.short_label,) for v in variants)
        )
        return format_html("{}:<br>{}", len(variants), rows)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Категорию выбираем выпадающим списком с отступами (видно вложенность дерева)."""
        if db_field.name == "category":
            return TreeNodeChoiceField(queryset=Category.objects.all(), label="Категория")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description="Название", ordering="name_ru")
    def display_name(self, obj):
        return obj.display_name
