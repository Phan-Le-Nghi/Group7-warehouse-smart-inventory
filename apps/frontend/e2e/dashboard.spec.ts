import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

async function signIn(page: Page, loginIdentifier: string) {
  await page.goto('/')
  await page.getByLabel('Login identifier').fill(loginIdentifier)
  await page.getByLabel('Password').fill(process.env.E2E_USER_PASSWORD ?? '')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(
    page.getByRole('heading', { name: 'Warehouse Dashboard' }),
  ).toBeVisible()
}

test('Warehouse Staff Dashboard exposes only generic Staff actions', async ({
  page,
}) => {
  await signIn(page, 'demo.warehouse_staff')

  await expect(page.getByRole('link', { name: /Open Receive/ })).toBeVisible()
  await expect(page.getByRole('link', { name: /Open Putaway/ })).toBeVisible()
  await expect(page.getByRole('link', { name: /Open New Audit/ })).toBeVisible()
  await expect(page.getByRole('link', { name: /Open Adjust Requests/ })).toBeVisible()
  await expect(page.getByText('Transfer History')).toHaveCount(0)
  await expect(page.getByText('Adjust Decisions')).toHaveCount(0)
  await page.getByRole('link', { name: /Open Adjust Requests/ }).click()
  await expect(page).toHaveURL(/\/adjustments$/)
  await expect(page.getByRole('heading', { name: 'Adjust Requests' })).toBeVisible()
})

test('Manager Dashboard exposes only Manager queues and history', async ({ page }) => {
  await signIn(page, 'demo.manager')

  await expect(
    page.getByRole('link', { name: /Open Transfer History/ }),
  ).toBeVisible()
  await expect(
    page.getByRole('link', { name: /Open Audit Discrepancies/ }),
  ).toBeVisible()
  await expect(
    page.getByRole('link', { name: /Open Adjust Decisions/ }),
  ).toBeVisible()
  await expect(page.getByText('Putaway')).toHaveCount(0)
  await expect(page.getByText('New Audit')).toHaveCount(0)
  await expect(page.getByRole('link', { name: /Open Adjust Requests/ })).toHaveCount(0)
})

for (const loginIdentifier of ['demo.purchasing', 'demo.admin']) {
  test(`${loginIdentifier} Dashboard has no invented actions`, async ({ page }) => {
    await signIn(page, loginIdentifier)

    await expect(
      page.getByText(
        'No dashboard actions are available for this role in the current MVP.',
      ),
    ).toBeVisible()
    await expect(page.getByText('Receive')).toHaveCount(0)
    await expect(page.getByText('Transfer History')).toHaveCount(0)
    await expect(page.getByRole('link', { name: /Open Adjust Requests/ })).toHaveCount(0)
  })
}
