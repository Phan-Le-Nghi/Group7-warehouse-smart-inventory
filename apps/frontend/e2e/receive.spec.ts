import { execFileSync } from 'node:child_process'
import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

const receiveId = '00000000-0000-0000-0000-000000000103'

function backendCommand(...args: string[]) {
  const uv = process.platform === 'win32' ? 'uv.exe' : 'uv'
  return execFileSync(
    uv,
    ['--directory', '../backend', 'run', 'python', '-m', 'warehouse_api.test_seed', ...args],
    { env: process.env, encoding: 'utf8' },
  ).trim()
}

function snapshot() {
  return JSON.parse(backendCommand('--snapshot', receiveId)) as {
    stock_quantity: number
    putaway_count: number
  }
}

async function signIn(page: Page) {
  await page.goto('/receive')
  await page.getByLabel('Login identifier').fill('demo.warehouse_staff')
  await page.getByLabel('Password').fill(process.env.E2E_USER_PASSWORD ?? '')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('heading', { name: 'Record Receive' })).toBeVisible()
}

test.describe.serial('US-REC-001 Receive flow', () => {
  test.beforeEach(() => {
    backendCommand('--receive-only')
  })

  test('TEST-REC-E2E-001 records matching Receive facts', async ({ page }) => {
    await signIn(page)
    await expect(page.getByText('REC-SKU-MATCH')).toBeVisible()
    await page.getByLabel('Document reference').fill('DELIVERY-001')
    await page.getByLabel('Actual quantity').fill('16')
    await page.getByRole('button', { name: 'Record Receive' }).click()

    await expect(page.getByText('Receive recorded')).toBeVisible()
    await expect(
      page.getByText('References match. This Receive is eligible for Putaway.'),
    ).toBeVisible()
    expect(snapshot()).toEqual({ stock_quantity: 0, putaway_count: 0 })
  })

  test('TEST-REC-E2E-002 reviews a discrepant reference', async ({ page }) => {
    await signIn(page)
    await page.getByLabel('Document reference').fill('DELIVERY-OTHER')
    await page.getByLabel('Actual quantity').fill('14')
    await expect(page.getByText('-2')).toBeVisible()
    await page.getByRole('button', { name: 'Record Receive' }).click()

    await expect(page.getByText('Review required')).toBeVisible()
    expect(snapshot()).toEqual({ stock_quantity: 0, putaway_count: 0 })
    await page.getByRole('button', { name: 'Acknowledge mismatch' }).click()
    await expect(page.getByText(/Mismatch acknowledged by/)).toBeVisible()
    expect(snapshot()).toEqual({ stock_quantity: 0, putaway_count: 0 })
  })
})
