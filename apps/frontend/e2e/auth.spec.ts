import { expect, test } from '@playwright/test'

test('session login, current actor, and logout work in the browser', async ({
  page,
}) => {
  await page.goto('/')
  await page.getByLabel('Login identifier').fill('demo.warehouse_staff')
  await page.getByLabel('Password').fill(process.env.E2E_USER_PASSWORD ?? '')
  await page.getByRole('button', { name: 'Sign in' }).click()

  await expect(page.getByText('Warehouse Staff')).toBeVisible()
  await page.getByRole('button', { name: 'Sign out' }).click()
  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()

  const meResponse = await page.request.get('http://127.0.0.1:8000/api/v1/auth/me')
  expect(meResponse.status()).toBe(401)
})
