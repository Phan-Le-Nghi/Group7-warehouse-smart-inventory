import { afterEach, expect, it, vi } from 'vitest'
import {
  ApiError,
  apiRequest,
  loadTransferHistory,
  recordReceive,
  submitAudit,
  submitPick,
  submitTransfer,
} from './api'

afterEach(() => {
  vi.restoreAllMocks()
})

it.each([200, 201])('accepts a %s Audit result with its opaque key', async (status) => {
  const responseBody = {
    audit_id: 'audit-id',
    warehouse_id: 'warehouse-id',
    scope_type: 'SELECTED_PAIRS',
    result: 'MATCH',
    status: 'MATCH_COMPLETED',
    audited_by_user_id: 'actor-id',
    audited_at: '2026-09-26T00:00:00Z',
    lines: [],
  }
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify(responseBody), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
  const command = {
    scope_type: 'SELECTED_PAIRS' as const,
    lines: [
      { sku_id: 'sku-id', location_id: 'location-id', physical_quantity: 0 },
    ],
  }
  await expect(submitAudit(command, 'Audit-Key')).resolves.toEqual(responseBody)
  expect(fetchMock.mock.calls[0][1]).toMatchObject({
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': 'Audit-Key',
    },
    body: JSON.stringify(command),
  })
})

it('loads Transfer history with a bodyless GET and no client Warehouse scope', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify({ items: [] }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }),
  )

  await expect(loadTransferHistory()).resolves.toEqual({ items: [] })
  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringMatching(/\/api\/v1\/transfers$/),
    { credentials: 'include' },
  )
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

it.each([200, 201])('accepts a %s Transfer result with its idempotency key', async (status) => {
  const responseBody = {
    transfer_id: 'transfer-id',
    warehouse_id: 'warehouse-id',
    sku_id: 'sku-id',
    quantity: 4,
    source_location_id: 'source-id',
    source_location: 'BACKROOM',
    destination_location_id: 'destination-id',
    destination_location: 'SALES_SHELF',
    transferred_by_user_id: 'actor-id',
    transferred_at: '2026-09-25T00:00:00Z',
    stock: { source_quantity: 8, destination_quantity: 10, warehouse_total: 18 },
  }
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify(responseBody), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
  const command = {
    sku_id: 'sku-id',
    source_location_id: 'source-id',
    destination_location_id: 'destination-id',
    quantity: 4,
  }
  await expect(submitTransfer(command, 'opaque-Key')).resolves.toEqual(responseBody)
  expect(fetchMock.mock.calls[0][1]).toMatchObject({
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': 'opaque-Key',
    },
    body: JSON.stringify(command),
  })
})
