import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { getOrder } from '../api/orders'
import { formatPrice } from '../utils/format'

// Страница заказа (Шаг 5). Открывается сразу после оформления (редирект) И позже
// гостем по секретной ссылке /order/{access_token} — доступ по самому токену,
// корзина/аккаунт не нужны. Всё показываем из снимка заказа (источник правды —
// ответ бэкенда, а не наши локальные вычисления).
function OrderPage() {
  const { token } = useParams()
  const { data: order, loading, error } = useApi(() => getOrder(token), [token])

  // Состояние кнопки «Скопировать ссылку» — короткое подтверждение «Скопировано».
  const [copied, setCopied] = useState(false)

  if (loading) {
    return <section><h1>Заказ</h1><p>Загрузка заказа…</p></section>
  }

  // 404 — неизвестный или битый (не-UUID) токен: бэкенд отвечает 404 в обоих случаях.
  if (error) {
    const notFound = error.status === 404
    return (
      <section>
        <h1>Заказ</h1>
        <p className="catalog-error">
          {notFound ? 'Заказ не найден. Проверьте ссылку.' : 'Не удалось загрузить заказ. Обнови страницу.'}
        </p>
        <p><Link to="/catalog">← В каталог</Link></p>
      </section>
    )
  }

  if (!order) return null

  const isLocal = order.delivery_method === 'LOCAL'

  function copyLink() {
    const url = window.location.href
    // В Codespaces forwarded-URL — HTTPS (secure context), clipboard доступен.
    // Если API нет — URL и так виден текстом ниже, копирование не критично.
    navigator.clipboard?.writeText(url).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }).catch(() => { /* нет доступа к буферу — пользователь скопирует URL вручную */ })
  }

  return (
    <section className="order-page">
      <h1>Заказ оформлен</h1>
      <p className="order-number">Номер заказа: <strong>{order.number}</strong></p>

      {/* Блок «сохраните ссылку» — единственный путь гостя вернуться к заказу. */}
      <div className="order-save-link">
        <p>Сохраните эту ссылку, чтобы вернуться к заказу:</p>
        {/* URL текстом — можно скопировать вручную на любом устройстве. */}
        <p className="order-url">{window.location.href}</p>
        <button type="button" className="order-copy" onClick={copyLink}>
          {copied ? 'Скопировано!' : 'Скопировать ссылку'}
        </button>
      </div>

      {/* Состав заказа — из снимка (замороженные названия и цены). */}
      <h2 className="order-section-title">Состав заказа</h2>
      <ul className="order-items">
        {order.items.map((item) => (
          <li key={item.id} className="order-item">
            <span className="order-item-name">
              {item.product_name}
              {item.variant_label && <span className="order-item-variant"> — {item.variant_label}</span>}
            </span>
            <span className="order-item-calc">
              {formatPrice(item.unit_price)} × {item.quantity} = <strong>{formatPrice(item.subtotal)}</strong>
            </span>
          </li>
        ))}
      </ul>

      {/* Суммы — из снимка заказа (замороженный итог, источник правды). */}
      <div className="order-totals">
        <p>Товары: <strong>{formatPrice(order.goods_total)}</strong></p>
        <p>
          Доставка ({order.delivery_method_display}):{' '}
          <strong>{Number(order.delivery_cost) === 0 ? 'Бесплатно' : formatPrice(order.delivery_cost)}</strong>
        </p>
        <p className="order-total">Итого: <strong>{formatPrice(order.total)}</strong></p>
      </div>

      {/* Данные покупателя. */}
      <h2 className="order-section-title">Данные покупателя</h2>
      <div className="order-customer">
        <p>Имя: {order.customer_name}</p>
        <p>Телефон: {order.customer_phone}</p>
        {order.email && <p>Email: {order.email}</p>}
        {isLocal && order.delivery_address && <p>Адрес: {order.delivery_address}</p>}
        {order.wanted_time && <p>Желаемое время: {order.wanted_time}</p>}
        {order.comment && <p>Комментарий: {order.comment}</p>}
      </div>

      {/* Статус — справочно (меняется владельцем в админке). */}
      <p className="order-status">
        Статус: {order.status_display}. Оплата: {order.payment_status_display}.
      </p>

      <p className="order-back"><Link to="/catalog">← В каталог</Link></p>
    </section>
  )
}

export default OrderPage
