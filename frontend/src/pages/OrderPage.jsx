import { useParams } from 'react-router-dom'

// Шаг 1: заглушка. Показываем :token из адреса (секретный access_token гостя).
function OrderPage() {
  const { token } = useParams()
  return (
    <section>
      <h1>Заказ {token}</h1>
      <p>Заглушка, Шаг 1. Здесь будут номер заказа GG-… и подтверждение для покупателя.</p>
    </section>
  )
}

export default OrderPage
