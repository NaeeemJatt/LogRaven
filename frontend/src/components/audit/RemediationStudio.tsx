// LogRaven — Remediation Studio Component
//
// Interactive tabbed remediation guides for compliance gaps:
// - Console Walkthrough (step-by-step checklist)
// - AWS CLI commands (copy-pasteable)
// - Terraform / OpenTofu HCL snippets
// - Verification command

import { useState } from 'react'
import {
  Wrench, Terminal, Layers, CheckCircle2, Copy, Check, Clock, ShieldAlert,
} from 'lucide-react'
import type { RemediationGuide } from '../../types/audit'

interface RemediationStudioProps {
  guide?: RemediationGuide | null
  fallbackText?: string | null
  controlId: string
}

type RemediationTab = 'console' | 'cli' | 'terraform' | 'verify'

export default function RemediationStudio({
  guide,
  fallbackText,
  controlId,
}: RemediationStudioProps) {
  const [activeTab, setActiveTab] = useState<RemediationTab>('console')
  const [copiedKey, setCopiedKey] = useState<string | null>(null)

  const copyToClipboard = async (text: string, key: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedKey(key)
      setTimeout(() => setCopiedKey(null), 2000)
    } catch {
      // ignore clipboard error
    }
  }

  if (!guide && !fallbackText) return null

  // If no structured guide is available, render legacy fallback guidance
  if (!guide) {
    return (
      <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/[0.04] p-4 space-y-2">
        <div className="font-mono text-[10px] uppercase tracking-wider text-indigo-300 flex items-center gap-1.5 font-semibold">
          <Wrench className="w-3.5 h-3.5" /> Recommended Remediation
        </div>
        <p className="text-xs text-text-secondary leading-relaxed">{fallbackText}</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-indigo-500/30 bg-[#0c101a] overflow-hidden shadow-lg shadow-black/40">
      {/* Header Banner */}
      <div className="p-4 border-b border-white/[0.08] bg-white/[0.02]">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/30 flex items-center gap-1">
                <Wrench className="w-3 h-3" /> Remediation Studio
              </span>
              <span className="text-[10px] font-mono text-text-muted flex items-center gap-1">
                <Clock className="w-3 h-3 text-indigo-400" /> ~{guide.estimated_time_minutes} min fix
              </span>
            </div>
            <h3 className="text-sm font-semibold text-text-primary leading-snug">
              {guide.title || `Remediate ${controlId}`}
            </h3>
          </div>
        </div>

        {guide.threat_rationale && (
          <p className="text-xs text-text-secondary mt-2 leading-relaxed border-l-2 border-indigo-500/40 pl-2.5">
            <strong className="text-indigo-300 font-medium">Why this matters: </strong>
            {guide.threat_rationale}
          </p>
        )}
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-white/[0.08] bg-black/30 px-3 pt-2 gap-1 overflow-x-auto">
        {([
          { id: 'console' as RemediationTab, label: 'Console Steps', icon: ShieldAlert, count: guide.console_steps?.length },
          { id: 'cli' as RemediationTab, label: 'AWS CLI', icon: Terminal, available: !!guide.aws_cli_command },
          { id: 'terraform' as RemediationTab, label: 'Terraform / IaC', icon: Layers, available: !!guide.terraform_snippet },
          { id: 'verify' as RemediationTab, label: 'Verification', icon: CheckCircle2, available: !!guide.verification_command },
        ]).map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-t-lg transition-colors border-t border-x -mb-[1px] ${
                isActive
                  ? 'bg-[#0c101a] border-white/10 text-indigo-300 font-semibold'
                  : 'bg-transparent border-transparent text-text-muted hover:text-text-primary'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-indigo-400' : 'text-text-muted'}`} />
              <span>{tab.label}</span>
              {tab.count !== undefined && tab.count > 0 && (
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-white/10 text-text-muted">
                  {tab.count}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Tab Content Panel */}
      <div className="p-4">
        {/* Tab 1: AWS Console Steps */}
        {activeTab === 'console' && (
          <div className="space-y-3">
            {guide.console_steps && guide.console_steps.length > 0 ? (
              <ol className="space-y-2.5">
                {guide.console_steps.map((step, idx) => (
                  <li key={idx} className="flex items-start gap-2.5 text-xs text-text-secondary leading-relaxed">
                    <span className="w-5 h-5 rounded-full bg-indigo-500/20 border border-indigo-500/40 text-indigo-300 flex items-center justify-center font-mono font-bold text-[10px] flex-shrink-0 mt-0.5">
                      {idx + 1}
                    </span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="text-xs text-text-muted">No console steps documented for this control.</p>
            )}
          </div>
        )}

        {/* Tab 2: AWS CLI Command */}
        {activeTab === 'cli' && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[11px] text-text-muted">
              <span>Execute via AWS CLI or CloudShell:</span>
              {guide.aws_cli_command && (
                <button
                  type="button"
                  onClick={() => copyToClipboard(guide.aws_cli_command, 'cli')}
                  className="flex items-center gap-1 px-2 py-1 rounded bg-white/5 hover:bg-white/10 text-indigo-300 hover:text-indigo-200 transition-colors text-[11px] font-mono"
                >
                  {copiedKey === 'cli' ? (
                    <>
                      <Check className="w-3 h-3 text-green-400" /> Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" /> Copy Command
                    </>
                  )}
                </button>
              )}
            </div>
            <pre className="p-3 rounded-lg bg-black/60 border border-white/10 text-[11px] font-mono text-indigo-200 overflow-x-auto whitespace-pre-wrap leading-relaxed selection:bg-indigo-500/30">
              {guide.aws_cli_command || '# No CLI command available.'}
            </pre>
          </div>
        )}

        {/* Tab 3: Terraform / IaC Snippet */}
        {activeTab === 'terraform' && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[11px] text-text-muted">
              <span>Declarative HashiCorp HCL configuration:</span>
              {guide.terraform_snippet && (
                <button
                  type="button"
                  onClick={() => copyToClipboard(guide.terraform_snippet, 'terraform')}
                  className="flex items-center gap-1 px-2 py-1 rounded bg-white/5 hover:bg-white/10 text-indigo-300 hover:text-indigo-200 transition-colors text-[11px] font-mono"
                >
                  {copiedKey === 'terraform' ? (
                    <>
                      <Check className="w-3 h-3 text-green-400" /> Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" /> Copy Terraform
                    </>
                  )}
                </button>
              )}
            </div>
            <pre className="p-3 rounded-lg bg-black/60 border border-white/10 text-[11px] font-mono text-purple-200 overflow-x-auto whitespace-pre-wrap leading-relaxed selection:bg-purple-500/30">
              {guide.terraform_snippet || '# No Terraform snippet available.'}
            </pre>
          </div>
        )}

        {/* Tab 4: Verification Command */}
        {activeTab === 'verify' && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[11px] text-text-muted">
              <span>Verify that the fix was applied before re-scanning:</span>
              {guide.verification_command && (
                <button
                  type="button"
                  onClick={() => copyToClipboard(guide.verification_command, 'verify')}
                  className="flex items-center gap-1 px-2 py-1 rounded bg-white/5 hover:bg-white/10 text-indigo-300 hover:text-indigo-200 transition-colors text-[11px] font-mono"
                >
                  {copiedKey === 'verify' ? (
                    <>
                      <Check className="w-3 h-3 text-green-400" /> Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" /> Copy
                    </>
                  )}
                </button>
              )}
            </div>
            <pre className="p-3 rounded-lg bg-black/60 border border-white/10 text-[11px] font-mono text-emerald-300 overflow-x-auto whitespace-pre-wrap leading-relaxed selection:bg-emerald-500/30">
              {guide.verification_command || '# Re-run audit to verify.'}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}
