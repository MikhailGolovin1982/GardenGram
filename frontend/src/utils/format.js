// Мелкие форматтеры отображения.

// Цена приходит из API строкой вида "600.00". Показываем по-человечески: «600 ₽».
// Срезаем незначащие нули и точку. Если цены нет (null) — null, страница решит сама.
export function formatPrice(value) {
  if (value === null || value === undefined) return null
  // Number красиво уберёт .00, а 2.50 → 2.5; затем добавляем рубль.
  const num = Number(value)
  if (Number.isNaN(num)) return null
  return `${num} ₽`
}
