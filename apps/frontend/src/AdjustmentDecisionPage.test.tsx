import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import AdjustmentDecisionPage from './AdjustmentDecisionPage'

const adjustmentId = '00000000-0000-0000-0000-000000000801'
const queueItem = {
  adjustment_id: adjustmentId,
  status: 'PENDING_MANAGER_DECISION',
  requested_by: { user_id: 'staff-id', login_identifier: 'adjust.staff' },
  requested_at: '2026-09-28T08:00:00Z',
  reason: 'Count confirmed',
  sku: { id: 'sku-id', code: 'ADJUST-SKU' },
  location: { id: 'location-id', code: 'BACKROOM' },
  requested_change: -2,
} as const

const detail = {
  ...queueItem,
  audit_recheck_id: 'recheck-id',
  warehouse_id: 'warehouse-id',
  original_audit: {
    audit_id: 'audit-id',
    audit_line_id: 'line-id',
    system_quantity: 12,
    physical_quantity: 10,
    quantity_discrepancy: -2,
    result: 'MISMATCH',
    audited_by: { user_id: 'staff-id', login_identifier: 'audit.staff' },
    audited_at: '2026-09-28T07:00:00Z',
  },
  manager_recheck: {
    recheck_id: 'recheck-id',
    recheck_system_quantity: 10,
    recheck_physical_quantity: 8,
    recheck_quantity_discrepancy: -2,
    result: 'MISMATCH',
    performed_by: { user_id: 'manager-id', login_identifier: 'audit.manager' },
    performed_at: '2026-09-28T07:30:00Z',
  },
  recheck_system_quantity_snapshot: 10,
  recheck_physical_quantity_snapshot: 8,
  decided_by: null,
  decided_at: null,
  rejection_reason: null,
  applied_stock_before: null,
  applied_stock_after: null,
} as const

function response(body: object, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

async function openDetail() {
  fireEvent.click(
    await screen.findByRole('button', { name: 'Review ADJUST-SKU at BACKROOM' }),
  )
  await screen.findByRole('heading', { name: 'PENDING_MANAGER_DECISION' })
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  window.history.replaceState({}, '', '/')
})

describe('US-ADJ-002 Manager decision page', () => {
  it('renders empty and forbidden queue states', async () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValueOnce(response({ items: [] }))
    const view = render(
      <AdjustmentDecisionPage onUnauthorized={() => undefined} />,
    )
    expect(await screen.findByText('No pending Adjust requests.')).toBeVisible()
    view.unmount()
    vi.restoreAllMocks()
    vi.spyOn(globalThis, 'fetch').mockReturnValueOnce(
      response({ error: { code: 'FORBIDDEN', message: 'Denied.' } }, 403),
    )
    render(<AdjustmentDecisionPage onUnauthorized={() => undefined} />)
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Manager role required',
    )
  })

  it('loads queue/detail and approves without quantity controls', async () => {
    const applied = {
      ...detail,
      status: 'APPLIED',
      decided_by: { user_id: 'manager-id', login_identifier: 'manager' },
      decided_at: '2026-09-28T09:00:00Z',
      applied_stock_before: 10,
      applied_stock_after: 8,
    } as const
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(response({ items: [queueItem] }))
      .mockReturnValueOnce(response(detail))
      .mockReturnValueOnce(response(applied))
    render(<AdjustmentDecisionPage onUnauthorized={() => undefined} />)
    await openDetail()
    expect(screen.getByText('ORIGINAL AUDIT')).toBeVisible()
    expect(screen.getByText('MANAGER RECHECK')).toBeVisible()
    expect(screen.queryByLabelText(/quantity/i)).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirm approval' }))
    expect(await screen.findByRole('heading', { name: 'APPLIED' })).toBeVisible()
    expect(screen.getByText(/Before: 10 · After: 8/)).toBeVisible()
    expect(fetchMock.mock.calls[2][1]?.body).toBe('{"decision":"APPROVE"}')
  })

  it('requires a rejection reason and reuses the key for unchanged retry', async () => {
    const rejected = {
      ...detail,
      status: 'REJECTED',
      decided_by: { user_id: 'manager-id', login_identifier: 'manager' },
      decided_at: '2026-09-28T09:00:00Z',
      rejection_reason: 'Evidence rejected',
    } as const
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(response({ items: [queueItem] }))
      .mockReturnValueOnce(response(detail))
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockReturnValueOnce(response(rejected))
    render(<AdjustmentDecisionPage onUnauthorized={() => undefined} />)
    await openDetail()
    fireEvent.click(screen.getByRole('button', { name: 'Reject' }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirm rejection' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Rejection reason')
    fireEvent.change(screen.getByLabelText('Rejection reason'), {
      target: { value: ' Evidence rejected ' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Confirm rejection' }))
    await screen.findByText('Failed to fetch')
    fireEvent.click(screen.getByRole('button', { name: 'Confirm rejection' }))
    expect(await screen.findByRole('heading', { name: 'REJECTED' })).toBeVisible()
    const firstHeaders = fetchMock.mock.calls[2][1]?.headers as Record<string, string>
    const retryHeaders = fetchMock.mock.calls[3][1]?.headers as Record<string, string>
    expect(retryHeaders['Idempotency-Key']).toBe(firstHeaders['Idempotency-Key'])
  })
})
