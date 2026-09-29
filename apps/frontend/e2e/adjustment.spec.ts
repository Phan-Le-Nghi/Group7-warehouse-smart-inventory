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
    adjust_statuses: string[]
    adjust_stock_quantity: number
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

async function createPendingAdjustment(page: Page) {
  const recheckId = await prepareMismatchRecheck(page)
  await openAsStaff(page, recheckId)
  await page.getByLabel('Reason').fill('Manager decision E2E evidence')
  await page.getByRole('button', { name: 'Create Adjust request' }).click()
  await expect(
    page.getByRole('heading', { name: 'PENDING_MANAGER_DECISION' }),
  ).toBeVisible()
  const context = await page.request.get(
    `http://127.0.0.1:8000/api/v1/adjustments/context/${recheckId}`,
  )
  const adjustmentId = (await context.json()).existing_adjustment
    .adjustment_id as string
  await page.getByRole('button', { name: 'Sign out' }).click()
  await signIn(page, '/adjustment-decisions', 'demo.manager')
  return { adjustmentId, recheckId }
}

test('TEST-ADJ2-E2E-001 Manager approves once and reloads APPLIED', async ({
  page,
}) => {
  const { adjustmentId, recheckId } = await createPendingAdjustment(page)
  await page.getByRole('button', { name: /Review AUDIT-SKU-MISSING-BALANCE/ }).click()
  await page.getByRole('button', { name: 'Approve' }).click()
  let intercepted = false
  await page.route('**/api/v1/adjustments/*/decision', async (route) => {
    if (intercepted) {
      await route.continue()
      return
    }
    intercepted = true
    await route.fetch()
    await route.abort('failed')
  })
  await page.getByRole('button', { name: 'Confirm approval' }).click()
  await expect(page.getByRole('alert')).toContainText('Failed to fetch')
  await page.unroute('**/api/v1/adjustments/*/decision')
  await page.getByRole('button', { name: 'Confirm approval' }).click()
  await expect(page.getByRole('heading', { name: 'APPLIED' })).toBeVisible()
  expect(snapshot().adjust_stock_quantity).toBe(2)
  expect(snapshot().adjust_statuses).toEqual(['APPLIED'])

  await page.reload()
  await expect(page.getByRole('heading', { name: 'APPLIED' })).toBeVisible()
  expect(new URL(page.url()).searchParams.get('adjustment_id')).toBe(adjustmentId)
  expect(snapshot().adjust_stock_quantity).toBe(2)

  await page.getByRole('button', { name: 'Sign out' }).click()
  await signIn(
    page,
    `/adjustments/${encodeURIComponent(recheckId)}`,
    'demo.warehouse_staff',
  )
  await expect(page.getByRole('heading', { name: 'APPLIED' })).toBeVisible()
  await expect(page.getByText(/approved and applied this request/)).toBeVisible()
  await page.reload()
  await expect(page.getByRole('heading', { name: 'APPLIED' })).toBeVisible()
  await expect(page.getByText(/approved and applied this request/)).toBeVisible()
})

test('TEST-ADJ2-E2E-002 Manager rejects without changing stock', async ({ page }) => {
  const { recheckId } = await createPendingAdjustment(page)
  await page.getByRole('button', { name: /Review AUDIT-SKU-MISSING-BALANCE/ }).click()
  await page.getByRole('button', { name: 'Reject' }).click()
  await page.getByLabel('Rejection reason').fill('Evidence is not accepted')
  await page.getByRole('button', { name: 'Confirm rejection' }).click()
  await expect(page.getByRole('heading', { name: 'REJECTED' })).toBeVisible()
  expect(snapshot().adjust_stock_quantity).toBe(0)
  expect(snapshot().adjust_statuses).toEqual(['REJECTED'])
  await page.reload()
  await expect(page.getByRole('heading', { name: 'REJECTED' })).toBeVisible()

  await page.getByRole('button', { name: 'Sign out' }).click()
  await signIn(
    page,
    `/adjustments/${encodeURIComponent(recheckId)}`,
    'demo.warehouse_staff',
  )
  await expect(page.getByRole('heading', { name: 'REJECTED' })).toBeVisible()
  await expect(page.getByText(/No adjustment was applied/)).toBeVisible()
  await page.reload()
  await expect(page.getByRole('heading', { name: 'REJECTED' })).toBeVisible()
  await expect(page.getByText(/No adjustment was applied/)).toBeVisible()
})

test('TEST-ADJ2-E2E-004 stale approval stays pending without decision evidence', async ({
  page,
}) => {
  const { adjustmentId } = await createPendingAdjustment(page)

  await page.getByRole('button', { name: 'Sign out' }).click()
  await signIn(page, '/audits/new', 'demo.warehouse_staff')
  const transfer = await page.request.post(
    'http://127.0.0.1:8000/api/v1/transfers',
    {
      headers: { 'Idempotency-Key': 'adjustment-stale-approved-transfer' },
      data: {
        sku_id: '00000000-0000-0000-0000-000000000502',
        source_location_id: '00000000-0000-0000-0000-000000000005',
        destination_location_id: '00000000-0000-0000-0000-000000000006',
        quantity: 1,
      },
    },
  )
  expect(transfer.status()).toBe(201)
  const beforeApproval = snapshot()
  await page.getByRole('button', { name: 'Sign out' }).click()
  await signIn(page, '/adjustment-decisions', 'demo.manager')
  await page.getByRole('button', { name: /Review AUDIT-SKU-MISSING-BALANCE/ }).click()

  await page.getByRole('button', { name: 'Approve' }).click()
  const decisionResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith(`/api/v1/adjustments/${adjustmentId}/decision`) &&
      response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Confirm approval' }).click()
  const stale = await decisionResponse
  expect(stale.status()).toBe(409)
  expect((await stale.json()).error.code).toBe('ADJUSTMENT_STALE')
  await expect(page.getByRole('alert')).toContainText(
    'Current stock no longer matches the recheck snapshot',
  )

  const afterApproval = snapshot()
  expect(afterApproval.adjust_stock_quantity).toBe(beforeApproval.adjust_stock_quantity)
  expect(afterApproval.adjust_statuses).toEqual(['PENDING_MANAGER_DECISION'])

  const detailResponse = await page.request.get(
    `http://127.0.0.1:8000/api/v1/adjustments/${adjustmentId}`,
  )
  expect(detailResponse.status()).toBe(200)
  const detail = await detailResponse.json()
  expect(detail.status).toBe('PENDING_MANAGER_DECISION')
  expect(detail.decided_by).toBeNull()
  expect(detail.decided_at).toBeNull()
  expect(detail.applied_stock_before).toBeNull()
  expect(detail.applied_stock_after).toBeNull()

  await page.reload()
  await expect(page.getByRole('heading', { name: 'PENDING_MANAGER_DECISION' })).toBeVisible()
  expect(snapshot().adjust_stock_quantity).toBe(beforeApproval.adjust_stock_quantity)
})

test('TEST-ADJ2-E2E-003 Warehouse Staff receives real backend 403', async ({
  page,
}) => {
  backendCommand('--audit-reset')
  await signIn(page, '/adjustment-decisions', 'demo.warehouse_staff')
  await expect(page.getByRole('alert')).toContainText('Manager role required')
  const response = await page.request.get(
    'http://127.0.0.1:8000/api/v1/adjustments?status=PENDING_MANAGER_DECISION',
  )
  expect(response.status()).toBe(403)
})
