import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

const receiveLineId = '00000000-0000-0000-0000-000000000004'
const context = {
  receive_line_id: receiveLineId,
  sku_id: '00000000-0000-0000-0000-000000000002',
  sku: 'SKU-001',
  actual_quantity: 16,
  confirmed_quantity: 0,
  eligible_quantity: 16,
  locations: [
    { id: 'backroom-id', code: 'BACKROOM' },
    { id: 'sales-shelf-id', code: 'SALES_SHELF' },
  ],
}
const actor = {
  id: 'actor-id',
  login_identifier: 'demo.warehouse_staff',
  role: 'WAREHOUSE_STAFF' as const,
}

function renderApp() {
  return render(
    <App
      actor={actor}
      onLogout={() => undefined}
      onUnauthorized={() => undefined}
      receiveLineId={receiveLineId}
    />,
  )
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

describe('US-PUT-001 Putaway', () => {
  it('allows destination selection', async () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(jsonResponse(context))
    renderApp()

    const salesShelf = await screen.findByRole('radio', { name: /Sales Shelf/i })
    fireEvent.click(salesShelf)

    expect(salesShelf).toBeChecked()
    expect(screen.getByText('16')).toBeInTheDocument()
  })

  it('submits the allocation and shows the committed result', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(jsonResponse(context))
      .mockReturnValueOnce(
        jsonResponse(
          {
            putaway_id: 'putaway-id',
            receive_line_id: receiveLineId,
            sku_id: context.sku_id,
            quantity: 16,
            destination_location_id: 'backroom-id',
            destination_location: 'BACKROOM',
            confirmed_at: '2026-09-05T00:00:00Z',
            stock: { destination_quantity: 16, warehouse_total: 16 },
          },
          201,
        ),
      )
    renderApp()

    fireEvent.click(
      await screen.findByRole('button', { name: 'Confirm Putaway' }),
    )

    expect(
      await screen.findByRole('heading', {
        name: '16 units placed in Backroom',
      }),
    ).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock.mock.calls[1][0]).toContain('/api/v1/putaways')
  })

  it('displays a backend validation error', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(jsonResponse(context))
      .mockReturnValueOnce(
        jsonResponse(
          {
            error: {
              code: 'PUTAWAY_EXCEEDS_ELIGIBLE_QUANTITY',
              message: 'Quantity exceeds the eligible remaining quantity.',
              details: {},
            },
          },
          409,
        ),
      )
    renderApp()

    fireEvent.click(
      await screen.findByRole('button', { name: 'Confirm Putaway' }),
    )

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(
        'Quantity exceeds the eligible remaining quantity.',
      )
    })
  })
})
