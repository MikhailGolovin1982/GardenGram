import { Link } from 'react-router-dom'

// Хлебные крошки: «Каталог → Декоративные → Гортензии».
// path — массив узлов от корня до текущего (из findPath). Текущий (последний) —
// просто текст, остальные — ссылки наверх по дереву. «Каталог» всегда первый.
function Breadcrumbs({ path }) {
  return (
    <nav className="breadcrumbs">
      <Link to="/catalog">Каталог</Link>
      {path.map((node, index) => {
        const isLast = index === path.length - 1
        return (
          <span key={node.id}>
            <span className="breadcrumbs-sep"> → </span>
            {isLast ? (
              <span className="breadcrumbs-current">{node.name}</span>
            ) : (
              <Link to={`/catalog?category=${node.id}`}>{node.name}</Link>
            )}
          </span>
        )
      })}
    </nav>
  )
}

export default Breadcrumbs
