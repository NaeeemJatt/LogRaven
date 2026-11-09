import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import Logo, { LogoIcon } from './Logo'

describe('Logo Component', () => {
  it('renders full logo with brand text, image icon, and signal dot by default', () => {
    render(<Logo subtitle="Cloud Security SOC" />)
    expect(screen.getByText('Cloud Security SOC')).toBeInTheDocument()
    expect(screen.getByTitle('Platform Live')).toBeInTheDocument()
    const img = screen.getByAltText('LogRaven')
    expect(img).toBeInTheDocument()
    expect(img).toHaveAttribute('src', '/logo-icon.png')
  })

  it('renders standalone icon variant', () => {
    render(<Logo variant="icon" size={48} />)
    const img = screen.getByAltText('LogRaven')
    expect(img).toBeInTheDocument()
    expect(img).toHaveAttribute('src', '/logo-icon.png')
    expect(img).toHaveAttribute('width', '48')
    expect(img).toHaveAttribute('height', '48')
  })

  it('renders wordmark variant without image', () => {
    const { container } = render(<Logo variant="wordmark" />)
    expect(container.querySelector('img')).toBeNull()
    expect(container.textContent).toContain('LogRaven')
  })

  it('renders LogoIcon directly', () => {
    render(<LogoIcon size={36} />)
    const img = screen.getByAltText('LogRaven')
    expect(img).toBeInTheDocument()
    expect(img).toHaveAttribute('src', '/logo-icon.png')
    expect(img).toHaveAttribute('width', '36')
    expect(img).toHaveAttribute('height', '36')
  })
})
