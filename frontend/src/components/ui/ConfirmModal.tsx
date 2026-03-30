// LogRaven — Confirm modal (matches dashboard / card chrome)
import { useEffect, useRef } from 'react'
import { AlertTriangle } from 'lucide-react'

interface ConfirmModalProps {
  isOpen: boolean
  title: string
  message: string
  confirmLabel?: string
  onConfirm: () => void
  onCancel: () => void
  isLoading?: boolean
}

export default function ConfirmModal({
  isOpen,
  title,
  message,
  confirmLabel = 'Delete',
  onConfirm,
  onCancel,
  isLoading = false,
}: ConfirmModalProps) {
  const cancelRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (isOpen) cancelRef.current?.focus()
  }, [isOpen])

  useEffect(() => {
    if (!isOpen) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [isOpen, onCancel])

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4"
      onClick={onCancel}
      role="presentation"
    >
      <div
        className="w-full max-w-md overflow-hidden rounded-xl border border-raven-700 bg-raven-900 shadow-2xl shadow-black/50"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-modal-title"
      >
        <div className="border-b border-raven-700 bg-raven-950 px-5 py-4">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-red-500/10 text-red-400">
              <AlertTriangle className="h-5 w-5" strokeWidth={2} aria-hidden />
            </span>
            <p id="confirm-modal-title" className="text-base font-semibold tracking-tight text-white">
              {title}
            </p>
          </div>
        </div>

        <div className="bg-raven-800/60 px-5 py-5">
          <p className="text-sm leading-relaxed text-raven-300">{message}</p>
          <p className="mt-3 font-mono text-xs text-raven-500">This action cannot be undone.</p>
        </div>

        <div className="flex items-center justify-end gap-3 border-t border-raven-700 bg-raven-950 px-5 py-4">
          <button
            ref={cancelRef}
            type="button"
            onClick={onCancel}
            disabled={isLoading}
            className="rounded-lg border border-white/10 px-5 py-2.5 text-sm font-semibold uppercase tracking-wide text-raven-200 transition-colors hover:bg-white/5 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isLoading}
            className="rounded-lg bg-red-600 px-5 py-2.5 text-sm font-semibold uppercase tracking-wide text-white transition-colors hover:bg-red-500 disabled:opacity-50"
          >
            {isLoading ? 'Deleting…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
