import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import AdjustmentPage from './AdjustmentPage'

const recheckId = '00000000-0000-0000-0000-000000000701'
const context = {
  audit_recheck_id: recheckId,
  warehouse_id: '00000000-0000-0000-0000-000000000001',
  sku: { id: '00000000-0000-0000-0000-000000000501', code: 'AUDIT-SKU' },
  location: {
    id: '00000000-0000-0000-0000-000000000005',
    code: 'BACKROOM',
  },
  original_audit: {
    audit_id: '00000000-0000-0000-0000-000000000600',
    audit_line_id: '00000000-0000-0000-0000-000000000601',
    system_quantity: 12,
    physical_quantity: 10,
    quantity_discrepancy: -2,
  },
  recheck: {
    recheck_system_quantity: 10,
    recheck_physical_quantity: 8,
    recheck_quantity_discrepancy: -2,
    result: 'MISMATCH',
    performed_at: '2026-09-27T08:00:00Z',
  },
  requested_change: -2,
  existing_adjustment: null,
} as const

const result = {
  adjustment_id: '00000000-0000-0000-0000-000000000801',
  audit_recheck_id: recheckId,
  warehouse_id: context.warehouse_id,
  sku: context.sku,
  location: context.location,
  recheck_system_quantity_snapshot: 10,
  recheck_physical_quantity_snapshot: 8,
  requested_change: -2,
  reason: 'Count confirmed',
  status: 'PENDING_MANAGER_DECISION',
  requested_by: {
    user_id: '00000000-0000-0000-0000-000000000901',
    login_identifier: 'adjust.staff',
  },
  requested_at: '2026-09-27T09:00:00Z',
} as const

