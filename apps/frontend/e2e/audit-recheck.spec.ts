import { execFileSync } from 'node:child_process'
import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

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
    audit_recheck_count: number
    missing_balance_count: number
  }
}

async function signIn(page: Page, path: string, login: string) {
  await page.goto(path)
  await page.getByLabel('Login identifier').fill(login)
  await page.getByLabel('Password').fill(process.env.E2E_USER_PASSWORD ?? '')
  await page.getByRole('button', { name: 'Sign in' }).click()
}

async function prepareStaffMismatchAndManager(page: Page) {
  backendCommand('--audit-reset')
  await signIn(page, '/audits/new', 'demo.warehouse_staff')
  await page
    .getByLabel('Count AUDIT-SKU-MISSING-BALANCE at SALES_SHELF')
    .check()
  await page
    .getByLabel(
      'Physical quantity for AUDIT-SKU-MISSING-BALANCE at SALES_SHELF',
    )
    .fill('3')
  await page.getByRole('button', { name: 'Record Audit' }).click()
  await expect(page.getByText('Discrepancy recorded')).toBeVisible()
  await page.getByRole('button', { name: 'Sign out' }).click()
  await signIn(page, '/audit-discrepancies', 'demo.manager')
  await expect(
    page.getByRole('heading', { name: 'Audit discrepancies' }),
  ).toBeVisible()
  await page
    .getByRole('button', {
      name: 'Review AUDIT-SKU-MISSING-BALANCE at SALES_SHELF',
    })
    .click()
}

test('TEST-AUD2-E2E-001 Manager rechecks a Staff mismatch to Match', async ({
  page,
}) => {
  await prepareStaffMismatchAndManager(page)
  const before = snapshot()
  await page.getByLabel('Recheck physical quantity').fill('0')
  await page.getByRole('button', { name: 'Record Manager recheck' }).click()
  await expect(page.getByRole('heading', { name: 'MATCH' })).toBeVisible()
  await expect(page.getByText(/Stock was not changed/)).toBeVisible()
  const after = snapshot()
  expect(after.business_state_digest).toBe(before.business_state_digest)
  expect(after.audit_count).toBe(before.audit_count)
  expect(after.audit_line_count).toBe(before.audit_line_count)
  expect(after.audit_recheck_count).toBe(1)
  expect(after.missing_balance_count).toBe(0)
})

test('TEST-AUD2-E2E-002 Manager records a still-mismatching recheck', async ({
  page,
}) => {
  await prepareStaffMismatchAndManager(page)
  const before = snapshot()
  await page.getByLabel('Recheck physical quantity').fill('2')
  await page.getByRole('button', { name: 'Record Manager recheck' }).click()
  await expect(page.getByRole('heading', { name: 'MISMATCH' })).toBeVisible()
  await expect(
    page.getByText(/eligible context for future Adjust work/),
  ).toBeVisible()
  const after = snapshot()
  expect(after.business_state_digest).toBe(before.business_state_digest)
  expect(after.audit_recheck_count).toBe(1)
})

test('TEST-AUD2-E2E-003 lost response safely replays one recheck', async ({
  page,
}) => {
  await prepareStaffMismatchAndManager(page)
  let intercepted = false
  await page.route('**/api/v1/audit-discrepancies/*/rechecks', async (route) => {
    if (intercepted) {
      await route.continue()
      return
    }
    intercepted = true
    await route.fetch()
    await route.abort('failed')
  })
  await page.getByLabel('Recheck physical quantity').fill('0')
  await page.getByRole('button', { name: 'Record Manager recheck' }).click()
  await expect(page.getByRole('alert')).toContainText('Failed to fetch')
  await page.unroute('**/api/v1/audit-discrepancies/*/rechecks')
  await page.getByRole('button', { name: 'Record Manager recheck' }).click()
  await expect(page.getByRole('heading', { name: 'MATCH' })).toBeVisible()
  expect(snapshot().audit_recheck_count).toBe(1)
})

test('TEST-AUD2-E2E-004 different key cannot create a second recheck', async ({
  page,
}) => {
  await prepareStaffMismatchAndManager(page)
  const listResponse = await page.request.get(
    'http://127.0.0.1:8000/api/v1/audit-discrepancies',
  )
  const lineId = (await listResponse.json()).items[0].audit_line_id as string
  await page.getByLabel('Recheck physical quantity').fill('0')
  await page.getByRole('button', { name: 'Record Manager recheck' }).click()
  await expect(page.getByRole('heading', { name: 'MATCH' })).toBeVisible()
  const duplicate = await page.request.post(
    `http://127.0.0.1:8000/api/v1/audit-discrepancies/${lineId}/rechecks`,
    {
      headers: { 'Idempotency-Key': 'different-browser-key' },
      data: { recheck_physical_quantity: 0 },
    },
  )
  expect(duplicate.status()).toBe(409)
  expect((await duplicate.json()).error.code).toBe('RECHECK_ALREADY_RECORDED')
  expect(snapshot().audit_recheck_count).toBe(1)
})

test('TEST-AUD2-E2E-005 Warehouse Staff receives a real backend 403', async ({
  page,
}) => {
  backendCommand('--audit-reset')
  await signIn(page, '/audit-discrepancies', 'demo.warehouse_staff')
  await expect(page.getByRole('alert')).toContainText('Manager role required')
  const response = await page.request.get(
    'http://127.0.0.1:8000/api/v1/audit-discrepancies',
  )
  expect(response.status()).toBe(403)
  expect((await response.json()).error.code).toBe('FORBIDDEN')
})
