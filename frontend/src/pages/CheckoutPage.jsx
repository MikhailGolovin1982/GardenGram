import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useCart } from '../context/CartContext'
import { useApi } from '../hooks/useApi'
import { getCheckoutPreview, createOrder } from '../api/orders'
import { formatPrice } from '../utils/format'

// Оформление заказа (Шаг 5). Форма покупателя + выбор доставки + итог.
// Сайт ничего не считает сам: суммы и цены доставки берём из /orders/preview/
// (грузим один раз — обе опции в ответе, переключение доставки нового запроса не
// требует). Замороженный итог придёт из ответа POST — он источник правды на /order.
function CheckoutPage() {
  const navigate = useNavigate()
  const { cart, loading: cartLoading, refresh: cartRefresh } = useCart()

  // Превью грузим ОДИН раз (обе опции доставки уже внутри). deps=[] — не перезапрашиваем.
  const { data: preview, loading: previewLoading, error: previewError } = useApi(
    getCheckoutPreview,
    [],
  )

  // Локальное состояние формы. Дефолт доставки — самовывоз (PICKUP): он бесплатный
  // и не требует адреса, безопасное начальное состояние.
  const [customerName, setCustomerName] = useState('')
  const [customerPhone, setCustomerPhone] = useState('')
  const [email, setEmail] = useState('')
  const [deliveryMethod, setDeliveryMethod] = useState('PICKUP')
  const [deliveryAddress, setDeliveryAddress] = useState('')
  const [wantedTime, setWantedTime] = useState('')
  const [comment, setComment] = useState('')

  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('') // общая ошибка (detail/сеть)
  const [fieldErrors, setFieldErrors] = useState({}) // ошибки полей от бэкенда

  // 1. Загрузка: ждём и гидрацию корзины, и превью.
  if (cartLoading || previewLoading) {
    return <section><h1>Оформление заказа</h1><p>Загрузка…</p></section>
  }

  // 2. Guard «нечего оформлять»: пустая корзина или нет доступных позиций (total==0).
  //    Форму не рисуем — бэкенд всё равно вернёт 400. Зеркалит логику CartPage.
  const nothingToOrder = !cart || cart.items.length === 0 || Number(cart.total) === 0
  if (nothingToOrder) {
    return (
      <section>
        <h1>Оформление заказа</h1>
        <p>Корзина пуста — оформлять нечего.</p>
        <p><Link to="/catalog">← В каталог</Link></p>
      </section>
    )
  }

  // 3. Ошибка превью (суммы/доставку взять неоткуда).
  if (previewError || !preview) {
    return (
      <section>
        <h1>Оформление заказа</h1>
        <p className="catalog-error">Не удалось загрузить оформление. Обнови страницу.</p>
        <p><Link to="/cart">← В корзину</Link></p>
      </section>
    )
  }

  // 4. Норма. Выбранная опция доставки — из уже загруженного превью (без нового запроса).
  const selectedOption = preview.delivery_options.find((o) => o.method === deliveryMethod)
  const deliveryCost = selectedOption ? Number(selectedOption.cost) : 0
  // Итого = сумма товаров + стоимость выбранной доставки. Оба числа посчитал бэкенд;
  // здесь только складываем для показа (замороженный total придёт из ответа POST).
  const displayTotal = Number(preview.goods_total) + deliveryCost
  const isLocal = deliveryMethod === 'LOCAL'
  const untilFree = Number(preview.amount_until_free_delivery)

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmitError('')
    setFieldErrors({})

    // Лёгкая клиентская проверка — только чтобы не гонять заведомо пустой запрос.
    // Формат телефона и всё остальное — источник правды бэкенд (покажем его ошибки полей).
    const localErrors = {}
    if (!customerName.trim()) localErrors.customer_name = 'Укажите имя.'
    if (!customerPhone.trim()) localErrors.customer_phone = 'Укажите телефон.'
    if (isLocal && !deliveryAddress.trim()) localErrors.delivery_address = 'Укажите адрес доставки.'
    if (Object.keys(localErrors).length > 0) {
      setFieldErrors(localErrors)
      return
    }

    setSubmitting(true)
    try {
      // Адрес при PICKUP бэкенд обнулит сам — можно слать как есть.
      const order = await createOrder({
        customer_name: customerName,
        customer_phone: customerPhone,
        email,
        delivery_method: deliveryMethod,
        delivery_address: deliveryAddress,
        wanted_time: wantedTime,
        comment,
      })
      // Бэкенд очистил строки корзины → обновляем контекст, чтобы бейдж стал 0.
      await cartRefresh().catch(() => { /* некритично: заказ уже создан */ })
      navigate(`/order/${order.access_token}`)
    } catch (err) {
      // 400 с телом: {"поле": ["..."]} → ошибки полей; {"detail": "..."} → общая
      // ошибка (корзина опустела в гонке / нет доступных позиций).
      if (err.status === 400 && err.data && typeof err.data === 'object') {
        if (typeof err.data.detail === 'string') {
          setSubmitError(err.data.detail)
        } else {
          setFieldErrors(err.data)
        }
      } else {
        setSubmitError('Не удалось оформить заказ. Попробуйте ещё раз.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section>
      <h1>Оформление заказа</h1>

      <form className="checkout-form" onSubmit={handleSubmit} noValidate>
        {/* Имя */}
        <label className="form-field">
          <span className="form-label">Имя*</span>
          <input
            type="text"
            value={customerName}
            onChange={(e) => setCustomerName(e.target.value)}
            autoComplete="name"
          />
          {fieldErrors.customer_name && (
            <span className="field-error">{fieldErrors.customer_name}</span>
          )}
        </label>

        {/* Телефон */}
        <label className="form-field">
          <span className="form-label">Телефон*</span>
          <input
            type="tel"
            value={customerPhone}
            onChange={(e) => setCustomerPhone(e.target.value)}
            placeholder="+7 900 000-00-00"
            autoComplete="tel"
          />
          {fieldErrors.customer_phone && (
            <span className="field-error">{fieldErrors.customer_phone}</span>
          )}
        </label>

        {/* Email — по желанию */}
        <label className="form-field">
          <span className="form-label">Email (по желанию)</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
          {fieldErrors.email && (
            <span className="field-error">{fieldErrors.email}</span>
          )}
        </label>

        {/* Способ доставки — radio из опций превью */}
        <fieldset className="form-field delivery-choice">
          <legend className="form-label">Способ получения</legend>
          {preview.delivery_options.map((opt) => (
            <label key={opt.method} className="delivery-option">
              <input
                type="radio"
                name="delivery_method"
                value={opt.method}
                checked={deliveryMethod === opt.method}
                onChange={() => setDeliveryMethod(opt.method)}
              />
              <span>
                {opt.label} — {opt.is_free ? 'Бесплатно' : formatPrice(opt.cost)}
              </span>
            </label>
          ))}
        </fieldset>

        {/* Адрес — только при доставке по Иглино, тогда обязателен */}
        {isLocal && (
          <label className="form-field">
            <span className="form-label">Адрес доставки*</span>
            <textarea
              rows={2}
              value={deliveryAddress}
              onChange={(e) => setDeliveryAddress(e.target.value)}
            />
            {fieldErrors.delivery_address && (
              <span className="field-error">{fieldErrors.delivery_address}</span>
            )}
          </label>
        )}

        {/* Желаемое время приезда — по желанию */}
        <label className="form-field">
          <span className="form-label">Желаемое время (по желанию)</span>
          <input
            type="text"
            value={wantedTime}
            onChange={(e) => setWantedTime(e.target.value)}
            placeholder="Например: суббота после обеда"
          />
        </label>

        {/* Комментарий — по желанию */}
        <label className="form-field">
          <span className="form-label">Комментарий к заказу (по желанию)</span>
          <textarea
            rows={2}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
        </label>

        {/* Сводка итога: два готовых числа бэкенда, сложенные для показа. */}
        <div className="checkout-summary">
          <p>Товары: <strong>{formatPrice(preview.goods_total)}</strong></p>
          <p>Доставка: <strong>{selectedOption?.is_free ? 'Бесплатно' : formatPrice(deliveryCost)}</strong></p>
          <p className="checkout-total">Итого: <strong>{formatPrice(displayTotal)}</strong></p>

          {/* Подсказка про порог — только при доставке (самовывоз и так бесплатен). */}
          {isLocal && (
            untilFree > 0
              ? <p className="checkout-hint">До бесплатной доставки осталось {formatPrice(untilFree)}.</p>
              : <p className="checkout-hint">Доставка бесплатна (сумма заказа достигла порога).</p>
          )}
        </div>

        {submitError && <p className="catalog-error">{submitError}</p>}

        <button type="submit" className="checkout-submit" disabled={submitting}>
          {submitting ? 'Оформляем…' : 'Оформить заказ'}
        </button>
      </form>

      <p className="checkout-back"><Link to="/cart">← Вернуться в корзину</Link></p>
    </section>
  )
}

export default CheckoutPage
