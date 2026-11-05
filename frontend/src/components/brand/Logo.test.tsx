import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import Logo, { LogoIcon } from './Logo'

describe('Logo Component', () => {
  it('renders full logo with brand text and signal dot by default', () => {
    render(<Logo subtitle="Cloud Security SOC" />)
    expect(screen.getByText('Cloud Security SOC')).toBeInTheDocument()
    expect(screen.getByTitle('Platform Live')).toBeInTheDocument()
  })

  it('renders standalone icon variant', () => {
    const { container } = render(<Logo variant="icon" size={48} />)
    const svg = container.querySelector('svg')
    expect(svg).toBeInTheDocument()
    expect(svg).toHaveAttribute('width', '48')
    expect(svg).toHaveAttribute('height', '48')
  })

  it('renders wordmark variant', () => {
    const { container } = render(<Logo variant="wordmark" />)
    expect(container.querySelector('svg')).toBeNull()
    expect(container.textContent).toContain('LogRaven')
  })

  it('renders LogoIcon directly', () => {
    const { container } = render(<LogoIcon size={36} />)
    const svg = container.querySelector('svg')
    expect(svg).toBeInTheDocument()
    expect(svg).toHaveAttribute('width', '36')
  })
})
