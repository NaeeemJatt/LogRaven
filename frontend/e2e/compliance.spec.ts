import { expect, test } from '@playwright/test'
import { fulfillJson, mockApi } from './mockApi'

test('user can submit a compliance audit with mocked collection', async ({ page }) => {
  let submittedAudit: Record<string, unknown> | undefined
  const control = {
    control_id: 'CC6.1',
    control_name: 'Logical access controls',
    status: 'PASS',
    confidence: 'HIGH',
    ai_description: 'Mocked evidence satisfies this control.',
    gaps: [],
    evidence_references: ['mock://iam'],
    framework: 'soc2',
    category: 'Security',
    automatable: true,
    remediation: null,
  }

  await mockApi(page, {
    authenticated: true,
    handleApi: async (route, url) => {
      const request = route.request()

      if (url.pathname === '/api/v1/compliance/frameworks') {
        await fulfillJson(route, [
          {
            id: 'soc2',
            name: 'SOC 2 Type II',
            version: '2017',
            description: 'Trust Services Criteria',
            control_count: 1,
            automatable_count: 1,
          },
        ])
        return true
      }

      if (url.pathname === '/api/v1/audit/start' && request.method() === 'POST') {
        submittedAudit = request.postDataJSON() as Record<string, unknown>
        await fulfillJson(
          route,
          {
            audit_id: 'audit-1',
            status: 'pending',
            message: 'Audit queued',
          },
          202,
        )
        return true
      }

      if (url.pathname === '/api/v1/audit/audit-1/status') {
        await fulfillJson(route, {
          audit_id: 'audit-1',
          status: 'complete',
          percent: 100,
          company_name: 'Acme Security',
          frameworks: ['soc2'],
          controls_assessed: 1,
          pass_count: 1,
          fail_count: 0,
          partial_count: 0,
          score_percent: 100,
          results: [control],
          framework_results: [
            {
              framework_id: 'soc2',
              framework_name: 'SOC 2 Type II',
              controls_assessed: 1,
              pass_count: 1,
              fail_count: 0,
              partial_count: 0,
              score_percent: 100,
              results: [control],
            },
          ],
        })
        return true
      }

      return false
    },
  })

  await page.goto('/compliance')
  await page.getByLabel('Company name').fill('Acme Security')
  await page.getByLabel('IAM role ARN').fill('arn:aws:iam::123456789012:role/LogRavenAudit')
  await page.getByLabel('Start date').fill('2024-01-01')
  await page.getByLabel('End date').fill('2024-02-01')
  await page.getByRole('button', { name: 'Run compliance audit (1)' }).click()

  await expect(page.getByRole('button', { name: /Control browser/ })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Logical access controls' })).toBeVisible()
  expect(submittedAudit).toEqual({
    company_name: 'Acme Security',
    role_arn: 'arn:aws:iam::123456789012:role/LogRavenAudit',
    audit_start_date: '2024-01-01',
    audit_end_date: '2024-02-01',
    frameworks: ['soc2'],
    recurrence: 'none',
  })
})
