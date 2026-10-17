import { Link } from 'react-router-dom'

export default function LegalLinks({ className = '' }: { className?: string }) {
  return (
    <nav
      aria-label="Legal and support"
      className={`flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-xs text-text-muted ${className}`}
    >
      <Link to="/privacy" className="min-h-11 inline-flex items-center hover:text-text-secondary">
        Privacy
      </Link>
      <Link to="/terms" className="min-h-11 inline-flex items-center hover:text-text-secondary">
        Terms
      </Link>
      <a
        href="mailto:support@lograven.io"
        className="min-h-11 inline-flex items-center hover:text-text-secondary"
      >
        Contact
      </a>
    </nav>
  )
}
