import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import AuditDiscrepancyPage from './AuditDiscrepancyPage'

const lineId = '00000000-0000-0000-0000-000000000601'
const detail = {
  audit_id: '00000000-0000-0000-0000-000000000600',
  audit_line_id: lineId,
  warehouse_id: '00000000-0000-0000-0000-000000000001',
  sku: { id: '00000000-0000-0000-0000-000000000501', code: 'AUDIT-SKU' },
  location: {
    id: '00000000-0000-0000-0000-000000000005',
    code: 'BACKROOM',
  },
  original: {
    system_quantity: 12,
    physical_quantity: 10,
    quantity_discrepancy: -2,
    result: 'MISMATCH',
    audited_by: {
      user_id: '00000000-0000-0000-0000-000000000590',
      login_identifier: 'audit.staff',
    },
    audited_at: '2026-09-26T08:00:00Z',
  },
  recheck: null,
  adjust_eligible: false,
} as const

const mismatchResult = {
  recheck_id: '00000000-0000-0000-0000-000000000701',
  audit_line_id: lineId,
  recheck_system_quantity: 11,
  recheck_physical_quantity: 9,
  recheck_quantity_discrepancy: -2,
  result: 'MISMATCH',
  performed_by: {
    user_id: '00000000-0000-0000-0000-000000000591',
    login_identifier: 'audit.manager',
  },
  performed_at: '2026-09-26T09:00:00Z',
  adjust_eligible: true,
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

async function openDetail() {
  fireEvent.click(
    await screen.findByRole('button', {
      name: 'Review AUDIT-SKU at BACKROOM',
    }),
  )
  await screen.findByRole('heading', { name: 'Physical recheck' })
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('US-AUD-002 Manager discrepancy page', () => {
  it('renders loading, empty, and backend forbidden states', async () => {
    let resolveList: ((value: Response) => void) | undefined
    vi.spyOn(globalThis, 'fetch').mockReturnValue(
      new Promise((resolve) => {
        resolveList = resolve
      }),
    )
    const view = render(
      <AuditDiscrepancyPage onUnauthorized={() => undefined} />,
    )
    expect(screen.getByRole('status')).toHaveTextContent(
      'Loading Audit discrepancies',
    )
    resolveList?.(
      new Response(JSON.stringify({ items: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    expect(
      await screen.findByText('No Audit discrepancies require review.'),
    ).toBeInTheDocument()

    view.unmount()
    vi.restoreAllMocks()
    vi.spyOn(globalThis, 'fetch').mockReturnValue(
      jsonResponse(
        { error: { code: 'FORBIDDEN', message: 'Access denied.' } },
        403,
      ),
    )
    render(<AuditDiscrepancyPage onUnauthorized={() => undefined} />)
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Manager role required',
    )
  })

  it('loads list and detail with visibly separated evidence', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(jsonResponse({ items: [detail] }))
      .mockReturnValueOnce(jsonResponse(detail))
    render(<AuditDiscrepancyPage onUnauthorized={() => undefined} />)
    await openDetail()
    expect(screen.getByText('ORIGINAL AUDIT')).toBeInTheDocument()
    expect(screen.getByText('MANAGER RECHECK')).toBeInTheDocument()
    expect(screen.getByText('audit.staff')).toBeInTheDocument()
    expect(screen.getByText(/Original Audit evidence is immutable/)).toBeVisible()
  })

  it('validates strict integer input and renders a mismatch result', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(jsonResponse({ items: [detail] }))
      .mockReturnValueOnce(jsonResponse(detail))
      .mockReturnValueOnce(jsonResponse(mismatchResult, 201))
    render(<AuditDiscrepancyPage onUnauthorized={() => undefined} />)
    await openDetail()
    const input = screen.getByLabelText('Recheck physical quantity')
    fireEvent.change(input, { target: { value: '1.5' } })
    fireEvent.click(screen.getByRole('button', { name: 'Record Manager recheck' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'non-negative integer',
    )
    expect(fetchMock).toHaveBeenCalledTimes(2)

    fireEvent.change(input, { target: { value: '9' } })
    fireEvent.click(screen.getByRole('button', { name: 'Record Manager recheck' }))
    expect(await screen.findByRole('heading', { name: 'MISMATCH' })).toBeVisible()
    expect(screen.getByText(/Stock was not changed/)).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Record Manager recheck' })).toBeNull()
  })

  it('renders an existing matching recheck as read-only', async () => {
    const matching = {
      ...detail,
      recheck: {
        recheck_id: mismatchResult.recheck_id,
        recheck_system_quantity: 11,
        recheck_physical_quantity: 11,
        recheck_quantity_discrepancy: 0,
        result: 'MATCH',
        performed_by: mismatchResult.performed_by,
        performed_at: mismatchResult.performed_at,
      },
      adjust_eligible: false,
    } as const
    vi.spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(jsonResponse({ items: [matching] }))
      .mockReturnValueOnce(jsonResponse(matching))
    render(<AuditDiscrepancyPage onUnauthorized={() => undefined} />)
    await openDetail()
    expect(screen.getByRole('heading', { name: 'MATCH' })).toBeVisible()
    expect(screen.queryByLabelText('Recheck physical quantity')).toBeNull()
    expect(screen.queryByText(/eligible context for future Adjust work/)).toBeNull()
  })

  it('reuses a key after response loss and changes it after input edit', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(jsonResponse({ items: [detail] }))
      .mockReturnValueOnce(jsonResponse(detail))
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockRejectedValueOnce(new TypeError('Failed again'))
      .mockReturnValueOnce(jsonResponse(mismatchResult, 201))
    render(<AuditDiscrepancyPage onUnauthorized={() => undefined} />)
    await openDetail()
    const input = screen.getByLabelText('Recheck physical quantity')
    const submit = screen.getByRole('button', { name: 'Record Manager recheck' })
    fireEvent.change(input, { target: { value: '9' } })
    fireEvent.click(submit)
    await screen.findByText('Failed to fetch')
    fireEvent.click(submit)
    await screen.findByText('Failed again')
    expect(keyFrom(fetchMock.mock.calls[2])).toBe(keyFrom(fetchMock.mock.calls[3]))

    fireEvent.change(input, { target: { value: '8' } })
    fireEvent.click(submit)
    await screen.findByRole('heading', { name: 'MISMATCH' })
    expect(keyFrom(fetchMock.mock.calls[4])).not.toBe(
      keyFrom(fetchMock.mock.calls[3]),
    )
  })

  it('refetches read-only detail without retrying a recorded race', async () => {
    const persisted = {
      ...detail,
      recheck: {
        recheck_id: mismatchResult.recheck_id,
        recheck_system_quantity: mismatchResult.recheck_system_quantity,
        recheck_physical_quantity: mismatchResult.recheck_physical_quantity,
        recheck_quantity_discrepancy:
          mismatchResult.recheck_quantity_discrepancy,
        result: mismatchResult.result,
        performed_by: mismatchResult.performed_by,
        performed_at: mismatchResult.performed_at,
      },
      adjust_eligible: true,
    }
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(jsonResponse({ items: [detail] }))
      .mockReturnValueOnce(jsonResponse(detail))
      .mockReturnValueOnce(
        jsonResponse(
          {
            error: {
              code: 'RECHECK_ALREADY_RECORDED',
              message: 'Already recorded.',
            },
          },
          409,
        ),
      )
      .mockReturnValueOnce(jsonResponse(persisted))
    render(<AuditDiscrepancyPage onUnauthorized={() => undefined} />)
    await openDetail()
    fireEvent.change(screen.getByLabelText('Recheck physical quantity'), {
      target: { value: '9' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Record Manager recheck' }))
    expect(
      await screen.findByText(/Another request recorded this recheck first/),
    ).toBeVisible()
    const postCalls = fetchMock.mock.calls.filter(
      (call) => call[1]?.method === 'POST',
    )
    expect(postCalls).toHaveLength(1)
  })

  it('uses auth recovery for a 401', async () => {
    const onUnauthorized = vi.fn()
    vi.spyOn(globalThis, 'fetch').mockReturnValue(
      jsonResponse(
        { error: { code: 'AUTHENTICATION_REQUIRED', message: 'Sign in.' } },
        401,
      ),
    )
    render(<AuditDiscrepancyPage onUnauthorized={onUnauthorized} />)
    await waitFor(() => expect(onUnauthorized).toHaveBeenCalledTimes(1))
  })
})
