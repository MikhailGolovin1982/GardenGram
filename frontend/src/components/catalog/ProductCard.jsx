import { Link } from 'react-router-dom'
import { formatPrice } from '../../utils/format'

// Одна карточка товара в сетке. Простая (Шаг 2): фото/заглушка, название, цена «от»,
// пометка «Нет в наличии». Полная карточка с вариантами — Шаг 3.
//
// Данные берём как есть из списка API:
// - display_name — уже собрано по правилу «Русское (Латинское)» на бэкенде;
// - thumbnail — абсолютный URL или null (тогда показываем заглушку «нет фото»);
// - price_from — минимальная цена среди активных вариантов или null;
// - is_available — есть ли хоть один вариант в наличии.
function ProductCard({ product }) {
  const price = formatPrice(product.price_from)

  return (
    <Link to={`/product/${product.id}`} className="product-card">
      <div className="product-thumb">
        {product.thumbnail ? (
          <img src={product.thumbnail} alt={product.display_name} loading="lazy" />
        ) : (
          <span className="product-thumb-empty">Нет фото</span>
        )}
      </div>

      <div className="product-info">
        <span className="product-name">{product.display_name}</span>

        {/* Цена «от …», т.к. в списке не знаем числа вариантов, показываем минимум.
            Нет активных вариантов → цены нет → «Цена уточняется». */}
        <span className="product-price">
          {price ? `от ${price}` : 'Цена уточняется'}
        </span>

        {/* Статус наличия не скрывает товар — показываем пометку (важно для сезонных). */}
        {!product.is_available && (
          <span className="product-out">Нет в наличии</span>
        )}
      </div>
    </Link>
  )
}

export default ProductCard
