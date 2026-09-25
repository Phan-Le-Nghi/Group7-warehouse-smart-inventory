import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import TransferPage from './TransferPage'

const skuId = '00000000-0000-0000-0000-000000000302'
const sourceId = '00000000-0000-0000-0000-000000000305'
const destinationId = '00000000-0000-0000-0000-000000000306'
const context = {
  warehouse_id: '00000000-0000-0000-0000-000000000001',
  sku_id: skuId,
  sku: 'TRANSFER-SKU',
  locations: [
    { id: sourceId, code: 'BACKROOM', available_quantity: 12 },
    { id: destinationId, code: 'SALES_SHELF', available_quantity: 6 },
  ],
  warehouse_total: 18,
} as const

const result = {
  transfer_id: '00000000-0000-0000-0000-000000000399',
  warehouse_id: context.warehouse_id,
  sku_id: skuId,
  quantity: 4,
  source_location_id: sourceId,
  source_location: 'BACKROOM',
  destination_location_id: destinationId,
  destination_location: 'SALES_SHELF',
  transferred_by_user_id: '00000000-0000-0000-0000-000000000390',
  transferred_at: '2026-09-25T00:00:00Z',
  stock: { source_quantity: 8, destination_quantity: 10, warehouse_total: 18 },
}

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

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('US-TRF-001 Transfer page', () => {
  it('shows availability and validates different locations and quantity', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockReturnValue(jsonResponse(context))
    render(<TransferPage skuId={skuId} onUnauthorized={() => undefined} />)
    expect(await screen.findByText('TRANSFER-SKU')).toBeInTheDocument()
    expect(screen.getByText('Available: 12')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Destination location'), {
      target: { value: sourceId },
    })
    fireEvent.change(screen.getByLabelText('Quantity'), { target: { value: '0' } })
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Transfer' }))
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Source and destination locations must be different.',
    )
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('reuses a key after a network failure for the same command', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(jsonResponse(context))
      .mockRejectedValueOnce(new TypeError('Network unavailable'))
      .mockReturnValueOnce(jsonResponse(result, 200))
    render(<TransferPage skuId={skuId} onUnauthorized={() => undefined} />)
    await screen.findByText('TRANSFER-SKU')
    fireEvent.change(screen.getByLabelText('Quantity'), { target: { value: '4' } })
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Transfer' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Network unavailable')
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Transfer' }))

    expect(await screen.findByText('Transfer confirmed')).toBeInTheDocument()
    expect(headerFrom(fetchMock.mock.calls[1])).toBe(
      headerFrom(fetchMock.mock.calls[2]),
    )
  })

  it('generates a new key after the command is edited', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(jsonResponse(context))
      .mockRejectedValueOnce(new TypeError('Network unavailable'))
      .mockReturnValueOnce(jsonResponse({ ...result, quantity: 3 }, 201))
    render(<TransferPage skuId={skuId} onUnauthorized={() => undefined} />)
    await screen.findByText('TRANSFER-SKU')
    fireEvent.change(screen.getByLabelText('Quantity'), { target: { value: '4' } })
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Transfer' }))
    await screen.findByRole('alert')
    fireEvent.change(screen.getByLabelText('Quantity'), { target: { value: '3' } })
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Transfer' }))

    await screen.findByText('Transfer confirmed')
    expect(headerFrom(fetchMock.mock.calls[1])).not.toBe(
      headerFrom(fetchMock.mock.calls[2]),
    )
  })

  it('keeps a stale command recoverable without claiming success', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(jsonResponse(context))
      .mockReturnValueOnce(
        jsonResponse(
          {
            error: {
              code: 'INSUFFICIENT_SOURCE_STOCK',
              message: 'The source does not have enough available stock.',
              details: {},
            },
          },
          409,
        ),
      )
    render(<TransferPage skuId={skuId} onUnauthorized={() => undefined} />)
    await screen.findByText('TRANSFER-SKU')
    fireEvent.change(screen.getByLabelText('Quantity'), { target: { value: '12' } })
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Transfer' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'does not have enough available stock',
    )
    expect(screen.getByLabelText('Quantity')).toHaveValue('12')
    expect(screen.queryByText('Transfer confirmed')).not.toBeInTheDocument()
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
    render(<TransferPage skuId={skuId} onUnauthorized={unauthorized} />)
    await waitFor(() => expect(unauthorized).toHaveBeenCalledOnce())
  })
})
