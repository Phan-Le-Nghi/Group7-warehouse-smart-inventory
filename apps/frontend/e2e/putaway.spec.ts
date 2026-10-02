import { expect, test } from '@playwright/test'

test('TEST-PUT-E2E-001 confirms 16 units into Backroom', async ({ page }) => {
  await page.goto('/putaway')
  await page.getByLabel('Login identifier').fill('demo.warehouse_staff')
  await page.getByLabel('Password').fill(process.env.E2E_USER_PASSWORD ?? '')
  await page.getByRole('button', { name: 'Sign in' }).click()

  await expect(page.getByText('SKU-001')).toBeVisible()
  await expect(page.getByText('16')).toBeVisible()
  await page.getByRole('radio', { name: /Backroom/i }).check()
  await page.getByRole('button', { name: 'Confirm Putaway' }).click()

  await expect(
    page.getByRole('heading', { name: '16 units placed in Backroom' }),
  ).toBeVisible()
  await expect(page.getByText('Putaway confirmed')).toBeVisible()
})

test('Manager direct Putaway route receives backend 403 from context GET', async ({
  page,
}) => {
  await page.goto('/putaway')
  await page.getByLabel('Login identifier').fill('demo.manager')
  await page.getByLabel('Password').fill(process.env.E2E_USER_PASSWORD ?? '')
  const forbiddenResponse = page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/putaways/context/') &&
      response.request().method() === 'GET',
  )
  await page.getByRole('button', { name: 'Sign in' }).click()

  const response = await forbiddenResponse
  expect(response.status()).toBe(403)
  const errorBody = (await response.json()) as {
    error: {
      code: string
      message: string
      details: { required_roles: string[] }
    }
  }
  expect(errorBody.error.code).toBe('FORBIDDEN')
  expect(errorBody.error.details.required_roles).toEqual(['WAREHOUSE_STAFF'])
  await expect(page.getByRole('alert')).toHaveText(errorBody.error.message)
})
