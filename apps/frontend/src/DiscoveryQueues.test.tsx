import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import PickQueuePage from './PickQueuePage'
import PutawayQueuePage from './PutawayQueuePage'
import ReceiveQueuePage from './ReceiveQueuePage'
import TransferSelectorPage from './TransferSelectorPage'

function response(body: object) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

it('links a prepared Receive queue item to its detail route', async () => {
  vi.spyOn(globalThis, 'fetch').mockReturnValue(
    response({
      items: [{
        receive_id: 'receive-id',
        warehouse_id: 'warehouse-id',
        expected_reference: 'DELIVERY-001',
        lines: [{ sku_id: 'sku-id', sku: 'SKU-001', expected_quantity: 16 }],
      }],
    }),
  )

  render(<ReceiveQueuePage onUnauthorized={() => undefined} />)

  expect(await screen.findByRole('link', { name: 'Record Receive' })).toHaveAttribute(
    'href',
    '/receive/receive-id',
  )
  expect(screen.getByText('SKU-001 × 16')).toBeVisible()
})

it('shows only backend-approved eligible quantity in the Putaway queue', async () => {
  vi.spyOn(globalThis, 'fetch').mockReturnValue(
    response({
      items: [{
        receive_line_id: 'line-id',
        receive_id: 'receive-id',
        expected_reference: 'DELIVERY-001',
        sku_id: 'sku-id',
        sku: 'SKU-001',
        actual_quantity: 16,
        confirmed_quantity: 6,
        eligible_quantity: 10,
      }],
    }),
  )

  render(<PutawayQueuePage onUnauthorized={() => undefined} />)

  expect(await screen.findByRole('link', { name: 'Open Putaway' })).toHaveAttribute(
    'href',
    '/putaway/line-id',
  )
  expect(screen.getByRole('row', { name: /DELIVERY-001 SKU-001 16 6 10/ })).toBeVisible()
})

it('links an actionable Pick and explains excluded outcomes', async () => {
  vi.spyOn(globalThis, 'fetch').mockReturnValue(
    response({
      items: [{
        pick_id: 'pick-id',
        sku_id: 'sku-id',
        sku: 'PICK-SKU',
        requested_quantity: 10,
        available_quantity: 18,
      }],
    }),
  )

  render(<PickQueuePage onUnauthorized={() => undefined} />)

  expect(await screen.findByRole('link', { name: 'Open Pick' })).toHaveAttribute(
    'href',
    '/pick/pick-id',
  )
  expect(screen.getByText(/PARTIAL_INSUFFICIENT outcomes are not shown/)).toBeVisible()
})

it('shows current tracked quantities before opening Transfer', async () => {
  vi.spyOn(globalThis, 'fetch').mockReturnValue(
    response({
      items: [{
        sku_id: 'sku-id',
        sku: 'TRANSFER-SKU',
        locations: [
          { id: 'backroom-id', code: 'BACKROOM', available_quantity: 12 },
          { id: 'shelf-id', code: 'SALES_SHELF', available_quantity: 6 },
        ],
        warehouse_total: 18,
      }],
    }),
  )

  render(<TransferSelectorPage onUnauthorized={() => undefined} />)

  expect(await screen.findByRole('link', { name: 'Open Transfer' })).toHaveAttribute(
    'href',
    '/transfer/sku-id',
  )
  expect(screen.getByRole('row', { name: /TRANSFER-SKU 12 6 18/ })).toBeVisible()
})
