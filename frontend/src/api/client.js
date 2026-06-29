// Тонкая обёртка над fetch — единственное место, где сайт «звонит» бэкенду.
// Зачем отдельный файл: все запросы (каталог сейчас, корзина/заказы позже) идут
// через одну дверь. Захотим добавить заголовки (токен гостя X-Cart-Token, JWT) —
// правим тут одно место, а не каждый вызов по всему коду.

// База API берётся из переменной окружения (без хардкода — адрес Codespace меняется).
// Vite подставляет её на сборке; см. frontend/.env.local.
const BASE_URL = import.meta.env.VITE_API_BASE_URL

// Собираем query-строку из объекта, выкидывая пустые значения
// (null/undefined/'' не шлём — чтобы не слать ?category=undefined).
function buildQuery(params) {
  if (!params) return ''
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      search.append(key, value)
    }
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

// GET-запрос к API. Возвращает разобранный JSON либо кидает понятную ошибку,
// текст которой мы покажем прямо на экране (диагностика с телефона без терминала).
export async function apiGet(path, params) {
  if (!BASE_URL) {
    throw new Error('Не задан VITE_API_BASE_URL (проверь frontend/.env.local).')
  }
  // path вида 'catalog/products/' — склеиваем с базой и query-строкой.
  const url = `${BASE_URL}/${path}${buildQuery(params)}`

  let response
  try {
    response = await fetch(url)
  } catch {
    // Сетевой сбой (Django не запущен, порт приватный и т.п.) — fetch бросает сам.
    throw new Error('Не удалось связаться с сервером. Проверь, что бэкенд запущен.')
  }

  if (!response.ok) {
    // 4xx/5xx — сервер ответил, но с ошибкой.
    // Аддитивно прикрепляем числовой статус к объекту ошибки: страница сможет
    // отличить 404 (товар не найден) от прочих сбоев и показать дружелюбный текст.
    // Каталог Шага 2 читает только err.message — для него поведение не меняется.
    const err = new Error(`Сервер вернул ошибку ${response.status}.`)
    err.status = response.status
    throw err
  }

  return response.json()
}

// На будущее (Шаги 4–5): сюда добавим apiPost/apiPatch/apiDelete и проброс
// заголовков X-Cart-Token / Authorization. Сейчас витрина — только чтение (GET).
