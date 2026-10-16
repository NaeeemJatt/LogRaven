import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import RemediationStudio from './RemediationStudio'
import type { RemediationGuide } from '../../types/audit'

const sampleGuide: RemediationGuide = {
  control_id: 'CC6.6',
  title: 'Restrict Ingress to Sensitive Ports from 0.0.0.0/0',
  threat_rationale: 'Exposing port 22 allows brute force and credential spraying.',
  estimated_time_minutes: 5,
  console_steps: [
    'Open EC2 console.',
    'Select Security Groups.',
    'Edit inbound rules and remove 0.0.0.0/0 on port 22.',
  ],
  aws_cli_command: 'aws ec2 revoke-security-group-ingress --group-id sg-12345 --protocol tcp --port 22 --cidr 0.0.0.0/0',
  terraform_snippet: 'resource "aws_security_group_rule" "ssh" { cidr_blocks = ["10.0.0.0/16"] }',
  verification_command: 'aws ec2 describe-security-groups --filters "Name=ip-permission.cidr,Values=0.0.0.0/0"',
}

describe('RemediationStudio', () => {
  it('renders null if neither guide nor fallback is provided', () => {
    const { container } = render(
      <RemediationStudio controlId="CC6.6" />,
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders fallback guidance when guide is not provided', () => {
    render(
      <RemediationStudio
        controlId="CC6.6"
        fallbackText="Review and close open security group ports."
      />,
    )
    expect(screen.getByText('Recommended Remediation')).toBeInTheDocument()
    expect(screen.getByText('Review and close open security group ports.')).toBeInTheDocument()
  })

  it('renders structured guide with header, time estimate, and console steps by default', () => {
    render(
      <RemediationStudio
        controlId="CC6.6"
        guide={sampleGuide}
      />,
    )

    expect(screen.getByText('Remediation Studio')).toBeInTheDocument()
    expect(screen.getByText('~5 min fix')).toBeInTheDocument()
    expect(screen.getByText('Restrict Ingress to Sensitive Ports from 0.0.0.0/0')).toBeInTheDocument()
    expect(screen.getByText(/Exposing port 22 allows brute force/)).toBeInTheDocument()

    // Console steps are visible by default
    expect(screen.getByText('Open EC2 console.')).toBeInTheDocument()
    expect(screen.getByText('Select Security Groups.')).toBeInTheDocument()
    expect(screen.getByText('Edit inbound rules and remove 0.0.0.0/0 on port 22.')).toBeInTheDocument()
  })

  it('switches tabs between Console, AWS CLI, Terraform, and Verification', () => {
    render(
      <RemediationStudio
        controlId="CC6.6"
        guide={sampleGuide}
      />,
    )

    // Switch to AWS CLI tab
    fireEvent.click(screen.getByRole('button', { name: /aws cli/i }))
    expect(screen.getByText(/aws ec2 revoke-security-group-ingress/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /copy command/i })).toBeInTheDocument()

    // Switch to Terraform tab
    fireEvent.click(screen.getByRole('button', { name: /terraform \/ iac/i }))
    expect(screen.getByText(/aws_security_group_rule/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /copy terraform/i })).toBeInTheDocument()

    // Switch to Verification tab
    fireEvent.click(screen.getByRole('button', { name: /verification/i }))
    expect(screen.getByText(/aws ec2 describe-security-groups/)).toBeInTheDocument()
  })

  it('copies command to clipboard when copy button is clicked', async () => {
    const writeTextMock = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, {
      clipboard: {
        writeText: writeTextMock,
      },
    })

    render(
      <RemediationStudio
        controlId="CC6.6"
        guide={sampleGuide}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: /aws cli/i }))
    const copyBtn = screen.getByRole('button', { name: /copy command/i })
    fireEvent.click(copyBtn)

    expect(writeTextMock).toHaveBeenCalledWith(sampleGuide.aws_cli_command)
    expect(await screen.findByText('Copied!')).toBeInTheDocument()
  })
})
