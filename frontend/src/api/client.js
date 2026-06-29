// Тонкая обёртка над fetch — единственное место, где сайт «звонит» бэкенду.
// Зачем отдельный файл: все запросы (каталог, корзина, заказы) идут через одну
// дверь. Захотим добавить заголовки (токен гостя X-Cart-Token, JWT) — правим тут
// одно место, а не каждый вызов по всему коду.

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

// Ядро всех запросов: проверка BASE_URL, сборка URL, единый разбор ошибок.
// method — 'GET'/'POST'/'PATCH'/'DELETE'; opts: { params, body, headers }.
// body, если передан, сериализуется в JSON и снабжается Content-Type.
// Возвращает разобранный JSON либо кидает понятную ошибку (её текст покажем
// прямо на экране — диагностика с телефона без терминала).
async function apiRequest(method, path, { params, body, headers } = {}) {
  if (!BASE_URL) {
    throw new Error('Не задан VITE_API_BASE_URL (проверь frontend/.env.local).')
  }
  // path вида 'catalog/products/' — склеиваем с базой и query-строкой.
  const url = `${BASE_URL}/${path}${buildQuery(params)}`

  // Собираем заголовки: переданные вызывающим (напр. X-Cart-Token) + Content-Type
  // только когда реально шлём тело (у GET/DELETE-без-тела его быть не должно).
  const finalHeaders = { ...headers }
  const init = { method, headers: finalHeaders }
  if (body !== undefined) {
    finalHeaders['Content-Type'] = 'application/json'
    init.body = JSON.stringify(body)
  }

  let response
  try {
    response = await fetch(url, init)
  } catch {
    // Сетевой сбой (Django не запущен, порт приватный и т.п.) — fetch бросает сам.
    throw new Error('Не удалось связаться с сервером. Проверь, что бэкенд запущен.')
  }

  if (!response.ok) {
    // 4xx/5xx — сервер ответил, но с ошибкой. Аддитивно прикрепляем числовой
    // статус: страница сможет отличить 404 (товар не найден) от прочих сбоев.
    const err = new Error(`Сервер вернул ошибку ${response.status}.`)
    err.status = response.status
    throw err
  }

  // 204 No Content тела не имеет; наши cart-эндпоинты всегда отдают JSON, даже
  // DELETE — но подстрахуемся, чтобы .json() не упал на пустом ответе.
  if (response.status === 204) return null
  return response.json()
}

// GET-запрос. Сигнатура обратносовместима: старые вызовы каталога apiGet(path,
// params) работают как раньше; третий аргумент headers нужен корзине (X-Cart-Token).
export function apiGet(path, params, headers) {
  return apiRequest('GET', path, { params, headers })
}

// Запись (POST/PATCH/DELETE). body опционален (у DELETE его нет), headers — для
// проброса X-Cart-Token. Используется доменным модулем корзины (api/cart.js).
export function apiSend(method, path, body, headers) {
  return apiRequest(method, path, { body, headers })
}
