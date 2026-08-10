import { useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { signInWithPassword, signUpWithPassword, signInWithGoogle, signOut, isSupabaseConfigured } from '../lib/supabase'

export default function AuthPanel({ onClose }) {
  const { isAuthenticated, userEmail } = useAuth()
  const [tab, setTab] = useState('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [info, setInfo] = useState(null)
  const [busy, setBusy] = useState(false)

  if (!isSupabaseConfigured) {
    return (
      <div className="auth-panel">
        <p className="auth-warning">
          Supabase isn't configured yet — add <code>VITE_SUPABASE_URL</code> and{' '}
          <code>VITE_SUPABASE_ANON_KEY</code> to your <code>.env</code> file.
        </p>
      </div>
    )
  }

  if (isAuthenticated) {
    return (
      <div className="auth-panel">
        <p className="auth-signed-in">
          Signed in as <strong>{userEmail}</strong>
        </p>
        <button className="btn btn-ghost btn-block" onClick={() => signOut()}>
          Sign out
        </button>
      </div>
    )
  }

  async function submit(e) {
    e.preventDefault()
    setError(null)
    setInfo(null)
    setBusy(true)
    const result = tab === 'signin'
      ? await signInWithPassword(email, password)
      : await signUpWithPassword(email, password)
    setBusy(false)

    if (result.error) {
      setError(result.error)
    } else if (result.pendingConfirmation) {
      setInfo(`Check your inbox — confirmation email sent to ${result.email}.`)
    } else {
      onClose?.()
    }
  }

  async function google() {
    setError(null)
    const result = await signInWithGoogle()
    if (result.error) setError(result.error)
    else if (result.url) window.location.href = result.url
  }

  return (
    <div className="auth-panel">
      <div className="auth-tabs">
        <button
          className={`auth-tab ${tab === 'signin' ? 'active' : ''}`}
          onClick={() => { setTab('signin'); setError(null) }}
        >
          Sign in
        </button>
        <button
          className={`auth-tab ${tab === 'signup' ? 'active' : ''}`}
          onClick={() => { setTab('signup'); setError(null) }}
        >
          Sign up
        </button>
      </div>

      {error && <div className="auth-alert error">{error}</div>}
      {info && <div className="auth-alert info">{info}</div>}

      <form onSubmit={submit} className="auth-form">
        <label>
          Email
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
        </label>
        <label>
          {tab === 'signup' ? 'Password (min 6 chars)' : 'Password'}
          <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
        </label>
        <button className="btn btn-primary btn-block" type="submit" disabled={busy}>
          {busy ? 'Please wait…' : tab === 'signin' ? 'Sign in' : 'Create account'}
        </button>
      </form>

      <div className="auth-divider"><span>or</span></div>
      <button className="btn btn-outline btn-block" onClick={google}>
        Continue with Google
      </button>
    </div>
  )
}
