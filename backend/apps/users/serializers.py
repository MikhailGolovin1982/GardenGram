import re

from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


def normalize_phone(value):
    """
    Приводим пользовательский ввод к каноническому виду +7XXXXXXXXXX.
    Принимаем распространённые формы: 8XXXXXXXXXX, 7XXXXXXXXXX, +7XXXXXXXXXX,
    а также номера с пробелами/скобками/дефисами.
    """
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 11 and digits[0] in ("7", "8"):
        digits = digits[1:]
    if len(digits) != 10:
        raise serializers.ValidationError(
            "Телефон должен содержать 10 цифр (например +7 917 123-45-67)."
        )
    return "+7" + digits


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField(required=True)  # обязателен при регистрации
    # Объявляем phone явно как обычный CharField, чтобы НЕ наследовать от модели
    # валидатор формата (^\+7\d{10}$) и max_length. Иначе они срабатывают раньше
    # validate_phone и отбивают «грязный» ввод (8 917…) до нормализации.
    phone = serializers.CharField()

    class Meta:
        model = User
        fields = ("phone", "email", "password", "city", "address")
        extra_kwargs = {
            "city": {"required": False},
            "address": {"required": False},
        }

    def validate_phone(self, value):
        return normalize_phone(value)

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(
            phone=validated_data["phone"],
            email=validated_data["email"],
            password=password,
            city=validated_data.get("city", ""),
            address=validated_data.get("address", ""),
            is_active=True,
        )


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "phone",
            "email",
            "city",
            "address",
            "phone_verified",
            "email_verified",
        )
        read_only_fields = ("phone_verified", "email_verified")
