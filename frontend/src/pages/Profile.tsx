import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  User, Lock, Key, CreditCard, Trash2,
  Save, Eye, EyeOff, Copy, Check,
  AlertTriangle, ChevronRight, Activity,
  Zap, Clock, CheckCircle2, X
} from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { useAuth } from '../hooks/useAuth'
import { useProfile } from '../hooks/useProfile'

const sections = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'security', label: 'Security', icon: Lock },
  { id: 'api', label: 'API Keys', icon: Key },
  { id: 'billing', label: 'Billing & Plan', icon: CreditCard },
  { id: 'activity', label: 'Activity', icon: Activity },
  { id: 'danger', label: 'Danger Zone', icon: AlertTriangle },
]

function FieldRow({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-start py-5 border-b border-white/[0.04] last:border-b-0">
      <div className="md:pt-2.5">
        <div className="text-sm font-medium text-text-primary">{label}</div>
        {hint && <div className="font-mono text-[10px] text-text-muted mt-0.5 leading-relaxed">{hint}</div>}
      </div>
      <div className="md:col-span-2">{children}</div>
    </div>
  )
}

function SectionCard({ title, description, children, danger }: {
  title: string; description?: string; children: React.ReactNode; danger?: boolean
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="rounded-2xl border border-white/[0.06] bg-surface/40 backdrop-blur overflow-hidden"
    >
      <div className="px-6 py-4 border-b border-white/[0.06]">
        <div className={`font-display font-semibold text-base ${danger ? 'text-rose-400' : 'text-text-primary'}`}>{title}</div>
        {description && <p className="text-text-muted text-xs mt-0.5">{description}</p>}
      </div>
      <div className="px-6 py-2">{children}</div>
    </motion.div>
  )
}

function Toast({ message, onDone }: { message: string; onDone: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 8, scale: 0.96 }}
      onAnimationComplete={() => setTimeout(onDone, 2200)}
      className="fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-xl border border-teal-500/25 bg-teal-500/10 backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.4)]"
    >
      <CheckCircle2 className="w-4 h-4 text-teal-400 flex-shrink-0" />
      <span className="text-sm font-medium text-teal-300">{message}</span>
      <button onClick={onDone} className="ml-1 text-teal-400/60 hover:text-teal-400 transition-colors">
        <X className="w-3.5 h-3.5" />
      </button>
    </motion.div>
  )
}

function ProfileSection({ onSave, onError }: { onSave: (msg: string) => void; onError: (msg: string) => void }) {
  const user = useAuthStore((s) => s.user)
  const { updateProfile, isUpdatingProfile } = useProfile()

  const defaultName = user?.email?.split('@')[0] ?? ''
  const [name, setName] = useState(defaultName)
  const [timezone, setTimezone] = useState('UTC+0 (London)')
  const initials = (name || defaultName).slice(0, 2).toUpperCase()

  const handleSave = async () => {
    try {
      await updateProfile({ name, timezone })
      onSave('Profile updated successfully')
    } catch {
      onError('Failed to update profile.')
    }
  }

  return (
    <SectionCard title="Profile information" description="Your account details and display name">
      <div className="py-5 border-b border-white/[0.04]">
        <div className="flex items-center gap-5">
          <div className="relative">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500/40 to-violet-500/40 border border-indigo-500/30 flex items-center justify-center">
              <span className="font-display font-bold text-xl text-indigo-200">{initials}</span>
            </div>
            <span className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-teal-400 border-2 border-surface" />
          </div>
          <div>
            <div className="text-sm font-medium text-text-primary mb-1">Profile avatar</div>
            <p className="font-mono text-[10px] text-text-muted">Generated from your display name</p>
          </div>
        </div>
      </div>

      <FieldRow label="Display name" hint="Your name shown across the platform">
        <input value={name} onChange={e => setName(e.target.value)}
          className="sovereign-input w-full px-4 py-2.5 rounded-xl text-sm" />
      </FieldRow>

      <FieldRow label="Email address" hint="Used for login — contact support to change">
        <div className="flex gap-2">
          <input value={user?.email ?? ''} readOnly
            className="sovereign-input flex-1 px-4 py-2.5 rounded-xl text-sm opacity-60 cursor-not-allowed" />
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-teal-500/10 border border-teal-500/20 text-teal-400 font-mono text-[10px] flex-shrink-0">
            <CheckCircle2 className="w-3 h-3" /> Verified
          </span>
        </div>
      </FieldRow>

      <FieldRow label="Plan" hint="Your current subscription tier">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs px-2.5 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-300">
            {user?.tier?.toUpperCase() ?? 'FREE'}
          </span>
        </div>
      </FieldRow>

      <FieldRow label="Timezone">
        <select value={timezone} onChange={e => setTimezone(e.target.value)}
          className="sovereign-input w-full px-4 py-2.5 rounded-xl text-sm cursor-pointer">
          {['UTC+0 (London)', 'UTC+1 (Berlin)', 'UTC+5 (Karachi)', 'UTC+8 (Singapore)', 'UTC-5 (New York)', 'UTC-8 (Los Angeles)'].map(t => (
            <option key={t} value={t} style={{ background: '#0F1422' }}>{t}</option>
          ))}
        </select>
      </FieldRow>

      <div className="flex justify-end py-4">
        <button onClick={handleSave} disabled={isUpdatingProfile}
          className="btn-sovereign flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white disabled:opacity-60">
          <Save className="w-4 h-4" /> {isUpdatingProfile ? 'Saving…' : 'Save changes'}
        </button>
      </div>
    </SectionCard>
  )
}

