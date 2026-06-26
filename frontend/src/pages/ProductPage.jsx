import { useParams } from 'react-router-dom'

// Шаг 1: заглушка. Показываем :id из адреса, чтобы проверить параметры маршрута.
function ProductPage() {
  const { id } = useParams()
  return (
    <section>
      <h1>Карточка товара #{id}</h1>
      <p>Заглушка, Шаг 1. Здесь будут фото, описание, варианты с ценами и «в корзину».</p>
    </section>
  )
}

export default ProductPage
