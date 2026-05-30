import { useRef } from 'react'
import { Link } from 'react-router-dom'
import { motion, useScroll, useTransform, useInView } from 'framer-motion'
import { Shield, ArrowRight, ChevronRight } from 'lucide-react'
import { useAuthStore } from '../store/authStore'

function SectionReveal({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-80px' })
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 32 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.7, delay, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      {children}
    </motion.div>
  )
}

function FeatureCard({ title, description, index }: { title: string; description: string; index: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-60px' })
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 24 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.5, delay: index * 0.07 }}
      className="p-6 rounded-2xl border border-white/[0.06] bg-surface/50 hover:border-white/[0.10] hover:bg-elevated/60 transition-all duration-200"
    >
      <h3 className="font-display font-semibold text-text-primary text-base mb-2">{title}</h3>
      <p className="text-text-secondary text-sm leading-relaxed">{description}</p>
    </motion.div>
  )
}

function Step({ num, title, description, index }: { num: string; title: string; description: string; index: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, margin: '-60px' })
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, x: -16 }}
      animate={inView ? { opacity: 1, x: 0 } : {}}
      transition={{ duration: 0.5, delay: index * 0.1 }}
      className="flex gap-5"
    >
      <div className="flex flex-col items-center">
        <div className="w-8 h-8 flex items-center justify-center flex-shrink-0">
          <span className="font-mono text-sm font-bold text-indigo-500">{num}</span>
        </div>
        {index < 3 && <div className="w-px flex-1 bg-white/[0.06] mt-2" />}
      </div>
      <div className="pb-10">
        <h3 className="font-display font-semibold text-text-primary mb-1">{title}</h3>
        <p className="text-text-secondary text-sm leading-relaxed">{description}</p>
      </div>
    </motion.div>
  )
}

function TerminalPreview() {
  const lines = [
    { text: '$ lograven analyze --files Security.evtx Sysmon.evtx', color: '#818CF8' },
    { text: '→ Parsed 284,712 events across 2 files', color: '#14B8A6', delay: 0.3 },
    { text: '→ Running 847 detection rules...', color: '#94A3B8', delay: 0.6 },
    { text: '⚠ T1003.001  CRITICAL  Credential Dumping via LSASS', color: '#F43F5E', delay: 0.9 },
    { text: '⚠ T1059.001  CRITICAL  Encoded PowerShell Execution', color: '#F43F5E', delay: 1.1 },
    { text: '→ Correlating across 2 sources...', color: '#94A3B8', delay: 1.4 },
    { text: '→ AI analysis complete (Gemini 1.5 Pro)', color: '#14B8A6', delay: 1.7 },
    { text: '✓ Report ready: 12 findings, 3 critical', color: '#818CF8', delay: 2.0 },
  ]
  return (
    <div className="rounded-2xl overflow-hidden border border-white/[0.06]" style={{ background: '#060810' }}>
      <div className="flex items-center gap-2 px-4 py-3 border-b border-white/[0.06]">
        <div className="flex gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-rose-500/60" />
          <div className="w-2.5 h-2.5 rounded-full bg-amber-500/60" />
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/60" />
        </div>
        <span className="ml-2 font-mono text-xs text-text-muted">lograven — analysis pipeline</span>
      </div>
      <div className="p-5 font-mono text-xs leading-7 space-y-0.5">
        {lines.map((line, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: line.delay || 0, duration: 0.4 }}
            style={{ color: line.color }}
          >
            {line.text}
          </motion.div>
        ))}
        <motion.div
          animate={{ opacity: [1, 0, 1] }}
          transition={{ repeat: Infinity, duration: 1 }}
          className="inline-block w-2 h-4 bg-indigo-400 ml-1"
        />
      </div>
    </div>
  )
}

