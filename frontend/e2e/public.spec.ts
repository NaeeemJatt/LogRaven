import { expect, test } from '@playwright/test'
import { mockApi } from './mockApi'

const publicRoutes = [
  { path: '/', heading: 'Watch your logs.' },
  { path: '/login', heading: 'Welcome back' },
  { path: '/register', heading: 'Create account' },
  { path: '/forgot-password', heading: 'Reset your password' },
  { path: '/reset-password', heading: 'Invalid link' },
  { path: '/verify-email', heading: 'Verification failed' },
  { path: '/privacy', heading: 'Privacy Policy' },
  { path: '/terms', heading: 'Terms of Service' },
]

test.describe('public routes', () => {
  for (const route of publicRoutes) {
    test(`${route.path} renders without a backend`, async ({ page }) => {
      await mockApi(page)

      await page.goto(route.path)

      await expect(page.getByRole('heading', { name: route.heading, exact: false })).toBeVisible()
      expect(new URL(page.url()).pathname).toBe(route.path)
      if (route.path === '/privacy') {
        await expect(page.getByRole('link', { name: 'Terms' })).toHaveAttribute('href', '/terms')
      }
      if (route.path === '/terms') {
        await expect(page.getByRole('link', { name: 'Privacy' })).toHaveAttribute(
          'href',
          '/privacy',
        )
      }
    })
  }
})

test('legal and contact links stay visible on mobile public screens', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await mockApi(page)

  for (const path of [
    '/',
    '/login',
    '/register',
    '/forgot-password',
    '/reset-password',
    '/verify-email',
    '/shared/audit/expired',
  ]) {
    await page.goto(path)
    await expect(page.getByRole('link', { name: 'Privacy' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Terms' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Contact' })).toHaveAttribute(
      'href',
      'mailto:support@lograven.io',
    )
  }
})

test('landing copy describes consent, polling, and twelve frameworks honestly', async ({
  page,
}) => {
  await mockApi(page)
  await page.goto('/')

  await expect(page.getByText(/explicitly consent to optional cloud AI/i)).toBeVisible()
  await expect(page.getByText(/refreshes every 2 seconds/i)).toBeVisible()
  await expect(page.getByText(/across 12 frameworks/i)).toBeVisible()
  await expect(page.getByText(/results stream in real-time/i)).toHaveCount(0)
})
