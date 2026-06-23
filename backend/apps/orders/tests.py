"""Тесты оформления заказа. См. _scratch/PLAN_ORDER.md, п.14.

Главное, что проверяем (самая хитрая логика):
- ЗАМОРОЗКА цены: после заказа меняем цену варианта — в заказе остаётся прежняя;
- РАСЧЁТ ДОСТАВКИ: самовывоз = 0; доставка ниже порога = 300; от порога = 0.
Плюс важные граничные случаи: адрес обязателен при доставке, недоступные позиции не
попадают в заказ, корзина очищается, цена и описание позиции взяты снимком.

Заказы оформляем как ГОСТЬ через API (корзина по заголовку X-Cart-Token) — это рабочий
сценарий «из браузера», а не вызов внутренних функций.
"""

from decimal import Decimal

from rest_framework.test import APITestCase

from apps.cart.models import Cart, CartItem
from apps.catalog.models import Category, Product, ProductVariant
from apps.orders.models import Order

ORDERS_URL = "/api/v1/orders/"


class OrderCheckoutTests(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Тест")
        self.product = Product.objects.create(
            category=self.category,
            name_ru="Гортензия",
            description="описание",
            is_published=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            price=Decimal("500"),
            availability_status=ProductVariant.Availability.IN_STOCK,
        )
        # Гостевая корзина: 2 шт по 500 = 1000 ₽.
        self.cart = Cart.objects.create()
        CartItem.objects.create(cart=self.cart, variant=self.variant, quantity=2)

    def _post_order(self, **overrides):
        payload = {
            "customer_name": "Иван",
            "customer_phone": "89171234567",
            "delivery_method": "PICKUP",
        }
        payload.update(overrides)
        return self.client.post(
            ORDERS_URL,
            payload,
            format="json",
            HTTP_X_CART_TOKEN=str(self.cart.token),
        )

    # --- Заморозка цены ---

    def test_price_is_frozen_after_catalog_change(self):
        resp = self._post_order()
        self.assertEqual(resp.status_code, 201, resp.data)
        order = Order.objects.get(number=resp.data["number"])
        item = order.items.get()
        self.assertEqual(item.unit_price, Decimal("500.00"))
        self.assertEqual(order.goods_total, Decimal("1000.00"))

        # Меняем цену в каталоге — в уже оформленном заказе цена не должна измениться.
        self.variant.price = Decimal("999")
        self.variant.save(update_fields=["price"])
        item.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(item.unit_price, Decimal("500.00"))
        self.assertEqual(order.goods_total, Decimal("1000.00"))

    def test_item_snapshot_fields_filled(self):
        resp = self._post_order()
        item = Order.objects.get(number=resp.data["number"]).items.get()
        self.assertEqual(item.product_name, "Гортензия")
        self.assertEqual(item.variant_label, self.variant.form_label)
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.subtotal, Decimal("1000.00"))

    # --- Расчёт доставки ---

    def test_pickup_is_free(self):
        resp = self._post_order(delivery_method="PICKUP")
        order = Order.objects.get(number=resp.data["number"])
        self.assertEqual(order.delivery_cost, Decimal("0.00"))
        self.assertEqual(order.total, Decimal("1000.00"))

    def test_local_below_threshold_is_paid(self):
        # 1000 ₽ < порога 3000 ₽ → доставка 300 ₽.
        resp = self._post_order(
            delivery_method="LOCAL", delivery_address="ул. Садовая, 1"
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        order = Order.objects.get(number=resp.data["number"])
        self.assertEqual(order.delivery_cost, Decimal("300.00"))
        self.assertEqual(order.total, Decimal("1300.00"))

    def test_local_at_threshold_is_free(self):
        # Поднимаем количество до 6 шт = 3000 ₽ (= порог) → доставка бесплатна.
        self.cart.items.update(quantity=6)
        resp = self._post_order(
            delivery_method="LOCAL", delivery_address="ул. Садовая, 1"
        )
        order = Order.objects.get(number=resp.data["number"])
        self.assertEqual(order.goods_total, Decimal("3000.00"))
        self.assertEqual(order.delivery_cost, Decimal("0.00"))
        self.assertEqual(order.total, Decimal("3000.00"))

    # --- Граничные случаи ---

    def test_local_requires_address(self):
        resp = self._post_order(delivery_method="LOCAL")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("delivery_address", resp.data)

    def test_empty_cart_rejected(self):
        self.cart.items.all().delete()
        resp = self._post_order()
        self.assertEqual(resp.status_code, 400)

    def test_unavailable_items_excluded(self):
        # Единственный вариант стал «нет в наличии» → активных позиций нет → 400.
        self.variant.availability_status = ProductVariant.Availability.OUT_OF_STOCK
        self.variant.save(update_fields=["availability_status"])
        resp = self._post_order()
        self.assertEqual(resp.status_code, 400)

    def test_cart_cleared_after_order(self):
        self._post_order()
        self.assertEqual(self.cart.items.count(), 0)

    def test_phone_normalized_in_order(self):
        resp = self._post_order(customer_phone="8 (917) 123-45-67")
        order = Order.objects.get(number=resp.data["number"])
        self.assertEqual(order.customer_phone, "+79171234567")

    def test_response_returns_number_and_token(self):
        resp = self._post_order()
        self.assertTrue(resp.data["number"].startswith("GG-"))
        self.assertIn("access_token", resp.data)


class CheckoutPreviewTests(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Тест")
        self.product = Product.objects.create(
            category=self.category, name_ru="Туя", description="x", is_published=True
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            price=Decimal("500"),
            availability_status=ProductVariant.Availability.IN_STOCK,
        )
        self.cart = Cart.objects.create()
        CartItem.objects.create(cart=self.cart, variant=self.variant, quantity=2)  # 1000

    def test_preview_hint_amount_until_free(self):
        resp = self.client.get(
            "/api/v1/orders/preview/", HTTP_X_CART_TOKEN=str(self.cart.token)
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Decimal(resp.data["goods_total"]), Decimal("1000.00"))
        # До порога 3000 не хватает 2000.
        self.assertEqual(
            Decimal(resp.data["amount_until_free_delivery"]), Decimal("2000.00")
        )
        options = {o["method"]: o for o in resp.data["delivery_options"]}
        self.assertEqual(Decimal(options["PICKUP"]["cost"]), Decimal("0.00"))
        self.assertEqual(Decimal(options["LOCAL"]["cost"]), Decimal("300.00"))
        self.assertFalse(options["LOCAL"]["is_free"])