export default function Landing() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const { scrollY } = useScroll()
  const heroY = useTransform(scrollY, [0, 600], [0, -80])
  const heroOpacity = useTransform(scrollY, [0, 400], [1, 0])

  const features = [
    { title: 'Universal Log Ingestion', description: 'Upload EVTX, syslog, CloudTrail, Nginx, and firewall logs. Native parsers extract structured events from every format.' },
    { title: 'Multi-Engine Detection', description: '847+ YAML detection rules run across every log line. Choose between native parsers, decoder-manager, or run both side-by-side.' },
    { title: 'Gemini AI Analysis', description: 'Opt-in AI layer contextualizes findings, identifies attack chains, and generates executive-ready summaries for each investigation.' },
    { title: 'MITRE ATT&CK Mapping', description: 'Every finding is automatically mapped to MITRE ATT&CK tactics and techniques, giving you the full kill chain at a glance.' },
    { title: 'Cross-Source Correlation', description: 'Correlate findings across multiple log files to surface multi-stage attack patterns invisible in any single source.' },
    { title: 'PDF Evidence Packages', description: 'Generate professional PDF reports with all findings, IOCs, and AI commentary — ready for security reviews or incident response.' },
  ]

  const steps = [
    { title: 'Upload your log files', description: 'Drag in any combination of log formats. LogRaven automatically detects source type and selects the appropriate parser.', num: '01' },
    { title: 'Configure & run analysis', description: 'Enable cross-file correlation, toggle AI enrichment, and kick off the pipeline. Results stream in real-time.', num: '02' },
    { title: 'Review findings', description: 'Explore prioritized findings, correlated attack chains, IOCs, and MITRE mappings in a rich interactive dashboard.', num: '03' },
    { title: 'Export & respond', description: 'Download a forensic-grade PDF report or review findings directly with your team. Every IOC is actionable.', num: '04' },
  ]

  return (
    <div className="bg-void min-h-screen overflow-hidden">
      {/* Landing-specific minimal header */}
      <header className="fixed top-0 left-0 right-0 z-50">
        <div className="px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center">
              <Shield className="w-4 h-4 text-indigo-400" />
            </div>
            <span className="font-display font-bold text-lg text-text-primary tracking-tight">
              Log<span className="text-indigo-400">Raven</span>
            </span>
          </Link>
          <div className="flex items-center gap-3">
            {isAuthenticated ? (
              <Link to="/dashboard" className="btn-sovereign px-4 py-2 rounded-lg text-sm font-semibold text-white">
                Open dashboard
              </Link>
            ) : (
              <>
                <Link to="/login" className="btn-ghost px-4 py-2 rounded-lg text-sm font-medium text-text-secondary">
                  Sign in
                </Link>
                <Link to="/register" className="btn-sovereign px-4 py-2 rounded-lg text-sm font-semibold text-white">
                  Get started
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative min-h-screen flex items-center justify-center px-6 pt-20">
        <div className="absolute inset-0 bg-hero-mesh" />
        <div className="absolute top-0 left-0 right-0 h-[600px] pointer-events-none"
          style={{ background: 'radial-gradient(ellipse 80% 50% at 50% -10%, rgba(99,102,241,0.07) 0%, transparent 70%)' }} />

        <motion.div
          style={{ y: heroY, opacity: heroOpacity }}
          className="relative z-10 max-w-5xl mx-auto text-center"
        >
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/[0.08] mb-8"
          >
            <span className="font-mono text-xs text-text-muted tracking-wider uppercase">
              Log analysis &amp; threat intelligence
            </span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.7 }}
            className="font-display font-extrabold leading-none tracking-tight mb-6"
            style={{ fontSize: 'clamp(3rem, 8vw, 6.5rem)' }}
          >
            <span className="text-text-primary">Watch your logs.</span>
            <br />
            <span className="text-indigo-400">Find the threat.</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.45 }}
            className="text-text-secondary text-lg sm:text-xl max-w-2xl mx-auto mb-10 leading-relaxed"
          >
            Upload any log format. Run 847 detection rules. Correlate across sources.
            Map findings to MITRE ATT&CK — with optional Gemini AI enrichment.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.58 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-3"
          >
            {isAuthenticated ? (
              <Link to="/dashboard" className="btn-sovereign flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white shadow-glow-indigo">
                Open dashboard <ArrowRight className="w-4 h-4" />
              </Link>
            ) : (
              <Link to="/register" className="btn-sovereign flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white shadow-glow-indigo">
                Start investigating <ArrowRight className="w-4 h-4" />
              </Link>
            )}
            <Link to="/login" className="btn-ghost flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-medium text-text-secondary">
              {isAuthenticated ? 'Account settings' : 'Sign in'}
              <ChevronRight className="w-4 h-4" />
            </Link>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
            className="flex items-center justify-center gap-8 mt-14 pt-10 border-t border-white/[0.05]"
          >
            {[
              { label: 'Detection Rules', value: '847+' },
              { label: 'Log Formats', value: '8' },
              { label: 'MITRE Techniques', value: '200+' },
              { label: 'Avg Analysis', value: '< 5m' },
            ].map(({ label, value }) => (
              <div key={label} className="text-center">
                <div className="font-display font-bold text-2xl text-text-primary">{value}</div>
                <div className="font-mono text-[10px] text-text-muted tracking-widest uppercase mt-0.5">{label}</div>
              </div>
            ))}
          </motion.div>
        </motion.div>
      </section>

      {/* Terminal */}
      <section className="relative px-6 py-24">
        <div className="max-w-4xl mx-auto">
          <SectionReveal delay={0.1}><TerminalPreview /></SectionReveal>
        </div>
      </section>

      {/* Features */}
      <section className="px-6 py-24">
        <div className="max-w-6xl mx-auto">
          <SectionReveal>
            <h2 className="font-display font-bold text-text-primary mb-3" style={{ fontSize: 'clamp(1.75rem, 4vw, 3rem)' }}>
              Everything you need to investigate
            </h2>
            <p className="text-text-secondary max-w-xl mb-12">
              From raw log ingestion to actionable threat reports — every step of the SOC workflow in one platform.
            </p>
          </SectionReveal>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {features.map((f, i) => (
              <FeatureCard key={f.title} title={f.title} description={f.description} index={i} />
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="px-6 py-24">
        <div className="max-w-4xl mx-auto">
          <div className="grid md:grid-cols-2 gap-16 items-start">
            <div>
              <SectionReveal>
                <h2 className="font-display font-bold text-text-primary mb-8" style={{ fontSize: 'clamp(1.75rem, 3.5vw, 2.5rem)' }}>
                  From logs to insight<br />in minutes
                </h2>
              </SectionReveal>
              <div className="space-y-0">
                {steps.map((s, i) => <Step key={s.num} num={s.num} title={s.title} description={s.description} index={i} />)}
              </div>
            </div>
            <SectionReveal delay={0.3}>
              <div className="sticky top-24">
                <div className="p-6 rounded-2xl border border-white/[0.06] bg-surface/60 backdrop-blur-xl mb-4">
                  <div className="flex items-center gap-2 mb-4">
                    <Shield className="w-4 h-4 text-indigo-400" />
                    <span className="font-mono text-xs text-indigo-400 tracking-widest uppercase">SOC 2 Compliance</span>
                  </div>
                  <h3 className="font-display font-semibold text-text-primary text-lg mb-2">
                    Automated AWS Compliance Audits
                  </h3>
                  <p className="text-text-secondary text-sm mb-4 leading-relaxed">
                    Provide an IAM role ARN and let LogRaven collect CloudTrail, IAM, and GuardDuty evidence.
                    Get a scored SOC 2 CC6/CC7 report in minutes.
                  </p>
                  <Link to="/compliance" className="flex items-center gap-2 text-sm font-semibold text-indigo-400 hover:text-indigo-300 transition-colors">
                    View compliance module <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
                <div className="p-5 rounded-2xl border border-rose-500/15 bg-rose-500/5">
                  <div className="mb-3">
                    <div className="font-mono text-[10px] text-rose-400/70 tracking-widest uppercase mb-1">Live threat indicator</div>
                    <div className="font-display font-bold text-3xl text-text-primary">12</div>
                    <div className="text-text-secondary text-xs mt-0.5">active findings detected</div>
                  </div>
                  <div className="flex gap-2">
                    {[['3', 'critical', '#F43F5E'], ['4', 'high', '#F97316'], ['5', 'med', '#FBBF24']].map(([n, label, color]) => (
                      <div key={label} className="flex-1 px-2 py-1.5 rounded-lg text-center"
                        style={{ background: `${color}10`, border: `1px solid ${color}25` }}>
                        <div className="font-mono font-bold text-sm" style={{ color }}>{n}</div>
                        <div className="font-mono text-[9px] mt-0.5" style={{ color, opacity: 0.6 }}>{label}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </SectionReveal>
          </div>
        </div>
      </section>

      {/* CTA Banner */}
      <section className="px-6 py-24">
        <div className="max-w-4xl mx-auto">
          <SectionReveal>
            <div className="relative p-12 rounded-3xl overflow-hidden text-center border border-indigo-500/20">
              <div className="absolute inset-0 bg-sovereign-radial" />
              <div className="absolute inset-0 border border-indigo-500/10 rounded-3xl" />
              <div className="relative z-10">
                <h2 className="font-display font-extrabold text-text-primary text-4xl mb-4">
                  Start your first investigation
                </h2>
                <p className="text-text-secondary text-lg mb-8 max-w-md mx-auto">
                  Upload logs, run detection, get answers. No configuration required.
                </p>
                <div className="flex items-center justify-center gap-3">
                  {isAuthenticated ? (
                    <Link to="/dashboard" className="btn-sovereign flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white">
                      Open dashboard <ArrowRight className="w-4 h-4" />
                    </Link>
                  ) : (
                    <Link to="/register" className="btn-sovereign flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white">
                      Create free account <ArrowRight className="w-4 h-4" />
                    </Link>
                  )}
                  <Link to="/login" className="btn-ghost px-6 py-3 rounded-xl text-sm font-medium text-text-secondary">
                    Sign in
                  </Link>
                </div>
              </div>
            </div>
          </SectionReveal>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/[0.04] px-6 py-10">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-indigo-400" />
            <span className="font-display font-bold text-text-secondary text-sm">
              Log<span className="text-indigo-400">Raven</span>
            </span>
          </div>
          <span className="font-mono text-xs text-text-muted">© 2026 LogRaven — Watch your logs. Find the threat.</span>
          <div className="flex items-center gap-4 text-xs text-text-muted">
            <Link to="/login" className="hover:text-text-secondary transition-colors">Sign in</Link>
            <Link to="/register" className="hover:text-text-secondary transition-colors">Register</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
