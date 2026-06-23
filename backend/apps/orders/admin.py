"""Админка заказов — чтобы Людмила видела новые заказы и собирала их.

Заказ — исторический документ: снимок покупателя, замороженные цены и суммы редактировать
руками нельзя (иначе теряется смысл заморозки), поэтому они read-only. Редактируемы только
статусы заказа и оплаты — их владелец переключает по ходу обработки.
"""

from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    """Позиции заказа прямо в карточке — только просмотр (снимок не правим)."""

    model = OrderItem
    extra = 0
    can_delete = False
    fields = ("product_name", "variant_label", "unit_price", "quantity", "subtotal", "variant")
    readonly_fields = ("product_name", "variant_label", "unit_price", "quantity", "subtotal", "variant")

    @admin.display(description="Сумма строки")
    def subtotal(self, obj):
        return obj.subtotal

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "created_at",
        "customer_name",
        "customer_phone",
        "delivery_method",
        "total",
        "status",
        "payment_status",
    )
    list_filter = ("status", "payment_status", "delivery_method", "created_at")
    search_fields = ("number", "customer_phone", "customer_name")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    # Статусы можно менять прямо из списка — быстрая обработка без захода в карточку.
    list_editable = ("status", "payment_status")
    inlines = [OrderItemInline]

    # Всё, кроме статусов, — read-only (снимок/заморозка/итоги).
    readonly_fields = (
        "number",
        "access_token",
        "user",
        "customer_name",
        "customer_phone",
        "email",
        "delivery_method",
        "delivery_address",
        "wanted_time",
        "comment",
        "goods_total",
        "delivery_cost",
        "total",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        ("Заказ", {"fields": ("number", "access_token", "user", "status", "payment_status")}),
        ("Покупатель", {"fields": ("customer_name", "customer_phone", "email")}),
        (
            "Доставка",
            {"fields": ("delivery_method", "delivery_address", "wanted_time", "comment")},
        ),
        ("Суммы", {"fields": ("goods_total", "delivery_cost", "total")}),
        ("Служебное", {"fields": ("created_at", "updated_at")}),
    )

    def has_add_permission(self, request):
        # Заказы создаются только через оформление (API), не вручную в админке.
        return False
