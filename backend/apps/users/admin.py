from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Стандартный UserAdmin завязан на username, которого у нас нет.
    Переопределяем fieldsets/list_display под наши поля (логин — phone).
    """

    ordering = ("phone",)
    list_display = ("phone", "email", "city", "is_staff", "is_active")
    list_filter = ("is_staff", "is_superuser", "is_active", "phone_verified", "email_verified")
    search_fields = ("phone", "email", "city")

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        (_("Контакты"), {"fields": ("email", "phone_verified", "email_verified")}),
        (_("Доставка"), {"fields": ("city", "address")}),
        (_("Персональные данные"), {"fields": ("first_name", "last_name")}),
        (
            _("Права доступа"),
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        (_("Важные даты"), {"fields": ("last_login", "date_joined")}),
    )

    # Поля на странице создания пользователя в админке.
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone", "email", "password1", "password2"),
            },
        ),
    )
