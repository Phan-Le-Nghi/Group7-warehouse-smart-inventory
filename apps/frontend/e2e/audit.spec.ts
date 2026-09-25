import { execFileSync } from 'node:child_process'
import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

const auditSkuId = '00000000-0000-0000-0000-000000000502'

function backendCommand(...args: string[]) {
  const uv = process.platform === 'win32' ? 'uv.exe' : 'uv'
  return execFileSync(
    uv,
    [
      '--directory',
      '../backend',
      'run',
      'python',
      '-m',
      'warehouse_api.test_seed',
      ...args,
    ],
    { env: process.env, encoding: 'utf8' },
  ).trim()
}

function snapshot() {
  return JSON.parse(backendCommand('--audit-snapshot')) as {
    business_state_digest: string
    audit_count: number
    audit_line_count: number
    missing_balance_count: number
  }
}

async function signIn(page: Page, login = 'demo.warehouse_staff') {
  await page.goto('/audits/new')
  await page.getByLabel('Login identifier').fill(login)
  await page.getByLabel('Password').fill(process.env.E2E_USER_PASSWORD ?? '')
  await page.getByRole('button', { name: 'Sign in' }).click()
}

async function selectAuditPair(
  page: Page,
  skuCode: string,
  location: string,
  physical: string,
) {
  await page.getByLabel(`Count ${skuCode} at ${location}`).check()
  await page
    .getByLabel(`Physical quantity for ${skuCode} at ${location}`)
    .fill(physical)
}

async function fillWholeWarehouseFromPreview(page: Page) {
  await page.getByLabel('Whole Warehouse').check()
  const rows = page.locator('tbody tr')
  const count = await rows.count()
  for (let index = 0; index < count; index += 1) {
    const row = rows.nth(index)
    const preview = (await row.locator('td').nth(3).textContent())?.trim() ?? '0'
    await row.locator('input[inputmode="numeric"]').fill(preview)
  }
}

test('TEST-AUD-E2E-001 records a selected-pair Match', async ({ page }) => {
  backendCommand('--audit-reset')
  const before = snapshot()
  await signIn(page)
  await selectAuditPair(page, 'AUDIT-SKU-MISSING-BALANCE', 'BACKROOM', '7')
  await page.getByRole('button', { name: 'Record Audit' }).click()
  await expect(page.getByText('All counted quantities match')).toBeVisible()
  const after = snapshot()
  expect(after.business_state_digest).toBe(before.business_state_digest)
  expect(after.audit_count).toBe(1)
  expect(after.audit_line_count).toBe(1)
})

test('TEST-AUD-E2E-002 records missing-balance mismatch without stock change', async ({
  page,
}) => {
  backendCommand('--audit-reset')
  const before = snapshot()
  expect(before.missing_balance_count).toBe(0)
  await signIn(page)
  await selectAuditPair(
    page,
    'AUDIT-SKU-MISSING-BALANCE',
    'SALES_SHELF',
    '3',
  )
  await page.getByRole('button', { name: 'Record Audit' }).click()
  await expect(page.getByText('Discrepancy recorded')).toBeVisible()
  await expect(page.getByText(/Stock was not changed/)).toBeVisible()
  const after = snapshot()
  expect(after.business_state_digest).toBe(before.business_state_digest)
  expect(after.missing_balance_count).toBe(0)
  expect(after.audit_count).toBe(1)
})

test('TEST-AUD-E2E-003 completes a Whole Warehouse Audit', async ({ page }) => {
  backendCommand('--audit-reset')
  await signIn(page)
  await fillWholeWarehouseFromPreview(page)
  await page.getByRole('button', { name: 'Record Audit' }).click()
  await expect(page.getByText('All counted quantities match')).toBeVisible()
  const after = snapshot()
  expect(after.audit_count).toBe(1)
  expect(after.audit_line_count).toBeGreaterThan(1)
})

test('TEST-AUD-E2E-004 safely replays after a lost response', async ({ page }) => {
  backendCommand('--audit-reset')
  await signIn(page)
  await selectAuditPair(page, 'AUDIT-SKU-MISSING-BALANCE', 'BACKROOM', '7')
  let intercepted = false
  await page.route('**/api/v1/audits', async (route) => {
    if (intercepted) {
      await route.continue()
      return
    }
    intercepted = true
    await route.fetch()
    await route.abort('failed')
  })
  await page.getByRole('button', { name: 'Record Audit' }).click()
  await expect(page.getByRole('alert')).toContainText('Failed to fetch')
  await page.unroute('**/api/v1/audits')
  await page.getByRole('button', { name: 'Record Audit' }).click()
  await expect(page.getByText('All counted quantities match')).toBeVisible()
  expect(snapshot().audit_count).toBe(1)
})

test('TEST-AUD-E2E-005 reports Whole Warehouse scope change', async ({ page }) => {
  backendCommand('--audit-reset')
  await signIn(page)
  await fillWholeWarehouseFromPreview(page)
  backendCommand('--audit-scope-add')
  await page.getByRole('button', { name: 'Record Audit' }).click()
  await expect(page.getByRole('alert')).toContainText('scope has changed')
  await expect(
    page.getByRole('button', { name: 'Reload and reconcile scope' }),
  ).toBeVisible()
  expect(snapshot().audit_count).toBe(0)
  backendCommand('--audit-scope-remove')
})

test('TEST-AUD-E2E-006 wrong role receives a real backend 403', async ({ page }) => {
  backendCommand('--audit-reset')
  await signIn(page, 'demo.manager')
  await expect(
    page.getByRole('heading', { name: 'Warehouse Staff role required' }),
  ).toBeVisible()
  const response = await page.request.post(
    'http://127.0.0.1:8000/api/v1/audits',
    {
      headers: { 'Idempotency-Key': 'wrong-role' },
      data: {
        scope_type: 'SELECTED_PAIRS',
        lines: [
          {
            sku_id: auditSkuId,
            location_id: '00000000-0000-0000-0000-000000000005',
            physical_quantity: 7,
          },
        ],
      },
    },
  )
  expect(response.status()).toBe(403)
  expect((await response.json()).error.code).toBe('FORBIDDEN')
})
