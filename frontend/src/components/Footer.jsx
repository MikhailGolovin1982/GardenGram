import { BRAND_FULL } from '../constants/brand'

// Подвал. Статичный, виден на всех экранах. Без логики.
function Footer() {
  const year = new Date().getFullYear()
  return (
    <footer className="site-footer">
      {BRAND_FULL} · с. Иглино, Башкортостан · {year}
    </footer>
  )
}

export default Footer
