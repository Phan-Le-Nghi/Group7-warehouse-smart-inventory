import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import AuthGate from './AuthGate'

const actor = {
  id: 'actor-id',
  login_identifier: 'demo.warehouse_staff',
  role: 'WAREHOUSE_STAFF',
}
function jsonResponse(body: object, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

it('shows login after an unauthenticated bootstrap and signs in', async () => {
  const fetchMock = vi
    .spyOn(globalThis, 'fetch')
    .mockReturnValueOnce(
      jsonResponse(
        {
          error: {
            code: 'AUTHENTICATION_REQUIRED',
            message: 'Authentication is required.',
            details: {},
          },
        },
        401,
      ),
    )
    .mockReturnValueOnce(jsonResponse(actor))

  render(<AuthGate />)
  fireEvent.change(await screen.findByLabelText('Login identifier'), {
    target: { value: 'demo.warehouse_staff' },
  })
  fireEvent.change(screen.getByLabelText('Password'), {
    target: { value: 'test-only-password' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

  expect(await screen.findByText('Warehouse Staff')).toBeInTheDocument()
  expect(fetchMock.mock.calls[1][1]).toMatchObject({
    credentials: 'include',
    method: 'POST',
  })
})

it('keeps an authenticated wrong-role actor and shows forbidden', async () => {
  vi.spyOn(globalThis, 'fetch').mockReturnValue(
    jsonResponse({ ...actor, role: 'MANAGER' }),
  )

  render(<AuthGate />)

  expect(
    await screen.findByRole('heading', {
      name: 'Warehouse Staff role required',
    }),
  ).toBeInTheDocument()
  expect(screen.getByText('Manager')).toBeInTheDocument()
  expect(globalThis.fetch).toHaveBeenCalledTimes(1)
})

it('clears frontend actor state after a successful logout', async () => {
  const fetchMock = vi
    .spyOn(globalThis, 'fetch')
    .mockReturnValueOnce(jsonResponse(actor))
    .mockReturnValueOnce(Promise.resolve(new Response(null, { status: 204 })))

  render(<AuthGate />)
  fireEvent.click(await screen.findByRole('button', { name: 'Sign out' }))

  await waitFor(() => {
    expect(screen.getByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
  })
  expect(fetchMock.mock.calls[1][1]).toMatchObject({
    credentials: 'include',
    method: 'POST',
  })
})

it('keeps the actor and allows retry when logout fails', async () => {
  const fetchMock = vi
    .spyOn(globalThis, 'fetch')
    .mockReturnValueOnce(jsonResponse(actor))
    .mockRejectedValueOnce(new TypeError('network unavailable'))
    .mockReturnValueOnce(Promise.resolve(new Response(null, { status: 204 })))

  render(<AuthGate />)
  fireEvent.click(await screen.findByRole('button', { name: 'Sign out' }))

  expect(
    await screen.findByText('Unable to sign out. Please try again.'),
  ).toBeInTheDocument()
  expect(screen.getByText('Warehouse Staff')).toBeInTheDocument()
  expect(
    screen.queryByRole('heading', { name: 'Sign in' }),
  ).not.toBeInTheDocument()

  fireEvent.click(screen.getByRole('button', { name: 'Sign out' }))

  expect(
    await screen.findByRole('heading', { name: 'Sign in' }),
  ).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledTimes(3)
})

it.each([
  ['an HTTP 5xx response', new Response('', { status: 503 })],
  [
    'an unexpected successful response',
    new Response('{}', {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }),
  ],
])('keeps the actor after logout receives %s', async (_label, response) => {
  vi.spyOn(globalThis, 'fetch')
    .mockReturnValueOnce(jsonResponse(actor))
    .mockResolvedValueOnce(response)

  render(<AuthGate />)
  fireEvent.click(await screen.findByRole('button', { name: 'Sign out' }))

  expect(
    await screen.findByText('Unable to sign out. Please try again.'),
  ).toBeInTheDocument()
  expect(screen.getByText('Warehouse Staff')).toBeInTheDocument()
  expect(
    screen.queryByRole('heading', { name: 'Sign in' }),
  ).not.toBeInTheDocument()
})
