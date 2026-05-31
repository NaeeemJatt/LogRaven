import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Lock, Save, Eye, EyeOff, CheckCircle2, X, LogOut,
  Mail, CalendarClock, BadgeCheck, ShieldCheck,
} from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { useAuth } from '../hooks/useAuth'
import { useProfile } from '../hooks/useProfile'

type Tone = 'success' | 'error'

// = SHARED PIECES =

function Toast({ message, tone, onDone }: { message: string; tone: Tone; onDone: () => void }) {
  const ok = tone === 'success'
  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 8, scale: 0.96 }}
      onAnimationComplete={() => setTimeout(onDone, 2600)}
      className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-xl backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.4)] border ${
        ok ? 'border-teal-500/25 bg-teal-500/10' : 'border-rose-500/25 bg-rose-500/10'
      }`}
    >
      {ok ? <CheckCircle2 className="w-4 h-4 text-teal-400 flex-shrink-0" /> : <X className="w-4 h-4 text-rose-400 flex-shrink-0" />}
      <span className={`text-sm font-medium ${ok ? 'text-teal-300' : 'text-rose-300'}`}>{message}</span>
      <button onClick={onDone} className={`ml-1 transition-colors ${ok ? 'text-teal-400/60 hover:text-teal-400' : 'text-rose-400/60 hover:text-rose-400'}`}>
        <X className="w-3.5 h-3.5" />
      </button>
    </motion.div>
  )
}

function SettingsCard({ icon: Icon, title, description, children }: {
  icon: typeof Lock; title: string; description: string; children: React.ReactNode
}) {
  return (
    <div className="rounded-2xl border border-white/[0.06] bg-surface/40 backdrop-blur overflow-hidden">
      <div className="px-6 py-5 border-b border-white/[0.06] flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center flex-shrink-0">
          <Icon className="w-4 h-4 text-indigo-400" />
        </div>
        <div>
          <div className="font-display font-semibold text-text-primary text-base">{title}</div>
          <p className="text-text-muted text-xs mt-0.5">{description}</p>
        </div>
      </div>
      <div className="px-6 py-5">{children}</div>
    </div>
  )
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="mb-5 last:mb-0">
      <label className="block text-sm font-medium text-text-primary mb-1.5">{label}</label>
      {hint && <p className="font-mono text-[10px] text-text-muted mb-2 leading-relaxed">{hint}</p>}
      {children}
    </div>
  )
}

// = PROFILE FORM =

function ProfileForm({ notify }: { notify: (msg: string, tone: Tone) => void }) {
  const user = useAuthStore((s) => s.user)
  const setUser = useAuthStore((s) => s.setUser)
  const { updateProfile, isUpdatingProfile } = useProfile()

  const defaultName = user?.name ?? user?.email?.split('@')[0] ?? ''
  const [name, setName] = useState(defaultName)

  const handleSave = async () => {
    try {
      const res = await updateProfile({ name })
      if (res?.data) setUser(res.data)
      notify('Profile updated successfully', 'success')
    } catch {
      notify('Failed to update profile.', 'error')
    }
  }

  return (
    <SettingsCard icon={BadgeCheck} title="Profile information" description="Your display name and preferences">
      <Field label="Display name" hint="Shown across the platform">
        <input value={name} onChange={(e) => setName(e.target.value)} maxLength={120}
          className="sovereign-input w-full px-4 py-2.5 rounded-xl text-sm" placeholder="Your name" />
      </Field>

      <Field label="Email address" hint="Used for login — contact support to change">
        <div className="flex gap-2">
          <input value={user?.email ?? ''} readOnly
            className="sovereign-input flex-1 px-4 py-2.5 rounded-xl text-sm opacity-60 cursor-not-allowed" />
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-teal-500/10 border border-teal-500/20 text-teal-400 font-mono text-[10px] flex-shrink-0">
            <CheckCircle2 className="w-3 h-3" /> Verified
          </span>
        </div>
      </Field>

      <div className="flex justify-end pt-1">
        <button onClick={handleSave} disabled={isUpdatingProfile}
          className="btn-sovereign flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white disabled:opacity-60">
          <Save className="w-4 h-4" /> {isUpdatingProfile ? 'Saving…' : 'Save changes'}
        </button>
      </div>
    </SettingsCard>
  )
}

// = SECURITY FORM =

function SecurityForm({ notify }: { notify: (msg: string, tone: Tone) => void }) {
  const { changePassword, isChangingPassword } = useProfile()
  const [showCurrent, setShowCurrent] = useState(false)
  const [showNew, setShowNew] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [currentPass, setCurrentPass] = useState('')
  const [newPass, setNewPass] = useState('')
  const [confirmPass, setConfirmPass] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)

  const strength = newPass.length === 0 ? 0 : newPass.length < 8 ? 1 : newPass.length < 14 ? 2 : 3
  const strengthColor = ['', '#DB8585', '#D9C27E', '#8FBDAD'][strength]
  const strengthLabel = ['', 'Weak', 'Fair', 'Strong'][strength]

  const handleChange = async () => {
    setLocalError(null)
    if (newPass !== confirmPass) { setLocalError('Passwords do not match.'); return }
    if (newPass.length < 8) { setLocalError('Password must be at least 8 characters.'); return }
    try {
      await changePassword({ current_password: currentPass, new_password: newPass })
      setCurrentPass(''); setNewPass(''); setConfirmPass('')
      notify('Password changed successfully', 'success')
    } catch (err: any) {
      notify(err?.response?.data?.detail ?? 'Failed to change password.', 'error')
    }
  }

  const eye = (shown: boolean, toggle: () => void) => (
    <button type="button" onClick={toggle}
      className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary transition-colors">
      {shown ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
    </button>
  )

  return (
    <SettingsCard icon={Lock} title="Password" description="Use a strong, unique password">
      <Field label="Current password">
        <div className="relative">
          <input type={showCurrent ? 'text' : 'password'} value={currentPass} onChange={(e) => setCurrentPass(e.target.value)}
            placeholder="••••••••" className="sovereign-input w-full pl-4 pr-10 py-2.5 rounded-xl text-sm" />
          {eye(showCurrent, () => setShowCurrent(!showCurrent))}
        </div>
      </Field>

      <Field label="New password" hint="Minimum 8 characters">
        <div className="relative mb-2">
          <input type={showNew ? 'text' : 'password'} value={newPass} onChange={(e) => setNewPass(e.target.value)}
            placeholder="New password" className="sovereign-input w-full pl-4 pr-10 py-2.5 rounded-xl text-sm" />
          {eye(showNew, () => setShowNew(!showNew))}
        </div>
        {newPass.length > 0 && (
          <div className="flex items-center gap-2">
            <div className="flex gap-1 flex-1">
              {[1, 2, 3].map((s) => (
                <div key={s} className="h-1 flex-1 rounded-full transition-all duration-300"
                  style={{ background: s <= strength ? strengthColor : 'rgba(255,255,255,0.06)' }} />
              ))}
            </div>
            <span className="font-mono text-[10px]" style={{ color: strengthColor }}>{strengthLabel}</span>
          </div>
        )}
      </Field>

      <Field label="Confirm new password">
        <div className="relative">
          <input type={showConfirm ? 'text' : 'password'} value={confirmPass} onChange={(e) => setConfirmPass(e.target.value)}
            placeholder="Repeat new password" className="sovereign-input w-full pl-4 pr-10 py-2.5 rounded-xl text-sm" />
          {eye(showConfirm, () => setShowConfirm(!showConfirm))}
        </div>
      </Field>

      {localError && (
        <p className="text-rose-400 text-xs font-mono px-4 py-2 rounded-lg bg-rose-500/5 border border-rose-500/15 mb-4">{localError}</p>
      )}

      <div className="flex justify-end pt-1">
        <button onClick={handleChange} disabled={isChangingPassword || !currentPass || !newPass}
          className="btn-sovereign flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white disabled:opacity-40">
          <Lock className="w-4 h-4" /> {isChangingPassword ? 'Updating…' : 'Update password'}
        </button>
      </div>
    </SettingsCard>
  )
}

// = PAGE =

export default function ProfilePage() {
  const user = useAuthStore((s) => s.user)
  const { logout } = useAuth()
  const [toast, setToast] = useState<{ msg: string; tone: Tone } | null>(null)

  const displayName = user?.name ?? user?.email?.split('@')[0] ?? 'User'
  const initials = displayName.slice(0, 2).toUpperCase()
  const tier = user?.tier?.toUpperCase() ?? 'FREE'
  const memberSince = user?.created_at
    ? new Date(user.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : '—'

  const notify = (msg: string, tone: Tone) => setToast({ msg, tone })

  return (
    <div className="pt-16 min-h-screen">
      {/* Page header */}
      <div className="border-b border-white/[0.04] bg-deep/30">
        <div className="px-4 sm:px-6 lg:px-8 py-5 max-w-6xl mx-auto">
          <div className="font-mono text-[10px] text-indigo-400 tracking-widest uppercase mb-1">Account</div>
          <h1 className="font-display font-bold text-text-primary text-2xl">Profile &amp; Settings</h1>
        </div>
      </div>

      <div className="px-4 sm:px-6 lg:px-8 py-8 max-w-6xl mx-auto">
        <div className="grid md:grid-cols-[300px_1fr] gap-6 items-start">

          {/* Identity rail */}
          <div className="md:sticky md:top-20">
            <div className="rounded-2xl border border-white/[0.06] bg-surface/40 backdrop-blur overflow-hidden">
              <div className="p-6 text-center border-b border-white/[0.06]">
                <div className="relative inline-block mb-4">
                  <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500/40 to-indigo-700/40 border border-indigo-500/30 flex items-center justify-center mx-auto">
                    <span className="font-display font-bold text-2xl text-indigo-200">{initials}</span>
                  </div>
                  <span className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-teal-400 border-[3px] border-surface" />
                </div>
                <div className="font-display font-semibold text-text-primary text-lg truncate">{displayName}</div>
                <div className="font-mono text-[11px] text-text-muted truncate mt-0.5">{user?.email}</div>
                <span className="inline-flex items-center gap-1.5 mt-3 px-2.5 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 font-mono text-[10px] tracking-wider">
                  <ShieldCheck className="w-3 h-3" /> {tier} PLAN
                </span>
              </div>

              <div className="p-4 space-y-3">
                <div className="flex items-center gap-2.5 text-text-secondary">
                  <Mail className="w-3.5 h-3.5 text-text-muted flex-shrink-0" />
                  <span className="text-xs truncate">{user?.email}</span>
                </div>
                <div className="flex items-center gap-2.5 text-text-secondary">
                  <CalendarClock className="w-3.5 h-3.5 text-text-muted flex-shrink-0" />
                  <span className="text-xs">Member since {memberSince}</span>
                </div>
              </div>

              <div className="p-4 border-t border-white/[0.06]">
                <button onClick={logout}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium border border-white/[0.08] text-text-secondary hover:text-rose-400 hover:border-rose-500/25 hover:bg-rose-500/5 transition-all">
                  <LogOut className="w-4 h-4" /> Sign out
                </button>
              </div>
            </div>
          </div>

          {/* Settings */}
          <motion.div
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
            className="space-y-6"
          >
            <ProfileForm notify={notify} />
            <SecurityForm notify={notify} />
          </motion.div>
        </div>
      </div>

      <AnimatePresence>
        {toast && <Toast message={toast.msg} tone={toast.tone} onDone={() => setToast(null)} />}
      </AnimatePresence>
    </div>
  )
}
