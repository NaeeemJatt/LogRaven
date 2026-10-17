import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { investigationsApi, findingsApi } from '../api/investigations'
import { authApi } from '../api/auth'
import LegalLinks from '../components/layout/LegalLinks'
import Navbar from '../components/layout/Navbar'
import { useAuthStore } from '../store/authStore'
import AlertFeed from './AlertFeed'
import Dashboard from './Dashboard'
import JobStatus from './JobStatus'
import VerifyEmail from './Auth/VerifyEmail'

const { jobStatusMock } = vi.hoisted(() => ({
  jobStatusMock: vi.fn(),
}))

vi.mock('../hooks/useJobStatus', () => ({
  useJobStatus: jobStatusMock,
}))

vi.mock('../api/investigations', () => ({
  investigationsApi: {
    list: vi.fn(),
    getDashboardStats: vi.fn(),
    delete: vi.fn(),
    getStatus: vi.fn(),
  },
  findingsApi: {
    list: vi.fn(),
  },
}))

vi.mock('../api/auth', () => ({
  authApi: {
    verifyEmail: vi.fn(),
  },
}))

function renderWithClient(ui: React.ReactNode, path = '/') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
}

const finding = {
  id: 'finding-1',
  report_id: 'report-1',
  title: 'Suspicious login',
  severity: 'high' as const,
  finding_type: 'single',
  description: 'Repeated failed authentication',
  mitre_technique_id: 'T1110',
  source_files: ['auth.log'],
  confidence: 0.9,
  created_at: '2026-07-10T12:00:00Z',
  investigation: {
    id: 'investigation-1',
    name: 'Authentication review',
    created_at: '2026-07-10T11:00:00Z',
  },
}

