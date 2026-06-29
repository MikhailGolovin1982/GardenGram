import { useParams, useNavigate, Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { getProduct } from '../api/catalog'
import ProductGallery from '../components/catalog/ProductGallery'
import VariantList from '../components/catalog/VariantList'

// Карточка товара (Шаг 3) — завершает «смотрящую» часть сайта.
// Только показ: фото/заглушка, имя по правилу латыни, сорт, описание, все варианты
// с ценой и наличием. Кнопок «в корзину»/выбора варианта здесь НЕТ (Шаг 4 и позже).
function ProductPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  // Тот же хук загрузки, что в каталоге. Зависимость [id]: сменился адрес → перезапрос.
  const { data: product, loading, error } = useApi(() => getProduct(id), [id])

  if (loading) {
    return <p>Загрузка товара…</p>
  }

  // 404 — несуществующий ИЛИ неопубликованный товар (бэкенд прячет черновики 404-м).
  // Дружелюбный экран вместо технического «Сервер вернул ошибку 404».
  if (error && error.status === 404) {
    return (
      <section className="product-detail">
        <h1>Товар не найден</h1>
        <p className="catalog-empty">Возможно, он снят с продажи.</p>
        <p>
          <Link to="/catalog">← В каталог</Link>
        </p>
      </section>
    )
  }

  // Прочие сбои (сеть, 5xx) — как на Шаге 2: показываем сообщение прямо на экране.
  if (error) {
    return <p className="catalog-error">{error.message}</p>
  }

  const category = product.category

  return (
    <section className="product-detail">
      {/* Простая навигация назад вместо полных хлебных крошек (сознательная граница шага):
          «← Назад» — по истории браузера; рядом ссылка на ветку категории товара. */}
      <p className="product-back">
        <button type="button" className="back-link" onClick={() => navigate(-1)}>
          ← Назад
        </button>
        {category && (
          <Link to={`/catalog?category=${category.id}`} className="back-category">
            {category.name}
          </Link>
        )}
      </p>

      {/* display_name уже собрано на бэкенде по правилу «Русское (Латинское)». */}
      <h1>{product.display_name}</h1>

      {/* Сорт — необязательный, показываем только если непуст. */}
      {product.cultivar && (
        <p className="product-cultivar">Сорт: {product.cultivar}</p>
      )}

      <ProductGallery images={product.images} alt={product.display_name} />

      <VariantList variants={product.variants} />

      <div className="product-description">
        <h2>Описание</h2>
        {/* white-space: pre-line в CSS сохраняет переносы строк, введённые в админке. */}
        <p>{product.description}</p>
      </div>
    </section>
  )
}

export default ProductPage
