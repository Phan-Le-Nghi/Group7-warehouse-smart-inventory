import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import EligibleAdjustmentsPage from './EligibleAdjustmentsPage'

function response(body: object, status = 200) {
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

it('renders loading then the approved empty state', async () => {
  let resolveFetch: ((value: Response) => void) | undefined
  vi.spyOn(globalThis, 'fetch').mockReturnValue(
    new Promise<Response>((resolve) => {
      resolveFetch = resolve
    }),
  )
  render(<EligibleAdjustmentsPage onUnauthorized={() => undefined} />)
  expect(screen.getByRole('status')).toHaveTextContent('Loading eligible adjustments')
  resolveFetch?.(
    new Response(JSON.stringify({ items: [] }), {
      headers: { 'Content-Type': 'application/json' },
    }),
  )
  expect(
    await screen.findByText('No eligible adjustment requests are available.'),
  ).toBeVisible()
})

it('renders eligible evidence and the exact dynamic link', async () => {
  vi.spyOn(globalThis, 'fetch').mockReturnValue(
    response({
      items: [
        {
          audit_recheck_id: '00000000-0000-0000-0000-000000000701',
          sku: { id: 'sku-id', code: 'ADJUST-SKU' },
          location: { id: 'location-id', code: 'BACKROOM' },
          recheck_system_quantity: 10,
          recheck_physical_quantity: 8,
          requested_change: -2,
          rechecked_at: '2026-09-27T09:00:00Z',
        },
      ],
    }),
  )
  render(<EligibleAdjustmentsPage onUnauthorized={() => undefined} />)

  expect(await screen.findByText('ADJUST-SKU')).toBeVisible()
  expect(screen.getByText('BACKROOM')).toBeVisible()
  expect(screen.getByText('-2')).toBeVisible()
  expect(
    screen.getByRole('link', { name: 'Create Adjust Request' }),
  ).toHaveAttribute(
    'href',
    '/adjustments/00000000-0000-0000-0000-000000000701',
  )
})

it('handles backend forbidden, error, and unauthorized responses', async () => {
  const onUnauthorized = vi.fn()
  vi.spyOn(globalThis, 'fetch')
    .mockReturnValueOnce(
      response(
        { error: { code: 'FORBIDDEN', message: 'Access denied.' } },
        403,
      ),
    )
  const forbidden = render(
    <EligibleAdjustmentsPage onUnauthorized={onUnauthorized} />,
  )
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Warehouse Staff role required',
  )
  forbidden.unmount()

  vi.spyOn(globalThis, 'fetch').mockReturnValueOnce(
    response({ error: { code: 'FAILED', message: 'Queue unavailable.' } }, 500),
  )
  const failed = render(
    <EligibleAdjustmentsPage onUnauthorized={onUnauthorized} />,
  )
  expect(await screen.findByRole('alert')).toHaveTextContent('Queue unavailable.')
  failed.unmount()

  vi.spyOn(globalThis, 'fetch').mockReturnValueOnce(
    response({ error: { code: 'UNAUTHORIZED', message: 'Sign in.' } }, 401),
  )
  render(<EligibleAdjustmentsPage onUnauthorized={onUnauthorized} />)
  await vi.waitFor(() => expect(onUnauthorized).toHaveBeenCalledOnce())
})
