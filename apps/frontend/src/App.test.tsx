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
      receiveId="00000000-0000-0000-0000-000000000103"
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
  window.history.pushState({}, '', '/')
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

describe('US-REC-001 addressing', () => {
  it('renders Receive at /receive without loading Putaway context', async () => {
    window.history.pushState({}, '', '/receive')
    vi.spyOn(globalThis, 'fetch').mockReturnValue(
      jsonResponse({
        receive_id: 'receive-id',
        warehouse_id: 'warehouse-id',
        reference: {
          expected: 'DELIVERY-001',
          document: null,
          match_status: null,
          reviewed_by_user_id: null,
          reviewed_at: null,
        },
        recorded_at: null,
        putaway_eligible: false,
        lines: [],
      }),
    )

    renderApp()

    expect(
      await screen.findByRole('heading', { name: 'Record Receive' }),
    ).toBeInTheDocument()
    expect(globalThis.fetch).toHaveBeenCalledTimes(1)
    expect(vi.mocked(globalThis.fetch).mock.calls[0][0]).toContain(
      '/api/v1/receives/context/',
    )
  })
})

describe('US-PICK-001 addressing', () => {
  it('reads the Pick ID from /pick/{pick_id}', async () => {
    const pickId = '00000000-0000-0000-0000-000000000201'
    window.history.pushState({}, '', `/pick/${pickId}`)
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockReturnValue(
      jsonResponse({
        pick_id: pickId,
        warehouse_id: 'warehouse-id',
        sku_id: 'sku-id',
        sku: 'PICK-SKU',
        requested_quantity: 10,
        outcome: null,
        locations: [],
        warehouse_total: 0,
      }),
    )

    renderApp()

    expect(
      await screen.findByRole('heading', { name: 'Confirm Pick' }),
    ).toBeInTheDocument()
    expect(fetchMock.mock.calls[0][0]).toContain(
      `/api/v1/picks/context/${pickId}`,
    )
  })
})

describe('US-TRF-001 addressing', () => {
  it('reads the SKU ID from /transfer/{sku_id}', async () => {
    const skuId = '00000000-0000-0000-0000-000000000302'
    window.history.pushState({}, '', `/transfer/${skuId}`)
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockReturnValue(
      jsonResponse({
        warehouse_id: 'warehouse-id',
        sku_id: skuId,
        sku: 'TRANSFER-SKU',
        locations: [],
        warehouse_total: 0,
      }),
    )

    renderApp()

    expect(
      await screen.findByRole('heading', { name: 'Confirm Transfer' }),
    ).toBeInTheDocument()
    expect(fetchMock.mock.calls[0][0]).toContain(
      `/api/v1/transfers/context/${skuId}`,
    )
  })
})

describe('US-TRF-002 addressing', () => {
  it('loads backend-authoritative history at /transfers/history for a Manager', async () => {
    window.history.pushState({}, '', '/transfers/history')
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockReturnValue(
      jsonResponse({ items: [] }),
    )

    render(
      <App
        actor={{ ...actor, role: 'MANAGER' }}
        onLogout={() => undefined}
        onUnauthorized={() => undefined}
        receiveLineId={receiveLineId}
      />,
    )

    expect(
      await screen.findByRole('heading', { name: 'Transfer history' }),
    ).toBeInTheDocument()
    expect(fetchMock.mock.calls[0][0]).toContain('/api/v1/transfers')
  })

  it('still requests history for a wrong role so backend can return 403', async () => {
    window.history.pushState({}, '', '/transfers/history')
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockReturnValue(
      jsonResponse(
        { error: { code: 'FORBIDDEN', message: 'Access denied.' } },
        403,
      ),
    )

    renderApp()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Manager role required',
    )
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})

describe('US-AUD-001 addressing', () => {
  it('loads the Audit page at /audits/new', async () => {
    window.history.pushState({}, '', '/audits/new')
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockReturnValue(
      jsonResponse({ warehouse_id: 'warehouse-id', pairs: [] }),
    )
    renderApp()
    expect(
      await screen.findByRole('heading', { name: 'New Audit' }),
    ).toBeInTheDocument()
    expect(fetchMock.mock.calls[0][0]).toContain('/api/v1/audits/context')
  })

  it('shows a presentation guard for a wrong role', () => {
    window.history.pushState({}, '', '/audits/new')
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    render(
      <App
        actor={{ ...actor, role: 'MANAGER' }}
        onLogout={() => undefined}
        onUnauthorized={() => undefined}
        receiveLineId={receiveLineId}
      />,
    )
    expect(
      screen.getByRole('heading', { name: 'Warehouse Staff role required' }),
    ).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })
})

describe('US-AUD-002 addressing', () => {
  it('loads backend-authoritative discrepancies at /audit-discrepancies', async () => {
    window.history.pushState({}, '', '/audit-discrepancies')
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockReturnValue(
      jsonResponse({ items: [] }),
    )
    render(
      <App
        actor={{ ...actor, role: 'MANAGER' }}
        onLogout={() => undefined}
        onUnauthorized={() => undefined}
        receiveLineId={receiveLineId}
      />,
    )
    expect(
      await screen.findByRole('heading', { name: 'Audit discrepancies' }),
    ).toBeInTheDocument()
    expect(fetchMock.mock.calls[0][0]).toContain('/api/v1/audit-discrepancies')
  })

  it('still requests discrepancies for a wrong role so backend returns 403', async () => {
    window.history.pushState({}, '', '/audit-discrepancies')
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockReturnValue(
      jsonResponse(
        { error: { code: 'FORBIDDEN', message: 'Access denied.' } },
        403,
      ),
    )
    renderApp()
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Manager role required',
    )
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})
