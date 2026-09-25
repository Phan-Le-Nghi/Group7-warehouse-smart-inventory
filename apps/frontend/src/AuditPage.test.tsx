import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import AuditPage from './AuditPage'

const firstSku = '00000000-0000-0000-0000-000000000501'
const secondSku = '00000000-0000-0000-0000-000000000502'
const backroom = '00000000-0000-0000-0000-000000000505'
const shelf = '00000000-0000-0000-0000-000000000506'
const context = {
  warehouse_id: '00000000-0000-0000-0000-000000000001',
  pairs: [
    {
      sku_id: firstSku,
      sku: 'AUDIT-A',
      location_id: backroom,
      location: 'BACKROOM',
      preview_system_quantity: 12,
    },
    {
      sku_id: secondSku,
      sku: 'AUDIT-B',
      location_id: shelf,
      location: 'SALES_SHELF',
      preview_system_quantity: 0,
    },
  ],
} as const

const mismatchResult = {
  audit_id: '00000000-0000-0000-0000-000000000599',
  warehouse_id: context.warehouse_id,
  scope_type: 'SELECTED_PAIRS',
  result: 'MISMATCH',
  status: 'MISMATCH_RECORDED',
  audited_by_user_id: '00000000-0000-0000-0000-000000000590',
  audited_at: '2026-09-26T00:00:00Z',
  lines: [
    {
      sku_id: secondSku,
      location_id: shelf,
      system_quantity: 0,
      physical_quantity: 3,
      quantity_discrepancy: 3,
      result: 'MISMATCH',
    },
  ],
} as const

function jsonResponse(body: object, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

function headerFrom(call: [RequestInfo | URL, RequestInit?]) {
  return (call[1]?.headers as Record<string, string>)['Idempotency-Key']
}

async function selectSecondPair() {
  fireEvent.click(await screen.findByLabelText('Count AUDIT-B at SALES_SHELF'))
  fireEvent.change(
    screen.getByLabelText('Physical quantity for AUDIT-B at SALES_SHELF'),
    { target: { value: '3' } },
  )
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('US-AUD-001 Audit page', () => {
  it('loads selected pairs and previews a discrepancy', async () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(jsonResponse(context))
    render(<AuditPage onUnauthorized={() => undefined} />)
    await selectSecondPair()
    expect(screen.getByText('AUDIT-B')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('submits Whole Warehouse with every pair', async () => {
    const matchResult = {
      ...mismatchResult,
      scope_type: 'WHOLE_WAREHOUSE',
      result: 'MATCH',
      status: 'MATCH_COMPLETED',
      lines: [],
    }
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(jsonResponse(context))
      .mockReturnValueOnce(jsonResponse(matchResult, 201))
    render(<AuditPage onUnauthorized={() => undefined} />)
    fireEvent.click(await screen.findByLabelText('Whole Warehouse'))
    fireEvent.change(
      screen.getByLabelText('Physical quantity for AUDIT-A at BACKROOM'),
      { target: { value: '12' } },
    )
    fireEvent.change(
      screen.getByLabelText('Physical quantity for AUDIT-B at SALES_SHELF'),
      { target: { value: '0' } },
    )
    fireEvent.click(screen.getByRole('button', { name: 'Record Audit' }))
    expect(
      await screen.findByText('All counted quantities match'),
    ).toBeInTheDocument()
    const body = JSON.parse(String(fetchMock.mock.calls[1][1]?.body))
    expect(body.scope_type).toBe('WHOLE_WAREHOUSE')
    expect(body.lines).toHaveLength(2)
  })

  it('reuses a key after response loss and shows stock-unchanged copy', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(jsonResponse(context))
      .mockRejectedValueOnce(new TypeError('Network unavailable'))
      .mockReturnValueOnce(jsonResponse(mismatchResult, 200))
    render(<AuditPage onUnauthorized={() => undefined} />)
    await selectSecondPair()
    fireEvent.click(screen.getByRole('button', { name: 'Record Audit' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Network unavailable')
    fireEvent.click(screen.getByRole('button', { name: 'Record Audit' }))
    expect(await screen.findByText('Discrepancy recorded')).toBeInTheDocument()
    expect(screen.getByText(/Stock was not changed/)).toBeInTheDocument()
    expect(headerFrom(fetchMock.mock.calls[1])).toBe(
      headerFrom(fetchMock.mock.calls[2]),
    )
  })

  it('invalidates the key when the effective command changes', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(jsonResponse(context))
      .mockRejectedValueOnce(new TypeError('Network unavailable'))
      .mockReturnValueOnce(jsonResponse(mismatchResult, 201))
    render(<AuditPage onUnauthorized={() => undefined} />)
    await selectSecondPair()
    fireEvent.click(screen.getByRole('button', { name: 'Record Audit' }))
    await screen.findByRole('alert')
    fireEvent.change(
      screen.getByLabelText('Physical quantity for AUDIT-B at SALES_SHELF'),
      { target: { value: '4' } },
    )
    fireEvent.click(screen.getByRole('button', { name: 'Record Audit' }))
    await screen.findByText('Discrepancy recorded')
    expect(headerFrom(fetchMock.mock.calls[1])).not.toBe(
      headerFrom(fetchMock.mock.calls[2]),
    )
  })

  it('preserves input on scope conflict and reloads explicitly', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(jsonResponse(context))
      .mockReturnValueOnce(
        jsonResponse(
          {
            error: {
              code: 'AUDIT_SCOPE_CHANGED',
              message: 'The Whole Warehouse Audit scope has changed.',
            },
          },
          409,
        ),
      )
      .mockReturnValueOnce(jsonResponse(context))
    render(<AuditPage onUnauthorized={() => undefined} />)
    fireEvent.click(await screen.findByLabelText('Whole Warehouse'))
    const firstInput = screen.getByLabelText(
      'Physical quantity for AUDIT-A at BACKROOM',
    )
    fireEvent.change(firstInput, { target: { value: '12' } })
    fireEvent.change(
      screen.getByLabelText('Physical quantity for AUDIT-B at SALES_SHELF'),
      { target: { value: '0' } },
    )
    fireEvent.click(screen.getByRole('button', { name: 'Record Audit' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('scope has changed')
    expect(firstInput).toHaveValue('12')
    fireEvent.click(
      screen.getByRole('button', { name: 'Reload and reconcile scope' }),
    )
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3))
    expect(firstInput).toHaveValue('12')
  })

  it('handles authentication and forbidden context errors', async () => {
    const unauthorized = vi.fn()
    vi.spyOn(globalThis, 'fetch').mockReturnValueOnce(
      jsonResponse(
        { error: { code: 'AUTHENTICATION_REQUIRED', message: 'Sign in.' } },
        401,
      ),
    )
    const first = render(<AuditPage onUnauthorized={unauthorized} />)
    await waitFor(() => expect(unauthorized).toHaveBeenCalledOnce())
    first.unmount()

    vi.restoreAllMocks()
    vi.spyOn(globalThis, 'fetch').mockReturnValueOnce(
      jsonResponse(
        { error: { code: 'FORBIDDEN', message: 'Access denied.' } },
        403,
      ),
    )
    render(<AuditPage onUnauthorized={() => undefined} />)
    expect(
      await screen.findByRole('heading', { name: 'Warehouse Staff role required' }),
    ).toBeInTheDocument()
  })
})
