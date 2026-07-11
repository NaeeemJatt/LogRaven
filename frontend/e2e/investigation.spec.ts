import { expect, test } from '@playwright/test'
import { fulfillJson, mockApi } from './mockApi'

test('user can create, upload to, and delete an investigation', async ({ page }) => {
  const investigation = {
    id: 'investigation-1',
    name: 'Mocked incident',
    status: 'draft',
    correlation_enabled: true,
    cloud_ai_enabled: false,
    files: [] as Array<Record<string, unknown>>,
    created_at: '2026-07-10T09:00:00Z',
    findings_count: 0,
    severity_summary: {},
  }
  let deleted = false
  let createdName: string | undefined

  await mockApi(page, {
    authenticated: true,
    handleApi: async (route, url) => {
      const request = route.request()

      if (url.pathname === '/api/v1/investigations' && request.method() === 'POST') {
        createdName = (request.postDataJSON() as { name: string }).name
        investigation.name = createdName
        await fulfillJson(route, investigation, 201)
        return true
      }

      if (url.pathname === '/api/v1/investigations' && request.method() === 'GET') {
        await fulfillJson(route, deleted ? [] : [investigation])
        return true
      }

      if (url.pathname === `/api/v1/investigations/${investigation.id}`) {
        if (request.method() === 'DELETE') {
          deleted = true
          await fulfillJson(route, {}, 204)
        } else {
          await fulfillJson(route, investigation)
        }
        return true
      }

      if (
        url.pathname === `/api/v1/investigations/${investigation.id}/files` &&
        request.method() === 'POST'
      ) {
        investigation.files = [
          {
            id: 'file-1',
            filename: 'security.log',
            source_type: 'linux_endpoint',
            log_type: 'syslog',
            status: 'parsed',
            event_count: 1,
          },
        ]
        await fulfillJson(route, investigation.files[0], 201)
        return true
      }

      return false
    },
  })

  await page.goto('/investigations/new')
  await page.getByPlaceholder('e.g. Prod server incident — May 28').fill('Mocked incident')
  await page.getByRole('button', { name: 'Continue to upload' }).click()

  await expect(page).toHaveURL(/\/investigations\/investigation-1$/)
  await expect(page.getByRole('heading', { name: 'Mocked incident' })).toBeVisible()
  expect(createdName).toBe('Mocked incident')

  await page.locator('input[type="file"]').setInputFiles({
    name: 'security.log',
    mimeType: 'text/plain',
    buffer: Buffer.from('Jul 10 host sshd: accepted publickey'),
  })
  await page.getByRole('button', { name: 'Upload 1 file' }).click()
  await expect(page.getByText('Uploaded files (1)')).toBeVisible()

  await page.goto('/dashboard')
  const row = page.getByRole('row').filter({ hasText: 'Mocked incident' })
  await row.hover()
  await row.getByRole('button', { name: 'Delete Mocked incident' }).click()
  await page.getByRole('dialog').getByRole('button', { name: 'Delete' }).click()

  await expect(page.getByText('No investigations yet')).toBeVisible()
  expect(deleted).toBe(true)
})
