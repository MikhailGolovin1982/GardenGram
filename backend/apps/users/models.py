from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models


# Валидатор канонического формата телефона: +7 и ровно 10 цифр.
# Уникальность работает посимвольно, поэтому храним номер строго в одном виде.
phone_validator = RegexValidator(
    regex=r"^\+7\d{10}$",
    message="Телефон должен быть в формате +7XXXXXXXXXX (10 цифр после +7).",
)


class UserManager(BaseUserManager):
    """
    Свой менеджер: стандартный завязан на username, которого у нас нет.
    Логин-ключ — phone, поэтому create_user принимает phone вместо username.
    """

    use_in_migrations = True

    def create_user(self, phone, email, password=None, **extra_fields):
        if not phone:
            raise ValueError("Телефон обязателен.")
        if not email:
            raise ValueError("Email обязателен.")
        email = self.normalize_email(email)
        user = self.model(phone=phone, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Суперпользователь должен иметь is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Суперпользователь должен иметь is_superuser=True.")

        return self.create_user(phone, email, password, **extra_fields)


class User(AbstractUser):
    """
    Кастомная модель пользователя GardenGram.
    Вход по телефону; email обязателен, но НЕ уникальный.
    """

    # Убираем username полностью — логинимся по телефону.
    username = None

    phone = models.CharField(
        "Телефон",
        max_length=12,
        unique=True,
        validators=[phone_validator],
    )
    email = models.EmailField(
        "Email",
        blank=False,
    )  # НЕ уникальный — одна семейная почта на несколько аккаунтов.

    city = models.CharField("Город", max_length=100, blank=True)
    address = models.TextField("Адрес доставки", blank=True)

    # Задел под подтверждение контактов. Пока всегда False.
    phone_verified = models.BooleanField("Телефон подтверждён", default=False)
    email_verified = models.BooleanField("Email подтверждён", default=False)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["email"]  # phone и password спрашиваются всегда, их сюда не включают.

    objects = UserManager()

    def __str__(self):
        return self.phone
