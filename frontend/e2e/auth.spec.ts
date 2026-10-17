import { expect, test } from '@playwright/test'
import { mockApi } from './mockApi'

test('user can sign in with a mocked session', async ({ page }) => {
  let submittedCredentials: { email: string; password: string } | undefined
  await mockApi(page, {
    onLogin: (credentials) => {
      submittedCredentials = credentials
    },
  })
  await page.goto('/login')

  await page.getByPlaceholder('operator@example.com').fill('analyst@example.com')
  await page.getByPlaceholder('••••••••••••').fill('correct-horse-battery-staple')
  await page.getByRole('button', { name: 'Sign In' }).click()

  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(page.getByRole('heading', { name: 'Investigations', exact: true })).toBeVisible()
  expect(submittedCredentials).toEqual({
    email: 'analyst@example.com',
    password: 'correct-horse-battery-staple',
  })
})
