// Доменный модуль заказов — поверх общего client.js.
// Здесь знание «какие у заказов эндпоинты». Preview и создание заказа резолвят
// корзину тем же гостевым токеном, что и cart.js, — поэтому переиспользуем сам
// ТОКЕН (getCartToken из общего хранилища), а не дублируем логику корзины.

import { apiGet, apiSend } from './client'
import { getCartToken } from './cartToken'

// Заголовок с токеном гостевой корзины, если он есть. Нужен preview и созданию
// заказа — по нему бэкенд находит корзину покупателя (как в cart.js). У гостя без
// корзины токена нет, но до checkout он в корзину уже что-то положил, так что есть.
function tokenHeaders() {
  const token = getCartToken()
  return token ? { 'X-Cart-Token': token } : {}
}

// Превью оформления: суммы товаров, порог бесплатной доставки и обе опции доставки
// с посчитанными ценами. Грузим ОДИН раз — переключение самовывоз/доставка на
// экране не требует нового запроса (обе опции уже в ответе).
export function getCheckoutPreview() {
  return apiGet('orders/preview/', undefined, tokenHeaders())
}

// Оформить заказ из текущей корзины. payload — данные покупателя и способ доставки.
// Успех: 201 с ПОЛНЫМ заказом (включая number и access_token). Бэкенд после этого
// очищает строки корзины (сам токен сохраняет).
export function createOrder(payload) {
  return apiSend('POST', 'orders/', payload, tokenHeaders())
}

// Открыть заказ по секретному access_token (UUID в пути). Корзинный токен НЕ нужен —
// доступ по самому токену заказа. По нему гость возвращается к заказу без аккаунта.
export function getOrder(accessToken) {
  return apiGet(`orders/${accessToken}/`)
}
