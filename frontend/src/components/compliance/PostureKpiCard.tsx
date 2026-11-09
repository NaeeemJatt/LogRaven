// LogRaven — Posture KPI Bento Card with Solid Bottom Accent Bar
import { Info } from 'lucide-react'

interface PostureKpiCardProps {
  title: string
  value: string | number
  accentColor?: 'critical' | 'high' | 'none'
  lastRefreshed?: string
  onClick?: () => void
}

export default function PostureKpiCard({
  title,
  value,
  accentColor = 'none',
  lastRefreshed = '19:05:00',
  onClick,
}: PostureKpiCardProps) {
  const accentBorderClass =
    accentColor === 'critical'
      ? 'bg-threat-critical'
      : accentColor === 'high'
      ? 'bg-threat-high'
      : ''

  return (
    <div
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      className={`relative rounded-xl border border-white/[0.08] bg-surface p-4 flex flex-col justify-between transition-colors duration-150 ${
        onClick
          ? 'cursor-pointer hover:border-white/[0.18] focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none motion-safe:active:scale-[0.98] motion-reduce:transform-none disabled:opacity-50 disabled:cursor-not-allowed'
          : ''
      }`}
    >
      <div>
        <div className="flex items-center justify-between text-xs text-text-muted mb-2">
          <div className="flex items-center gap-1.5 font-medium">
            <span>{title}</span>
            <Info className="w-3 h-3 text-text-muted/70" />
          </div>
        </div>

        <div className="font-display font-bold text-3xl sm:text-4xl text-text-primary tabular-nums tracking-tight">
          {value}
        </div>
      </div>

      <div className="mt-4 pt-2 flex items-center justify-between text-[10px] text-text-muted">
        <span>Last refreshed: {lastRefreshed}</span>
      </div>

      {/* Solid bottom accent strip (CrowdStrike Falcon KPI Pattern) */}
      {accentColor !== 'none' && (
        <div
          className={`absolute bottom-0 left-0 right-0 h-1 rounded-b-xl ${accentBorderClass}`}
        />
      )}
    </div>
  )
}
