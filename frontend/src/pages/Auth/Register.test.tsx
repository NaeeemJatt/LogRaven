import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Register from './Register'

const mockRegister = vi.fn()

vi.mock('../../hooks/useAuth', () => ({
  useAuth: () => ({
    register: mockRegister,
  }),
}))

describe('Register Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockRegister.mockResolvedValue(undefined)
  })

  it('renders registration form elements correctly', () => {
    render(
      <MemoryRouter>
        <Register />
      </MemoryRouter>
    )

    expect(screen.getByRole('heading', { name: /create account/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/^email$/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^confirm password$/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/show password/i)).toBeInTheDocument()
  })

  it('toggles password and confirm password visibility between password and text types', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <Register />
      </MemoryRouter>
    )

    const passwordInput = screen.getByLabelText(/^password$/i)
    const toggleButton = screen.getByLabelText(/^show password$/i)

    expect(passwordInput).toHaveAttribute('type', 'password')

    await user.click(toggleButton)
    expect(passwordInput).toHaveAttribute('type', 'text')
    expect(screen.getByLabelText(/^hide password$/i)).toBeInTheDocument()

    await user.click(screen.getByLabelText(/^hide password$/i))
    expect(passwordInput).toHaveAttribute('type', 'password')

    // Test confirm password toggle
    const confirmInput = screen.getByLabelText(/^confirm password$/i)
    const confirmToggle = screen.getByLabelText(/^show confirm password$/i)

    expect(confirmInput).toHaveAttribute('type', 'password')
    await user.click(confirmToggle)
    expect(confirmInput).toHaveAttribute('type', 'text')
    expect(screen.getByLabelText(/^hide confirm password$/i)).toBeInTheDocument()

    await user.click(screen.getByLabelText(/^hide confirm password$/i))
    expect(confirmInput).toHaveAttribute('type', 'password')
  })

  it('displays the live password strength tracker when typing a password', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <Register />
      </MemoryRouter>
    )

    // Initially strength meter is not rendered
    expect(screen.queryByTestId('password-strength-meter')).not.toBeInTheDocument()

    const passwordInput = screen.getByLabelText(/^password$/i)
    // Type a password missing special characters (like Google suggested password)
    await user.type(passwordInput, 'GoogleSuggestedPassword123')

    expect(screen.getByTestId('password-strength-meter')).toBeInTheDocument()
    expect(screen.getByText(/password strength/i)).toBeInTheDocument()
    expect(screen.getByText(/special symbol/i)).toBeInTheDocument()
  })

  it('blocks submission and warns user if password does not satisfy all complexity requirements', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <Register />
      </MemoryRouter>
    )

    const emailInput = screen.getByLabelText(/^email$/i)
    const passwordInput = screen.getByLabelText(/^password$/i)
    const confirmInput = screen.getByLabelText(/^confirm password$/i)

    await user.type(emailInput, 'test@example.com')
    // Missing special character
    await user.type(passwordInput, 'GoogleSuggestedPassword123')
    await user.type(confirmInput, 'GoogleSuggestedPassword123')

    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(
      screen.getByText(/please satisfy all password complexity requirements shown below/i)
    ).toBeInTheDocument()
    expect(mockRegister).not.toHaveBeenCalled()
  })

  it('blocks submission if passwords do not match', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <Register />
      </MemoryRouter>
    )

    const emailInput = screen.getByLabelText(/^email$/i)
    const passwordInput = screen.getByLabelText(/^password$/i)
    const confirmInput = screen.getByLabelText(/^confirm password$/i)

    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'CompliantPassword123!')
    await user.type(confirmInput, 'DifferentPassword123!')

    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument()
    expect(mockRegister).not.toHaveBeenCalled()
  })

  it('submits compliant credentials successfully', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <Register />
      </MemoryRouter>
    )

    const emailInput = screen.getByLabelText(/^email$/i)
    const passwordInput = screen.getByLabelText(/^password$/i)
    const confirmInput = screen.getByLabelText(/^confirm password$/i)

    await user.type(emailInput, 'operator@lograven.io')
    await user.type(passwordInput, 'CompliantPassword123!')
    await user.type(confirmInput, 'CompliantPassword123!')

    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith('operator@lograven.io', 'CompliantPassword123!')
    })
  })
})
