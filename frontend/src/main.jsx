import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import { CartProvider } from './context/CartContext.jsx'

// BrowserRouter включает клиентский роутинг (адрес меняет браузер, без перезагрузки).
// CartProvider внутри роутера: и шапка (бейдж), и страницы видят ОДНУ корзину.
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <CartProvider>
        <App />
      </CartProvider>
    </BrowserRouter>
  </StrictMode>,
)
