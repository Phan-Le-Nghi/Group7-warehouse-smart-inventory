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

function renderPutawayApp() {
  window.history.pushState({}, '', '/putaway')
  return renderApp()
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
    renderPutawayApp()

    const salesShelf = await screen.findByRole('radio', { name: /Sales Shelf/i })
    fireEvent.click(salesShelf)

    expect(salesShelf).toBeChecked()
    expect(screen.getByText('16')).toBeInTheDocument()
  })

  it('does not allow another putaway when the receive line is fully put away', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockReturnValue(
      jsonResponse({
        ...context,
        confirmed_quantity: 16,
        eligible_quantity: 0,
      }),
    )
    renderPutawayApp()

    expect(
      await screen.findByText('This receive line has been fully put away.'),
    ).toHaveAttribute('role', 'status')
    expect(screen.queryByRole('radio')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Confirm Putaway' }),
    ).not.toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(1)
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
    renderPutawayApp()

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
    renderPutawayApp()

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

describe('role Dashboard routing', () => {
  it('renders Staff actions at / without loading business context', () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    renderApp()

    expect(
      screen.getByRole('heading', { name: 'Warehouse Dashboard' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open Receive/ })).toHaveAttribute(
      'href',
      '/receive',
    )
    expect(screen.getByRole('link', { name: /Open Putaway/ })).toHaveAttribute(
      'href',
      '/putaway',
    )
    expect(screen.getByRole('link', { name: /Open New Audit/ })).toHaveAttribute(
      'href',
      '/audits/new',
    )
    expect(screen.queryByText('Transfer History')).not.toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('shows unavailable Staff cards instead of links without prepared context', () => {
    render(
      <App
        actor={actor}
        onLogout={() => undefined}
        onUnauthorized={() => undefined}
        receiveId=""
        receiveLineId=""
      />,
    )

    expect(screen.getAllByText('Requires prepared context.')).toHaveLength(2)
    expect(screen.queryByRole('link', { name: /Open Receive/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open Putaway/ })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open New Audit/ })).toBeInTheDocument()
  })

  it('renders only Manager actions for a Manager', () => {
    render(
      <App
        actor={{ ...actor, role: 'MANAGER' }}
        onLogout={() => undefined}
        onUnauthorized={() => undefined}
        receiveId="receive-id"
        receiveLineId={receiveLineId}
      />,
    )

    expect(screen.getByRole('link', { name: /Open Transfer History/ })).toHaveAttribute(
      'href',
      '/transfers/history',
    )
    expect(screen.getByRole('link', { name: /Open Audit Discrepancies/ })).toHaveAttribute(
      'href',
      '/audit-discrepancies',
    )
    expect(screen.getByRole('link', { name: /Open Adjust Decisions/ })).toHaveAttribute(
      'href',
      '/adjustment-decisions',
    )
    expect(screen.queryByText('New Audit')).not.toBeInTheDocument()
    expect(screen.queryByText('Putaway')).not.toBeInTheDocument()
  })

  it.each(['PURCHASING', 'ADMIN'] as const)(
    'renders a neutral state without fake actions for %s',
    (role) => {
      render(
        <App
          actor={{ ...actor, role }}
          onLogout={() => undefined}
          onUnauthorized={() => undefined}
          receiveId="receive-id"
          receiveLineId={receiveLineId}
        />,
      )

      expect(
        screen.getByText(
          'No dashboard actions are available for this role in the current MVP.',
        ),
      ).toBeInTheDocument()
      expect(screen.queryByText('Receive')).not.toBeInTheDocument()
      expect(screen.queryByText('Transfer History')).not.toBeInTheDocument()
      cleanup()
    },
  )

  it('renders Page not found instead of Putaway for an unknown route', () => {
    window.history.pushState({}, '', '/unknown-route')
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    renderApp()

    expect(
      screen.getByRole('heading', { name: 'This page is not available' }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('heading', { name: 'Confirm Putaway' }),
    ).not.toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })
})

describe('backend-authoritative Staff route authorization', () => {
  it.each([
    ['/putaway', '/api/v1/putaways/context/'],
    ['/receive', '/api/v1/receives/context/'],
    ['/pick/pick-id', '/api/v1/picks/context/pick-id'],
    ['/transfer/sku-id', '/api/v1/transfers/context/sku-id'],
  ])('requests the safe read endpoint for a Manager at %s', async (path, endpoint) => {
    window.history.pushState({}, '', path)
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockReturnValue(
      jsonResponse(
        {
          error: {
            code: 'FORBIDDEN',
            message: 'The authenticated actor does not have the required role.',
          },
        },
        403,
      ),
    )

    render(
      <App
        actor={{ ...actor, role: 'MANAGER' }}
        onLogout={() => undefined}
        onUnauthorized={() => undefined}
        receiveId="receive-id"
        receiveLineId={receiveLineId}
      />,
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The authenticated actor does not have the required role.',
    )
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toContain(endpoint)
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

  it('requests context for a wrong role so the backend remains authoritative', async () => {
    window.history.pushState({}, '', '/audits/new')
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockReturnValue(
      jsonResponse(
        { error: { code: 'FORBIDDEN', message: 'Warehouse Staff role required' } },
        403,
      ),
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
      await screen.findByRole('heading', { name: 'Warehouse Staff role required' }),
    ).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toContain('/api/v1/audits/context')
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

describe('US-ADJ-001 exact-context addressing', () => {
  it('loads the exact recheck at /adjustments/{audit_recheck_id}', async () => {
    const recheckId = '00000000-0000-0000-0000-000000000701'
    window.history.pushState({}, '', `/adjustments/${recheckId}`)
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockReturnValue(
      jsonResponse({
        audit_recheck_id: recheckId,
        warehouse_id: 'warehouse-id',
        sku: { id: 'sku-id', code: 'AUDIT-SKU' },
        location: { id: 'location-id', code: 'BACKROOM' },
        original_audit: {
          audit_id: 'audit-id',
          audit_line_id: 'line-id',
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
      }),
    )
    renderApp()
    expect(
      await screen.findByRole('heading', { name: 'Create Adjust request' }),
    ).toBeVisible()
    expect(fetchMock.mock.calls[0][0]).toContain(
      `/api/v1/adjustments/context/${recheckId}`,
    )
  })
})

describe('US-ADJ-002 Manager addressing', () => {
  it('loads the Manager queue at /adjustment-decisions', async () => {
    window.history.pushState({}, '', '/adjustment-decisions')
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
      await screen.findByRole('heading', { name: 'Adjust decisions' }),
    ).toBeVisible()
    expect(fetchMock.mock.calls[0][0]).toContain(
      '/api/v1/adjustments?status=PENDING_MANAGER_DECISION',
    )
  })

  it('preserves the adjustment_id query deep link', () => {
    window.history.pushState(
      {},
      '',
      '/adjustment-decisions?adjustment_id=adjustment-id',
    )
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      () => new Promise<Response>(() => undefined),
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
      screen.getByRole('heading', { name: 'Adjust decisions' }),
    ).toBeInTheDocument()
    expect(window.location.search).toBe('?adjustment_id=adjustment-id')
  })
})
