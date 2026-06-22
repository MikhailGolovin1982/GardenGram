"""Модели корзины GardenGram.

Корзина — контейнер (Cart), внутри — строки (CartItem). Единица строки — конкретный
ВАРИАНТ товара (ProductVariant), а не товар целиком: цена и наличие живут на варианте.

Ключевые решения (см. _scratch/PLAN_CART.md):
- Корзина гостя опознаётся анонимным токеном (UUID), который клиент шлёт в заголовке
  X-Cart-Token; корзина пользователя привязана к аккаунту. Одна корзина на субъекта.
- Цену и доступность в строке НЕ храним — считаем живыми из варианта при каждом показе.
- Недоступный (скрытый/«нет в наличии») вариант ОСТАЁТСЯ в корзине, но помечается и в
  сумму не входит.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction


class CartManager(models.Manager):
    """Резолв «текущей корзины» по запросу и слияние гостевой корзины в аккаунт."""

    def resolve(self, request, create=False):
        """Найти корзину для запроса (или создать, если create=True).

        Залогиненный пользователь → корзина по аккаунту.
        Гость → корзина по токену из заголовка X-Cart-Token (только гостевые корзины).

        create=False (для чтения) → вернуть существующую корзину или None, НЕ засоряя БД
        пустыми корзинами (важно против ботов). create=True (для добавления) → гарантированно
        вернуть корзину, при необходимости создав новую (гостю — с новым токеном).
        """
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            if create:
                cart, _ = self.get_or_create(user=user)
                return cart
            return self.filter(user=user).first()

        # Гость: ищем строго гостевую корзину (user пуст) по токену.
        token = request.headers.get("X-Cart-Token")
        if token:
            try:
                cart = self.filter(token=token, user__isnull=True).first()
            except (ValueError, ValidationError):
                cart = None  # битый токен в заголовке — считаем, что корзины нет
            if cart is not None:
                return cart

        if create:
            return self.create()  # токен сгенерируется автоматически (default)
        return None

    @transaction.atomic
    def merge_guest_into_user(self, guest_cart, user):
        """Слить гостевую корзину в корзину пользователя. Без потерь и без дублей.

        Если у пользователя ещё НЕТ корзины — просто «усыновляем» гостевую (дёшево,
        без копирования строк). Иначе переносим строки: совпавший вариант → суммируем
        количества, новый → создаём строку. В конце гостевую корзину удаляем.

        Всё в одной транзакции (@transaction.atomic) — слияние «всё или ничего».
        """
        user_cart = self.filter(user=user).first()

        if user_cart is None:
            guest_cart.user = user
            guest_cart.save(update_fields=["user", "updated_at"])
            return guest_cart

        if user_cart.pk == guest_cart.pk:
            return user_cart  # нечего сливать (та же корзина)

        for g_item in guest_cart.items.select_related("variant"):
            u_item, created = user_cart.items.get_or_create(
                variant=g_item.variant,
                defaults={"quantity": g_item.quantity},
            )
            if not created:
                u_item.quantity += g_item.quantity  # совпал вариант → СУММИРУЕМ
                u_item.save(update_fields=["quantity", "updated_at"])

        guest_cart.delete()  # CASCADE удалит и строки гостевой корзины
        return user_cart


class Cart(models.Model):
    """Корзина: одна на пользователя ИЛИ одна на гостя (по токену).

    «Одна корзина на субъекта» обеспечивается на уровне БД: уникальный user (OneToOne)
    для пользователя и уникальный token для гостя.
    """

    # OneToOne: один пользователь = одна корзина. null=True — у гостевой корзины владельца
    # нет; в Postgres несколько строк с user=NULL разрешено (NULL'ы считаются различными),
    # поэтому гостевые корзины друг другу не мешают.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cart",
        verbose_name="Пользователь",
    )
    # Анонимный идентификатор гостя. Клиент хранит его и шлёт в заголовке X-Cart-Token.
    # Есть у всех корзин (в т.ч. пользовательских — там просто не используется); для гостя
    # это ключ доступа, поэтому при резолве по токену берём только корзины без пользователя.
    token = models.UUIDField(
        "Токен гостя",
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлена", auto_now=True)

    objects = CartManager()

    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Корзины"

    def __str__(self):
        who = self.user if self.user_id else f"гость {self.token}"
        return f"Корзина ({who})"

    # --- Живые расчёты. Опираются на self.items.all() — во вьюхе строки префетчатся
    #     вместе с variant/product, чтобы расчёт шёл в памяти без N+1. ---

    @property
    def active_items(self):
        """Строки, доступные к оформлению (вариант не скрыт и в наличии)."""
        return [item for item in self.items.all() if item.is_available_now]

    @property
    def total(self):
        """Сумма по ДОСТУПНЫМ строкам (цена × количество). Недоступные не считаем."""
        return sum((item.subtotal for item in self.active_items), start=0)

    @property
    def count(self):
        """Суммарное количество штук во всех строках корзины (для бейджа «в корзине N»)."""
        return sum(item.quantity for item in self.items.all())

    @property
    def has_unavailable_items(self):
        """Есть ли в корзине помеченные недоступными строки (подсказка фронту)."""
        return any(not item.is_available_now for item in self.items.all())


class CartItem(models.Model):
    """Строка корзины: конкретный вариант товара + количество.

    Цену и наличие тут не храним — берём из варианта на момент показа (живая цена).
    """

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Корзина",
    )
    # CASCADE: при жёстком удалении варианта строка исчезает. В норме владелец не удаляет
    # вариант, а прячет (is_active=False) или ставит «нет в наличии» — такой вариант
    # остаётся в корзине с пометкой (см. is_available_now).
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name="Вариант товара",
    )
    quantity = models.PositiveIntegerField("Количество", default=1)
    added_at = models.DateTimeField("Добавлена", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлена", auto_now=True)

    class Meta:
        verbose_name = "Строка корзины"
        verbose_name_plural = "Строки корзины"
        ordering = ["added_at", "id"]
        constraints = [
            # Один вариант = одна строка в корзине. Повторное добавление увеличивает
            # количество существующей строки, а не плодит дубли.
            models.UniqueConstraint(
                fields=["cart", "variant"], name="unique_variant_per_cart"
            )
        ]

    def __str__(self):
        return f"{self.quantity} × {self.variant} в {self.cart}"

    @property
    def is_available_now(self):
        """Доступна ли строка к оформлению сейчас: вариант не скрыт И в наличии."""
        return self.variant.is_active and self.variant.is_available

    @property
    def subtotal(self):
        """Сумма по строке: живая цена варианта × количество."""
        return self.variant.price * self.quantity
