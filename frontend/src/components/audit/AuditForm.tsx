// LogRaven — SOC 2 Audit Form Component
//
// Form for initiating a new SOC 2 compliance audit.
// Collects: company name, AWS role ARN, and audit date range.

import { useState, useCallback } from 'react'

// Read the real LogRaven AWS account ID from the Vite env (set VITE_AWS_ACCOUNT_ID in .env).
// Falls back to a placeholder so customers know to replace it rather than copying 123456789012.
const LOGRAVEN_ACCOUNT_ID = import.meta.env.VITE_AWS_ACCOUNT_ID ?? 'YOUR_LOGRAVEN_ACCOUNT_ID'

interface AuditFormProps {
  onSubmit: (formData: AuditFormData) => void
  isLoading: boolean
}

export interface AuditFormData {
  companyName: string
  roleArn: string
  auditStartDate: string
  auditEndDate: string
}

interface FieldErrors {
  companyName?: string
  roleArn?: string
  auditStartDate?: string
  auditEndDate?: string
}

interface DirtyFields {
  companyName: boolean
  roleArn: boolean
  auditStartDate: boolean
  auditEndDate: boolean
}

const IAM_POLICY_JSON = `{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudtrail:LookupEvents",
        "iam:GetAccountSummary",
        "iam:GetAccountPasswordPolicy",
        "iam:ListUsers",
        "iam:ListMFADevices",
        "guardduty:ListDetectors",
        "guardduty:ListFindings",
        "guardduty:GetFindings"
      ],
      "Resource": "*"
    }
  ]
}`

