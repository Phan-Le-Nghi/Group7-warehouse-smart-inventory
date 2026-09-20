import { FormEvent, useState } from 'react'
import { ApiError } from './api'
import { login } from './auth'
import type { Actor } from './auth'

type LoginPageProps = {
  onAuthenticated: (actor: Actor) => void
}

export default function LoginPage({ onAuthenticated }: LoginPageProps) {
  const [loginIdentifier, setLoginIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (submitting) return
    setSubmitting(true)
    setError('')
    try {
      onAuthenticated(await login(loginIdentifier, password))
      setPassword('')
    } catch (requestError) {
      setError(
        requestError instanceof ApiError && requestError.status === 401
          ? 'Invalid login identifier or password.'
          : 'Unable to sign in. Please try again.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="auth-shell">
      <section className="login-card" aria-labelledby="login-title">
        <div className="brand-mark" aria-hidden="true">
          W
        </div>
        <p className="eyebrow">Smart Inventory</p>
        <h1 id="login-title">Sign in</h1>
        <p className="supporting-copy">
          Use the account provided by your warehouse administrator.
        </p>
        <form onSubmit={handleSubmit}>
          <label className="login-field">
            <span>Login identifier</span>
            <input
              name="login_identifier"
              autoComplete="username"
              required
              value={loginIdentifier}
              onChange={(event) => setLoginIdentifier(event.target.value)}
            />
          </label>
          <label className="login-field">
            <span>Password</span>
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {error && (
            <p className="error-panel" role="alert">
              {error}
            </p>
          )}
          <button type="submit" disabled={submitting}>
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </section>
    </main>
  )
}
