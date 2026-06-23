"""Модели заказа GardenGram.

Order — «шапка» заказа (кто, куда, почём итого, статусы), OrderItem — позиции (что куплено
и по какой ЗАМОРОЖЕННОЙ цене). Ключевая идея — снимок: заказ это исторический документ,
поэтому всё важное копируется в него ЗНАЧЕНИЯМИ, а не держится живыми ссылками на каталог
и профиль (в отличие от корзины, где всё живое). См. _scratch/PLAN_ORDER.md.

Замораживаем:
- цены и описания позиций → в OrderItem (unit_price, product_name, variant_label);
- данные покупателя (имя/телефон/адрес) → в Order (профиль потом может измениться);
- стоимость доставки и итоги → в Order (тарифы магазина потом могут измениться).
"""

import secrets
import uuid
from datetime import date

from django.conf import settings
from django.db import models

from apps.core.models import DeliveryMethod
from apps.users.models import phone_validator

# Алфавит для случайного хвоста номера: без похожих символов (0/O, 1/I/L) — чтобы номер
# было легко продиктовать по телефону и не перепутать.
NUMBER_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def generate_order_number():
    """Читаемый номер заказа: GG-ГГММДД-XXXX (дата оформления + 4 случайных символа).

    Не голый автоинкремент: не выдаёт число заказов и не перебирается «соседний +1»,
    но человекочитаем и содержит дату. Уникальность гарантирует БД (unique=True) плюс
    повтор генерации при крайне редком совпадении (см. Order.save).
    """
    today = date.today().strftime("%y%m%d")
    tail = "".join(secrets.choice(NUMBER_ALPHABET) for _ in range(4))
    return f"GG-{today}-{tail}"


class Order(models.Model):
    """Заказ: снимок покупки на момент оформления + статусы для обработки владельцем."""

    class Status(models.TextChoices):
        NEW = "NEW", "Новый"
        ASSEMBLED = "ASSEMBLED", "Собран"
        ISSUED = "ISSUED", "Выдан"
        CANCELLED = "CANCELLED", "Отменён"

    class PaymentStatus(models.TextChoices):
        UNPAID = "UNPAID", "Не оплачен"
        PAID = "PAID", "Оплачен"

    # Удобный алиас, чтобы способы доставки были доступны как Order.Delivery.PICKUP/LOCAL.
    # Сами choices определены в apps.core (рядом с расчётом стоимости доставки).
    Delivery = DeliveryMethod

    # --- Идентификаторы (два разных назначения, см. план п.1.4) ---
    number = models.CharField(
        "Номер заказа",
        max_length=20,
        unique=True,
        editable=False,
        help_text="Читаемый номер для покупателя и владельца (GG-ГГММДД-XXXX).",
    )
    access_token = models.UUIDField(
        "Токен доступа",
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text="Секретный ключ: по нему гость открывает свой заказ без аккаунта.",
    )
    # SET_NULL: заказ — исторический документ, должен пережить удаление аккаунта.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name="Пользователь",
    )

    # --- Снимок покупателя (копируем при оформлении; изменения профиля не влияют) ---
    customer_name = models.CharField("Имя покупателя", max_length=255)
    customer_phone = models.CharField(
        "Телефон", max_length=12, validators=[phone_validator]
    )
    email = models.EmailField("Email", blank=True)

    # --- Доставка ---
    delivery_method = models.CharField(
        "Способ доставки",
        max_length=10,
        choices=DeliveryMethod.choices,
        default=DeliveryMethod.PICKUP,
    )
    delivery_address = models.TextField(
        "Адрес доставки",
        blank=True,
        help_text="Обязателен при доставке; при самовывозе пусто.",
    )
    wanted_time = models.CharField(
        "Желаемое время приезда",
        max_length=255,
        blank=True,
        help_text="Свободный текст, например «после 18:00 в будни».",
    )
    comment = models.TextField("Комментарий покупателя", blank=True)

    # --- Замороженные суммы (считаются один раз при создании, потом не пересчитываются) ---
    goods_total = models.DecimalField(
        "Сумма товаров, ₽", max_digits=12, decimal_places=2
    )
    delivery_cost = models.DecimalField(
        "Стоимость доставки, ₽", max_digits=12, decimal_places=2
    )
    total = models.DecimalField("Итого, ₽", max_digits=12, decimal_places=2)

    # --- Статусы (переключаются в админке владельцем) ---
    status = models.CharField(
        "Статус заказа",
        max_length=12,
        choices=Status.choices,
        default=Status.NEW,
    )
    payment_status = models.CharField(
        "Статус оплаты",
        max_length=8,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
        help_text="Задел под будущую оплату. Пока переключается вручную.",
    )

    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-created_at"]  # новые сверху — владельцу видно свежие

    def __str__(self):
        return f"Заказ {self.number}"

    def save(self, *args, **kwargs):
        # Генерируем читаемый номер при первом сохранении. Совпадение (тот же день + тот же
        # случайный хвост) крайне маловероятно (≈31^4 вариантов в день), но на всякий случай
        # пробуем несколько раз; финальную уникальность всё равно держит unique=True в БД.
        if not self.number:
            for _ in range(10):
                candidate = generate_order_number()
                if not Order.objects.filter(number=candidate).exists():
                    self.number = candidate
                    break
            else:
                raise RuntimeError("Не удалось сгенерировать уникальный номер заказа.")
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """Позиция заказа: снимок купленного варианта с ЗАМОРОЖЕННОЙ ценой.

    Цена и описания скопированы на момент заказа — живой каталог потом не влияет. Ссылка на
    вариант мягкая (SET_NULL): даже если вариант уберут из каталога, позиция в заказе читается
    полностью по своему текстовому снимку.
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Заказ",
    )
    # SET_NULL: удаление варианта из каталога не должно стирать историческую позицию заказа.
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
        verbose_name="Вариант товара",
    )

    # --- Снимок на момент заказа (источник правды, даже если каталог изменится) ---
    product_name = models.CharField("Название товара", max_length=255)
    variant_label = models.CharField("Форма продажи", max_length=255)
    unit_price = models.DecimalField(
        "Цена за шт., ₽",
        max_digits=10,
        decimal_places=2,
        help_text="Замороженная цена варианта на момент оформления заказа.",
    )
    quantity = models.PositiveIntegerField("Количество")

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"
        ordering = ["id"]

    def __str__(self):
        return f"{self.quantity} × {self.product_name} ({self.variant_label})"

    @property
    def subtotal(self):
        """Сумма по строке: замороженная цена × количество (оба множителя зафиксированы)."""
        return self.unit_price * self.quantity
