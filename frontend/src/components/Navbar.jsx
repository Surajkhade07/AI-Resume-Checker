import { useState, useRef, useEffect } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import AuthPanel from './AuthPanel.jsx'

const NAV_ITEMS = [
  { key: 'landing', label: 'Home' },
  { key: 'scorer', label: 'ATS Scorer' },
  { key: 'history', label: 'History' },
  { key: 'resources', label: 'Resources' },
]

export default function Navbar({ view, setView }) {
  const { isAuthenticated, userEmail } = useAuth()
  const [authOpen, setAuthOpen] = useState(false)
  const popoverRef = useRef(null)

  useEffect(() => {
    function onClick(e) {
      if (popoverRef.current && !popoverRef.current.contains(e.target)) setAuthOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <button className="brand" onClick={() => setView('landing')}>
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 32 32" width="26" height="26">
              <circle cx="16" cy="16" r="14" fill="none" stroke="currentColor" strokeWidth="2.5" />
              <circle cx="16" cy="16" r="7.5" fill="none" stroke="currentColor" strokeWidth="2.5" />
              <circle cx="16" cy="16" r="2" fill="currentColor" />
            </svg>
          </span>
          <span className="brand-text">ATS Resume Scorer</span>
        </button>

        <nav className="nav-items">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              className={`nav-item ${view === item.key ? 'active' : ''}`}
              onClick={() => setView(item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="navbar-account" ref={popoverRef}>
          <button className="btn btn-account" onClick={() => setAuthOpen((v) => !v)}>
            <span className="account-dot" data-on={isAuthenticated} />
            {isAuthenticated ? (userEmail?.split('@')[0] ?? 'Account') : 'Sign in'}
          </button>
          {authOpen && (
            <div className="popover">
              <AuthPanel onClose={() => setAuthOpen(false)} />
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
