import { Link } from 'react-router-dom'
import { formatPrice } from '../../utils/format'
import { useCart } from '../../context/CartContext'

// Одна строка корзины. Получает item из cart.items; действия и флаг mutating —
// из общего состояния. Сама ничего не считает: цену/подытог/доступность дал бэкенд.
function CartItemRow({ item }) {
  const { updateItem, removeItem, mutating } = useCart()
  const { variant } = item
  const available = item.is_available_now
  const qty = item.quantity

  return (
    <li className={'cart-item' + (available ? '' : ' cart-item-out')}>
      {/* Мини-фото или заглушка «Нет фото» (тот же приём, что в каталоге). */}
      <div className="cart-thumb product-thumb">
        {variant.thumbnail
          ? <img src={variant.thumbnail} alt={variant.product_name} />
          : <span className="product-thumb-empty">Нет фото</span>}
      </div>

      <div className="cart-item-info">
        {/* Название — ссылка на карточку товара (product_id, не вариант). */}
        <Link to={`/product/${variant.product_id}`} className="cart-item-name">
          {variant.product_name}
        </Link>
        <span className="cart-item-form">{variant.form_label}</span>
        <span className="cart-item-unit">{formatPrice(variant.price)} / шт</span>
        {/* Недоступная позиция остаётся в корзине, но не входит в сумму. */}
        {!available && (
          <span className="cart-item-flag">Нет в наличии · не входит в сумму</span>
        )}
      </div>

      <div className="cart-item-controls">
        {/* Степпер только у доступной строки: менять количество недоступного смысла
            нет. «−» отключена при qty===1 (бэкенд не принимает quantity<1 — уменьшать
            до нуля нельзя; удаление — отдельной кнопкой) и во время записи (mutating). */}
        {available && (
          <div className="qty-stepper">
            <button
              type="button"
              onClick={() => updateItem(item.id, qty - 1)}
              disabled={mutating || qty === 1}
              aria-label="Уменьшить количество"
            >−</button>
            <span className="qty-value">{qty}</span>
            <button
              type="button"
              onClick={() => updateItem(item.id, qty + 1)}
              disabled={mutating}
              aria-label="Увеличить количество"
            >+</button>
          </div>
        )}

        {/* Подытог: живая цена × количество (бэкенд считает и для недоступной). */}
        <span className="cart-item-subtotal">{formatPrice(item.subtotal)}</span>

        <button
          type="button"
          className="cart-item-remove"
          onClick={() => removeItem(item.id)}
          disabled={mutating}
        >Удалить</button>
      </div>
    </li>
  )
}

export default CartItemRow