function SecuritySection({ onSave, onError }: { onSave: (msg: string) => void; onError: (msg: string) => void }) {
  const { changePassword, isChangingPassword } = useProfile()
  const [showCurrent, setShowCurrent] = useState(false)
  const [showNew, setShowNew] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [currentPass, setCurrentPass] = useState('')
  const [newPass, setNewPass] = useState('')
  const [confirmPass, setConfirmPass] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)

  const strength = newPass.length === 0 ? 0 : newPass.length < 8 ? 1 : newPass.length < 14 ? 2 : 3
  const strengthColor = ['', '#F43F5E', '#FBBF24', '#14B8A6'][strength]
  const strengthLabel = ['', 'Weak', 'Fair', 'Strong'][strength]

  const handlePasswordChange = async () => {
    setLocalError(null)
    if (newPass !== confirmPass) { setLocalError('Passwords do not match.'); return }
    if (newPass.length < 8) { setLocalError('Password must be at least 8 characters.'); return }
    try {
      await changePassword({ current_password: currentPass, new_password: newPass })
      setCurrentPass(''); setNewPass(''); setConfirmPass('')
      onSave('Password changed successfully')
    } catch (err: any) {
      onError(err?.response?.data?.detail ?? 'Failed to change password.')
    }
  }

  const sessions = [
    { device: 'Chrome · Windows 11', location: 'Current session', time: 'Now', current: true },
    { device: 'Firefox · macOS', location: 'Previous session', time: '2 days ago', current: false },
  ]

  return (
    <div className="space-y-5">
      <SectionCard title="Change password" description="Use a strong, unique password for your account">
        <FieldRow label="Current password">
          <div className="relative">
            <input type={showCurrent ? 'text' : 'password'} value={currentPass} onChange={e => setCurrentPass(e.target.value)} placeholder="••••••••"
              className="sovereign-input w-full pl-4 pr-10 py-2.5 rounded-xl text-sm" />
            <button onClick={() => setShowCurrent(!showCurrent)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary transition-colors">
              {showCurrent ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            </button>
          </div>
        </FieldRow>
        <FieldRow label="New password" hint="Minimum 8 characters">
          <div className="relative mb-2">
            <input type={showNew ? 'text' : 'password'} value={newPass} onChange={e => setNewPass(e.target.value)} placeholder="New password"
              className="sovereign-input w-full pl-4 pr-10 py-2.5 rounded-xl text-sm" />
            <button onClick={() => setShowNew(!showNew)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary transition-colors">
              {showNew ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            </button>
          </div>
          {newPass.length > 0 && (
            <div className="flex items-center gap-2">
              <div className="flex gap-1 flex-1">
                {[1, 2, 3].map(s => (
                  <div key={s} className="h-1 flex-1 rounded-full transition-all duration-300"
                    style={{ background: s <= strength ? strengthColor : 'rgba(255,255,255,0.06)' }} />
                ))}
              </div>
              <span className="font-mono text-[10px]" style={{ color: strengthColor }}>{strengthLabel}</span>
            </div>
          )}
        </FieldRow>
        <FieldRow label="Confirm new password">
          <div className="relative">
            <input type={showConfirm ? 'text' : 'password'} value={confirmPass} onChange={e => setConfirmPass(e.target.value)} placeholder="Repeat new password"
              className="sovereign-input w-full pl-4 pr-10 py-2.5 rounded-xl text-sm" />
            <button onClick={() => setShowConfirm(!showConfirm)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary transition-colors">
              {showConfirm ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            </button>
          </div>
        </FieldRow>
        {localError && (
          <p className="text-rose-400 text-xs font-mono px-4 py-2 rounded-lg bg-rose-500/5 border border-rose-500/15 my-2">{localError}</p>
        )}
        <div className="flex justify-end py-4">
          <button onClick={handlePasswordChange} disabled={isChangingPassword || !currentPass || !newPass}
            className="btn-sovereign flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white disabled:opacity-40">
            <Lock className="w-4 h-4" /> {isChangingPassword ? 'Updating…' : 'Update password'}
          </button>
        </div>
      </SectionCard>

      <SectionCard title="Active sessions" description="Devices currently signed in to your account">
        <div className="py-2">
          {sessions.map((s, i) => (
            <div key={i} className="flex items-center justify-between py-3.5 border-b border-white/[0.04] last:border-b-0">
              <div className="flex items-center gap-3">
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${s.current ? 'bg-teal-400' : 'bg-text-muted'}`} />
                <div>
                  <div className="text-sm font-medium text-text-primary flex items-center gap-2">
                    {s.device}
                    {s.current && (
                      <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-teal-500/10 border border-teal-500/20 text-teal-400">Current</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="font-mono text-[10px] text-text-muted">{s.location}</span>
                    <span className="text-text-ghost">·</span>
                    <span className="font-mono text-[10px] text-text-muted flex items-center gap-1">
                      <Clock className="w-2.5 h-2.5" /> {s.time}
                    </span>
                  </div>
                </div>
              </div>
              {!s.current && (
                <button className="text-xs text-text-muted hover:text-rose-400 transition-colors font-medium">Revoke</button>
              )}
            </div>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Two-factor authentication" description="Add an extra layer of security to your account">
        <div className="py-4 flex items-center justify-between">
          <div>
            <div className="text-sm font-medium text-text-primary flex items-center gap-2">
              Authenticator app
              <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 text-amber-400">Not configured</span>
            </div>
            <div className="font-mono text-[10px] text-text-muted mt-0.5">Adds a one-time code requirement at sign-in</div>
          </div>
          <button className="btn-sovereign flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold text-white">
            Enable 2FA <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </SectionCard>
    </div>
  )
}

function ApiSection({ onSave }: { onSave: (msg: string) => void }) {
  const [copied, setCopied] = useState<string | null>(null)
  const [showKey, setShowKey] = useState<string | null>(null)

  const keys = [
    { id: 'k1', name: 'Production key', key: 'lr_live_sk_9xKm2pQwRt8vNcLjHbFdYeUoAiZgXs3T', created: 'Jan 12, 2026', last_used: '2 hours ago', active: true },
    { id: 'k2', name: 'CI/CD pipeline', key: 'lr_live_sk_4mDnE7fCaWqBxVyGhPzOuIjKlRsT2N5Y', created: 'Mar 5, 2026', last_used: 'Yesterday', active: true },
  ]

  const copyKey = (id: string, key: string) => {
    navigator.clipboard.writeText(key).catch(() => {})
    setCopied(id)
    setTimeout(() => setCopied(null), 2000)
  }

  const maskKey = (key: string) => key.slice(0, 14) + '••••••••••••••••' + key.slice(-4)

  return (
    <SectionCard title="API keys" description="Use these keys to authenticate with the LogRaven API">
      <div className="py-2">
        {keys.map((k) => (
          <div key={k.id} className="py-4 border-b border-white/[0.04] last:border-b-0">
            <div className="flex items-start justify-between gap-4 mb-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-text-primary">{k.name}</span>
                  <span className={`font-mono text-[9px] px-1.5 py-0.5 rounded border ${
                    k.active ? 'bg-teal-500/10 border-teal-500/20 text-teal-400' : 'bg-white/[0.04] border-white/[0.08] text-text-muted'
                  }`}>{k.active ? 'Active' : 'Inactive'}</span>
                </div>
                <div className="flex items-center gap-3 mt-0.5">
                  <span className="font-mono text-[10px] text-text-muted">Created {k.created}</span>
                  <span className="text-text-ghost">·</span>
                  <span className="font-mono text-[10px] text-text-muted flex items-center gap-1">
                    <Zap className="w-2.5 h-2.5" /> Last used {k.last_used}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-1 flex-shrink-0">
                <button onClick={() => setShowKey(showKey === k.id ? null : k.id)}
                  className="p-1.5 rounded-lg hover:bg-white/[0.05] text-text-muted hover:text-text-secondary transition-all">
                  {showKey === k.id ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                </button>
                <button onClick={() => copyKey(k.id, k.key)}
                  className="p-1.5 rounded-lg hover:bg-white/[0.05] text-text-muted hover:text-indigo-400 transition-all">
                  {copied === k.id ? <Check className="w-3.5 h-3.5 text-teal-400" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
                <button className="p-1.5 rounded-lg hover:bg-rose-500/10 text-text-muted hover:text-rose-400 transition-all">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-deep border border-white/[0.05]">
              <Key className="w-3 h-3 text-text-muted flex-shrink-0" />
              <code className="font-mono text-[11px] text-indigo-300/80 flex-1 truncate">
                {showKey === k.id ? k.key : maskKey(k.key)}
              </code>
            </div>
          </div>
        ))}
      </div>
      <div className="flex justify-end py-4">
        <button onClick={() => onSave('New API key generated')}
          className="btn-sovereign flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white">
          <Key className="w-4 h-4" /> Generate new key
        </button>
      </div>
    </SectionCard>
  )
}

function BillingSection() {
  const user = useAuthStore((s) => s.user)
  const tier = user?.tier?.toLowerCase() ?? 'free'
  const isPro = tier === 'pro'

  return (
    <div className="space-y-5">
      <SectionCard title="Current plan" description="Your subscription and usage">
        <div className="py-4">
          <div className="flex items-start justify-between gap-4 mb-6">
            <div>
              <div className="font-display font-bold text-text-primary text-lg">{isPro ? 'Pro Plan' : 'Free Plan'}</div>
              <div className="text-text-muted text-sm">{isPro ? '$49 / month' : 'No subscription'}</div>
            </div>
            <button className="btn-ghost px-4 py-2 rounded-xl text-xs font-medium text-text-secondary flex-shrink-0">
              {isPro ? 'Change plan' : 'Upgrade to Pro'}
            </button>
          </div>
          {[
            { label: 'Investigations', used: 18, limit: isPro ? null : 5 },
            { label: 'AI analysis calls', used: 12, limit: isPro ? null : 10 },
            { label: 'PDF reports', used: 6, limit: isPro ? null : 3 },
          ].map(({ label, used, limit }) => (
            <div key={label} className="flex items-center justify-between py-2.5 border-b border-white/[0.04] last:border-b-0">
              <span className="text-sm text-text-secondary">{label}</span>
              <div className="flex items-center gap-3">
                {limit !== null && limit !== undefined && (
                  <div className="w-24 h-1 rounded-full bg-white/[0.06] overflow-hidden">
                    <div className="h-full rounded-full bg-indigo-500/60" style={{ width: `${Math.min((used / (limit as number)) * 100, 100)}%` }} />
                  </div>
                )}
                <span className="font-mono text-xs text-text-muted">
                  {used}{limit !== null && limit !== undefined ? ` / ${limit}` : ' / ∞'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  )
}

function ActivitySection() {
  const events = [
    { color: '#14B8A6', title: 'Investigation completed', sub: 'Prod Server Anomaly — 12 findings', time: '2h ago' },
    { color: '#818CF8', title: 'API key used', sub: 'Production key · POST /api/v1/investigations', time: '2h ago' },
    { color: '#F97316', title: 'Analysis started', sub: 'CloudTrail Lateral Movement Review', time: '2 days ago' },
    { color: '#F43F5E', title: 'Password changed', sub: 'From Chrome on Windows 11', time: '5 days ago' },
    { color: '#818CF8', title: 'Account created', sub: 'Welcome to LogRaven', time: 'Jan 12, 2026' },
  ]
  return (
    <SectionCard title="Recent activity" description="Audit log of actions on your account">
      <div className="py-2">
        {events.map((e, i) => (
          <motion.div key={i}
            initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }}
            className="flex items-start justify-between gap-4 py-3.5 border-b border-white/[0.04] last:border-b-0"
          >
            <div className="flex items-start gap-3 min-w-0">
              <div className="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0" style={{ background: e.color }} />
              <div className="min-w-0">
                <div className="text-sm font-medium text-text-primary">{e.title}</div>
                <div className="font-mono text-[10px] text-text-muted mt-0.5">{e.sub}</div>
              </div>
            </div>
            <div className="font-mono text-[10px] text-text-muted flex-shrink-0 mt-0.5">{e.time}</div>
          </motion.div>
        ))}
      </div>
    </SectionCard>
  )
}

function DangerSection() {
  const { logout } = useAuth()
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [confirmInput, setConfirmInput] = useState('')

  return (
    <div className="space-y-4">
      <SectionCard title="Danger zone" description="Irreversible actions. Proceed with caution." danger>
        <div className="divide-y divide-white/[0.04]">
          <div className="flex items-center justify-between py-4">
            <div>
              <div className="text-sm font-medium text-text-primary">Sign out everywhere</div>
              <div className="font-mono text-[10px] text-text-muted mt-0.5">Revokes your current session and redirects to login</div>
            </div>
            <button onClick={logout}
              className="px-4 py-2 rounded-xl text-xs font-medium border border-white/[0.08] text-text-secondary hover:text-text-primary hover:bg-white/[0.04] transition-all flex-shrink-0 ml-4">
              Sign out
            </button>
          </div>

          <div className="flex items-center justify-between py-4">
            <div>
              <div className="text-sm font-medium text-text-primary">Export all data</div>
              <div className="font-mono text-[10px] text-text-muted mt-0.5">Download a complete archive of your investigations and reports</div>
            </div>
            <button className="btn-ghost px-4 py-2 rounded-xl text-xs font-medium text-text-secondary flex-shrink-0 ml-4">
              Request export
            </button>
          </div>

          <div className="flex items-center justify-between py-4">
            <div>
              <div className="text-sm font-medium text-rose-400">Delete account</div>
              <div className="font-mono text-[10px] text-text-muted mt-0.5">Permanently delete your account, all investigations, and data</div>
            </div>
            <button onClick={() => setConfirmDelete(true)}
              className="px-4 py-2 rounded-xl text-xs font-medium border border-rose-500/25 bg-rose-500/8 text-rose-400 hover:bg-rose-500/15 transition-all flex-shrink-0 ml-4">
              Delete account
            </button>
          </div>
        </div>
      </SectionCard>

      <AnimatePresence>
        {confirmDelete && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
              onClick={() => setConfirmDelete(false)} />
            <motion.div initial={{ opacity: 0, scale: 0.96, y: 16 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.96 }}
              className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-md px-4">
              <div className="rounded-2xl border border-rose-500/20 bg-[#0d0810] p-6 shadow-[0_24px_64px_rgba(0,0,0,0.8)]">
                <h3 className="font-display font-bold text-text-primary text-lg mb-1">Delete your account?</h3>
                <p className="text-text-muted text-sm mb-5 leading-relaxed">
                  This will permanently delete your account, all investigations, reports, and data. This action{' '}
                  <strong className="text-text-primary">cannot be undone</strong>.
                </p>
                <div className="mb-5">
                  <label className="block font-mono text-[10px] text-text-muted tracking-widest uppercase mb-2">
                    Type <span className="text-rose-400">delete my account</span> to confirm
                  </label>
                  <input value={confirmInput} onChange={e => setConfirmInput(e.target.value)}
                    placeholder="delete my account"
                    className="sovereign-input w-full px-4 py-2.5 rounded-xl text-sm" autoFocus />
                </div>
                <div className="flex gap-3">
                  <button onClick={() => setConfirmDelete(false)}
                    className="flex-1 btn-ghost py-2.5 rounded-xl text-sm font-medium text-text-secondary">Cancel</button>
                  <button disabled={confirmInput !== 'delete my account'}
                    className="flex-1 py-2.5 rounded-xl text-sm font-semibold border border-rose-500/30 bg-rose-500/15 text-rose-400 hover:bg-rose-500/25 transition-all disabled:opacity-30 disabled:cursor-not-allowed">
                    Delete permanently
                  </button>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}

export default function ProfilePage() {
  const user = useAuthStore((s) => s.user)
  const [activeSection, setActiveSection] = useState('profile')
  const [toast, setToast] = useState<string | null>(null)

  const displayName = user?.email?.split('@')[0] ?? 'User'
  const initials = displayName.slice(0, 2).toUpperCase()
  const tier = user?.tier?.toUpperCase() ?? 'FREE'

  const handleSave = (msg: string) => setToast(msg)
  const handleError = (msg: string) => setToast(msg)

  const sectionComponents: Record<string, React.ReactNode> = {
    profile: <ProfileSection onSave={handleSave} onError={handleError} />,
    security: <SecuritySection onSave={handleSave} onError={handleError} />,
    api: <ApiSection onSave={handleSave} />,
    billing: <BillingSection />,
    activity: <ActivitySection />,
    danger: <DangerSection />,
  }

  return (
    <div className="pt-16 min-h-screen">
      <div className="border-b border-white/[0.04] bg-deep/30">
        <div className="px-4 sm:px-6 lg:px-8 py-5">
          <div className="font-mono text-[10px] text-indigo-400 tracking-widest uppercase mb-1">Account</div>
          <h1 className="font-display font-bold text-text-primary text-2xl">Profile &amp; Settings</h1>
        </div>
      </div>

      <div className="px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">

          {/* Sidebar */}
          <div className="lg:col-span-1">
            <div className="rounded-2xl border border-white/[0.06] bg-surface/40 overflow-hidden sticky top-20">
              <div className="px-4 py-4 border-b border-white/[0.06] flex items-center gap-3">
                <div className="relative flex-shrink-0">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500/40 to-violet-500/40 border border-indigo-500/30 flex items-center justify-center">
                    <span className="font-display font-bold text-sm text-indigo-200">{initials}</span>
                  </div>
                  <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-teal-400 border-2 border-surface" />
                </div>
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-text-primary truncate">{displayName}</div>
                  <div className="font-mono text-[10px] text-text-muted truncate">{tier} plan</div>
                </div>
              </div>

              <div className="p-2">
                {sections.map(({ id, label, icon: Icon }) => (
                  <button
                    key={id}
                    onClick={() => setActiveSection(id)}
                    className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm transition-all duration-150 text-left ${
                      activeSection === id
                        ? id === 'danger'
                          ? 'bg-rose-500/10 border border-rose-500/20 text-rose-400'
                          : 'bg-indigo-500/10 border border-indigo-500/20 text-indigo-300'
                        : id === 'danger'
                          ? 'text-rose-400/60 hover:text-rose-400 hover:bg-rose-500/8 border border-transparent'
                          : 'text-text-secondary hover:text-text-primary hover:bg-white/[0.04] border border-transparent'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5 flex-shrink-0" />
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Main content */}
          <div className="lg:col-span-3">
            <AnimatePresence mode="wait">
              <motion.div key={activeSection}>
                {sectionComponents[activeSection]}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>

      <AnimatePresence>
        {toast && <Toast message={toast} onDone={() => setToast(null)} />}
      </AnimatePresence>
    </div>
  )
}
