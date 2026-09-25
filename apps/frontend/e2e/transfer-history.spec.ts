import { execFileSync } from 'node:child_process'
import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

function backendCommand(...args: string[]) {
  const uv = process.platform === 'win32' ? 'uv.exe' : 'uv'
  return execFileSync(
    uv,
    ['--directory', '../backend', 'run', 'python', '-m', 'warehouse_api.test_seed', ...args],
    { env: process.env, encoding: 'utf8' },
  ).trim()
}

function snapshot() {
  return JSON.parse(backendCommand('--history-snapshot')) as {
    business_state_digest: string
    transfer_count: number
    stock_row_count: number
    receive_count: number
    putaway_count: number
    pick_count: number
  }
}

async function signIn(page: Page, loginIdentifier: string) {
  await page.goto('/transfers/history')
  await page.getByLabel('Login identifier').fill(loginIdentifier)
  await page.getByLabel('Password').fill(process.env.E2E_USER_PASSWORD ?? '')
  await page.getByRole('button', { name: 'Sign in' }).click()
}

test('TEST-TRF2-E2E-001 Manager sees deterministic confirmed history', async ({
  page,
}) => {
  backendCommand('--history-reset', 'rows')
  await signIn(page, 'demo.manager')
  await expect(page.getByRole('heading', { name: 'Transfer history' })).toBeVisible()
  const rows = page.getByRole('row')
  await expect(rows).toHaveCount(3)
  await expect(rows.nth(1)).toContainText('TRANSFER-SKU-REPLAY')
  await expect(rows.nth(2)).toContainText('TRANSFER-SKU-SUCCESS')
  await expect(page.getByText('demo.warehouse_staff')).toHaveCount(2)
})

test('TEST-TRF2-E2E-002 Manager sees an empty history state', async ({ page }) => {
  backendCommand('--history-reset', 'empty')
  await signIn(page, 'demo.manager')
  await expect(page.getByText('No confirmed Transfers yet.')).toBeVisible()
})

test('TEST-TRF2-E2E-003 wrong role receives backend forbidden', async ({ page }) => {
  backendCommand('--history-reset', 'rows')
  await signIn(page, 'demo.warehouse_staff')
  await expect(page.getByRole('alert')).toContainText('Manager role required')
  await expect(page.getByText('Transfer history')).toBeVisible()
})

test('TEST-TRF2-E2E-004 browser history read has no business-data effect', async ({
  page,
}) => {
  backendCommand('--history-reset', 'rows')
  const before = snapshot()
  await signIn(page, 'demo.manager')
  await expect(page.getByRole('table')).toBeVisible()
  expect(snapshot()).toEqual(before)
})
