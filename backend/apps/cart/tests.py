"""Тесты корзины: слияние гостевой корзины в аккаунт и расчёт total.

Самая хитрая логика — поэтому покрываем её unit-тестами (см. _scratch/PLAN_CART.md, п.9).
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.catalog.models import Category, Product, ProductVariant

from .models import Cart, CartItem

User = get_user_model()


class CartTestBase(TestCase):
    """Общие данные: категория, товар и удобный конструктор вариантов."""

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="Гортензии")
        cls.product = Product.objects.create(
            category=cls.category,
            name_ru="Гортензия метельчатая",
            description="Тестовый товар",
            is_published=True,
        )

    @classmethod
    def make_variant(cls, price, *, active=True, status=ProductVariant.Availability.IN_STOCK):
        return ProductVariant.objects.create(
            product=cls.product,
            price=Decimal(price),
            is_active=active,
            availability_status=status,
        )


class MergeCartTests(CartTestBase):
    def test_merge_sums_overlap_and_keeps_unique(self):
        """Совпавший вариант → количества суммируются; уникальные переносятся; без дублей."""
        user = User.objects.create_user(phone="+79170000001", email="u@example.com", password="passw0rd123")
        v1 = self.make_variant("100.00")
        v2 = self.make_variant("200.00")
        v3 = self.make_variant("300.00")

        user_cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=user_cart, variant=v1, quantity=3)  # пересечётся
        CartItem.objects.create(cart=user_cart, variant=v3, quantity=1)  # только у юзера

        guest_cart = Cart.objects.create()
        CartItem.objects.create(cart=guest_cart, variant=v1, quantity=2)  # пересечётся
        CartItem.objects.create(cart=guest_cart, variant=v2, quantity=1)  # только у гостя

        result = Cart.objects.merge_guest_into_user(guest_cart, user)

        self.assertEqual(result.pk, user_cart.pk)
        # Без дублей: ровно три строки (v1, v2, v3).
        self.assertEqual(result.items.count(), 3)
        self.assertEqual(result.items.get(variant=v1).quantity, 5)  # 3 + 2 — суммировано
        self.assertEqual(result.items.get(variant=v2).quantity, 1)  # перенесено
        self.assertEqual(result.items.get(variant=v3).quantity, 1)  # сохранено
        # Гостевая корзина удалена вместе со строками.
        self.assertFalse(Cart.objects.filter(pk=guest_cart.pk).exists())

    def test_merge_adopts_guest_cart_when_user_has_none(self):
        """Если у пользователя корзины нет — гостевая «усыновляется» (без копирования строк)."""
        user = User.objects.create_user(phone="+79170000002", email="u2@example.com", password="passw0rd123")
        v1 = self.make_variant("100.00")
        guest_cart = Cart.objects.create()
        CartItem.objects.create(cart=guest_cart, variant=v1, quantity=4)

        result = Cart.objects.merge_guest_into_user(guest_cart, user)

        self.assertEqual(result.pk, guest_cart.pk)  # та же строка корзины
        self.assertEqual(result.user, user)
        self.assertEqual(result.items.get(variant=v1).quantity, 4)
        self.assertEqual(Cart.objects.filter(user=user).count(), 1)


class TotalTests(CartTestBase):
    def test_total_excludes_unavailable_lines(self):
        """В total входят только доступные строки; недоступные остаются и помечаются."""
        v_in = self.make_variant("100.00")  # активен, в наличии
        v_out = self.make_variant("50.00", status=ProductVariant.Availability.OUT_OF_STOCK)
        v_inactive = self.make_variant("70.00", active=False)  # скрыт владельцем

        cart = Cart.objects.create()
        CartItem.objects.create(cart=cart, variant=v_in, quantity=2)  # 200 — в total
        CartItem.objects.create(cart=cart, variant=v_out, quantity=1)  # недоступен
        CartItem.objects.create(cart=cart, variant=v_inactive, quantity=1)  # недоступен

        self.assertEqual(cart.total, Decimal("200.00"))  # только доступная строка
        self.assertEqual(len(cart.active_items), 1)
        self.assertEqual(cart.count, 4)  # суммарно штук по ВСЕМ строкам (2+1+1)
        self.assertTrue(cart.has_unavailable_items)

    def test_item_availability_flag(self):
        v_in = self.make_variant("100.00")
        v_out = self.make_variant("50.00", status=ProductVariant.Availability.OUT_OF_STOCK)
        cart = Cart.objects.create()
        item_in = CartItem.objects.create(cart=cart, variant=v_in, quantity=1)
        item_out = CartItem.objects.create(cart=cart, variant=v_out, quantity=1)

        self.assertTrue(item_in.is_available_now)
        self.assertFalse(item_out.is_available_now)
        self.assertEqual(item_in.subtotal, Decimal("100.00"))
