import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useCart } from '../context/CartContext'
import { formatPrice } from '../utils/format'
import CartItemRow from '../components/cart/CartItemRow'

// Страница корзины (Шаг 4). Сама ничего не считает — показывает то, что вернул
// бэкенд (сумма total, счётчик, доступность). Checkout — Шаг 5, здесь только ссылка.
function CartPage() {
  const { cart, loading, error, mutating, refresh, clear } = useCart()

  // При заходе на страницу один раз тянем свежее состояние (вдруг наличие изменилось
  // в админке). Дёшево: ответ — полный cart. Бейдж в шапке гидрируется отдельно на старте.
  useEffect(() => {
    refresh().catch(() => { /* ошибку покажем через error из контекста */ })
  }, [refresh])

  // 1. Первичная гидрация ещё идёт.
  if (loading) {
    return <section><h1>Корзина</h1><p>Загрузка корзины…</p></section>
  }

  // 2. Ошибка загрузки (тот же приём, что на Шагах 2–3).
  if (error) {
    return (
      <section>
        <h1>Корзина</h1>
        <p className="catalog-error">Не удалось загрузить корзину. Обнови страницу.</p>
      </section>
    )
  }

  // 3. Пусто.
  if (!cart || cart.items.length === 0) {
    return (
      <section>
        <h1>Корзина</h1>
        <p>Корзина пуста.</p>
        <p><Link to="/catalog">← В каталог</Link></p>
      </section>
    )
  }

  // 4. Есть позиции. Оформление недоступно, если нет ни одной доступной (total == 0).
  const hasPayable = Number(cart.total) > 0

  return (
    <section>
      <h1>Корзина</h1>

      <ul className="cart-list">
        {cart.items.map((item) => <CartItemRow key={item.id} item={item} />)}
      </ul>

      <div className="cart-summary">
        <p className="cart-total">
          Товары: <strong>{formatPrice(cart.total)}</strong>
        </p>
        <p className="cart-delivery-note">Доставка рассчитывается при оформлении.</p>
        {cart.has_unavailable_items && (
          <p className="cart-unavailable-note">
            Некоторые позиции сейчас недоступны и не входят в сумму.
          </p>
        )}
      </div>

      <div className="cart-actions">
        <button
          type="button"
          className="cart-clear"
          onClick={() => { if (window.confirm('Очистить корзину?')) clear() }}
          disabled={mutating}
        >Очистить корзину</button>

        {/* Заглушка Шага 5: если оплачивать нечего — ведём ссылку как неактивную. */}
        {hasPayable
          ? <Link to="/checkout" className="cart-checkout">Оформить заказ</Link>
          : <span className="cart-checkout cart-checkout-disabled">Оформить заказ</span>}
      </div>
    </section>
  )
}

export default CartPage
