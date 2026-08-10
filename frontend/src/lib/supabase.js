import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY
export const AUTH_REDIRECT_URL = import.meta.env.VITE_AUTH_REDIRECT_URL || window.location.origin

export const isSupabaseConfigured = Boolean(SUPABASE_URL && SUPABASE_ANON_KEY)

// supabase-js handles PKCE + the ?code= exchange on page load automatically
// (detectSessionInUrl: true is the default), mirroring what the Streamlit
// app did by hand in streamlit_app.py.
// Use sessionStorage so when the user closes the website, the session
// is cleared and requires signing in again on next visit.
export const supabase = isSupabaseConfigured
  ? createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
      auth: {
        storage: typeof window !== 'undefined' ? window.sessionStorage : undefined,
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    })
  : null

function humanize(message) {
  const msg = (message || '').toLowerCase()
  if (msg.includes('invalid_grant') || msg.includes('invalid login')) return 'Wrong email or password'
  if (msg.includes('already registered')) return 'An account with this email already exists — try signing in'
  if (msg.includes('password should be at least')) return 'Password too short (minimum 6 characters)'
  return message
}

export async function signInWithPassword(email, password) {
  if (!supabase) return { error: 'Supabase is not configured — set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY' }
  const { data, error } = await supabase.auth.signInWithPassword({ email, password })
  if (error) return { error: humanize(error.message) }
  return { session: data.session, user: data.user }
}

export async function signUpWithPassword(email, password) {
  if (!supabase) return { error: 'Supabase is not configured — set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY' }
  const { data, error } = await supabase.auth.signUp({ email, password })
  if (error) return { error: humanize(error.message) }
  if (!data.session && data.user) return { pendingConfirmation: true, email }
  return { session: data.session, user: data.user }
}

export async function signInWithGoogle() {
  if (!supabase) return { error: 'Supabase is not configured' }
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: { redirectTo: AUTH_REDIRECT_URL },
  })
  if (error) return { error: humanize(error.message) }
  return { url: data.url }
}

export async function signOut() {
  if (!supabase) return
  await supabase.auth.signOut()
}
