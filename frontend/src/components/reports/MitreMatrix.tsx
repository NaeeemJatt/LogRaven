// MITRE ATT&CK — technique list in a scannable grid (data is technique id strings from API)

interface MitreMatrixProps {
  techniques: string[]
}

export default function MitreMatrix({ techniques }: MitreMatrixProps) {
  if (!techniques?.length) return null
  const unique = [...new Set(techniques)].sort()

  return (
    <div className="rounded-xl border border-raven-700 bg-raven-900/30 p-5">
      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-raven-500 mb-4">
        Techniques referenced
      </p>
      <div className="flex flex-wrap gap-2">
        {unique.map((t) => (
          <span
            key={t}
            className="inline-flex items-center rounded-lg border border-electric-500/25 bg-raven-800/90 px-3 py-1.5 font-mono text-xs text-electric-300 shadow-sm shadow-black/20"
          >
            {t}
          </span>
        ))}
      </div>
    </div>
  )
}
