import { Outlet } from 'react-router-dom'
import Header from '../components/Header'
import Footer from '../components/Footer'

// Общий каркас сайта: шапка + текущая страница + подвал.
// <Outlet/> — «дырка», куда React Router подставляет страницу активного маршрута.
// При переходах перерисовывается только середина, шапка и подвал остаются.
function RootLayout() {
  return (
    <>
      <Header />
      <main className="site-main">
        <Outlet />
      </main>
      <Footer />
    </>
  )
}

export default RootLayout
