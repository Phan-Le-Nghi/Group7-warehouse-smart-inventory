import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import CreatePickRequestPage from './CreatePickRequestPage'

function response(body: object, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  }))
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('DEC-045 Create Pick Request', () => {
  it('loads SKUs and creates actionable work', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(response({ items: [{ sku_id: 'sku-1', sku: 'SKU-001' }] }))
      .mockReturnValueOnce(response({
        pick_id: 'pick-id', warehouse_id: 'warehouse-id', sku_id: 'sku-1',
        sku: 'SKU-001', requested_quantity: 10, outcome: null,
      }, 201))
    render(<CreatePickRequestPage onUnauthorized={() => undefined} />)
    await screen.findByRole('option', { name: 'SKU-001' })
    fireEvent.change(screen.getByLabelText('SKU'), { target: { value: 'sku-1' } })
    fireEvent.change(screen.getByLabelText('Requested quantity'), { target: { value: '10' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create' }))
    expect(await screen.findByText('Pick Request created and ready for Warehouse Staff.')).toBeVisible()
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toEqual({
      sku_id: 'sku-1', requested_quantity: 10,
    })
  })

  it('validates SKU and strict positive integer quantity', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockReturnValue(
      response({ items: [{ sku_id: 'sku-1', sku: 'SKU-001' }] }),
    )
    render(<CreatePickRequestPage onUnauthorized={() => undefined} />)
    await screen.findByRole('button', { name: 'Create' })
    fireEvent.click(screen.getByRole('button', { name: 'Create' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Select a SKU')
    fireEvent.change(screen.getByLabelText('SKU'), { target: { value: 'sku-1' } })
    fireEvent.change(screen.getByLabelText('Requested quantity'), { target: { value: '1.5' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create' }))
    expect(screen.getByRole('alert')).toHaveTextContent('positive integer')
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('shows API failure and backend-driven forbidden state', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(response({ items: [{ sku_id: 'sku-1', sku: 'SKU-001' }] }))
      .mockReturnValueOnce(response({ error: { code: 'FAILED', message: 'Request unavailable.' } }, 500))
    render(<CreatePickRequestPage onUnauthorized={() => undefined} />)
    await screen.findByRole('option', { name: 'SKU-001' })
    fireEvent.change(screen.getByLabelText('SKU'), { target: { value: 'sku-1' } })
    fireEvent.change(screen.getByLabelText('Requested quantity'), { target: { value: '2' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Request unavailable.')

    cleanup()
    fetchMock.mockReset().mockReturnValue(response({ error: { code: 'FORBIDDEN', message: 'Forbidden' } }, 403))
    render(<CreatePickRequestPage onUnauthorized={() => undefined} />)
    expect(await screen.findByRole('heading', { name: 'Manager role required' })).toBeVisible()
  })
})
