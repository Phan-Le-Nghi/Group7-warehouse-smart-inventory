import { useEffect, useState } from 'react'
import App from './App'
import { ApiError } from './api'
import { getCurrentActor, logout } from './auth'
import type { Actor } from './auth'
import LoginPage from './LoginPage'

export default function AuthGate() {
  const [actor, setActor] = useState<Actor | null | undefined>(undefined)
  const [bootstrapError, setBootstrapError] = useState('')
  const [logoutError, setLogoutError] = useState('')

  useEffect(() => {
    let active = true
    getCurrentActor()
      .then((currentActor) => {
        if (active) setActor(currentActor)
      })
      .catch((error: unknown) => {
        if (!active) return
        if (error instanceof ApiError && error.status === 401) {
          setActor(null)
          return
        }
        setBootstrapError('Unable to check the current session.')
      })
    return () => {
      active = false
    }
  }, [])

  async function handleLogout() {
    setLogoutError('')
    try {
      await logout()
      setActor(null)
    } catch {
      setLogoutError('Unable to sign out. Please try again.')
    }
  }

  if (bootstrapError) {
    return (
      <main className="auth-shell">
        <p className="error-panel" role="alert">
          {bootstrapError}
        </p>
      </main>
    )
  }
  if (actor === undefined) {
    return (
      <main className="auth-shell">
        <p className="status-panel" role="status">
          Checking session…
        </p>
      </main>
    )
  }
  if (actor === null) {
    return <LoginPage onAuthenticated={setActor} />
  }
  return (
    <>
      {logoutError && (
        <p className="error-panel logout-error" role="alert">
          {logoutError}
        </p>
      )}
      <App
        actor={actor}
        onLogout={handleLogout}
        onUnauthorized={() => setActor(null)}
      />
    </>
  )
}