export default function AuditForm({ onSubmit, isLoading }: AuditFormProps) {
  const [formData, setFormData] = useState<AuditFormData>({
    companyName: '',
    roleArn: '',
    auditStartDate: '',
    auditEndDate: '',
  })

  const [errors, setErrors] = useState<FieldErrors>({})
  const [dirty, setDirty] = useState<DirtyFields>({
    companyName: false,
    roleArn: false,
    auditStartDate: false,
    auditEndDate: false,
  })
  const [showHelper, setShowHelper] = useState(false)

  // Validation functions
  const validateCompanyName = useCallback((value: string): string | undefined => {
    if (!value.trim()) return 'Company name is required'
    if (value.length < 2) return 'Company name must be at least 2 characters'
    if (value.length > 100) return 'Company name must be at most 100 characters'
    return undefined
  }, [])

  const validateRoleArn = useCallback((value: string): string | undefined => {
    if (!value.trim()) return 'AWS Role ARN is required'
    const arnPattern = /^arn:aws:iam::\d{12}:role\/.+$/
    if (!arnPattern.test(value)) {
      return 'Invalid ARN format. Expected: arn:aws:iam::123456789012:role/RoleName'
    }
    return undefined
  }, [])

  const validateStartDate = useCallback((value: string): string | undefined => {
    if (!value) return 'Audit start date is required'
    const date = new Date(value)
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    if (date > today) {
      return 'Start date cannot be in the future'
    }
    return undefined
  }, [])

  const validateEndDate = useCallback((value: string, startDate: string): string | undefined => {
    if (!value) return 'Audit end date is required'
    if (!startDate) return undefined

    const start = new Date(startDate)
    const end = new Date(value)

    if (end <= start) {
      return 'End date must be after start date'
    }

    const daysDiff = Math.floor((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24))
    if (daysDiff > 365) {
      return 'Audit period cannot exceed 365 days'
    }

    return undefined
  }, [])

  // Handle blur events with validation
  const handleBlur = useCallback(
    (field: keyof AuditFormData) => {
      setDirty((prev) => ({ ...prev, [field]: true }))

      let error: string | undefined
      if (field === 'companyName') {
        error = validateCompanyName(formData.companyName)
      } else if (field === 'roleArn') {
        error = validateRoleArn(formData.roleArn)
      } else if (field === 'auditStartDate') {
        error = validateStartDate(formData.auditStartDate)
      } else if (field === 'auditEndDate') {
        error = validateEndDate(formData.auditEndDate, formData.auditStartDate)
      }

      setErrors((prev) => ({
        ...prev,
        [field]: error,
      }))
    },
    [formData, validateCompanyName, validateRoleArn, validateStartDate, validateEndDate]
  )

  const handleChange = useCallback((field: keyof AuditFormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
    // Clear error if field was previously dirty and now has content
    if (dirty[field] && value.trim()) {
      setErrors((prev) => ({ ...prev, [field]: undefined }))
    }
  }, [dirty])

  // Check if form is valid
  const hasErrors = Object.values(errors).some((e) => e !== undefined)
  const hasAllFields =
    formData.companyName.trim() &&
    formData.roleArn.trim() &&
    formData.auditStartDate &&
    formData.auditEndDate

  const isFormValid = hasAllFields && !hasErrors

  const handleSubmit = () => {
    // Mark all fields as dirty to show any validation errors
    setDirty({
      companyName: true,
      roleArn: true,
      auditStartDate: true,
      auditEndDate: true,
    })

    // Validate all fields
    const newErrors: FieldErrors = {
      companyName: validateCompanyName(formData.companyName),
      roleArn: validateRoleArn(formData.roleArn),
      auditStartDate: validateStartDate(formData.auditStartDate),
      auditEndDate: validateEndDate(formData.auditEndDate, formData.auditStartDate),
    }

    setErrors(newErrors)

    // Only submit if no errors
    if (Object.values(newErrors).every((e) => !e)) {
      onSubmit(formData)
    }
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* Background and container */}
      <div
        className="rounded-lg p-8 border"
        style={{
          backgroundColor: '#161B22',
          borderColor: '#30363D',
        }}
      >
        {/* Header */}
        <h1
          className="text-2xl font-bold mb-2"
          style={{ color: '#E6EDF3' }}
        >
          Start SOC 2 Audit
        </h1>
        <p
          className="text-sm mb-6"
          style={{ color: '#8B949E' }}
        >
          Enter your organization details and AWS credentials to begin the compliance assessment.
        </p>

        {/* Form fields container */}
        <div className="space-y-6">
          {/* Company Name field */}
          <div>
            <label
              className="block text-sm font-medium mb-2"
              style={{ color: '#E6EDF3' }}
            >
              Company Name
            </label>
            <input
              type="text"
              value={formData.companyName}
              onChange={(e) => handleChange('companyName', e.target.value)}
              onBlur={() => handleBlur('companyName')}
              placeholder="e.g., Acme Inc."
              className="w-full px-4 py-2 rounded text-sm border transition-colors"
              style={{
                backgroundColor: '#0D1117',
                borderColor: errors.companyName ? '#F85149' : '#30363D',
                color: '#E6EDF3',
              }}
            />
            {dirty.companyName && errors.companyName && (
              <p
                className="text-xs mt-1"
                style={{ color: '#F85149' }}
              >
                {errors.companyName}
              </p>
            )}
          </div>

          {/* AWS Role ARN field */}
          <div>
            <label
              className="block text-sm font-medium mb-2"
              style={{ color: '#E6EDF3' }}
            >
              AWS Role ARN
            </label>
            <input
              type="text"
              value={formData.roleArn}
              onChange={(e) => handleChange('roleArn', e.target.value)}
              onBlur={() => handleBlur('roleArn')}
              placeholder="arn:aws:iam::123456789012:role/LogRavenAudit"
              className="w-full px-4 py-2 rounded text-sm border transition-colors font-mono"
              style={{
                backgroundColor: '#0D1117',
                borderColor: errors.roleArn ? '#F85149' : '#30363D',
                color: '#E6EDF3',
              }}
            />
            {dirty.roleArn && errors.roleArn && (
              <p
                className="text-xs mt-1"
                style={{ color: '#F85149' }}
              >
                {errors.roleArn}
              </p>
            )}

            {/* Collapsible helper */}
            <button
              type="button"
              onClick={() => setShowHelper(!showHelper)}
              className="flex items-center gap-2 text-sm mt-2 transition-colors hover:opacity-80"
              style={{ color: '#2F81F7' }}
            >
              <span>{showHelper ? '▼' : '▶'}</span>
              <span>How to create the AWS role</span>
            </button>

            {showHelper && (
              <div
                className="mt-4 p-4 rounded border text-sm"
                style={{
                  backgroundColor: '#0D1117',
                  borderColor: '#30363D',
                }}
              >
                <ol className="space-y-3">
                  <li style={{ color: '#E6EDF3' }}>
                    <span className="font-semibold" style={{ color: '#2F81F7' }}>Step 1:</span>
                    {' '}In your AWS account, go to IAM → Roles → Create role
                  </li>
                  <li style={{ color: '#E6EDF3' }}>
                    <span className="font-semibold" style={{ color: '#2F81F7' }}>Step 2:</span>
                    {' '}Choose "Another AWS account" and enter: <span className="font-mono font-semibold" style={{ color: '#E6EDF3' }}>{LOGRAVEN_ACCOUNT_ID}</span> (LogRaven account)
                  </li>
                  <li style={{ color: '#E6EDF3' }}>
                    <span className="font-semibold" style={{ color: '#2F81F7' }}>Step 3:</span>
                    {' '}Attach the following policy inline:
                  </li>
                </ol>
                <div
                  className="mt-3 p-3 rounded font-mono text-xs overflow-auto max-h-48 border"
                  style={{
                    backgroundColor: '#161B22',
                    borderColor: '#30363D',
                    color: '#8B949E',
                  }}
                >
                  <pre>{IAM_POLICY_JSON}</pre>
                </div>
              </div>
            )}
          </div>

          {/* Audit Start Date field */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label
                className="block text-sm font-medium mb-2"
                style={{ color: '#E6EDF3' }}
              >
                Audit Start Date
              </label>
              <input
                type="date"
                value={formData.auditStartDate}
                onChange={(e) => handleChange('auditStartDate', e.target.value)}
                onBlur={() => handleBlur('auditStartDate')}
                className="w-full px-4 py-2 rounded text-sm border transition-colors"
                style={{
                  backgroundColor: '#0D1117',
                  borderColor: errors.auditStartDate ? '#F85149' : '#30363D',
                  color: '#E6EDF3',
                }}
              />
              {dirty.auditStartDate && errors.auditStartDate && (
                <p
                  className="text-xs mt-1"
                  style={{ color: '#F85149' }}
                >
                  {errors.auditStartDate}
                </p>
              )}
            </div>

            {/* Audit End Date field */}
            <div>
              <label
                className="block text-sm font-medium mb-2"
                style={{ color: '#E6EDF3' }}
              >
                Audit End Date
              </label>
              <input
                type="date"
                value={formData.auditEndDate}
                onChange={(e) => handleChange('auditEndDate', e.target.value)}
                onBlur={() => handleBlur('auditEndDate')}
                className="w-full px-4 py-2 rounded text-sm border transition-colors"
                style={{
                  backgroundColor: '#0D1117',
                  borderColor: errors.auditEndDate ? '#F85149' : '#30363D',
                  color: '#E6EDF3',
                }}
              />
              {dirty.auditEndDate && errors.auditEndDate && (
                <p
                  className="text-xs mt-1"
                  style={{ color: '#F85149' }}
                >
                  {errors.auditEndDate}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Submit button */}
        <button
          onClick={handleSubmit}
          disabled={!isFormValid || isLoading}
          className="w-full mt-8 py-3 rounded font-medium text-sm transition-all flex items-center justify-center gap-2"
          style={{
            backgroundColor: isFormValid && !isLoading ? '#2F81F7' : '#4B5563',
            color: '#E6EDF3',
            cursor: isFormValid && !isLoading ? 'pointer' : 'not-allowed',
            opacity: isFormValid && !isLoading ? 1 : 0.6,
          }}
        >
          {isLoading ? (
            <>
              <span
                className="inline-block w-4 h-4 border-2 border-transparent rounded-full animate-spin"
                style={{
                  borderTopColor: '#E6EDF3',
                  borderRightColor: '#E6EDF3',
                }}
              />
              Running...
            </>
          ) : (
            'Run SOC 2 Audit'
          )}
        </button>
      </div>
    </div>
  )
}
