import { Link } from 'react-router-dom'

// Список категорий (плитками). Используется и в корне каталога (верхний уровень),
// и внутри ветки (подкатегории). Каждая категория — ссылка, меняющая ?category=id;
// благодаря этому «назад» браузера работает само.
//
// Счётчиков товаров намеренно НЕТ: API дерева их не отдаёт (см. PLAN_STEP_2, п.1.1).
function CategoryList({ nodes }) {
  if (!nodes || nodes.length === 0) return null

  return (
    <ul className="category-list">
      {nodes.map((node) => (
        <li key={node.id}>
          <Link to={`/catalog?category=${node.id}`} className="category-tile">
            {node.name}
          </Link>
        </li>
      ))}
    </ul>
  )
}

export default CategoryList
