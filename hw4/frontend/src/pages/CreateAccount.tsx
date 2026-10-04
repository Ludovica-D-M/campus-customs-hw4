import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

const EMPTY = {
  first_name: '',
  last_name: '',
  email: '',
  password: '',
  confirm_password: '',
}

export default function CreateAccount() {
  const { user, register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (user) navigate('/account', { replace: true })
  }, [user, navigate])

  const set = (key: keyof typeof form) => (e: ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [key]: e.target.value }))

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    // Check here too so the password never leaves the browser needlessly.
    if (form.password !== form.confirm_password) {
      setError('Those passwords do not match.')
      return
    }
    if (form.password.length < 8) {
      setError('Your password must be at least 8 characters.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      await register(form)
      navigate('/account')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'We could not create your account.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="wrap auth">
      <div className="panel">
        <h1>Create an account</h1>
        <p className="sub">Save your size, keep your chat history, and check out faster.</p>

        {error && <div className="notice error">{error}</div>}

        <form onSubmit={onSubmit}>
          <div className="row2">
            <div className="field">
              <label htmlFor="first">First name</label>
              <input id="first" type="text" required autoComplete="given-name"
                value={form.first_name} onChange={set('first_name')} />
            </div>
            <div className="field">
              <label htmlFor="last">Last name</label>
              <input id="last" type="text" required autoComplete="family-name"
                value={form.last_name} onChange={set('last_name')} />
            </div>
          </div>
          <div className="field">
            <label htmlFor="newemail">Email</label>
            <input id="newemail" type="email" required autoComplete="email"
              value={form.email} placeholder="you@yale.edu" onChange={set('email')} />
          </div>
          <div className="field">
            <label htmlFor="newpass">Password</label>
            <input id="newpass" type="password" required minLength={8} autoComplete="new-password"
              value={form.password} onChange={set('password')} />
            <p className="hint">At least 8 characters.</p>
          </div>
          <div className="field">
            <label htmlFor="confirm">Confirm password</label>
            <input id="confirm" type="password" required autoComplete="new-password"
              value={form.confirm_password} onChange={set('confirm_password')} />
          </div>
          <button className="btn block" type="submit" disabled={busy}>
            {busy ? 'Creating your account…' : 'Create account'}
          </button>
        </form>

        <p className="foot">
          Already have one? <Link to="/login">Log in</Link>
        </p>
      </div>
    </div>
  )
}
