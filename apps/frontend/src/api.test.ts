import { afterEach, expect, it, vi } from 'vitest'
import { ApiError, apiRequest } from './api'

afterEach(() => {
  vi.restoreAllMocks()
})

it('preserves a JSON error envelope', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(
      JSON.stringify({
        error: {
          code: 'FORBIDDEN',
          message: 'Access denied.',
          details: { required_roles: ['MANAGER'] },
        },
      }),
      { status: 403, headers: { 'Content-Type': 'application/json' } },
    ),
  )

  await expect(apiRequest('/protected')).rejects.toMatchObject({
    status: 403,
    code: 'FORBIDDEN',
    message: 'Access denied.',
    details: { required_roles: ['MANAGER'] },
  })
})

it.each([
  ['HTML', '<h1>Bad gateway</h1>', 'text/html'],
  ['plain text', 'upstream unavailable', 'text/plain'],
  ['empty', '', 'text/plain'],
])('returns a typed API error for a %s error response', async (_label, body, type) => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(body, { status: 502, headers: { 'Content-Type': type } }),
  )

  const request = apiRequest('/protected')

  await expect(request).rejects.toBeInstanceOf(ApiError)
  await expect(request).rejects.toMatchObject({
    status: 502,
    code: 'REQUEST_FAILED',
    message: 'The request could not be completed.',
  })
})

it('returns a typed API error for malformed JSON', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response('{invalid', {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    }),
  )

  await expect(apiRequest('/protected')).rejects.toMatchObject({
    status: 500,
    code: 'REQUEST_FAILED',
  })
})

it('rejects an unexpected successful status', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response('{}', {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }),
  )

  await expect(apiRequest('/logout', {}, 204)).rejects.toMatchObject({
    status: 200,
    code: 'UNEXPECTED_RESPONSE',
  })
})
