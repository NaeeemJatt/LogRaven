// LogRaven — Shared navigation and action state between AuditResults and AppHeader
import { create } from 'zustand'

export interface AuditNavState {
  isAuditActive: boolean
  auditId: string | null
  activeFrameworkId: string | null
  companyName: string
  totalExceptions: number
  downloading: string | null
  onDownloadPdf: (() => void) | null
  onDownloadCsv: (() => void) | null
  onDownloadZip: (() => void) | null
  onShare: (() => void) | null
  setAuditNav: (state: Partial<AuditNavState>) => void
  resetAuditNav: () => void
}

export const useAuditNavStore = create<AuditNavState>((set) => ({
  isAuditActive: false,
  auditId: null,
  activeFrameworkId: null,
  companyName: '',
  totalExceptions: 0,
  downloading: null,
  onDownloadPdf: null,
  onDownloadCsv: null,
  onDownloadZip: null,
  onShare: null,
  setAuditNav: (partial) => set((prev) => ({ ...prev, ...partial })),
  resetAuditNav: () =>
    set({
      isAuditActive: false,
      auditId: null,
      activeFrameworkId: null,
      companyName: '',
      totalExceptions: 0,
      downloading: null,
      onDownloadPdf: null,
      onDownloadCsv: null,
      onDownloadZip: null,
      onShare: null,
    }),
}))
