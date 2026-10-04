import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function Login() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  // Already signed in? There is nothing to do on this page.
  useEffect(() => {
    if (user) navigate('/account', { replace: true })
  }, [user, navigate])

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(email, password)
      navigate('/account')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'We could not sign you in.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="wrap auth">
      <div className="panel">
        <h1>Log in</h1>
        <p className="sub">Sign in to pick up your chat history and past orders.</p>

        {error && <div className="notice error">{error}</div>}

        <form onSubmit={onSubmit}>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              placeholder="you@yale.edu"
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <button className="btn block" type="submit" disabled={busy}>
            {busy ? 'Signing in…' : 'Log in'}
          </button>
        </form>

        <p className="foot">
          New to Campus Customs? <Link to="/create-account">Create an account</Link>
        </p>
      </div>
    </div>
  )
}
