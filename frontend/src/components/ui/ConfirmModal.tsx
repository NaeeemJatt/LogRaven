// LogRaven — Confirm Modal
// Reusable destructive-action confirmation dialog.
// Replaces the browser native confirm() with a styled modal.

import { useEffect, useRef } from 'react'

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

  // Focus cancel button when modal opens
  useEffect(() => {
    if (isOpen) cancelRef.current?.focus()
  }, [isOpen])

  // Close on Escape
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
    // Backdrop
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={onCancel}
    >
      {/* Panel — stop click propagation so clicking inside doesn't close */}
      <div
        className="w-full max-w-sm bg-raven-800 border border-raven-600 shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="border-b border-raven-700 px-6 py-4">
          <div className="flex items-center gap-2">
            <span className="text-red-400 text-sm">⚠</span>
            <p className="text-raven-200 text-sm font-semibold tracking-tight">{title}</p>
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-5">
          <p className="text-raven-400 text-sm leading-relaxed">{message}</p>
          <p className="text-raven-600 text-xs font-mono mt-2">This action cannot be undone.</p>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-raven-700 bg-raven-900">
          <button
            ref={cancelRef}
            onClick={onCancel}
            disabled={isLoading}
            className="text-raven-400 text-xs uppercase tracking-widest font-mono hover:text-raven-200 transition-colors disabled:opacity-50 px-3 py-1.5"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isLoading}
            className="bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white text-xs uppercase tracking-widest font-mono px-4 py-1.5 transition-colors"
          >
            {isLoading ? 'Deleting...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
