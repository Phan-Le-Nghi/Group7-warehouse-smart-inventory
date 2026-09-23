import { execFileSync } from 'node:child_process'
import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

const fullPickId = '00000000-0000-0000-0000-000000000201'
const partialPickId = '00000000-0000-0000-0000-000000000211'
const stalePickId = '00000000-0000-0000-0000-000000000221'

function backendCommand(...args: string[]) {
  const uv = process.platform === 'win32' ? 'uv.exe' : 'uv'
  return execFileSync(
    uv,
    ['--directory', '../backend', 'run', 'python', '-m', 'warehouse_api.test_seed', ...args],
    { env: process.env, encoding: 'utf8' },
  ).trim()
}

function snapshot(pickId: string) {
  return JSON.parse(backendCommand('--pick-snapshot', pickId)) as {
    outcome: string | null
    allocation_count: number
    balances: Record<string, number>
  }
}

async function signIn(page: Page, pickId: string) {
  await page.goto(`/pick/${pickId}`)
  await page.getByLabel('Login identifier').fill('demo.warehouse_staff')
  await page.getByLabel('Password').fill(process.env.E2E_USER_PASSWORD ?? '')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('heading', { name: 'Confirm Pick' })).toBeVisible()
}

test('TEST-PICK-E2E-001 confirms a full multi-location Pick', async ({ page }) => {
  backendCommand('--pick-reset', fullPickId)
  await signIn(page, fullPickId)
  await expect(page.getByText('PICK-SKU-FULL')).toBeVisible()
  await page.getByRole('checkbox', { name: /Backroom/i }).check()
  await page.getByLabel('Quantity from Backroom').fill('6')
  await page.getByRole('checkbox', { name: /Sales Shelf/i }).check()
  await page.getByLabel('Quantity from Sales Shelf').fill('4')
  await page.getByRole('button', { name: 'Review and confirm Pick' }).click()

  await expect(page.getByText('Pick fully completed')).toBeVisible()
  await expect(page.getByRole('heading', { name: '10 of 10 units picked' })).toBeVisible()
  expect(snapshot(fullPickId)).toEqual({
    outcome: 'FULLY_COMPLETED',
    allocation_count: 2,
    balances: { BACKROOM: 0, SALES_SHELF: 0 },
  })
})

test('TEST-PICK-E2E-002 explicitly confirms a partial Pick', async ({ page }) => {
  backendCommand('--pick-reset', partialPickId)
  await signIn(page, partialPickId)
  await page.getByRole('checkbox', { name: /Backroom/i }).check()
  await page.getByLabel('Quantity from Backroom').fill('6')
  await page.getByRole('button', { name: 'Review and confirm Pick' }).click()

  await expect(
    page.getByText('Pick is not fully completed. 4 units remain unfulfilled.'),
  ).toBeVisible()
  expect(snapshot(partialPickId).outcome).toBeNull()
  await page.getByRole('button', { name: 'Confirm partial Pick' }).click()

  await expect(page.getByText('Partial Pick recorded')).toBeVisible()
  await expect(
    page.getByText('Pick is not fully completed. 4 units remain unfulfilled.'),
  ).toBeVisible()
  expect(snapshot(partialPickId)).toEqual({
    outcome: 'PARTIAL_INSUFFICIENT',
    allocation_count: 1,
    balances: { BACKROOM: 2, SALES_SHELF: 6 },
  })
})

test('TEST-PICK-E2E-003 rejects stale stock without a Pick mutation', async ({ page }) => {
  backendCommand('--pick-reset', stalePickId)
  await signIn(page, stalePickId)
  await expect(page.getByText('8 available')).toBeVisible()
  await page.getByRole('checkbox', { name: /Backroom/i }).check()
  await page.getByLabel('Quantity from Backroom').fill('8')
  await page.getByRole('checkbox', { name: /Sales Shelf/i }).check()
  await page.getByLabel('Quantity from Sales Shelf').fill('2')
  backendCommand('--pick-deplete', stalePickId)
  const before = snapshot(stalePickId)

  await page.getByRole('button', { name: 'Review and confirm Pick' }).click()

  await expect(page.getByRole('alert')).toContainText(
    'does not have enough available stock',
  )
  expect(snapshot(stalePickId)).toEqual(before)
  await expect(page.getByLabel('Quantity from Backroom')).toHaveValue('8')
  await expect(page.getByText('Pick fully completed')).toHaveCount(0)
})
