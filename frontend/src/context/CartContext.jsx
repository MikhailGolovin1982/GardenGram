// Общее состояние корзины на весь сайт (React Context).
//
// Почему Context, а не useApi: корзину одновременно показывают ДВА места — бейдж в
// шапке (виден всегда) и страница /cart, — и добавление с карточки товара должно
// мгновенно обновить бейдж. useApi грузит данные «на одну страницу»; здесь нужно
// одно состояние, общее для всех. Redux/Zustand не берём — встроенного Context хватает.
//
// Единый источник правды: каждая операция корзины возвращает ПОЛНЫЙ объект Cart.
// Поэтому после любого действия мы просто кладём ответ в state — сумму, счётчик и
// доступность считает бэкенд, фронт ничего не пересчитывает. Логика тонкая и устойчивая.

import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import * as cartApi from '../api/cart'

const CartContext = createContext(null)

export function CartProvider({ children }) {
  const [cart, setCart] = useState(null) // объект Cart или null (ещё не загрузили)
  const [loading, setLoading] = useState(true) // идёт первичная гидрация (один GET)
  const [error, setError] = useState(null) // ошибка первичной загрузки
  const [mutating, setMutating] = useState(false) // идёт запись — блокируем кнопки

  // На старте один раз подтягиваем корзину по сохранённому токену, чтобы бейдж был
  // корректен сразу после перезагрузки. Ошибку гасим тихо: бейдж покажет 0, а на
  // странице /cart человек увидит честную ошибку при заходе (там свой refresh).
  useEffect(() => {
    let cancelled = false
    cartApi.getCart()
      .then((data) => { if (!cancelled) setCart(data) })
      .catch((err) => { if (!cancelled) setError(err) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  // Обёртка для всех пишущих действий: ставим mutating (защита от гонок двойных
  // кликов), зовём cart.js, кладём полный ответ в state. Ошибку ПРОБРАСЫВАЕМ наверх,
  // чтобы кнопка показала сбой; mutating снимаем в любом случае.
  const run = useCallback(async (fn) => {
    setMutating(true)
    try {
      const data = await fn()
      setCart(data)
      return data
    } finally {
      setMutating(false)
    }
  }, [])

  const addItem = useCallback((variantId, qty = 1) => run(() => cartApi.addCartItem(variantId, qty)), [run])
  const updateItem = useCallback((itemId, qty) => run(() => cartApi.updateCartItem(itemId, qty)), [run])
  const removeItem = useCallback((itemId) => run(() => cartApi.removeCartItem(itemId)), [run])
  const clear = useCallback(() => run(() => cartApi.clearCart()), [run])

  // refresh — мягкое обновление без mutating-блокировки (зовёт страница /cart при
  // заходе). Обновляет cart и снимает прежнюю ошибку при успехе.
  const refresh = useCallback(async () => {
    try {
      const data = await cartApi.getCart()
      setCart(data)
      setError(null)
      return data
    } catch (err) {
      setError(err)
      throw err
    }
  }, [])

  const value = {
    cart,
    loading,
    error,
    mutating,
    count: cart?.count ?? 0, // для бейджа в шапке
    addItem,
    updateItem,
    removeItem,
    clear,
    refresh,
  }

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>
}

// Хук-обёртка: любой компонент зовёт useCart() и получает состояние + действия.
export function useCart() {
  const ctx = useContext(CartContext)
  if (ctx === null) {
    throw new Error('useCart должен использоваться внутри <CartProvider>.')
  }
  return ctx
}
