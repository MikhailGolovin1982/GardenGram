// Подвал. Статичный, виден на всех экранах. Без логики.
function Footer() {
  const year = new Date().getFullYear()
  return (
    <footer className="site-footer">
      GardenGram · с. Иглино, Башкортостан · {year}
    </footer>
  )
}

export default Footer
