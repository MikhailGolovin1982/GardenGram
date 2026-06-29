import { useEffect, useRef, useState } from 'react'
import { useCart } from '../../context/CartContext'

// Кнопка «В корзину» у конкретного варианта (Путь 1 — у каждого доступного варианта
// своя кнопка). Недоступные варианты её вообще не получают — это решает VariantList.
//
// Локальный цикл: idle → adding (disabled, «Добавляем…») → added («В корзине ✓» ~1.5с)
// → снова idle. Ошибка → подпись «Не удалось», кнопка возвращается в idle.
// Состояние одной кнопки локальное; общую корзину обновляет addItem из контекста.
function AddToCartButton({ variantId }) {
  const { addItem } = useCart()
  const [status, setStatus] = useState('idle') // idle | adding | added | error
  const timerRef = useRef(null)

  // Чистим таймер сброса «added», если компонент исчезнет раньше срабатывания.
  useEffect(() => () => clearTimeout(timerRef.current), [])

  async function handleClick() {
    setStatus('adding')
    try {
      await addItem(variantId, 1)
      setStatus('added')
      timerRef.current = setTimeout(() => setStatus('idle'), 1500)
    } catch {
      // Честная граница: вариант мог стать недоступен между загрузкой и кликом
      // (бэкенд вернёт 400). Показываем общий «Не удалось» — разбор точного текста
      // ошибки DRF отложен (см. §5.1 плана).
      setStatus('error')
    }
  }

  const label = {
    idle: 'В корзину',
    adding: 'Добавляем…',
    added: 'В корзине ✓',
    error: 'Не удалось',
  }[status]

  return (
    <button
      type="button"
      className="add-to-cart"
      onClick={handleClick}
      disabled={status === 'adding'}
    >
      {label}
    </button>
  )
}

export default AddToCartButton
