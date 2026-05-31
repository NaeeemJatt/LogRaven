import React, { useId, useState } from 'react'
import { AlertCircle, AlertTriangle, CheckCircle2, ChevronDown, Info, X } from 'lucide-react'

export type PlayParserAlertVariant = 'info' | 'success' | 'warning' | 'danger'

export interface PlayParserAlertProps {
  /** Visual and semantic tone */
  variant: PlayParserAlertVariant
  /** Optional heading */
  title?: string
  onDismiss?: () => void
  /** Long text shown collapsed by default when length > 200 */
  collapsibleDetail?: string
  children?: React.ReactNode
  className?: string
}

const variantStyles: Record<
  PlayParserAlertVariant,
  { wrap: string; icon: React.ReactNode; iconWrap: string }
> = {
  info: {
    wrap: 'border-zinc-500/35 bg-gradient-to-r from-zinc-800/60 to-zinc-900/80 text-play-fg ring-1 ring-zinc-400/10',
    icon: <Info className="h-4 w-4 shrink-0" aria-hidden />,
    iconWrap: 'text-zinc-300',
  },
  success: {
    wrap: 'border-emerald-400/35 bg-gradient-to-r from-emerald-950/50 to-zinc-900/70 text-play-fg ring-1 ring-emerald-400/20',
    icon: <CheckCircle2 className="h-4 w-4 shrink-0" aria-hidden />,
    iconWrap: 'text-emerald-300',
  },
  warning: {
    wrap: 'border-amber-400/40 bg-gradient-to-r from-amber-950/55 to-zinc-900/75 text-play-fg ring-1 ring-amber-400/20',
    icon: <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden />,
    iconWrap: 'text-amber-300',
  },
  danger: {
    wrap: 'border-rose-400/40 bg-gradient-to-r from-rose-950/55 to-zinc-900/75 text-play-fg ring-1 ring-rose-400/15',
    icon: <AlertCircle className="h-4 w-4 shrink-0" aria-hidden />,
    iconWrap: 'text-rose-300',
  },
}

const COLLAPSE_THRESHOLD = 200

export const PlayParserAlert: React.FC<PlayParserAlertProps> = ({
  variant,
  title,
  onDismiss,
  collapsibleDetail,
  children,
  className = '',
}) => {
  const detailId = useId()
  const [detailOpen, setDetailOpen] = useState(false)
  const vs = variantStyles[variant]
  const detail = collapsibleDetail?.trim() ?? ''
  const useCollapsible = detail.length > COLLAPSE_THRESHOLD

  return (
    <div
      role="alert"
      aria-live="polite"
      className={`rounded-xl border px-3.5 py-3 font-play ${vs.wrap} ${className}`}
    >
      <div className="flex gap-3">
        <span className={`mt-0.5 ${vs.iconWrap}`}>{vs.icon}</span>
        <div className="min-w-0 flex-1 space-y-1.5">
          {title ? (
            <p className="text-sm font-semibold text-play-fg tracking-tight">{title}</p>
          ) : null}
          {children ? <div className="text-sm text-play-muted leading-relaxed">{children}</div> : null}
          {detail ? (
            useCollapsible ? (
              <div>
                {!detailOpen ? <span className="sr-only">{detail}</span> : null}
                <button
                  type="button"
                  onClick={() => setDetailOpen((o) => !o)}
                  className="inline-flex items-center gap-1 text-xs font-medium text-amber-300 hover:text-amber-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-400/45 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-900 rounded transition-colors motion-reduce:transition-none"
                  aria-expanded={detailOpen}
                  aria-controls={detailOpen ? detailId : undefined}
                >
                  <ChevronDown
                    className={`h-3.5 w-3.5 transition-transform motion-reduce:transition-none ${detailOpen ? 'rotate-180' : ''}`}
                    aria-hidden
                  />
                  {detailOpen ? 'Hide details' : 'Show full details'}
                </button>
                {detailOpen ? (
                  <pre
                    id={detailId}
                    className="mt-2 max-h-48 overflow-auto rounded-lg bg-play-base/80 border border-play-border px-2.5 py-2 text-[11px] font-play-mono text-play-muted whitespace-pre-wrap break-words"
                  >
                    {detail}
                  </pre>
                ) : null}
              </div>
            ) : (
              <pre className="max-h-32 overflow-auto rounded-lg bg-play-base/80 border border-play-border px-2.5 py-2 text-[11px] font-play-mono text-play-muted whitespace-pre-wrap break-words">
                {detail}
              </pre>
            )
          ) : null}
        </div>
        {onDismiss ? (
          <button
            type="button"
            onClick={onDismiss}
            className="shrink-0 rounded-lg p-1 text-zinc-400 hover:text-white hover:bg-zinc-700/80 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-400/45 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-900 transition-colors motion-reduce:transition-none"
            aria-label="Dismiss"
          >
            <X className="h-4 w-4" />
          </button>
        ) : null}
      </div>
    </div>
  )
}
