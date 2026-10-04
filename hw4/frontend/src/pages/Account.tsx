import { Link, useNavigate } from 'react-router-dom'
import { useAuth, greetingName } from '../auth'

export default function Account() {
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()

  if (loading) return <div className="wrap section"><p className="state">Loading…</p></div>

  if (!user) {
    return (
      <div className="wrap auth">
        <div className="panel">
          <h1>Your account</h1>
          <p className="sub">You need to be signed in to see this page.</p>
          <Link className="btn block" to="/login">Log in</Link>
          <p className="foot">No account yet? <Link to="/create-account">Create one</Link></p>
        </div>
      </div>
    )
  }

  async function signOut() {
    await logout()
    navigate('/')
  }

  const joined = new Date(user.created_at.replace(' ', 'T') + 'Z').toLocaleDateString('en-US', {
    year: 'numeric', month: 'long', day: 'numeric',
  })

  return (
    <div className="wrap section">
      <div className="section-head">
        <h1>Welcome back, {greetingName(user)}.</h1>
        <p>This is your Campus Customs account.</p>
      </div>

      <div className="cards" style={{ maxWidth: 760 }}>
        <div className="card">
          <h3>Name</h3>
          <p>{user.name}</p>
        </div>
        <div className="card">
          <h3>Email</h3>
          <p>{user.email}</p>
        </div>
        <div className="card">
          <h3>Member since</h3>
          <p>{joined}</p>
        </div>
      </div>

      <p style={{ marginTop: 30, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <Link className="btn outline" to="/products">Keep shopping</Link>
        <button className="btn" onClick={signOut}>Log out</button>
      </p>
    </div>
  )
}