function jsonResponse(body: object, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

function keyFrom(call: [RequestInfo | URL, RequestInit?]) {
  return (call[1]?.headers as Record<string, string>)['Idempotency-Key']
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('US-ADJ-001 Warehouse Staff Adjust page', () => {
  it('renders loading and immutable eligible evidence', async () => {
    let resolveContext: ((value: Response) => void) | undefined
    vi.spyOn(globalThis, 'fetch').mockReturnValue(
      new Promise((resolve) => {
        resolveContext = resolve
      }),
    )
    render(
      <AdjustmentPage
        auditRecheckId={recheckId}
        onUnauthorized={() => undefined}
      />,
    )
    expect(screen.getByRole('status')).toHaveTextContent('Loading Adjust context')
    resolveContext?.(
      new Response(JSON.stringify(context), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    expect(await screen.findByText('ORIGINAL AUDIT')).toBeVisible()
    expect(screen.getByText('MANAGER RECHECK')).toBeVisible()
    expect(screen.getByTestId('requested-change')).toHaveTextContent('-2')
    expect(screen.queryByLabelText(/quantity/i)).toBeNull()
    expect(screen.getByText(/Stock remains unchanged/)).toBeVisible()
  })

  it('validates normalized reason and renders success', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(jsonResponse(context))
      .mockReturnValueOnce(jsonResponse(result, 201))
    render(
      <AdjustmentPage
        auditRecheckId={recheckId}
        onUnauthorized={() => undefined}
      />,
    )
    const reason = await screen.findByLabelText('Reason')
    const submit = screen.getByRole('button', { name: 'Create Adjust request' })
    fireEvent.change(reason, { target: { value: '   ' } })
    fireEvent.click(submit)
    expect(await screen.findByRole('alert')).toHaveTextContent('Reason is required')
    expect(fetchMock).toHaveBeenCalledTimes(1)

    fireEvent.change(reason, { target: { value: ` ${'x'.repeat(501)} ` } })
    fireEvent.click(submit)
    expect(await screen.findByRole('alert')).toHaveTextContent('500 characters')
    expect(fetchMock).toHaveBeenCalledTimes(1)

    fireEvent.change(reason, { target: { value: '  Count confirmed  ' } })
    fireEvent.click(submit)
    expect(
      await screen.findByRole('heading', { name: 'PENDING_MANAGER_DECISION' }),
    ).toBeVisible()
    const body = JSON.parse(fetchMock.mock.calls[1][1]?.body as string)
    expect(body).toEqual({
      audit_recheck_id: recheckId,
      reason: 'Count confirmed',
    })
    expect(screen.getByText(/Stock was not changed/)).toBeVisible()
  })

  it('reuses a key for an unchanged retry and invalidates it after editing', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(jsonResponse(context))
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockRejectedValueOnce(new TypeError('Failed again'))
      .mockReturnValueOnce(jsonResponse({ ...result, reason: 'Edited reason' }, 201))
    render(
      <AdjustmentPage
        auditRecheckId={recheckId}
        onUnauthorized={() => undefined}
      />,
    )
    const reason = await screen.findByLabelText('Reason')
    const submit = screen.getByRole('button', { name: 'Create Adjust request' })
    fireEvent.change(reason, { target: { value: 'Count confirmed' } })
    fireEvent.click(submit)
    await screen.findByText('Failed to fetch')
    fireEvent.click(submit)
    await screen.findByText('Failed again')
    expect(keyFrom(fetchMock.mock.calls[1])).toBe(keyFrom(fetchMock.mock.calls[2]))

    fireEvent.change(reason, { target: { value: 'Edited reason' } })
    fireEvent.click(submit)
    await screen.findByRole('heading', { name: 'PENDING_MANAGER_DECISION' })
    expect(keyFrom(fetchMock.mock.calls[3])).not.toBe(
      keyFrom(fetchMock.mock.calls[2]),
    )
  })

  it('refetches an existing request after a duplicate race', async () => {
    const existing = {
      ...context,
      existing_adjustment: {
        adjustment_id: result.adjustment_id,
        reason: result.reason,
        requested_change: result.requested_change,
        status: result.status,
        requested_by: result.requested_by,
        requested_at: result.requested_at,
      },
    }
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(jsonResponse(context))
      .mockReturnValueOnce(
        jsonResponse(
          {
            error: {
              code: 'ADJUSTMENT_ALREADY_EXISTS',
              message: 'Already exists.',
            },
          },
          409,
        ),
      )
      .mockReturnValueOnce(jsonResponse(existing))
    render(
      <AdjustmentPage
        auditRecheckId={recheckId}
        onUnauthorized={() => undefined}
      />,
    )
    fireEvent.change(await screen.findByLabelText('Reason'), {
      target: { value: 'Count confirmed' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Create Adjust request' }))
    expect(
      await screen.findByRole('heading', { name: 'PENDING_MANAGER_DECISION' }),
    ).toBeVisible()
    expect(
      fetchMock.mock.calls.filter((call) => call[1]?.method === 'POST'),
    ).toHaveLength(1)
  })

  it('renders existing, forbidden, ineligible, and auth recovery states', async () => {
    const existing = {
      ...context,
      existing_adjustment: {
        adjustment_id: result.adjustment_id,
        reason: result.reason,
        requested_change: result.requested_change,
        status: result.status,
        requested_by: result.requested_by,
        requested_at: result.requested_at,
      },
    }
    vi.spyOn(globalThis, 'fetch').mockReturnValue(jsonResponse(existing))
    render(
      <AdjustmentPage
        auditRecheckId={recheckId}
        onUnauthorized={() => undefined}
      />,
    )
    expect(
      await screen.findByRole('heading', { name: 'PENDING_MANAGER_DECISION' }),
    ).toBeVisible()
    cleanup()
    vi.restoreAllMocks()

    vi.spyOn(globalThis, 'fetch').mockReturnValue(
      jsonResponse({ error: { code: 'FORBIDDEN', message: 'Forbidden.' } }, 403),
    )
    render(
      <AdjustmentPage
        auditRecheckId={recheckId}
        onUnauthorized={() => undefined}
      />,
    )
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Warehouse Staff role required',
    )
    cleanup()
    vi.restoreAllMocks()

    vi.spyOn(globalThis, 'fetch').mockReturnValue(
      jsonResponse(
        { error: { code: 'ADJUSTMENT_NOT_ELIGIBLE', message: 'No.' } },
        409,
      ),
    )
    render(
      <AdjustmentPage
        auditRecheckId={recheckId}
        onUnauthorized={() => undefined}
      />,
    )
    expect(await screen.findByRole('alert')).toHaveTextContent('not eligible')
    cleanup()
    vi.restoreAllMocks()

    const onUnauthorized = vi.fn()
    vi.spyOn(globalThis, 'fetch').mockReturnValue(
      jsonResponse(
        { error: { code: 'AUTHENTICATION_REQUIRED', message: 'Sign in.' } },
        401,
      ),
    )
    render(
      <AdjustmentPage
        auditRecheckId={recheckId}
        onUnauthorized={onUnauthorized}
      />,
    )
    await waitFor(() => expect(onUnauthorized).toHaveBeenCalled())
  })
})
