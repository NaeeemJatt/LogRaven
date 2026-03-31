// IOC table — type inferred from value

function inferIocType(value: string): string {
  const v = value.trim()
  if (/^\d{1,3}(\.\d{1,3}){3}$/.test(v)) return 'IPv4'
  if (/^[a-fA-F0-9]{32}$/.test(v)) return 'MD5'
  if (/^[a-fA-F0-9]{40}$/.test(v)) return 'SHA1'
  if (/^[a-fA-F0-9]{64}$/.test(v)) return 'SHA256'
  if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) return 'Email'
  if (/^[a-zA-Z0-9][-a-zA-Z0-9.]*\.[a-zA-Z]{2,}$/.test(v)) return 'Domain'
  return 'Other'
}

interface IOCTableProps {
  values: string[]
  /** Optional map of IOC string → source file hints */
  sourceHint?: Record<string, string>
}

export default function IOCTable({ values, sourceHint }: IOCTableProps) {
  if (values.length === 0) return null

  return (
    <div className="rounded-xl border border-raven-700 bg-raven-900/40 overflow-hidden">
      <div className="grid grid-cols-[minmax(0,7rem)_1fr_minmax(0,8rem)] gap-2 px-4 py-2 border-b border-raven-700 bg-raven-800/80 text-[10px] font-semibold uppercase tracking-wider text-raven-500">
        <span>Type</span>
        <span>Value</span>
        <span className="hidden sm:block text-right">Note</span>
      </div>
      <ul className="max-h-72 overflow-y-auto divide-y divide-raven-800/80">
        {values.map((raw, i) => {
          const type = inferIocType(raw)
          const hint = sourceHint?.[raw]
          return (
            <li
              key={`${raw}-${i}`}
              className="grid grid-cols-1 sm:grid-cols-[minmax(0,7rem)_1fr_minmax(0,8rem)] gap-1 sm:gap-2 px-4 py-2.5 text-sm items-start"
            >
              <span className="font-mono text-electric-400/90 text-xs">{type}</span>
              <span className="text-electric-200 font-mono text-xs break-all">{raw}</span>
              <span className="text-raven-500 text-xs sm:text-right">{hint ?? '—'}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
