import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import PickPage from './PickPage'

const pickId = '00000000-0000-0000-0000-000000000201'
const context = {
  pick_id: pickId,
  warehouse_id: '00000000-0000-0000-0000-000000000001',
  sku_id: '00000000-0000-0000-0000-000000000202',
  sku: 'PICK-SKU',
  requested_quantity: 10,
  outcome: null,
  locations: [
    {
      id: '00000000-0000-0000-0000-000000000205',
      code: 'BACKROOM',
      available_quantity: 8,
    },
    {
      id: '00000000-0000-0000-0000-000000000206',
      code: 'SALES_SHELF',
      available_quantity: 6,
    },
  ],
  warehouse_total: 14,
} as const

function jsonResponse(body: object, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

function result(outcome: 'FULLY_COMPLETED' | 'PARTIAL_INSUFFICIENT') {
  const picked = outcome === 'FULLY_COMPLETED' ? 10 : 6
  return {
    pick_id: pickId,
    sku_id: context.sku_id,
    requested_quantity: 10,
    picked_quantity: picked,
    remaining_quantity: 10 - picked,
    outcome,
    allocations: [],
    confirmed_by_user_id: 'actor-id',
    confirmed_at: '2026-09-22T00:00:00Z',
    warehouse_total: 14 - picked,
  }
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('US-PICK-001 Pick page', () => {
  it('shows source availability and live picked/requested/remaining totals', async () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(jsonResponse(context))
    render(<PickPage pickId={pickId} onUnauthorized={() => undefined} />)

    expect(await screen.findByText('PICK-SKU')).toBeInTheDocument()
    expect(screen.getByText('8 available')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('checkbox', { name: /Backroom/i }))
    fireEvent.change(screen.getByLabelText('Quantity from Backroom'), {
      target: { value: '6' },
    })
    expect(screen.getAllByText('6').length).toBeGreaterThan(0)
    expect(screen.getAllByText('4').length).toBeGreaterThan(0)
  })

  it('posts a full multi-location Pick without a partial gate', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(jsonResponse(context))
      .mockReturnValueOnce(jsonResponse(result('FULLY_COMPLETED'), 201))
    render(<PickPage pickId={pickId} onUnauthorized={() => undefined} />)

    await screen.findByText('PICK-SKU')
    fireEvent.click(screen.getByRole('checkbox', { name: /Backroom/i }))
    fireEvent.change(screen.getByLabelText('Quantity from Backroom'), {
      target: { value: '6' },
    })
    fireEvent.click(screen.getByRole('checkbox', { name: /Sales Shelf/i }))
    fireEvent.change(screen.getByLabelText('Quantity from Sales Shelf'), {
      target: { value: '4' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Review and confirm Pick' }))

    expect(await screen.findByText('Pick fully completed')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toEqual({
      pick_id: pickId,
      allocations: [
        { source_location_id: context.locations[0].id, quantity: 6 },
        { source_location_id: context.locations[1].id, quantity: 4 },
      ],
    })
  })

  it('requires a second explicit action before posting a partial Pick', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(jsonResponse(context))
      .mockReturnValueOnce(jsonResponse(result('PARTIAL_INSUFFICIENT'), 201))
    render(<PickPage pickId={pickId} onUnauthorized={() => undefined} />)

    await screen.findByText('PICK-SKU')
    fireEvent.click(screen.getByRole('checkbox', { name: /Backroom/i }))
    fireEvent.change(screen.getByLabelText('Quantity from Backroom'), {
      target: { value: '6' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Review and confirm Pick' }))

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(
      screen.getByText('Pick is not fully completed. 4 units remain unfulfilled.'),
    ).toBeInTheDocument()
    expect(screen.getAllByText('Requested quantity')).toHaveLength(2)
    fireEvent.click(screen.getByRole('button', { name: 'Confirm partial Pick' }))

    expect(await screen.findByText('Partial Pick recorded')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('keeps entered allocations recoverable after an insufficient-stock conflict', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(jsonResponse(context))
      .mockReturnValueOnce(
        jsonResponse(
          {
            error: {
              code: 'INSUFFICIENT_SOURCE_STOCK',
              message: 'A selected source does not have enough available stock.',
              details: {},
            },
          },
          409,
        ),
      )
    render(<PickPage pickId={pickId} onUnauthorized={() => undefined} />)

    await screen.findByText('PICK-SKU')
    fireEvent.click(screen.getByRole('checkbox', { name: /Backroom/i }))
    fireEvent.change(screen.getByLabelText('Quantity from Backroom'), {
      target: { value: '10' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Review and confirm Pick' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'does not have enough available stock',
    )
    expect(screen.getByLabelText('Quantity from Backroom')).toHaveValue('10')
    expect(screen.queryByText('Pick fully completed')).not.toBeInTheDocument()
  })

  it('returns to authentication after a 401', async () => {
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
    render(<PickPage pickId={pickId} onUnauthorized={unauthorized} />)

    await waitFor(() => expect(unauthorized).toHaveBeenCalledOnce())
  })
})
