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
    adjust_request_count: number
  }
}

async function signIn(page: Page, path: string, login: string) {
  await page.goto(path)
  await page.getByLabel('Login identifier').fill(login)
  await page.getByLabel('Password').fill(process.env.E2E_USER_PASSWORD ?? '')
  await page.getByRole('button', { name: 'Sign in' }).click()
}

async function prepareMismatchRecheck(page: Page) {
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
  await page
    .getByRole('button', {
      name: 'Review AUDIT-SKU-MISSING-BALANCE at SALES_SHELF',
    })
    .click()
  await page.getByLabel('Recheck physical quantity').fill('2')
  await page.getByRole('button', { name: 'Record Manager recheck' }).click()
  await expect(page.getByRole('heading', { name: 'MISMATCH' })).toBeVisible()

  const listResponse = await page.request.get(
    'http://127.0.0.1:8000/api/v1/audit-discrepancies',
  )
  const lineId = (await listResponse.json()).items[0].audit_line_id as string
  const detailResponse = await page.request.get(
    `http://127.0.0.1:8000/api/v1/audit-discrepancies/${lineId}`,
  )
  return (await detailResponse.json()).recheck.recheck_id as string
}

async function openAsStaff(page: Page, recheckId: string) {
  await page.getByRole('button', { name: 'Sign out' }).click()
  await signIn(
    page,
    `/adjustments/${encodeURIComponent(recheckId)}`,
    'demo.warehouse_staff',
  )
  await expect(
    page.getByRole('heading', { name: 'Create Adjust request' }),
  ).toBeVisible()
}

test('TEST-ADJ1-E2E-001 Staff creates and reloads an immutable Adjust request', async ({
  page,
}) => {
  const recheckId = await prepareMismatchRecheck(page)
  const before = snapshot()
  await openAsStaff(page, recheckId)
  await expect(page.getByTestId('requested-change')).toHaveText('+2')
  await page.getByLabel('Reason').fill('Count confirmed after Manager recheck')
  await page.getByRole('button', { name: 'Create Adjust request' }).click()
  await expect(
    page.getByRole('heading', { name: 'PENDING_MANAGER_DECISION' }),
  ).toBeVisible()
  await expect(page.getByText(/Stock was not changed/)).toBeVisible()

  await page.reload()
  await expect(
    page.getByRole('heading', { name: 'PENDING_MANAGER_DECISION' }),
  ).toBeVisible()
  const after = snapshot()
  expect(after.business_state_digest).toBe(before.business_state_digest)
  expect(after.audit_count).toBe(before.audit_count)
  expect(after.audit_line_count).toBe(before.audit_line_count)
  expect(after.audit_recheck_count).toBe(before.audit_recheck_count)
  expect(after.adjust_request_count).toBe(1)
})

test('TEST-ADJ1-E2E-002 lost response replays and a different key cannot duplicate', async ({
  page,
}) => {
  const recheckId = await prepareMismatchRecheck(page)
  await openAsStaff(page, recheckId)
  let intercepted = false
  await page.route('**/api/v1/adjustments', async (route) => {
    if (route.request().method() !== 'POST' || intercepted) {
      await route.continue()
      return
    }
    intercepted = true
    await route.fetch()
    await route.abort('failed')
  })
  await page.getByLabel('Reason').fill('Stable retry reason')
  await page.getByRole('button', { name: 'Create Adjust request' }).click()
  await expect(page.getByRole('alert')).toContainText('Failed to fetch')
  await page.unroute('**/api/v1/adjustments')
  await page.getByRole('button', { name: 'Create Adjust request' }).click()
  await expect(
    page.getByRole('heading', { name: 'PENDING_MANAGER_DECISION' }),
  ).toBeVisible()
  expect(snapshot().adjust_request_count).toBe(1)

  const duplicate = await page.request.post(
    'http://127.0.0.1:8000/api/v1/adjustments',
    {
      headers: { 'Idempotency-Key': 'different-browser-key' },
      data: {
        audit_recheck_id: recheckId,
        reason: 'Stable retry reason',
      },
    },
  )
  expect(duplicate.status()).toBe(409)
  expect((await duplicate.json()).error.code).toBe(
    'ADJUSTMENT_ALREADY_EXISTS',
  )
  expect(snapshot().adjust_request_count).toBe(1)
})

test('TEST-ADJ1-E2E-003 Manager receives real backend 403 responses', async ({
  page,
}) => {
  const recheckId = await prepareMismatchRecheck(page)
  await page.goto(`/adjustments/${encodeURIComponent(recheckId)}`)
  await expect(page.getByRole('alert')).toContainText(
    'Warehouse Staff role required',
  )
  const contextResponse = await page.request.get(
    `http://127.0.0.1:8000/api/v1/adjustments/context/${recheckId}`,
  )
  expect(contextResponse.status()).toBe(403)
  const createResponse = await page.request.post(
    'http://127.0.0.1:8000/api/v1/adjustments',
    {
      headers: { 'Idempotency-Key': 'manager-forbidden' },
      data: { audit_recheck_id: recheckId, reason: 'Forbidden' },
    },
  )
  expect(createResponse.status()).toBe(403)
  expect(snapshot().adjust_request_count).toBe(0)
})
