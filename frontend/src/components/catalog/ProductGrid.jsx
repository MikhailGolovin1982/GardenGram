import ProductCard from './ProductCard'

// Адаптивная сетка карточек. Сама раскладка — в CSS (.product-grid):
// grid auto-fill → 1 колонка на телефоне, несколько на широком экране (без media-query).
function ProductGrid({ products }) {
  if (!products || products.length === 0) return null

  return (
    <div className="product-grid">
      {products.map((product) => (
        <ProductCard key={product.id} product={product} />
      ))}
    </div>
  )
}

export default ProductGrid
