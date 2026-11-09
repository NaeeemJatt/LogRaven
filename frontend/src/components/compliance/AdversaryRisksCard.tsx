// LogRaven — Adversary Aware Risks Intelligence KPI Card (CrowdStrike Threat Actor Correlation)
import { Info, Bug, ShieldAlert, Zap } from 'lucide-react'

interface AdversaryItem {
  name: string
  risks: number
  icon: 'spider' | 'panda' | 'chollima'
}

interface AdversaryRisksCardProps {
  lastRefreshed?: string
  onClick?: () => void
}

export default function AdversaryRisksCard({
  lastRefreshed = '19:05:08',
  onClick,
}: AdversaryRisksCardProps) {
  const adversaries: AdversaryItem[] = [
    { name: 'SCATTERED SPIDER', risks: 3, icon: 'spider' },
    { name: 'GENESIS PANDA', risks: 2, icon: 'panda' },
    { name: 'GOLDEN CHOLLIMA', risks: 1, icon: 'chollima' },
  ]

  const getActorIcon = (type: AdversaryItem['icon']) => {
    switch (type) {
      case 'spider':
        return <Bug className="w-3.5 h-3.5 text-threat-critical" />
      case 'panda':
        return <ShieldAlert className="w-3.5 h-3.5 text-threat-high" />
      case 'chollima':
        return <Zap className="w-3.5 h-3.5 text-amber-400" />
    }
  }

  return (
    <div
      onClick={onClick}
      className={`rounded-xl border border-white/[0.08] bg-surface p-4 flex flex-col justify-between transition-colors duration-150 ${
        onClick ? 'cursor-pointer hover:border-white/[0.18]' : ''
      }`}
    >
      <div>
        <div className="flex items-center justify-between text-xs text-text-muted mb-2">
          <div className="flex items-center gap-1.5 font-medium">
            <span>Adversary aware risks</span>
            <Info className="w-3 h-3 text-text-muted/70" />
          </div>
        </div>

        {/* Threat Actor Table */}
        <div className="mt-1 space-y-1.5">
          <div className="flex items-center justify-between text-[11px] font-semibold text-text-muted border-b border-white/[0.06] pb-1">
            <span>Adversary</span>
            <span>Risks</span>
          </div>

          <div className="space-y-1">
            {adversaries.map((actor) => (
              <div
                key={actor.name}
                className="flex items-center justify-between text-xs py-0.5 hover:bg-white/[0.02] rounded px-1 -mx-1"
              >
                <div className="flex items-center gap-1.5 min-w-0 pr-2">
                  <div className="w-4 h-4 rounded bg-white/[0.04] flex items-center justify-center shrink-0">
                    {getActorIcon(actor.icon)}
                  </div>
                  <span className="text-[11px] font-semibold text-text-primary truncate font-mono">
                    {actor.name}
                  </span>
                </div>
                <span className="font-mono text-xs font-bold text-threat-critical tabular-nums">
                  {actor.risks}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-3 pt-2 border-t border-white/[0.04] flex items-center justify-between text-[10px] text-text-muted">
        <span>Last refreshed: {lastRefreshed}</span>
      </div>
    </div>
  )
}
