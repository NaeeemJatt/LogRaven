// LogRaven — Alert modal (non-destructive notice, e.g. pipeline failure)
// Uses the investigation-page chrome (surface / void / text tokens) so it
// looks native across the app. Surfaces investigation breakage to the user
// with a clear message and a primary recovery action.
import { AlertTriangle } from 'lucide-react'
import { useModalFocus } from '../../hooks/useModalFocus'

interface AlertModalProps {
  isOpen: boolean
  title: string
  message: string
  /** Primary action label (e.g. "Back to setup"). */
  actionLabel?: string
  onAction?: () => void
  /** Dismiss label (defaults to "Close"). */
  dismissLabel?: string
  onDismiss: () => void
  /** "danger" (rose, default) or "warning" (amber) accent. */
  tone?: 'danger' | 'warning'
}

export default function AlertModal({
  isOpen,
  title,
  message,
  actionLabel,
  onAction,
  dismissLabel = 'Close',
  onDismiss,
  tone = 'danger',
}: AlertModalProps) {
  const dialogRef = useModalFocus<HTMLDivElement>(isOpen, onDismiss)

  if (!isOpen) return null

  const accent =
    tone === 'warning'
      ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
      : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4"
      onClick={onDismiss}
      role="presentation"
    >
      <div
        ref={dialogRef}
        tabIndex={-1}
        className="w-full max-w-md overflow-hidden rounded-2xl border border-white/[0.08] bg-surface shadow-2xl shadow-black/60"
        onClick={(e) => e.stopPropagation()}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="alert-modal-title"
      >
        <div className="border-b border-white/[0.06] bg-void/60 px-5 py-4">
          <div className="flex items-center gap-3">
            <span className={`flex h-9 w-9 items-center justify-center rounded-lg ${accent}`}>
              <AlertTriangle className="h-5 w-5" strokeWidth={2} aria-hidden />
            </span>
            <p id="alert-modal-title" className="text-base font-semibold tracking-tight text-text-primary">
              {title}
            </p>
          </div>
        </div>

        <div className="px-5 py-5">
          <p className="text-sm leading-relaxed text-text-secondary whitespace-pre-wrap break-words">{message}</p>
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-white/[0.06] bg-void/40 px-5 py-4">
          <button
            data-autofocus
            type="button"
            onClick={onDismiss}
            className="btn-ghost rounded-lg px-4 py-2.5 text-sm font-medium text-text-secondary"
          >
            {dismissLabel}
          </button>
          {actionLabel && onAction && (
            <button
              type="button"
              onClick={onAction}
              className="btn-sovereign rounded-lg px-4 py-2.5 text-sm font-semibold text-white"
            >
              {actionLabel}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