describe('frontend product gaps', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.getState().logout()
  })

  it('loads findings directly and opens a dismissible mobile inspector', async () => {
    const user = userEvent.setup()
    vi.mocked(findingsApi.list).mockResolvedValue({
      items: [finding],
      page: 1,
      limit: 20,
      total: 1,
      total_pages: 1,
      severity_counts: { high: 1 },
    })

    renderWithClient(<AlertFeed />)

    await user.click(await screen.findByRole('button', { name: /Suspicious login/i }))
    expect(screen.getByRole('dialog', { name: 'Finding inspector' })).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Close finding inspector' }))
    await waitFor(() =>
      expect(screen.queryByRole('dialog', { name: 'Finding inspector' })).not.toBeInTheDocument(),
    )
    expect(findingsApi.list).toHaveBeenCalledWith({
      page: 1,
      limit: 20,
      severity: undefined,
      search: undefined,
    })
  })

  it('shows an explicit retry state when findings cannot be loaded', async () => {
    vi.mocked(findingsApi.list).mockRejectedValue(new Error('offline'))

    renderWithClient(<AlertFeed />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Findings could not be loaded')
    expect(screen.queryByText('Queue is clear')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry' })).toBeVisible()
  })

  it('requests the next dashboard page while keeping account-wide stats separate', async () => {
    const user = userEvent.setup()
    vi.mocked(investigationsApi.list).mockResolvedValue({
      items: [],
      page: 1,
      limit: 20,
      total: 21,
      totalPages: 2,
    })
    vi.mocked(investigationsApi.getDashboardStats).mockResolvedValue({
      total_investigations: 21,
      active_investigations: 1,
      files_analyzed: 3,
      avg_analysis_time: '2m',
      status_counts: { complete: 19, processing: 1, failed: 1 },
      severity_counts: { critical: 4, high: 5 },
      recent_investigation_dates: [],
      recent_daily_counts: {},
    })

    renderWithClient(<Dashboard />)

    expect(await screen.findByText('21')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Next page' }))
    await waitFor(() =>
      expect(investigationsApi.list).toHaveBeenLastCalledWith({
        page: 2,
        limit: 20,
        search: undefined,
        sort: 'created_at',
        direction: 'desc',
      }),
    )
  })

  it('does not claim nominal threat posture when dashboard stats fail', async () => {
    vi.mocked(investigationsApi.list).mockResolvedValue({
      items: [],
      page: 1,
      limit: 20,
      total: 0,
      totalPages: 0,
    })
    vi.mocked(investigationsApi.getDashboardStats).mockRejectedValue(new Error('offline'))

    renderWithClient(<Dashboard />)

    expect(await screen.findByRole('alert')).toHaveTextContent('threat posture are unavailable')
    expect(screen.queryByText('Nominal')).not.toBeInTheDocument()
  })

  it('gates report navigation until completion and shows parser metadata', () => {
    jobStatusMock.mockReturnValue({
      status: 'processing',
      progressStage: 'parsing',
      errorMessage: null,
      files: [
        {
          id: 'file-1',
          filename: 'auth.log',
          source_type: 'linux_endpoint',
          status: 'parsed',
          event_count: 4,
          parser_detection_confidence: 0.92,
          parser_selection_detail: {
            requested_ingestion_mode: 'decoders',
            actual_ingestion_path: 'parsers',
            fallback_used: true,
            user_warnings: ['Decoder unavailable; native parser used.'],
          },
        },
      ],
      isLoading: false,
      isError: false,
      isComplete: false,
      isFailed: false,
      isDraft: false,
    })

    renderWithClient(
      <Routes>
        <Route path="/investigations/:id/status" element={<JobStatus />} />
      </Routes>,
      '/investigations/investigation-1/status',
    )

    expect(screen.queryByRole('link', { name: /View report/i })).not.toBeInTheDocument()
    expect(screen.getByText('92% confidence')).toBeVisible()
    expect(screen.getByText(/Decoders → Parsers/i)).toBeVisible()
    expect(screen.getByText('Decoder unavailable; native parser used.')).toBeVisible()
  })

  it('uses authenticated and anonymous verification destinations with a live status', async () => {
    vi.mocked(authApi.verifyEmail).mockResolvedValue({ data: {} } as never)
    const { unmount } = renderWithClient(<VerifyEmail />, '/verify-email?token=ok')
    expect(await screen.findByRole('status')).toHaveTextContent('Email verified')
    expect(screen.getByRole('link', { name: 'Go to sign in' })).toHaveAttribute('href', '/login')
    unmount()

    useAuthStore.getState().setUser({
      id: 'user-1',
      email: 'analyst@example.com',
      tier: 'pro',
    })
    renderWithClient(<VerifyEmail />, '/verify-email?token=ok')
    expect(await screen.findByRole('link', { name: 'Go to dashboard' })).toHaveAttribute(
      'href',
      '/dashboard',
    )
  })

  it('renders reusable legal links including contact', () => {
    renderWithClient(<LegalLinks />)
    expect(screen.getByRole('link', { name: 'Privacy' })).toHaveAttribute('href', '/privacy')
    expect(screen.getByRole('link', { name: 'Terms' })).toHaveAttribute('href', '/terms')
    expect(screen.getByRole('link', { name: 'Contact' })).toHaveAttribute(
      'href',
      'mailto:support@lograven.io',
    )
  })

  it('exposes Profile in the accessible mobile navigation', async () => {
    const user = userEvent.setup()
    useAuthStore.getState().setUser({
      id: 'user-1',
      email: 'analyst@example.com',
      tier: 'pro',
    })
    renderWithClient(<Navbar />, '/dashboard')

    const toggle = screen.getByRole('button', { name: 'Open navigation menu' })
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    await user.click(toggle)
    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('link', { name: 'Profile' })).toHaveAttribute('href', '/profile')
    await user.keyboard('{Escape}')
    await waitFor(() => expect(toggle).toHaveAttribute('aria-expanded', 'false'))
    expect(toggle).toHaveFocus()

    const accountMenu = screen.getByRole('button', { name: 'Account menu' })
    await user.click(accountMenu)
    const profileAction = screen.getByRole('button', { name: 'My Profile' })
    profileAction.focus()
    await user.keyboard('{Escape}')
    await waitFor(() => expect(accountMenu).toHaveFocus())
  })
})
