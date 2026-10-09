import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import PrepareReceivePage from './PrepareReceivePage'

function response(body: object, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  }))
}

const catalog = {
  items: [
    { sku_id: 'sku-1', sku: 'SKU-001' },
    { sku_id: 'sku-2', sku: 'SKU-002' },
  ],
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('DEC-045 Prepare Receive', () => {
  it('loads generic SKUs and creates a multiline Receive', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockReturnValueOnce(response(catalog))
      .mockReturnValueOnce(response({
        receive_id: 'receive-id',
        warehouse_id: 'warehouse-id',
        expected_reference: 'DELIVERY-001',
        recorded_at: null,
        lines: [
          { receive_line_id: 'line-1', sku_id: 'sku-1', sku: 'SKU-001', expected_quantity: 4 },
          { receive_line_id: 'line-2', sku_id: 'sku-2', sku: 'SKU-002', expected_quantity: 6 },
        ],
      }, 201))
    render(<PrepareReceivePage onUnauthorized={() => undefined} />)

    await screen.findByRole('option', { name: 'SKU-001' })
    fireEvent.change(screen.getByLabelText('Expected reference'), { target: { value: ' DELIVERY-001 ' } })
    fireEvent.change(screen.getByLabelText('SKU'), { target: { value: 'sku-1' } })
    fireEvent.change(screen.getByLabelText('Expected quantity'), { target: { value: '4' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add line' }))
    const skuInputs = screen.getAllByLabelText('SKU')
    const quantityInputs = screen.getAllByLabelText('Expected quantity')
    fireEvent.change(skuInputs[1], { target: { value: 'sku-2' } })
    fireEvent.change(quantityInputs[1], { target: { value: '6' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create' }))

    expect(await screen.findByText('Prepared Receive created and ready for Warehouse Staff.')).toBeVisible()
    const body = JSON.parse(String(fetchMock.mock.calls[1][1]?.body))
    expect(body).toEqual({
      expected_reference: 'DELIVERY-001',
      lines: [
        { sku_id: 'sku-1', expected_quantity: 4 },
        { sku_id: 'sku-2', expected_quantity: 6 },
      ],
    })
  })

  it('supports removing a line and prevents duplicate selection', async () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(response(catalog))
    render(<PrepareReceivePage onUnauthorized={() => undefined} />)
    await screen.findByRole('option', { name: 'SKU-001' })
    fireEvent.change(screen.getByLabelText('SKU'), { target: { value: 'sku-1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add line' }))
    expect(screen.getAllByRole('button', { name: 'Remove line' })).toHaveLength(2)
    expect(screen.getAllByRole('option', { name: 'SKU-001' })[1]).toBeDisabled()
    fireEvent.click(screen.getAllByRole('button', { name: 'Remove line' })[1])
    expect(screen.queryByRole('button', { name: 'Remove line' })).not.toBeInTheDocument()
  })

  it('validates required fields before calling create', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockReturnValue(response(catalog))
    render(<PrepareReceivePage onUnauthorized={() => undefined} />)
    await screen.findByRole('button', { name: 'Create' })
    fireEvent.click(screen.getByRole('button', { name: 'Create' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Expected reference')
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('shows backend errors and forbidden state', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockReturnValueOnce(response(catalog))
      .mockReturnValueOnce(response({ error: { code: 'SKU_NOT_FOUND', message: 'SKU was not found.' } }, 404))
    render(<PrepareReceivePage onUnauthorized={() => undefined} />)
    await screen.findByRole('option', { name: 'SKU-001' })
    fireEvent.change(screen.getByLabelText('Expected reference'), { target: { value: 'R-1' } })
    fireEvent.change(screen.getByLabelText('SKU'), { target: { value: 'sku-1' } })
    fireEvent.change(screen.getByLabelText('Expected quantity'), { target: { value: '1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('SKU was not found.')

    cleanup()
    fetchMock.mockReset().mockReturnValue(response({ error: { code: 'FORBIDDEN', message: 'Forbidden' } }, 403))
    render(<PrepareReceivePage onUnauthorized={() => undefined} />)
    expect(await screen.findByRole('heading', { name: 'Purchasing role required' })).toBeVisible()
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Create' })).not.toBeInTheDocument())
  })
})
