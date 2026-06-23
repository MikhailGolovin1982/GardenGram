"""Общие настройки магазина GardenGram.

Здесь живёт ShopSettings — единственная запись с настройками, которые владелец правит
в админке (принцип CLAUDE.md «настройки — в админке, не в коде»). Сейчас это параметры
доставки (порог бесплатной + стоимость платной); сюда же лягут будущие общие настройки.

DeliveryMethod вынесен сюда (а не в apps.orders), чтобы расчёт стоимости доставки жил
рядом с настройками, а зависимость шла в одну сторону: orders → core (core ни на кого
из наших приложений не ссылается).
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class DeliveryMethod(models.TextChoices):
    """Способы доставки. По России (Почта/СДЭК) пока не делаем (см. CLAUDE.md)."""

    PICKUP = "PICKUP", "Самовывоз"
    LOCAL = "LOCAL", "Доставка по Иглино"


class ShopSettings(models.Model):
    """Глобальные настройки магазина — ОДНА запись (синглтон), правится в админке.

    «Ровно одна запись» обеспечивается жёстко: save() всегда ставит pk=1, поэтому вторую
    строку завести нельзя. В коде настройки берём через ShopSettings.load() — он гарантированно
    вернёт запись (создав с дефолтами, если её ещё нет), чтобы логика заказа не проверяла
    «а вдруг настроек нет».
    """

    free_delivery_threshold = models.DecimalField(
        "Порог бесплатной доставки, ₽",
        max_digits=10,
        decimal_places=2,
        default=Decimal("3000"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="От этой суммы товаров доставка по Иглино бесплатна.",
    )
    local_delivery_price = models.DecimalField(
        "Стоимость доставки по Иглино, ₽",
        max_digits=10,
        decimal_places=2,
        default=Decimal("300"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Берётся, если сумма товаров меньше порога бесплатной доставки.",
    )

    class Meta:
        verbose_name = "Настройки магазина"
        verbose_name_plural = "Настройки магазина"

    def __str__(self):
        return "Настройки магазина"

    def save(self, *args, **kwargs):
        # Синглтон: жёстко фиксируем pk=1 — запись всегда одна.
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        """Единая точка получения настроек: вернуть запись (создать с дефолтами при отсутствии)."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def delivery_cost(self, method, goods_total):
        """Стоимость доставки по правилу магазина. Возвращает Decimal.

        Самовывоз — всегда 0. Доставка по Иглино — бесплатна при сумме товаров от порога,
        иначе берётся local_delivery_price. Значения — из этой же записи (не хардкод).
        """
        if method == DeliveryMethod.PICKUP:
            return Decimal("0")
        if goods_total >= self.free_delivery_threshold:
            return Decimal("0")
        return self.local_delivery_price

    def amount_until_free_delivery(self, goods_total):
        """Сколько ещё добрать товаров до бесплатной доставки (0, если порог уже достигнут)."""
        left = self.free_delivery_threshold - goods_total
        return left if left > Decimal("0") else Decimal("0")
