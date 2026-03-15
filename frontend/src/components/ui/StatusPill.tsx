// LogRaven — Job Status Pill
// Shows investigation/file status as a colored pill.
// draft=gray, queued=yellow, processing=blue (animated), complete=green, failed=red
// TODO Month 1 Week 3: Implement.

export default function StatusPill({ status }: { status: string }) {
  return <span className="px-2 py-1 rounded-full text-xs bg-gray-100">{status}</span>
}
