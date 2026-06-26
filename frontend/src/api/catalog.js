// Доменные запросы каталога — поверх общего client.js.
// Здесь живёт знание «какие у каталога эндпоинты и параметры», а не «как ходить в сеть».

import { apiGet } from './client'

// Дерево категорий целиком (один запрос, без пагинации).
// Ответ — массив корневых узлов: { id, name, slug, children: [...] }.
export function getCategoryTree() {
  return apiGet('catalog/categories/')
}

// Список товаров. Все параметры необязательны:
// - category: id ветки (бэкенд включает товары всех подкатегорий);
// - search: строка поиска по названию/латыни/сорту (глобально, мимо дерева);
// - page: номер страницы (пагинация по 20).
// Ответ — конверт: { count, next, previous, results: [...] }.
export function getProducts({ category, search, page } = {}) {
  return apiGet('catalog/products/', { category, search, page })
}
