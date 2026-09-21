import { afterEach, expect, it, vi } from 'vitest'
import { ApiError, apiRequest, recordReceive, submitPick } from './api'

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

it('sends a typed Receive record command as JSON', async () => {
  const responseBody = {
    receive_id: 'receive-id',
    warehouse_id: 'warehouse-id',
    reference: {
      expected: 'DELIVERY-001',
      document: 'DELIVERY-001',
      match_status: 'REFERENCE_MATCH',
      reviewed_by_user_id: null,
      reviewed_at: null,
    },
    recorded_at: '2026-09-22T00:00:00Z',
    putaway_eligible: true,
    lines: [],
  }
  const fetchMock = vi
    .spyOn(globalThis, 'fetch')
    .mockResolvedValue(
      new Response(JSON.stringify(responseBody), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
  const command = {
    receive_id: 'receive-id',
    document_reference: 'DELIVERY-001',
    lines: [],
  }

  await expect(recordReceive(command)).resolves.toEqual(responseBody)
  expect(fetchMock.mock.calls[0][1]).toMatchObject({
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(command),
  })
})

it('sends Pick allocations without an idempotency or partial-confirmed field', async () => {
  const responseBody = {
    pick_id: 'pick-id',
    sku_id: 'sku-id',
    requested_quantity: 10,
    picked_quantity: 6,
    remaining_quantity: 4,
    outcome: 'PARTIAL_INSUFFICIENT',
    allocations: [],
    confirmed_by_user_id: 'actor-id',
    confirmed_at: '2026-09-22T00:00:00Z',
    warehouse_total: 8,
  }
  const fetchMock = vi
    .spyOn(globalThis, 'fetch')
    .mockResolvedValue(
      new Response(JSON.stringify(responseBody), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
  const allocations = [{ source_location_id: 'location-id', quantity: 6 }]

  await expect(submitPick('pick-id', allocations)).resolves.toEqual(responseBody)
  expect(fetchMock.mock.calls[0][1]).toMatchObject({
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pick_id: 'pick-id', allocations }),
  })
})
