"""Админка настроек магазина — синглтон: одна запись, без добавления и удаления.

Людмила просто открывает единственную запись «Настройки магазина» и меняет числа.
"""

from django.contrib import admin

from .models import ShopSettings


@admin.register(ShopSettings)
class ShopSettingsAdmin(admin.ModelAdmin):
    list_display = ("__str__", "free_delivery_threshold", "local_delivery_price")

    def has_add_permission(self, request):
        # Нельзя завести вторую запись, если настройки уже существуют.
        return not ShopSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Единственную запись настроек удалять нельзя.
        return False
