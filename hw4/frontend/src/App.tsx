import { Outlet, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import Nav from './components/Nav'
import Footer from './components/Footer'
import ChatWidget from './components/ChatWidget'

export default function App() {
  const { pathname } = useLocation()

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])

  return (
    <div className="app">
      <Nav />
      <main>
        <Outlet />
      </main>
      <Footer />
      <ChatWidget />
    </div>
  )
}
