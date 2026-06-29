// Доменный модуль корзины — поверх общего client.js.
// Здесь живёт знание «какие у корзины эндпоинты» И вся возня с гостевым токеном:
// подставить X-Cart-Token в запрос, запомнить token из ответа. Остальной код
// (Context, страницы) про токен не знает — просто получает готовый объект Cart.

import { apiGet, apiSend } from './client'
import { getCartToken, setCartToken } from './cartToken'

// Заголовки запроса корзины: токен, если он у нас есть. Нового гостя (токена ещё
// нет) шлём без заголовка — бэкенд при первом POST создаст корзину и вернёт token.
function tokenHeaders() {
  const token = getCartToken()
  return token ? { 'X-Cart-Token': token } : {}
}

// После любой операции бэкенд возвращает ПОЛНЫЙ объект Cart с полем token.
// Запоминаем токен (setCartToken игнорирует null — пустой ответ не затрёт наш
// сохранённый токен) и возвращаем cart дальше как есть.
function remember(cart) {
  setCartToken(cart?.token)
  return cart
}

// Показать корзину. Нет корзины → бэкенд отдаёт пустое представление (token:null).
export function getCart() {
  return apiGet('cart/', undefined, tokenHeaders()).then(remember)
}

// Добавить вариант. Повтор того же варианта → бэкенд СУММИРУЕТ количество (дублей
// нет). Недоступный вариант → 400 (ошибку пробросим наверх, кнопка покажет сбой).
export function addCartItem(variantId, quantity = 1) {
  return apiSend('POST', 'cart/items/', { variant: variantId, quantity }, tokenHeaders()).then(remember)
}

// Изменить количество строки (id — это id СТРОКИ, не варианта). quantity ≥ 1.
export function updateCartItem(itemId, quantity) {
  return apiSend('PATCH', `cart/items/${itemId}/`, { quantity }, tokenHeaders()).then(remember)
}

// Удалить строку.
export function removeCartItem(itemId) {
  return apiSend('DELETE', `cart/items/${itemId}/`, undefined, tokenHeaders()).then(remember)
}

// Очистить корзину: бэкенд удаляет все строки, саму корзину (и токен) сохраняет.
export function clearCart() {
  return apiSend('DELETE', 'cart/', undefined, tokenHeaders()).then(remember)
}
