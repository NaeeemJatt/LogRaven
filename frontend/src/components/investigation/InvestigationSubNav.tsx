// LogRaven — Switch between file setup and live pipeline status for one investigation

import { Link } from 'react-router-dom'

interface InvestigationSubNavProps {
  investigationId: string
  active: 'files' | 'progress'
}

export function InvestigationSubNav({ investigationId, active }: InvestigationSubNavProps) {
  const tab =
    'inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors'
  const activeCls = 'text-white border-electric-500'
  const idleCls =
    'text-raven-500 border-transparent hover:text-electric-300 hover:border-raven-600'

  return (
    <nav
      className="flex flex-wrap gap-2 mb-6 border-b border-raven-700"
      aria-label="Investigation sections"
    >
      <Link
        to={`/investigations/${investigationId}`}
        className={`${tab} ${active === 'files' ? activeCls : idleCls}`}
      >
        Files & setup
      </Link>
      <Link
        to={`/investigations/${investigationId}/status`}
        className={`${tab} ${active === 'progress' ? activeCls : idleCls}`}
      >
        Analysis progress
      </Link>
    </nav>
  )
}
