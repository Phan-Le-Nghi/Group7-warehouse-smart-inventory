import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import TransferHistoryPage from './TransferHistoryPage'

const first = {
  transfer_id: '00000000-0000-0000-0000-000000000030',
  warehouse_id: '00000000-0000-0000-0000-000000000001',
  sku: { id: 'sku-1', code: 'SKU-NEW' },
  quantity: 4,
  source: { id: 'source-1', code: 'BACKROOM' },
  destination: { id: 'destination-1', code: 'SALES_SHELF' },
  transferred_by: {
    user_id: 'user-1',
    login_identifier: 'demo.warehouse_staff',
  },
  transferred_at: '2026-09-25T08:30:00Z',
}

const second = {
  ...first,
  transfer_id: '00000000-0000-0000-0000-000000000020',
  sku: { id: 'sku-2', code: 'SKU-OLDER' },
  quantity: 2,
  transferred_at: '2026-09-24T08:30:00Z',
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

describe('US-TRF-002 Transfer history page', () => {
  it('shows loading, then the empty state', async () => {
    let resolveRequest!: (response: Response) => void
    vi.spyOn(globalThis, 'fetch').mockReturnValue(
      new Promise((resolve) => {
        resolveRequest = resolve
      }),
    )
    render(<TransferHistoryPage onUnauthorized={() => undefined} />)
    expect(screen.getByRole('status')).toHaveTextContent(
      'Loading Transfer history',
    )
    resolveRequest(
      new Response(JSON.stringify({ items: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    expect(await screen.findByText('No confirmed Transfers yet.')).toBeInTheDocument()
  })

  it('renders the approved table fields and preserves raw timestamps', async () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(
      jsonResponse({ items: [first, second] }),
    )
    render(<TransferHistoryPage onUnauthorized={() => undefined} />)

    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(screen.getAllByRole('columnheader').map((cell) => cell.textContent)).toEqual([
      'SKU',
      'Source',
      'Destination',
      'Quantity',
      'Actor',
      'Transferred at',
    ])
    expect(screen.getByText('SKU-NEW')).toBeInTheDocument()
    expect(screen.getByText('SKU-OLDER')).toBeInTheDocument()
    expect(screen.getAllByText('BACKROOM')).toHaveLength(2)
    expect(screen.getAllByText('SALES_SHELF')).toHaveLength(2)
    expect(screen.getAllByText('demo.warehouse_staff')).toHaveLength(2)
    expect(document.querySelector(`time[datetime="${first.transferred_at}"]`)).not.toBeNull()
    for (const action of ['Edit', 'Delete', 'Reverse', 'Rerun', 'Export', 'Search']) {
      expect(screen.queryByRole('button', { name: action })).not.toBeInTheDocument()
    }
  })

  it('offers retry for a server error and then loads rows', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(
        jsonResponse(
          { error: { code: 'REQUEST_FAILED', message: 'History unavailable.' } },
          500,
        ),
      )
      .mockReturnValueOnce(jsonResponse({ items: [first] }))
    render(<TransferHistoryPage onUnauthorized={() => undefined} />)

    expect(await screen.findByRole('alert')).toHaveTextContent('History unavailable.')
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('SKU-NEW')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('returns to auth recovery after a 401', async () => {
    const unauthorized = vi.fn()
    vi.spyOn(globalThis, 'fetch').mockReturnValue(
      jsonResponse(
        { error: { code: 'AUTHENTICATION_REQUIRED', message: 'Sign in.' } },
        401,
      ),
    )
    render(<TransferHistoryPage onUnauthorized={unauthorized} />)
    await waitFor(() => expect(unauthorized).toHaveBeenCalledOnce())
  })

  it('renders the real backend forbidden response after a 403', async () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(
      jsonResponse(
        { error: { code: 'FORBIDDEN', message: 'Access denied.' } },
        403,
      ),
    )
    render(<TransferHistoryPage onUnauthorized={() => undefined} />)
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Manager role required',
    )
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/transfers'),
      expect.objectContaining({ credentials: 'include' }),
    )
  })
})
