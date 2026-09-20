import { expect, test } from '@playwright/test'

test('TEST-PUT-E2E-001 confirms 16 units into Backroom', async ({ page }) => {
  await page.goto('/')
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
