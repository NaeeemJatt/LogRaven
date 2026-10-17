import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AttackPathCanvas from './AttackPathCanvas'
import * as complianceApi from '../../api/compliance'
import type { AttackPathGraph } from '../../types/audit'

vi.mock('../../api/compliance', () => ({
  getAuditAttackPathGraph: vi.fn(),
}))

const mockGraphData: AttackPathGraph = {
  toxic_combinations_count: 1,
  nodes: [
    {
      id: 'internet',
      label: '0.0.0.0/0 (Public Internet)',
      category: 'internet',
      provider: 'aws',
      severity: 'critical',
      failing_controls: [],
      metadata: { exposure: 'public' },
    },
    {
      id: 'sg-public-web',
      label: 'Security Group (sg-public-web)',
      category: 'network',
      provider: 'aws',
      severity: 'high',
      failing_controls: ['CC6.6'],
      metadata: { open_ports: [80, 443, 22] },
    },
    {
      id: 'ec2-prod-web-01',
      label: 'EC2 Instance (prod-web-01)',
      category: 'compute',
      provider: 'aws',
      severity: 'high',
      failing_controls: ['CC6.1'],
      metadata: { public_ip: '54.210.10.15' },
    },
    {
      id: 'role-app-admin',
      label: 'IAM Role (AppAdminAccess)',
      category: 'identity',
      provider: 'aws',
      severity: 'medium',
      failing_controls: ['CC6.3'],
      metadata: { role_arn: 'arn:aws:iam::123:role/AppAdmin' },
    },
    {
      id: 's3-customer-pii',
      label: 'S3 Bucket (customer-pii-vault)',
      category: 'storage',
      provider: 'aws',
      severity: 'critical',
      failing_controls: ['CC6.6', 'CC6.7'],
      metadata: { encrypted: false, public_access: true },
    },
  ],
  edges: [
    {
      id: 'edge-1',
      source: 'internet',
      target: 'sg-public-web',
      relationship: 'exposes',
      is_attack_path: true,
    },
    {
      id: 'edge-2',
      source: 'sg-public-web',
      target: 'ec2-prod-web-01',
      relationship: 'attaches_to',
      is_attack_path: true,
    },
    {
      id: 'edge-3',
      source: 'ec2-prod-web-01',
      target: 'role-app-admin',
      relationship: 'assumes_role',
      is_attack_path: true,
    },
    {
      id: 'edge-4',
      source: 'role-app-admin',
      target: 's3-customer-pii',
      relationship: 'reads_from',
      is_attack_path: true,
    },
  ],
  critical_paths: [
    {
      path_id: 'toxic-path-1',
      title: 'Internet ➔ EC2 ➔ Role ➔ S3 Data Exfiltration',
      severity: 'critical',
      description: 'Public ingress allows remote takeover of EC2 holding administrative S3 role.',
      node_ids: [
        'internet',
        'sg-public-web',
        'ec2-prod-web-01',
        'role-app-admin',
        's3-customer-pii',
      ],
    },
  ],
  assessed_at: '2026-10-16T12:00:00Z',
}

describe('AttackPathCanvas', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders loading state initially', () => {
    vi.mocked(complianceApi.getAuditAttackPathGraph).mockReturnValue(new Promise(() => {}))
    render(<AttackPathCanvas auditId="audit-123" />)

    expect(screen.getByText(/constructing asset relationship dag/i)).toBeInTheDocument()
  })

  it('renders error state and allows retry', async () => {
    vi.mocked(complianceApi.getAuditAttackPathGraph).mockRejectedValueOnce(
      new Error('Network connection aborted')
    )

    render(<AttackPathCanvas auditId="audit-123" />)

    await waitFor(() => {
      expect(screen.getByText('Graph Analysis Unavailable')).toBeInTheDocument()
      expect(screen.getByText('Network connection aborted')).toBeInTheDocument()
    })

    vi.mocked(complianceApi.getAuditAttackPathGraph).mockResolvedValueOnce(mockGraphData)
    fireEvent.click(screen.getByRole('button', { name: /retry analysis/i }))

    await waitFor(() => {
      expect(screen.getByText(/1 Toxic Multi-Hop Attack Path/i)).toBeInTheDocument()
    })
  })

  it('renders toxic attack path banner and critical path selector', async () => {
    vi.mocked(complianceApi.getAuditAttackPathGraph).mockResolvedValueOnce(mockGraphData)

    render(<AttackPathCanvas auditId="audit-123" />)

    await waitFor(() => {
      expect(screen.getByText(/1 Toxic Multi-Hop Attack Path/i)).toBeInTheDocument()
      expect(screen.getByText(/Internet ➔ EC2 ➔ Role ➔ S3 Data Exfiltration/i)).toBeInTheDocument()
      expect(screen.getByText('EC2 Instance (prod-web-01)')).toBeInTheDocument()
      expect(screen.getByText('S3 Bucket (customer-pii-vault)')).toBeInTheDocument()
    })
  })

  it('opens inspector drawer on node click and triggers remediation', async () => {
    vi.mocked(complianceApi.getAuditAttackPathGraph).mockResolvedValueOnce(mockGraphData)
    const onRemediate = vi.fn()

    render(<AttackPathCanvas auditId="audit-123" onRemediateControl={onRemediate} />)

    await waitFor(() => {
      expect(screen.getByText('EC2 Instance (prod-web-01)')).toBeInTheDocument()
    })

    // Click on node
    fireEvent.click(screen.getByText('EC2 Instance (prod-web-01)'))

    // Inspector opens
    await waitFor(() => {
      expect(screen.getByText('Cloud Configuration & Telemetry')).toBeInTheDocument()
      expect(screen.getByText(/ID: ec2-prod-web-01/i)).toBeInTheDocument()
      expect(screen.getByText('CC6.1')).toBeInTheDocument()
    })

    // Click Fix button
    const fixButton = screen.getByRole('button', { name: /fix/i })
    fireEvent.click(fixButton)

    expect(onRemediate).toHaveBeenCalledWith('CC6.1')
  })

  it('filters by category tier', async () => {
    vi.mocked(complianceApi.getAuditAttackPathGraph).mockResolvedValueOnce(mockGraphData)

    render(<AttackPathCanvas auditId="audit-123" />)

    await waitFor(() => {
      expect(screen.getByText('EC2 Instance (prod-web-01)')).toBeInTheDocument()
    })

    // Filter to storage only
    fireEvent.click(screen.getByRole('button', { name: /storage/i }))

    expect(screen.getByText('S3 Bucket (customer-pii-vault)')).toBeInTheDocument()
    expect(screen.queryByText('EC2 Instance (prod-web-01)')).not.toBeInTheDocument()
  })

  it('renders clean message when zero toxic paths exist', async () => {
    vi.mocked(complianceApi.getAuditAttackPathGraph).mockResolvedValueOnce({
      ...mockGraphData,
      toxic_combinations_count: 0,
      critical_paths: [],
      edges: mockGraphData.edges.map((e) => ({ ...e, is_attack_path: false })),
    })

    render(<AttackPathCanvas auditId="audit-123" />)

    await waitFor(() => {
      expect(screen.getByText(/zero toxic attack paths detected/i)).toBeInTheDocument()
    })
  })
})
