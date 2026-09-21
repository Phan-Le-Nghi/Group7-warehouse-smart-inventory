import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ReceivePage from './ReceivePage'

const receiveId = '00000000-0000-0000-0000-000000000103'
const lineId = '00000000-0000-0000-0000-000000000104'
const context = {
  receive_id: receiveId,
  warehouse_id: '00000000-0000-0000-0000-000000000101',
  reference: {
    expected: 'DELIVERY-001',
    document: null,
    match_status: null,
    reviewed_by_user_id: null,
    reviewed_at: null,
  },
  recorded_at: null,
  putaway_eligible: false,
  lines: [
    {
      receive_line_id: lineId,
      sku_id: '00000000-0000-0000-0000-000000000102',
      sku: 'REC-SKU-001',
      expected_quantity: 16,
      actual_quantity: null,
      quantity_discrepancy: null,
    },
  ],
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

describe('US-REC-001 Receive', () => {
  it('loads prepared expected context and previews a signed discrepancy', async () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(jsonResponse(context))
    render(<ReceivePage receiveId={receiveId} onUnauthorized={() => undefined} />)

    expect(await screen.findByText('DELIVERY-001')).toBeInTheDocument()
    expect(screen.getByText('REC-SKU-001')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Actual quantity'), {
      target: { value: '14' },
    })
    expect(screen.getByText('-2')).toBeInTheDocument()
  })

  it('validates required input and retains entered values', async () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(jsonResponse(context))
    render(<ReceivePage receiveId={receiveId} onUnauthorized={() => undefined} />)
    await screen.findByText('REC-SKU-001')
    fireEvent.change(screen.getByLabelText('Actual quantity'), {
      target: { value: 'bad' },
    })

    fireEvent.click(screen.getByRole('button', { name: 'Record Receive' }))

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Check the highlighted Receive fields.',
    )
    expect(screen.getByText('Document reference is required.')).toBeInTheDocument()
    expect(screen.getByLabelText(/Actual quantity/)).toHaveValue('bad')
    expect(globalThis.fetch).toHaveBeenCalledTimes(1)
  })

  it('records matching facts and reports Putaway eligibility', async () => {
    const recorded = {
      ...context,
      recorded_at: '2026-09-22T00:00:00Z',
      putaway_eligible: true,
      reference: {
        ...context.reference,
        document: 'DELIVERY-001',
        match_status: 'REFERENCE_MATCH',
      },
      lines: [
        {
          ...context.lines[0],
          actual_quantity: 16,
          quantity_discrepancy: 0,
        },
      ],
    }
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(jsonResponse(context))
      .mockReturnValueOnce(jsonResponse(recorded, 201))
    render(<ReceivePage receiveId={receiveId} onUnauthorized={() => undefined} />)
    fireEvent.change(await screen.findByLabelText('Document reference'), {
      target: { value: 'DELIVERY-001' },
    })
    fireEvent.change(screen.getByLabelText('Actual quantity'), {
      target: { value: '16' },
    })

    fireEvent.click(screen.getByRole('button', { name: 'Record Receive' }))

    expect(await screen.findByText('Receive recorded')).toBeInTheDocument()
    expect(
      screen.getByText('References match. This Receive is eligible for Putaway.'),
    ).toBeInTheDocument()
    expect(fetchMock.mock.calls[1][0]).toContain('/api/v1/receives')
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: 'POST' })
  })

  it('shows mismatch review and records acknowledgement without authority copy', async () => {
    const mismatch = {
      ...context,
      recorded_at: '2026-09-22T00:00:00Z',
      reference: {
        ...context.reference,
        document: 'DELIVERY-OTHER',
        match_status: 'REFERENCE_MISMATCH',
      },
      lines: [
        {
          ...context.lines[0],
          actual_quantity: 14,
          quantity_discrepancy: -2,
        },
      ],
    }
    vi.spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(jsonResponse(mismatch))
      .mockReturnValueOnce(
        jsonResponse({
          receive_id: receiveId,
          match_status: 'REFERENCE_MISMATCH',
          reviewed_by_user_id: 'staff-user-id',
          reviewed_at: '2026-09-22T01:00:00Z',
          putaway_eligible: true,
        }),
      )
    render(<ReceivePage receiveId={receiveId} onUnauthorized={() => undefined} />)

    expect(await screen.findByText('Review required')).toBeInTheDocument()
    expect(screen.getByText('DELIVERY-001')).toBeInTheDocument()
    expect(screen.getByText('DELIVERY-OTHER')).toBeInTheDocument()
    expect(screen.queryByText(/authoritative/i)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Acknowledge mismatch' }))

    expect(
      await screen.findByText(/Mismatch acknowledged by staff-user-id/),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Acknowledge mismatch' }),
    ).not.toBeInTheDocument()
  })

  it('resets authentication after a 401 while loading', async () => {
    const unauthorized = vi.fn()
    vi.spyOn(globalThis, 'fetch').mockReturnValue(
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

    render(<ReceivePage receiveId={receiveId} onUnauthorized={unauthorized} />)

    await waitFor(() => expect(unauthorized).toHaveBeenCalledOnce())
  })

  it('shows an API error and does not report success', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(jsonResponse(context))
      .mockReturnValueOnce(
        jsonResponse(
          {
            error: {
              code: 'RECEIVE_ALREADY_RECORDED',
              message: 'Receive facts have already been recorded.',
              details: {},
            },
          },
          409,
        ),
      )
    render(<ReceivePage receiveId={receiveId} onUnauthorized={() => undefined} />)
    fireEvent.change(await screen.findByLabelText('Document reference'), {
      target: { value: 'DELIVERY-001' },
    })
    fireEvent.change(screen.getByLabelText('Actual quantity'), {
      target: { value: '16' },
    })

    fireEvent.click(screen.getByRole('button', { name: 'Record Receive' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Receive facts have already been recorded.',
    )
    expect(screen.queryByText('Receive recorded')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Actual quantity')).toHaveValue('16')
  })
})
