// LogRaven — Empty State Component
// Shown when a list has no items (no investigations, no reports, etc.)
// TODO Month 1 Week 3: Implement.

export default function EmptyState({ message, actionLabel, onAction }: {
  message: string, actionLabel?: string, onAction?: () => void
}) {
  return (
    <div className="text-center py-16">
      <p className="text-gray-500">{message}</p>
      {actionLabel && (
        <button onClick={onAction} className="mt-4 text-blue-600 hover:underline">{actionLabel}</button>
      )}
    </div>
  )
}
