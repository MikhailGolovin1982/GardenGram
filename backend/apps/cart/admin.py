"""Админка корзины — для просмотра/поддержки и отладки (не для наполнения каталога).

Строки корзины показываем инлайном на странице корзины. Цены/наличие в строках живые,
поэтому суммы выводим как вычисляемые read-only поля.
"""

from django.contrib import admin

from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    raw_id_fields = ("variant",)  # вариантов много — выбор по id, без тяжёлого выпадающего
    fields = ("variant", "quantity", "subtotal", "is_available_now")
    readonly_fields = ("subtotal", "is_available_now")

    @admin.display(description="Сумма строки")
    def subtotal(self, obj):
        return obj.subtotal

    @admin.display(boolean=True, description="Доступна сейчас")
    def is_available_now(self, obj):
        return obj.is_available_now


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "count", "total", "has_unavailable_items", "updated_at")
    readonly_fields = ("token", "created_at", "updated_at")
    search_fields = ("user__phone", "token")
    inlines = [CartItemInline]

    @admin.display(description="Владелец")
    def owner(self, obj):
        return obj.user if obj.user_id else f"гость {obj.token}"

    @admin.display(description="Штук")
    def count(self, obj):
        return obj.count

    @admin.display(description="Итого (доступные)")
    def total(self, obj):
        return obj.total

    @admin.display(boolean=True, description="Есть недоступные")
    def has_unavailable_items(self, obj):
        return obj.has_unavailable_items
