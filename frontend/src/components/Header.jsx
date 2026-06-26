import { Link, NavLink } from 'react-router-dom'
import { BRAND_SHORT } from '../constants/brand'

// Шапка с навигацией. Видна на всех экранах (вставляется в RootLayout).
// NavLink сам подсвечивает активный пункт через класс "active" (см. index.css).
function Header() {
  return (
    <header className="site-header">
      {/* Логотип-текст (короткая форма бренда) — ссылка на главную */}
      <Link to="/" className="logo">{BRAND_SHORT}</Link>

      <nav className="site-nav">
        <NavLink to="/catalog">Каталог</NavLink>
        <NavLink to="/about">О нас</NavLink>
        <NavLink to="/cart">Корзина</NavLink>
        <NavLink to="/login">Вход</NavLink>
      </nav>
    </header>
  )
}

export default Header
