import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { investigationsApi } from '../api/investigations'
import type { Investigation as InvestigationData } from '../types/investigation'
import Investigation from './Investigation'

vi.mock('../api/investigations', () => ({
  investigationsApi: {
    get: vi.fn(),
    update: vi.fn(),
    uploadFile: vi.fn(),
    deleteFile: vi.fn(),
    analyze: vi.fn(),
  },
}))

const draftInvestigation: InvestigationData = {
  id: 'investigation-1',
  name: 'Authentication review',
  status: 'draft',
  correlation_enabled: true,
  cloud_ai_enabled: false,
  files: [],
  created_at: '2026-07-10T12:00:00',
  queued_at: null,
  findings_count: 0,
  severity_summary: {},
}

function renderPage(investigation: InvestigationData) {
  vi.mocked(investigationsApi.get).mockResolvedValue({
    data: investigation,
  } as Awaited<ReturnType<typeof investigationsApi.get>>)

  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/investigations/investigation-1']}>
        <Routes>
          <Route path="/investigations/:id" element={<Investigation />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Investigation correlation control', () => {
  beforeEach(() => {
    vi.mocked(investigationsApi.get).mockReset()
    vi.mocked(investigationsApi.update).mockReset()
  })

  it('lets draft investigations disable correlation with an accessible control', async () => {
    const user = userEvent.setup()
    vi.mocked(investigationsApi.update).mockResolvedValue({
      data: { ...draftInvestigation, correlation_enabled: false },
    } as Awaited<ReturnType<typeof investigationsApi.update>>)
    renderPage(draftInvestigation)

    const control = await screen.findByRole('checkbox', { name: 'Cross-file correlation' })
    expect(control).toBeChecked()

    await user.click(control)

    expect(investigationsApi.update).toHaveBeenCalledWith('investigation-1', {
      correlation_enabled: false,
    })
    await vi.waitFor(() => expect(control).not.toBeChecked())
  })

  it('shows read-only correlation status after analysis starts', async () => {
    renderPage({ ...draftInvestigation, status: 'complete' })

    expect(await screen.findByText('Authentication review')).toBeInTheDocument()
    expect(
      screen.queryByRole('checkbox', { name: 'Cross-file correlation' }),
    ).not.toBeInTheDocument()
    expect(screen.getByText('On')).toBeInTheDocument()
  })
})
