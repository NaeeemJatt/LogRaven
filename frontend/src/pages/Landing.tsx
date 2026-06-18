import { useRef, useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion, useScroll, useTransform, useInView } from 'framer-motion'
import { Shield, ArrowRight, ChevronRight, ChevronLeft } from 'lucide-react'
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

type Feature = { title: string; description: string; tag: string }

function FeatureCard({ feature, index, cardRef }: { feature: Feature; index: number; cardRef?: (el: HTMLDivElement | null) => void }) {
  return (
    <div
      ref={cardRef}
      className="flex-shrink-0 w-[300px] sm:w-[340px] min-h-[320px] p-7 rounded-2xl border border-white/[0.06] bg-surface/50 hover:border-indigo-500/20 hover:bg-elevated/60 transition-all duration-200 flex flex-col select-none"
    >
      <div className="font-mono text-[10px] text-indigo-400/70 tracking-widest">{String(index + 1).padStart(2, '0')}</div>
      <h3 className="font-display font-semibold text-text-primary text-lg mt-5 mb-3">{feature.title}</h3>
      <p className="text-text-secondary text-sm leading-relaxed">{feature.description}</p>
      <div className="mt-auto pt-6 flex items-center gap-3">
        <div className="h-px flex-1 bg-white/[0.07]" />
        <span className="font-mono text-[10px] text-text-muted tracking-[0.18em] uppercase">{feature.tag}</span>
      </div>
    </div>
  )
}

