// LogRaven — Password Strength Meter Component
//
// PURPOSE:
//   Live visual feedback on NIST SP 800-63B password complexity requirements:
//   - 12+ characters
//   - Uppercase letter
//   - Lowercase letter
//   - Number
//   - Special symbol
//   Displays an animated progress bar and accessible checklist.

import { Check, X } from 'lucide-react'

interface PasswordStrengthMeterProps {
  password: string
}

interface Criterion {
  id: string
  label: string
  met: boolean
}

export function evaluatePasswordStrength(password: string): {
  score: number
  criteria: Criterion[]
  isCompliant: boolean
} {
  const criteria: Criterion[] = [
    {
      id: 'length',
      label: 'At least 12 characters',
      met: password.length >= 12,
    },
    {
      id: 'upper',
      label: 'Uppercase letter (A-Z)',
      met: /[A-Z]/.test(password),
    },
    {
      id: 'lower',
      label: 'Lowercase letter (a-z)',
      met: /[a-z]/.test(password),
    },
    {
      id: 'digit',
      label: 'Number (0-9)',
      met: /\d/.test(password),
    },
    {
      id: 'special',
      label: 'Special symbol (!@#$%^&*...)',
      met: /[!"#$%&'()*+,\-./:;<=>?@[\\\]^_`{|}~]/.test(password),
    },
  ]

  const metCount = criteria.filter((c) => c.met).length
  const score = Math.round((metCount / criteria.length) * 100)
  const isCompliant = metCount === criteria.length

  return { score, criteria, isCompliant }
}

export default function PasswordStrengthMeter({ password }: PasswordStrengthMeterProps) {
  if (!password) {
    return null
  }

  const { score, criteria } = evaluatePasswordStrength(password)

  // Color mapping based on score
  let barColor = 'bg-rose-500'
  let labelText = 'Weak'
  let labelColor = 'text-rose-400'

  if (score >= 100) {
    barColor = 'bg-teal-400'
    labelText = 'Enterprise Compliant'
    labelColor = 'text-teal-400'
  } else if (score >= 80) {
    barColor = 'bg-indigo-400'
    labelText = 'Strong'
    labelColor = 'text-indigo-400'
  } else if (score >= 40) {
    barColor = 'bg-amber-400'
    labelText = 'Moderate'
    labelColor = 'text-amber-400'
  }

  return (
    <div className="mt-3 p-3.5 rounded-lg bg-surface/80 border border-white/[0.06] space-y-2.5" data-testid="password-strength-meter">
      <div className="flex items-center justify-between text-xs">
        <span className="text-text-muted font-mono uppercase tracking-wider text-[10px]">Password Strength</span>
        <span className={`font-mono font-medium text-[11px] ${labelColor}`}>{labelText}</span>
      </div>

      {/* Strength Bar */}
      <div className="h-1.5 w-full bg-void/80 border border-white/[0.04] rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ease-out rounded-full ${barColor}`}
          style={{ width: `${score}%` }}
          role="progressbar"
          aria-valuenow={score}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>

      {/* Criteria Checklist */}
      <ul className="grid grid-cols-1 gap-1.5 pt-1 text-[11px] font-mono">
        {criteria.map((c) => (
          <li
            key={c.id}
            className={`flex items-center gap-1.5 transition-colors ${
              c.met ? 'text-teal-400' : 'text-text-ghost'
            }`}
          >
            {c.met ? (
              <Check className="w-3.5 h-3.5 text-teal-400 shrink-0" aria-hidden />
            ) : (
              <X className="w-3.5 h-3.5 text-text-ghost shrink-0" aria-hidden />
            )}
            <span>{c.label}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
