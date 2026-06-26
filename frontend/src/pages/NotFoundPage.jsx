import { Link } from 'react-router-dom'

// Шаг 1: ловит несуществующие адреса (маршрут "*").
function NotFoundPage() {
  return (
    <section>
      <h1>404 — страница не найдена</h1>
      <p>Такого адреса нет. <Link to="/">Вернуться на главную</Link>.</p>
    </section>
  )
}

export default NotFoundPage