function FeatureCarousel({ features }: { features: Feature[] }) {
  const len = features.length
  const COPIES = 5
  const START = len * 2
  const cards = Array.from({ length: COPIES }, () => features).flat()

  const [index, setIndex] = useState(START)
  const [withTransition, setWithTransition] = useState(true)
  const [step, setStep] = useState(356)
  const firstCard = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const measure = () => {
      if (firstCard.current) setStep(firstCard.current.offsetWidth + 16)
    }
    measure()
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [])

  const paginate = (dir: number) => {
    setWithTransition(true)
    setIndex((i) => i + dir)
  }

  const normalize = () => {
    if (index >= len * (COPIES - 1)) { setWithTransition(false); setIndex((i) => i - len) }
    else if (index < len) { setWithTransition(false); setIndex((i) => i + len) }
  }

  return (
    <>
      <div className="max-w-6xl mx-auto px-6 mb-10 flex items-end justify-between gap-6">
        <SectionReveal>
          <div className="font-mono text-[10px] text-indigo-400 tracking-[0.22em] uppercase mb-3">Capabilities</div>
          <h2 className="font-display font-bold text-text-primary mb-3" style={{ fontSize: 'clamp(1.75rem, 3.5vw, 2.5rem)' }}>
            Everything you need to investigate
          </h2>
          <p className="text-text-secondary text-sm leading-relaxed max-w-xl">
            From raw log ingestion to actionable threat reports — every step of the SOC workflow in one platform.
          </p>
        </SectionReveal>
        <div className="hidden sm:flex items-center gap-2 flex-shrink-0">
          <button
            onClick={() => paginate(-1)} aria-label="Previous"
            className="w-11 h-11 rounded-xl border border-white/[0.08] bg-surface/50 text-text-secondary hover:text-text-primary hover:border-indigo-500/30 hover:bg-elevated/60 transition-all flex items-center justify-center"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <button
            onClick={() => paginate(1)} aria-label="Next"
            className="w-11 h-11 rounded-xl border border-white/[0.08] bg-surface/50 text-text-secondary hover:text-text-primary hover:border-indigo-500/30 hover:bg-elevated/60 transition-all flex items-center justify-center"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>

      <div className="relative">
        <div className="absolute left-0 top-0 bottom-0 w-16 sm:w-32 z-10 bg-gradient-to-r from-void to-transparent pointer-events-none" />
        <div className="absolute right-0 top-0 bottom-0 w-16 sm:w-32 z-10 bg-gradient-to-l from-void to-transparent pointer-events-none" />

        <div className="overflow-hidden">
          <motion.div
            className="flex gap-4 w-max px-6"
            initial={false}
            animate={{ x: -index * step }}
            transition={withTransition ? { duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] } : { duration: 0 }}
            onAnimationComplete={normalize}
          >
            {cards.map((f, i) => (
              <FeatureCard
                key={i}
                feature={f}
                index={i % len}
                cardRef={i === 0 ? (el) => { firstCard.current = el } : undefined}
              />
            ))}
          </motion.div>
        </div>

        {/* Mobile arrows */}
        <div className="flex sm:hidden items-center justify-center gap-3 mt-8">
          <button
            onClick={() => paginate(-1)} aria-label="Previous"
            className="w-11 h-11 rounded-xl border border-white/[0.08] bg-surface/50 text-text-secondary hover:text-text-primary transition-all flex items-center justify-center"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <button
            onClick={() => paginate(1)} aria-label="Next"
            className="w-11 h-11 rounded-xl border border-white/[0.08] bg-surface/50 text-text-secondary hover:text-text-primary transition-all flex items-center justify-center"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    </>
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
    { text: '$ lograven analyze --files Security.evtx Sysmon.evtx', color: '#E3B57E' },
    { text: '→ Parsed 284,712 events across 2 files', color: '#8FBDAD', delay: 0.3 },
    { text: '→ Running 847 detection rules...', color: '#94A3B8', delay: 0.6 },
    { text: '⚠ T1003.001  CRITICAL  Credential Dumping via LSASS', color: '#DB8585', delay: 0.9 },
    { text: '⚠ T1059.001  CRITICAL  Encoded PowerShell Execution', color: '#DB8585', delay: 1.1 },
    { text: '→ Correlating across 2 sources...', color: '#94A3B8', delay: 1.4 },
    { text: '→ AI analysis complete', color: '#8FBDAD', delay: 1.7 },
    { text: '✓ Report ready: 12 findings, 3 critical', color: '#E3B57E', delay: 2.0 },
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

  const features: Feature[] = [
    { tag: 'Ingestion', title: 'Universal Log Ingestion', description: 'Upload EVTX, syslog, CloudTrail, Nginx, and firewall logs. Native parsers extract structured events from every format.' },
    { tag: 'Detection', title: 'Multi-Engine Detection', description: '847+ YAML detection rules run across every log line. Choose between native parsers, decoder-manager, or run both side-by-side.' },
    { tag: 'AI Layer', title: 'AI Analysis', description: 'Opt-in AI layer contextualizes findings, identifies attack chains, and generates executive-ready summaries for each investigation.' },
    { tag: 'Mapping', title: 'MITRE ATT&CK Mapping', description: 'Every finding is automatically mapped to MITRE ATT&CK tactics and techniques, giving you the full kill chain at a glance.' },
    { tag: 'Correlation', title: 'Cross-Source Correlation', description: 'Correlate findings across multiple log files to surface multi-stage attack patterns invisible in any single source.' },
    { tag: 'Reporting', title: 'PDF Evidence Packages', description: 'Generate professional PDF reports with all findings, IOCs, and AI commentary — ready for security reviews or incident response.' },
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

      {/* Hero — asymmetric split: copy left, live console right */}
      <section className="relative min-h-screen flex items-center px-6 pt-28 pb-16">
        <div className="absolute inset-0 bg-hero-mesh" />
        <div className="absolute top-0 left-0 right-0 h-[600px] pointer-events-none"
          style={{ background: 'radial-gradient(ellipse 70% 50% at 30% -10%, rgba(227,181,126,0.06) 0%, transparent 70%)' }} />

        <div className="relative z-10 max-w-7xl mx-auto w-full grid md:grid-cols-[1.05fr_1fr] gap-12 md:gap-16 items-center">
          {/* Left — copy */}
          <motion.div style={{ y: heroY, opacity: heroOpacity }}>
            <motion.div
              initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/[0.08] mb-7"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
              <span className="font-mono text-[11px] text-text-muted tracking-wider uppercase">
                Log analysis &amp; threat intelligence
              </span>
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25, duration: 0.7 }}
              className="font-display font-extrabold leading-[0.95] tracking-tight mb-6"
              style={{ fontSize: 'clamp(2.75rem, 6vw, 5rem)' }}
            >
              <span className="text-text-primary">Watch your logs.</span><br />
              <span className="text-indigo-400">Find the threat.</span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
              className="text-text-secondary text-lg max-w-xl mb-9 leading-relaxed"
            >
              Upload any log format. Run 847 detection rules. Correlate across sources.
              Map findings to MITRE ATT&CK — with optional AI enrichment.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.52 }}
              className="flex flex-col sm:flex-row items-start gap-3"
            >
              {isAuthenticated ? (
                <Link to="/dashboard" className="btn-sovereign flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold">
                  Open dashboard <ArrowRight className="w-4 h-4" />
                </Link>
              ) : (
                <Link to="/register" className="btn-sovereign flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold">
                  Start investigating <ArrowRight className="w-4 h-4" />
                </Link>
              )}
              <Link to="/login" className="btn-ghost flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-medium text-text-secondary">
                {isAuthenticated ? 'Account settings' : 'Sign in'}
                <ChevronRight className="w-4 h-4" />
              </Link>
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.7 }}
              className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-12 pt-8 border-t border-white/[0.06]"
            >
              {[
                { label: 'Detection Rules', value: '847+' },
                { label: 'Log Formats', value: '8' },
                { label: 'MITRE Techniques', value: '200+' },
                { label: 'Avg Analysis', value: '< 5m' },
              ].map(({ label, value }) => (
                <div key={label}>
                  <div className="font-display font-bold text-2xl text-text-primary">{value}</div>
                  <div className="font-mono text-[10px] text-text-muted tracking-widest uppercase mt-0.5">{label}</div>
                </div>
              ))}
            </motion.div>
          </motion.div>

          {/* Right — live console */}
          <motion.div
            initial={{ opacity: 0, y: 30, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ delay: 0.45, duration: 0.7, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="relative"
          >
            <div className="absolute -inset-4 bg-hero-mesh opacity-40 blur-2xl rounded-3xl pointer-events-none" />
            <div className="relative">
              <TerminalPreview />
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features — manual infinite carousel */}
      <section className="py-24 border-t border-white/[0.04] overflow-hidden">
        <FeatureCarousel features={features} />
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
                    {[['3', 'critical', '#DB8585'], ['4', 'high', '#E0A86F'], ['5', 'med', '#D9C27E']].map(([n, label, color]) => (
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
