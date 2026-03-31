// LogRaven — Public marketing landing (dashboard-aligned chrome, no auth)
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Upload, GitMerge, FileText, Shield, Lock, Zap, Search } from 'lucide-react'

import { useAuthStore } from '../store/authStore'

function useScrollAnimation() {
  const [inView, setInView] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const element = ref.current
    if (!element) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        setInView(entry.isIntersecting)
      },
      { root: null, rootMargin: '0px', threshold: 0.1 },
    )

    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  return [ref, inView] as const
}

const features = [
  {
    title: 'Detection across sources',
    description:
      'Rule engine plus AI-assisted review flags suspicious patterns and anomalies across EVTX, web, syslog, and cloud exports.',
    icon: Shield,
  },
  {
    title: 'Multi-file correlation',
    description:
      'Link entities across uploads so single-source noise becomes cross-source signal within configurable time windows.',
    icon: GitMerge,
  },
  {
    title: 'MITRE ATT&CK mapping',
    description:
      'Findings tied to tactics and techniques so you can prioritise response and reporting consistently.',
    icon: Search,
  },
  {
    title: 'Fast pipeline',
    description:
      'Parse, correlate, and generate PDF reports without leaving the workflow—built for real investigations.',
    icon: Zap,
  },
] as const

const howItWorksSteps = [
  {
    title: 'Upload your logs',
    description:
      'Bring Windows, web server, syslog, or CloudTrail-style exports. Multiple files per case are supported.',
    icon: Upload,
    step: '01',
  },
  {
    title: 'Correlate events',
    description:
      'The engine extracts IPs, users, and hosts, then builds chains across files before AI and rules add context.',
    icon: GitMerge,
    step: '02',
  },
  {
    title: 'Export the report',
    description:
      'Download a structured PDF with severity, MITRE references, correlated narratives, and remediation hints.',
    icon: FileText,
    step: '03',
  },
] as const

const cardClass =
  'bg-raven-800 border border-raven-700 rounded-xl p-8 shadow-lg shadow-black/20 transition-all duration-300 hover:border-electric-500/40'

export default function Landing() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  const [headerRef, headerInView] = useScrollAnimation()
  const [subRef, subInView] = useScrollAnimation()
  const [btnRef, btnInView] = useScrollAnimation()

  return (
    <div className="min-h-screen bg-raven-950 text-raven-200 font-sans">
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-electric-500/10 via-transparent to-transparent pointer-events-none" />

        <section className="relative px-4 sm:px-6 py-24 md:py-32 lg:py-40">
          <div className="max-w-7xl mx-auto">
            <div className="max-w-4xl mx-auto text-center">
              <h1
                ref={headerRef}
                className={`text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold mb-6 tracking-tight transition-all duration-700 ease-out ${
                  headerInView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'
                }`}
              >
                Watch your logs.{' '}
                <span className="text-electric-500">Find the threat.</span>
              </h1>

              <p
                ref={subRef}
                className={`text-lg md:text-xl text-raven-500 mb-8 max-w-3xl mx-auto transition-all duration-700 ease-out delay-200 ${
                  subInView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'
                }`}
              >
                Multi-file correlation, YAML rules, and AI-assisted triage—with MITRE ATT&CK context and
                exportable PDF reports for stakeholders.
              </p>

              <div
                ref={btnRef}
                className={`flex flex-col sm:flex-row gap-4 justify-center items-center transition-all duration-700 ease-out delay-300 ${
                  btnInView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'
                }`}
              >
                {isAuthenticated ? (
                  <Link
                    to="/dashboard"
                    className="px-8 py-3.5 bg-electric-500 hover:bg-electric-400 text-raven-950 font-semibold rounded-lg transition-all duration-200 shadow-lg shadow-electric-500/15 hover:shadow-electric-500/30 w-full sm:w-auto text-center"
                  >
                    Open dashboard
                  </Link>
                ) : (
                  <Link
                    to="/register"
                    className="px-8 py-3.5 bg-electric-500 hover:bg-electric-400 text-raven-950 font-semibold rounded-lg transition-all duration-200 shadow-lg shadow-electric-500/15 hover:shadow-electric-500/30 w-full sm:w-auto text-center"
                  >
                    Get started
                  </Link>
                )}
                <Link
                  to="/login"
                  className="px-8 py-3.5 border border-raven-600 bg-raven-800/80 text-raven-200 font-semibold rounded-lg transition-all duration-200 hover:border-electric-500/40 hover:bg-raven-800 w-full sm:w-auto text-center"
                >
                  {isAuthenticated ? 'Account' : 'Sign in'}
                </Link>
              </div>
            </div>
          </div>
        </section>

        <section className="relative px-4 sm:px-6 py-24 md:py-32">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-16">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-2 tracking-tight">
                How it works
              </h2>
              <p className="text-raven-500 text-sm sm:text-base">Three steps from raw logs to a shareable report</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8">
              {howItWorksSteps.map((step, index) => {
                const Icon = step.icon
                return (
                  <div key={step.step} className="relative group">
                    <div className={`${cardClass} h-full`}>
                      <div className="flex items-start gap-4 mb-4">
                        <div className="text-5xl font-bold text-electric-500/25 tabular-nums">{step.step}</div>
                        <div className="p-3 bg-electric-500/10 rounded-lg border border-electric-500/20">
                          <Icon className="w-6 h-6 text-electric-400" />
                        </div>
                      </div>
                      <h3 className="text-lg font-semibold text-white mb-3">{step.title}</h3>
                      <p className="text-raven-500 text-sm leading-relaxed">{step.description}</p>
                    </div>
                    {index < howItWorksSteps.length - 1 && (
                      <div className="hidden md:block absolute top-1/2 -right-4 w-8 h-0.5 bg-gradient-to-r from-electric-500/50 to-transparent" />
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </section>

        <section className="relative px-4 sm:px-6 py-24 md:py-32">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-16">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-2 tracking-tight">
                Built for investigations
              </h2>
              <p className="text-raven-500 text-sm sm:text-base">Correlation, context, and reporting in one place</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {features.map((feature) => {
                const Icon = feature.icon
                return (
                  <div key={feature.title} className="group relative">
                    <div className="absolute inset-0 bg-gradient-to-br from-electric-500/10 to-transparent rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 blur-xl pointer-events-none" />
                    <div className={`relative ${cardClass}`}>
                      <div className="p-3 bg-electric-500/10 rounded-lg border border-electric-500/20 w-fit mb-4">
                        <Icon className="w-6 h-6 text-electric-400" />
                      </div>
                      <h3 className="text-lg font-semibold text-white mb-3">{feature.title}</h3>
                      <p className="text-raven-500 text-sm leading-relaxed">{feature.description}</p>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </section>

        <footer className="relative border-t border-raven-800 px-4 sm:px-6 py-12">
          <div className="max-w-7xl mx-auto">
            <div className="flex flex-col items-center text-center">
              <div className="flex items-center gap-2 mb-4">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-electric-500/35 bg-electric-500/10 text-electric-400">
                  <Lock className="w-4 h-4" aria-hidden />
                </span>
                <span className="text-lg font-bold text-white tracking-tight">LogRaven</span>
              </div>
              <p className="text-raven-500 text-sm mb-6 max-w-md">
                Log correlation and reporting for security teams—without shipping your data to a black box you
                cannot inspect.
              </p>
              <p className="text-xs text-raven-600 font-mono mb-2">lograven.io</p>
              <div className="text-sm text-raven-600">© 2026 LogRaven. All rights reserved.</div>
            </div>
          </div>
        </footer>
      </div>
    </div>
  )
}
