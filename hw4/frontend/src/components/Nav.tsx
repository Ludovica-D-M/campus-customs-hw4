import { useEffect, useState } from 'react'
import { NavLink, Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth, greetingName } from '../auth'
import Labubu from './Labubu'

const link = ({ isActive }: { isActive: boolean }) => (isActive ? 'active' : undefined)

export default function Nav() {
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)

  // A shadow once the page moves, so the bar separates from the content.
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // Close the mobile menu whenever the route changes.
  useEffect(() => setOpen(false), [pathname])

  async function signOut() {
    setOpen(false)
    await logout()
    navigate('/')
  }

  return (
    <>
      <div className="topbar">
        <div className="wrap">
          <span>Officially licensed Yale apparel · 57 Broadway, New Haven</span>
          <span>Worldwide shipping · (475) 301-4205</span>
        </div>
      </div>
      <header className={scrolled ? 'nav scrolled' : 'nav'}>
        <div className="wrap">
          <Link to="/" className="brand">
            <span className="brand-mark">Y</span>
            <span className="brand-text">
              <strong>Campus Customs</strong>
              <span>Yale Bulldog Blue</span>
            </span>
          </Link>

          <button
            className="nav-toggle"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-label={open ? 'Close menu' : 'Open menu'}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              {open ? <path d="M18 6 6 18M6 6l12 12" /> : <path d="M3 6h18M3 12h18M3 18h18" />}
            </svg>
          </button>

          <nav className={open ? 'nav-links open' : 'nav-links'}>
            <NavLink to="/" end className={link}>Home</NavLink>
            <NavLink to="/products" className={link}>Products</NavLink>
            <NavLink to="/about" className={link}>About Us</NavLink>

            {loading ? null : user ? (
              <>
                <NavLink to="/account" className={link}>
                  <Labubu size={22} />
                  Hi, {greetingName(user)}
                </NavLink>
                <button className="link-button" onClick={signOut}>Log out</button>
              </>
            ) : (
              <>
                <NavLink to="/login" className={link}>Log in</NavLink>
                <NavLink to="/create-account" className={({ isActive }) => (isActive ? 'cta active' : 'cta')}>
                  <Labubu size={22} />
                  Create account
                </NavLink>
              </>
            )}
          </nav>
        </div>
      </header>
    </>
  )
}
