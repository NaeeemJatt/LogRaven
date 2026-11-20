// LogRaven — Cloud Asset Detail Inspection Drawer
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Copy, Check, ShieldCheck, AlertTriangle, Server, Tag, Code2 } from 'lucide-react'
import type { AssetDetailRecord } from '../../api/assets'

interface AssetDetailDrawerProps {
  asset: AssetDetailRecord | null
  onClose: () => void
}

export default function AssetDetailDrawer({ asset, onClose }: AssetDetailDrawerProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'config' | 'tags'>('overview')
  const [copiedUrn, setCopiedUrn] = useState(false)
  const [copiedJson, setCopiedJson] = useState(false)

  if (!asset) return null

  const handleCopyUrn = () => {
    navigator.clipboard.writeText(asset.urn)
    setCopiedUrn(true)
    setTimeout(() => setCopiedUrn(false), 2000)
  }

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(asset.config_json, null, 2))
    setCopiedJson(true)
    setTimeout(() => setCopiedJson(false), 2000)
  }

  const isCompliant = asset.compliance_status === 'COMPLIANT'

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 overflow-hidden">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        />

        <div className="absolute inset-y-0 right-0 max-w-full flex pl-10">
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="w-screen max-w-2xl bg-[#0E1015] border-l border-white/[0.08] shadow-2xl flex flex-col"
          >
            {/* Header */}
            <div className="p-5 border-b border-white/[0.08] flex items-start justify-between gap-4 bg-[#0B0B0D]">
              <div className="min-w-0">
                <div className="flex items-center gap-2 mb-1.5">
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
                    isCompliant ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                  }`}>
                    {isCompliant ? <ShieldCheck className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                    {asset.compliance_status}
                  </span>
                  <span className="text-[11px] font-mono text-text-muted">
                    {asset.provider} • {asset.service}
                  </span>
                </div>
                <h2 className="text-base font-semibold text-text-primary truncate" title={asset.resource_name}>
                  {asset.resource_name}
                </h2>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-text-muted font-mono truncate max-w-md">{asset.urn}</span>
                  <button
                    type="button"
                    onClick={handleCopyUrn}
                    className="p-1 rounded text-text-muted hover:text-text-primary hover:bg-white/10 transition-colors"
                    title="Copy URN"
                  >
                    {copiedUrn ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              <button
                type="button"
                onClick={onClose}
                className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-white/10 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Subnav Tabs */}
            <div className="flex items-center gap-2 px-5 pt-3 border-b border-white/[0.08] bg-white/[0.02]">
              <button
                type="button"
                onClick={() => setActiveTab('overview')}
                className={`pb-2.5 px-2 text-xs font-medium border-b-2 transition-colors cursor-pointer flex items-center gap-1.5 ${
                  activeTab === 'overview' ? 'border-amber-400 text-amber-300' : 'border-transparent text-text-muted hover:text-text-primary'
                }`}
              >
                <Server className="w-3.5 h-3.5" /> Overview
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('config')}
                className={`pb-2.5 px-2 text-xs font-medium border-b-2 transition-colors cursor-pointer flex items-center gap-1.5 ${
                  activeTab === 'config' ? 'border-amber-400 text-amber-300' : 'border-transparent text-text-muted hover:text-text-primary'
                }`}
              >
                <Code2 className="w-3.5 h-3.5" /> Configuration JSON
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('tags')}
                className={`pb-2.5 px-2 text-xs font-medium border-b-2 transition-colors cursor-pointer flex items-center gap-1.5 ${
                  activeTab === 'tags' ? 'border-amber-400 text-amber-300' : 'border-transparent text-text-muted hover:text-text-primary'
                }`}
              >
                <Tag className="w-3.5 h-3.5" /> Tags ({Object.keys(asset.tags || {}).length})
              </button>
            </div>

            {/* Content Body */}
            <div className="flex-1 overflow-y-auto p-5">
              {activeTab === 'overview' && (
                <div className="space-y-6">
                  {/* Key metadata grid */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-lg border border-white/[0.08] p-3 bg-white/[0.02]">
                      <span className="text-[11px] text-text-muted font-mono block">Cloud provider</span>
                      <span className="text-sm font-semibold text-text-primary mt-0.5 block">{asset.provider}</span>
                    </div>
                    <div className="rounded-lg border border-white/[0.08] p-3 bg-white/[0.02]">
                      <span className="text-[11px] text-text-muted font-mono block">Account ID</span>
                      <span className="text-sm font-mono text-text-primary mt-0.5 block">{asset.account_id}</span>
                    </div>
                    <div className="rounded-lg border border-white/[0.08] p-3 bg-white/[0.02]">
                      <span className="text-[11px] text-text-muted font-mono block">Service / Category</span>
                      <span className="text-sm font-semibold text-text-primary mt-0.5 block">{asset.service}</span>
                    </div>
                    <div className="rounded-lg border border-white/[0.08] p-3 bg-white/[0.02]">
                      <span className="text-[11px] text-text-muted font-mono block">Region</span>
                      <span className="text-sm font-mono text-text-primary mt-0.5 block">{asset.region}</span>
                    </div>
                    <div className="rounded-lg border border-white/[0.08] p-3 bg-white/[0.02]">
                      <span className="text-[11px] text-text-muted font-mono block">Resource type</span>
                      <span className="text-sm font-mono text-text-primary mt-0.5 block">{asset.resource_type}</span>
                    </div>
                    <div className="rounded-lg border border-white/[0.08] p-3 bg-white/[0.02]">
                      <span className="text-[11px] text-text-muted font-mono block">Resource ID</span>
                      <span className="text-sm font-mono text-text-primary mt-0.5 block truncate" title={asset.resource_id}>{asset.resource_id}</span>
                    </div>
                  </div>

                  {/* Security Posture Status */}
                  <div className="rounded-lg border border-white/[0.08] p-4 bg-white/[0.02] border-l-2 border-l-amber-400">
                    <h3 className="text-xs font-semibold text-text-primary mb-2 flex items-center justify-between">
                      <span>Evaluated Compliance Controls</span>
                      <span className="text-xs font-mono text-text-muted">
                        {asset.passing_rule_count} Passed • {asset.failing_rule_count} Failed
                      </span>
                    </h3>
                    <p className="text-xs text-text-secondary leading-relaxed">
                      {isCompliant
                        ? 'This asset conforms to current cloud baseline hardening configurations and has zero active posture violations.'
                        : 'Security violations or misconfigurations were detected on this asset by deterministic CSPM compliance rules.'}
                    </p>
                  </div>

                  {/* Timestamps */}
                  <div className="rounded-lg border border-white/[0.08] p-3 bg-white/[0.02] space-y-1.5 text-xs text-text-muted font-mono">
                    <div className="flex justify-between">
                      <span>First Discovered:</span>
                      <span className="text-text-primary">{new Date(asset.first_seen_at).toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Last Seen / Verified:</span>
                      <span className="text-text-primary">{new Date(asset.last_seen_at).toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Configuration State SHA-256:</span>
                      <span className="text-text-primary truncate max-w-[200px]" title={asset.config_sha256}>{asset.config_sha256}</span>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'config' && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-text-muted font-mono">Raw Configuration Snapshot</span>
                    <button
                      type="button"
                      onClick={handleCopyJson}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded border border-white/10 text-xs font-mono text-text-muted hover:text-text-primary hover:bg-white/10 transition-colors"
                    >
                      {copiedJson ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedJson ? 'Copied' : 'Copy JSON'}</span>
                    </button>
                  </div>
                  <pre className="p-4 rounded-xl border border-white/[0.08] bg-[#070709] text-[11px] font-mono text-text-secondary overflow-x-auto max-h-[550px] leading-relaxed">
                    {JSON.stringify(asset.config_json, null, 2)}
                  </pre>
                </div>
              )}

              {activeTab === 'tags' && (
                <div className="space-y-3">
                  <span className="text-xs text-text-muted font-mono block">Cloud Resource Tags</span>
                  {Object.keys(asset.tags || {}).length === 0 ? (
                    <div className="rounded-lg border border-white/[0.08] p-6 text-center text-xs text-text-muted bg-white/[0.02]">
                      No tags or metadata labels discovered on this resource.
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 gap-2">
                      {Object.entries(asset.tags).map(([key, value]) => (
                        <div key={key} className="rounded-lg border border-white/[0.08] p-2.5 bg-white/[0.02] flex items-center justify-between font-mono text-xs">
                          <span className="text-text-secondary truncate mr-2">{key}</span>
                          <span className="text-text-primary truncate">{String(value)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        </div>
      </div>
    </AnimatePresence>
  )
}
