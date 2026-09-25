import { execFileSync } from 'node:child_process'
import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

const successSkuId = '00000000-0000-0000-0000-000000000302'
const replaySkuId = '00000000-0000-0000-0000-000000000312'
const staleSkuId = '00000000-0000-0000-0000-000000000322'

function backendCommand(...args: string[]) {
  const uv = process.platform === 'win32' ? 'uv.exe' : 'uv'
  return execFileSync(
    uv,
    ['--directory', '../backend', 'run', 'python', '-m', 'warehouse_api.test_seed', ...args],
    { env: process.env, encoding: 'utf8' },
  ).trim()
}

function snapshot(skuId: string) {
  return JSON.parse(backendCommand('--transfer-snapshot', skuId)) as {
    transfer_count: number
    balances: Record<string, number>
    warehouse_total: number
  }
}

async function signIn(page: Page, skuId: string) {
  await page.goto(`/transfer/${skuId}`)
  await page.getByLabel('Login identifier').fill('demo.warehouse_staff')
  await page.getByLabel('Password').fill(process.env.E2E_USER_PASSWORD ?? '')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('heading', { name: 'Confirm Transfer' })).toBeVisible()
}

async function submitQuantity(page: Page, quantity: string) {
  await page.getByLabel('Quantity').fill(quantity)
  await page.getByRole('button', { name: 'Confirm Transfer' }).click()
}

test('TEST-TRF-E2E-001 confirms a Transfer with an unchanged total', async ({ page }) => {
  backendCommand('--transfer-reset', successSkuId)
  await signIn(page, successSkuId)
  await submitQuantity(page, '4')
  await expect(page.getByText('Transfer confirmed')).toBeVisible()
  expect(snapshot(successSkuId)).toEqual({
    transfer_count: 1,
    balances: { BACKROOM: 8, SALES_SHELF: 10 },
    warehouse_total: 18,
  })
})

test('TEST-TRF-E2E-002 safely replays after a lost response', async ({ page }) => {
  backendCommand('--transfer-reset', replaySkuId)
  await signIn(page, replaySkuId)
  let intercepted = false
  await page.route('**/api/v1/transfers', async (route) => {
    if (intercepted) {
      await route.continue()
      return
    }
    intercepted = true
    await route.fetch()
    await route.abort('failed')
  })
  await submitQuantity(page, '4')
  await expect(page.getByRole('alert')).toContainText('Failed to fetch')
  await page.unroute('**/api/v1/transfers')
  await page.getByRole('button', { name: 'Confirm Transfer' }).click()
  await expect(page.getByText('Transfer confirmed')).toBeVisible()
  expect(snapshot(replaySkuId)).toEqual({
    transfer_count: 1,
    balances: { BACKROOM: 8, SALES_SHELF: 10 },
    warehouse_total: 18,
  })
})

test('TEST-TRF-E2E-003 rejects stale stock without effects', async ({ page }) => {
  backendCommand('--transfer-reset', staleSkuId)
  await signIn(page, staleSkuId)
  await expect(page.getByText('Available: 12')).toBeVisible()
  await page.getByLabel('Quantity').fill('4')
  backendCommand('--transfer-deplete', staleSkuId)
  const before = snapshot(staleSkuId)
  await page.getByRole('button', { name: 'Confirm Transfer' }).click()
  await expect(page.getByRole('alert')).toContainText(
    'does not have enough available stock',
  )
  expect(snapshot(staleSkuId)).toEqual(before)
  await expect(page.getByLabel('Quantity')).toHaveValue('4')
})
