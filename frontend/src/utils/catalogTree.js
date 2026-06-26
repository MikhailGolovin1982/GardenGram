// Чистые функции по дереву категорий (без React и без запросов).
// Дерево мы грузим один раз и держим в стейте; навигацию по нему считаем тут,
// не дёргая API на каждый шаг вглубь.
//
// Узел дерева: { id, name, slug, children: [...] }.

// Найти узел по id. Возвращает узел или null. Обход в глубину.
export function findNode(nodes, id) {
  if (!nodes) return null
  for (const node of nodes) {
    if (node.id === id) return node
    const found = findNode(node.children, id)
    if (found) return found
  }
  return null
}

// Путь от корня до узла с данным id (для хлебных крошек), включая сам узел.
// Возвращает массив узлов [корень, …, текущий] или [] если не нашли.
export function findPath(nodes, id) {
  if (!nodes) return []
  for (const node of nodes) {
    if (node.id === id) return [node]
    const sub = findPath(node.children, id)
    if (sub.length) return [node, ...sub]
  }
  return []
}
