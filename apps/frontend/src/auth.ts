import { apiRequest } from './api'

export type Role = 'WAREHOUSE_STAFF' | 'MANAGER' | 'PURCHASING' | 'ADMIN'

export type Actor = {
  id: string
  login_identifier: string
  role: Role
}

export function getCurrentActor(): Promise<Actor> {
  return apiRequest<Actor>('/api/v1/auth/me')
}

export function login(
  loginIdentifier: string,
  password: string,
): Promise<Actor> {
  return apiRequest<Actor>('/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      login_identifier: loginIdentifier,
      password,
    }),
  })
}

export function logout(): Promise<void> {
  return apiRequest<void>(
    '/api/v1/auth/logout',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
    },
    204,
  )
}
