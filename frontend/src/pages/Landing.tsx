// LogRaven — Security Operations Center & Compliance Intelligence Platform
// Hallmark · v2.0.0 | shape: stage | theme: watchtower | genre: modern-minimal

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Shield,
  ArrowRight,
  Terminal,
  FileCode2,
  Server,
  Cloud,
  ChevronRight,
} from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import client from '../api/client'
import LegalLinks from '../components/layout/LegalLinks'

interface PlatformStats {
  detection_rules: number
  log_formats: number
  mitre_techniques: number
}

function usePlatformStats() {
  const [stats, setStats] = useState<PlatformStats | null>(null)
  useEffect(() => {
    let cancelled = false
    client
      .get<PlatformStats>('/api/v1/meta/stats')
      .then((res) => {
        if (!cancelled && res.data) setStats(res.data)
      })
      .catch(() => {
        // Fallback gracefully when backend API is offline
      })
    return () => {
      cancelled = true
    }
  }, [])
  return {
    rules: stats ? stats.detection_rules.toLocaleString() : '2,000+',
    formats: stats ? String(stats.log_formats) : '5',
    mitre: stats ? String(stats.mitre_techniques) : '300+',
  }
}

type WorkbenchTab = 'stream' | 'rule' | 'chain'

export default function Landing() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const stats = usePlatformStats()
  const [activeTab, setActiveTab] = useState<WorkbenchTab>('stream')

  return (
    <div className="bg-void text-text-primary min-h-dvh flex flex-col overflow-x-clip selection:bg-amber-400/20 selection:text-amber-200">
      {/* ── Header ───────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 border-b border-white/[0.06] bg-void/90 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link
            to="/"
            className="flex items-center gap-2.5 rounded-lg focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
            aria-label="LogRaven Home"
          >
            <div className="w-8 h-8 rounded-lg bg-surface border border-white/[0.08] flex items-center justify-center">
              <Shield className="w-4 h-4 text-amber-400" strokeWidth={2} />
            </div>
            <span className="font-display font-bold text-lg tracking-tight text-text-primary">
              Log<span className="text-amber-400">Raven</span>
            </span>
          </Link>

          <nav aria-label="Primary" className="hidden md:flex items-center gap-8 text-sm text-text-secondary">
            <a
              href="#workbench"
              className="hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded"
            >
              Live workbench
            </a>
            <a
              href="#parsers"
              className="hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded"
            >
              Parsers
            </a>
            <a
              href="#pipeline"
              className="hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded"
            >
              Investigation pipeline
            </a>
            <a
              href="#compliance"
              className="hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded"
            >
              Compliance
            </a>
          </nav>

          <div className="flex items-center gap-3">
            {isAuthenticated ? (
              <Link
                to="/dashboard"
                className="btn-sovereign text-xs font-semibold px-4 py-2 rounded-lg motion-safe:transition-transform motion-safe:active:scale-[0.98] motion-reduce:transition-none focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Open dashboard
              </Link>
            ) : (
              <>
                <Link
                  to="/login"
                  className="text-xs font-medium text-text-secondary hover:text-text-primary px-3 py-2 rounded-lg transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Sign in
                </Link>
                <Link
                  to="/register"
                  className="btn-sovereign text-xs font-semibold px-4 py-2 rounded-lg motion-safe:transition-transform motion-safe:active:scale-[0.98] motion-reduce:transition-none focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Start investigation
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* ── Hero: Stage Posture (Asymmetric Split) ─────────────── */}
      <section className="relative pt-12 pb-20 md:pt-16 md:pb-28 border-b border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-6 grid lg:grid-cols-[1fr_1.15fr] gap-12 lg:gap-16 items-center">
          {/* Left: Concise Copy & Action */}
          <div>
            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-md bg-surface border border-white/[0.08] mb-6">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span className="text-xs text-text-muted">Security intelligence and SOC audit</span>
            </div>

            <h1 className="font-display font-bold text-3xl sm:text-4xl lg:text-5xl tracking-tight text-text-primary leading-[1.08] mb-4">
              Security log analysis and threat detection
            </h1>

            <p className="text-text-secondary text-base sm:text-lg leading-relaxed mb-8 max-w-xl">
              Detect attacks across Windows, Linux, and cloud logs in seconds.
            </p>

            <div className="flex flex-wrap items-center gap-3">
              {isAuthenticated ? (
                <Link
                  to="/dashboard"
                  className="btn-sovereign inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold motion-safe:transition-transform motion-safe:active:scale-[0.98] motion-reduce:transition-none focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span>Open dashboard</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
              ) : (
                <Link
                  to="/register"
                  className="btn-sovereign inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold motion-safe:transition-transform motion-safe:active:scale-[0.98] motion-reduce:transition-none focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span>Start investigation</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
              )}

              <a
                href="#workbench"
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium text-text-secondary hover:text-text-primary border border-white/[0.08] hover:border-white/[0.18] transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none"
              >
                <span>Explore live workbench</span>
                <ChevronRight className="w-4 h-4" />
              </a>
            </div>

            {/* Quick Metrics Bar */}
            <div className="grid grid-cols-3 gap-6 pt-10 mt-10 border-t border-white/[0.06]">
              <div>
                <div className="font-display font-bold text-2xl text-text-primary tabular-nums">{stats.rules}</div>
                <div className="text-xs text-text-muted mt-1">Detection rules</div>
              </div>
              <div>
                <div className="font-display font-bold text-2xl text-text-primary tabular-nums">{stats.formats}</div>
                <div className="text-xs text-text-muted mt-1">Native log parsers</div>
              </div>
              <div>
                <div className="font-display font-bold text-2xl text-text-primary tabular-nums">{stats.mitre}</div>
                <div className="text-xs text-text-muted mt-1">MITRE techniques</div>
              </div>
            </div>
          </div>

          {/* Right: The Signature Workbench Stage */}
          <div id="workbench" className="rounded-xl border border-white/[0.08] bg-surface overflow-hidden">
            {/* Workbench Top Bar */}
            <div className="px-4 py-3 bg-deep border-b border-white/[0.06] flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-amber-400" />
                <span className="text-xs text-text-secondary font-medium">lograven.soc.telemetry</span>
              </div>

              <div className="flex items-center gap-1.5 p-1 rounded-lg bg-surface border border-white/[0.06]">
                <button
                  type="button"
                  onClick={() => setActiveTab('stream')}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed ${
                    activeTab === 'stream'
                      ? 'bg-elevated text-amber-300 font-semibold'
                      : 'text-text-muted hover:text-text-secondary'
                  }`}
                >
                  Event stream
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('rule')}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed ${
                    activeTab === 'rule'
                      ? 'bg-elevated text-amber-300 font-semibold'
                      : 'text-text-muted hover:text-text-secondary'
                  }`}
                >
                  Sigma rule
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('chain')}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none disabled:opacity-50 disabled:cursor-not-allowed ${
                    activeTab === 'chain'
                      ? 'bg-elevated text-amber-300 font-semibold'
                      : 'text-text-muted hover:text-text-secondary'
                  }`}
                >
                  Attack chain
                </button>
              </div>
            </div>

            {/* Workbench Body */}
            <div className="p-5 text-xs min-h-[300px]">
              {activeTab === 'stream' && (
                <div className="space-y-3 font-mono">
                  <div className="flex items-center justify-between text-[11px] text-text-muted pb-2 border-b border-white/[0.06]">
                    <span>Timestamp &amp; host</span>
                    <span>Event &amp; technique</span>
                    <span>Severity</span>
                  </div>

                  <div className="p-3 rounded-lg bg-elevated/70 border border-threat-critical/20 flex items-start justify-between gap-3">
                    <div>
                      <div className="text-text-primary font-medium">18:42:01.402 · WIN-SRV01</div>
                      <div className="text-text-muted text-[11px] mt-0.5">Sysmon Event 10: ProcessAccess → lsass.exe</div>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-threat-critical/15 text-threat-critical border border-threat-critical/30">
                      T1003.001
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-elevated/70 border border-threat-high/20 flex items-start justify-between gap-3">
                    <div>
                      <div className="text-text-primary font-medium">18:42:00.819 · WIN-SRV01</div>
                      <div className="text-text-muted text-[11px] mt-0.5">Security 4688: powershell.exe -enc JABz…</div>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-threat-high/15 text-threat-high border border-threat-high/30">
                      T1059.001
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-elevated/70 border border-white/[0.06] flex items-start justify-between gap-3">
                    <div>
                      <div className="text-text-primary font-medium">18:41:55.104 · aws-cloudtrail</div>
                      <div className="text-text-muted text-[11px] mt-0.5">sts:AssumeRole with AdministratorAccess from anomalous ASN</div>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-threat-medium/15 text-threat-medium border border-threat-medium/30">
                      T1078.004
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-elevated/40 border border-white/[0.04] flex items-start justify-between gap-3">
                    <div>
                      <div className="text-text-secondary font-medium">18:41:40.012 · bastion-deb12</div>
                      <div className="text-text-muted text-[11px] mt-0.5">pam_unix(sshd:auth): 4 failed attempts for user root</div>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-threat-low/15 text-threat-low border border-threat-low/30">
                      T1110.001
                    </span>
                  </div>
                </div>
              )}

              {activeTab === 'rule' && (
                <div className="space-y-2 text-text-secondary">
                  <div className="text-text-muted pb-1 border-b border-white/[0.06] flex items-center justify-between text-xs">
                    <span>rules/windows/sysmon_lsass_dump.yml</span>
                    <span className="text-amber-400 font-medium">Sigma engine v2</span>
                  </div>
                  <pre className="p-3 rounded-lg bg-deep border border-white/[0.06] overflow-x-auto text-[11px] leading-relaxed text-text-primary font-mono">
{`title: LSASS Process Access via Procdump or OpenProcess
id: 5aa38556-5346-4287-9753-fb82947b3559
status: production
logsource:
  category: process_access
  product: windows
detection:
  selection:
    TargetImage|endswith: '\\lsass.exe'
    GrantedAccess|contains:
      - '0x0010' # PROCESS_VM_READ
      - '0x1F0FFF' # PROCESS_ALL_ACCESS
  condition: selection
level: critical
tags:
  - attack.credential_access
  - attack.t1003.001`}
                  </pre>
                </div>
              )}

              {activeTab === 'chain' && (
                <div className="space-y-3">
                  <div className="text-text-muted pb-1 border-b border-white/[0.06] text-xs">
                    Correlated multi-stage attack timeline (confidence score: 96%)
                  </div>

                  <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-white/[0.08]">
                    <div className="relative">
                      <div className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-threat-medium ring-4 ring-surface" />
                      <div className="text-text-primary font-medium">Initial access via credential stuffing</div>
                      <div className="text-text-muted text-[11px]">SSH brute-force succeeds on public bastion host</div>
                    </div>

                    <div className="relative">
                      <div className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-threat-high ring-4 ring-surface" />
                      <div className="text-text-primary font-medium">Privilege escalation &amp; encoded payload</div>
                      <div className="text-text-muted text-[11px]">PowerShell process spawns with base64 memory injector</div>
                    </div>

                    <div className="relative">
                      <div className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-threat-critical ring-4 ring-surface" />
                      <div className="text-text-primary font-medium">Credential dumping from LSASS</div>
                      <div className="text-text-muted text-[11px]">Memory read handle acquired on domain controller</div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Workbench Status Bar */}
            <div className="px-4 py-2.5 bg-deep border-t border-white/[0.06] flex items-center justify-between text-[11px] text-text-muted">
              <div className="flex items-center gap-3">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  <span>Pipeline active</span>
                </span>
                <span className="text-text-ghost">|</span>
                <span>Throughput: <strong className="text-text-secondary font-mono tabular-nums">28,410 eps</strong></span>
              </div>
              <div>
                <span>Mean latency: <strong className="text-text-secondary font-mono tabular-nums">8.2ms</strong></span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Section 2: Ingestion & Parser Matrix ───────────────── */}
      <section id="parsers" className="py-20 border-b border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="max-w-2xl mb-12">
            <h2 className="font-display font-bold text-2xl sm:text-3xl tracking-tight text-text-primary mb-3">
              Native parsers for hybrid infrastructure
            </h2>
            <p className="text-text-secondary text-sm sm:text-base leading-relaxed">
              Parse and normalize raw event streams directly without custom regular expressions.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="p-6 rounded-xl border border-white/[0.08] bg-surface flex flex-col">
              <div className="w-10 h-10 rounded-lg bg-elevated border border-white/[0.06] flex items-center justify-center mb-5">
                <Server className="w-5 h-5 text-amber-400" />
              </div>
              <h3 className="font-display font-semibold text-lg text-text-primary mb-2">Windows EVTX &amp; Sysmon</h3>
              <p className="text-text-secondary text-xs sm:text-sm leading-relaxed mb-6 flex-1">
                Zero-dependency binary parser for Security, System, and Sysmon channels with sub-millisecond event decoding.
              </p>
              <div className="pt-4 border-t border-white/[0.06] text-[11px] text-text-muted">
                Event IDs 4624, 4688, 4720, 7045
              </div>
            </div>

            <div className="p-6 rounded-xl border border-white/[0.08] bg-surface flex flex-col">
              <div className="w-10 h-10 rounded-lg bg-elevated border border-white/[0.06] flex items-center justify-center mb-5">
                <Cloud className="w-5 h-5 text-amber-400" />
              </div>
              <h3 className="font-display font-semibold text-lg text-text-primary mb-2">AWS CloudTrail &amp; GuardDuty</h3>
              <p className="text-text-secondary text-xs sm:text-sm leading-relaxed mb-6 flex-1">
                Multi-region JSON event normalization, cross-account IAM role assumption tracking, and anomaly attribution.
              </p>
              <div className="pt-4 border-t border-white/[0.06] text-[11px] text-text-muted">
                AssumeRole, S3, KMS, IAM events
              </div>
            </div>

            <div className="p-6 rounded-xl border border-white/[0.08] bg-surface flex flex-col">
              <div className="w-10 h-10 rounded-lg bg-elevated border border-white/[0.06] flex items-center justify-center mb-5">
                <Terminal className="w-5 h-5 text-amber-400" />
              </div>
              <h3 className="font-display font-semibold text-lg text-text-primary mb-2">Linux Audit &amp; Syslog</h3>
              <p className="text-text-secondary text-xs sm:text-sm leading-relaxed mb-6 flex-1">
                Native streaming parser for auditd, auth.log, and journald with PAM authentication clustering and privilege checks.
              </p>
              <div className="pt-4 border-t border-white/[0.06] text-[11px] text-text-muted">
                EXECVE, USER_AUTH, SUDO telemetry
              </div>
            </div>

            <div className="p-6 rounded-xl border border-white/[0.08] bg-surface flex flex-col">
              <div className="w-10 h-10 rounded-lg bg-elevated border border-white/[0.06] flex items-center justify-center mb-5">
                <FileCode2 className="w-5 h-5 text-amber-400" />
              </div>
              <h3 className="font-display font-semibold text-lg text-text-primary mb-2">Web Server Telemetry</h3>
              <p className="text-text-secondary text-xs sm:text-sm leading-relaxed mb-6 flex-1">
                Structured parser for Nginx, Apache, and IIS access logs identifying path traversal, SQL injection, and probe bursts.
              </p>
              <div className="pt-4 border-t border-white/[0.06] text-[11px] text-text-muted">
                Combined &amp; Common log formats
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Section 3: Investigation Pipeline ──────────────────── */}
      <section id="pipeline" className="py-20 border-b border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="max-w-2xl mb-12">
            <h2 className="font-display font-bold text-2xl sm:text-3xl tracking-tight text-text-primary mb-3">
              From raw telemetry to corroborated evidence
            </h2>
            <p className="text-text-secondary text-sm sm:text-base leading-relaxed">
              Four automated stages transform high-volume logs into structured incident reports.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="p-6 rounded-xl border border-white/[0.08] bg-surface">
              <div className="text-xs text-amber-400 font-semibold mb-3">Stage 01</div>
              <h3 className="font-display font-semibold text-lg text-text-primary mb-2">Ingestion &amp; parsing</h3>
              <p className="text-text-secondary text-xs sm:text-sm leading-relaxed">
                Upload files or stream logs via API. Binary EVTX and text lines are converted to typed memory records.
              </p>
            </div>

            <div className="p-6 rounded-xl border border-white/[0.08] bg-surface">
              <div className="text-xs text-amber-400 font-semibold mb-3">Stage 02</div>
              <h3 className="font-display font-semibold text-lg text-text-primary mb-2">Multi-engine rules</h3>
              <p className="text-text-secondary text-xs sm:text-sm leading-relaxed">
                Evaluate over {stats.rules} Sigma and Wazuh detection rules in memory to flag adversarial tactics.
              </p>
            </div>

            <div className="p-6 rounded-xl border border-white/[0.08] bg-surface">
              <div className="text-xs text-amber-400 font-semibold mb-3">Stage 03</div>
              <h3 className="font-display font-semibold text-lg text-text-primary mb-2">Cross-source correlation</h3>
              <p className="text-text-secondary text-xs sm:text-sm leading-relaxed">
                Correlate events across different hosts and cloud accounts by timestamp, IP address, and identity.
              </p>
            </div>

            <div className="p-6 rounded-xl border border-white/[0.08] bg-surface">
              <div className="text-xs text-amber-400 font-semibold mb-3">Stage 04</div>
              <h3 className="font-display font-semibold text-lg text-text-primary mb-2">Evidence packages</h3>
              <p className="text-text-secondary text-xs sm:text-sm leading-relaxed">
                Export verifiable PDF reports with findings, MITRE ATT&amp;CK mappings, and indicators of compromise.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Section 4: Cloud Compliance Automation ─────────────── */}
      <section id="compliance" className="py-20 border-b border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="max-w-2xl mb-12">
            <h2 className="font-display font-bold text-2xl sm:text-3xl tracking-tight text-text-primary mb-3">
              Automated audit readiness across 12 frameworks
            </h2>
            <p className="text-text-secondary text-sm sm:text-base leading-relaxed">
              Verify security controls and generate audit-ready evidence for AWS and hybrid environments.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="p-6 rounded-xl border border-white/[0.08] bg-surface flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className="font-display font-semibold text-lg text-text-primary">SOC 2 Type II</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Automated
                  </span>
                </div>
                <p className="text-text-secondary text-xs sm:text-sm leading-relaxed mb-4">
                  Continuous validation of CC6.1 logical access controls, CC6.6 perimeter defense, and CC7.2 anomaly detection.
                </p>
              </div>
              <div className="text-[11px] text-text-muted pt-3 border-t border-white/[0.06]">
                Trust Services Criteria CC6, CC7
              </div>
            </div>

            <div className="p-6 rounded-xl border border-white/[0.08] bg-surface flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className="font-display font-semibold text-lg text-text-primary">ISO/IEC 27001:2022</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Automated
                  </span>
                </div>
                <p className="text-text-secondary text-xs sm:text-sm leading-relaxed mb-4">
                  Evidence verification for Annex A.8.15 logging, A.8.16 security monitoring, and A.8.20 network management.
                </p>
              </div>
              <div className="text-[11px] text-text-muted pt-3 border-t border-white/[0.06]">
                Annex A.8 Technical Controls
              </div>
            </div>

            <div className="p-6 rounded-xl border border-white/[0.08] bg-surface flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className="font-display font-semibold text-lg text-text-primary">CIS AWS Benchmark</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Automated
                  </span>
                </div>
                <p className="text-text-secondary text-xs sm:text-sm leading-relaxed mb-4">
                  Automated checks for IAM root keys, S3 public access block, CloudTrail multi-region logs, and KMS encryption.
                </p>
              </div>
              <div className="text-[11px] text-text-muted pt-3 border-t border-white/[0.06]">
                CIS AWS Foundations v3.0
              </div>
            </div>

            <div className="p-6 rounded-xl border border-white/[0.08] bg-surface flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className="font-display font-semibold text-lg text-text-primary">HIPAA Security Rule</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Automated
                  </span>
                </div>
                <p className="text-text-secondary text-xs sm:text-sm leading-relaxed mb-4">
                  Verification of audit controls under section 164.312(b) and ePHI data transmission safeguards under 164.312(e).
                </p>
              </div>
              <div className="text-[11px] text-text-muted pt-3 border-t border-white/[0.06]">
                45 CFR Part 164 Subpart C
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Section 5: Engine Specifications ───────────────────── */}
      <section className="py-20 border-b border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="p-8 rounded-xl border border-white/[0.08] bg-surface">
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-8">
              <div>
                <div className="text-xs text-text-muted mb-1">Parser throughput</div>
                <div className="font-display font-bold text-2xl text-text-primary tabular-nums">140,000 eps</div>
                <div className="text-xs text-text-muted mt-1">Multi-core binary decoder</div>
              </div>

              <div>
                <div className="text-xs text-text-muted mb-1">Correlation latency</div>
                <div className="font-display font-bold text-2xl text-text-primary tabular-nums">&lt; 15ms</div>
                <div className="text-xs text-text-muted mt-1">In-memory sliding window</div>
              </div>

              <div>
                <div className="text-xs text-text-muted mb-1">Threat framework</div>
                <div className="font-display font-bold text-2xl text-text-primary">MITRE v14</div>
                <div className="text-xs text-text-muted mt-1">Enterprise attack matrix</div>
              </div>

              <div>
                <div className="text-xs text-text-muted mb-1">Execution model</div>
                <div className="font-display font-bold text-2xl text-text-primary">Sovereign</div>
                <div className="text-xs text-text-muted mt-1">Air-gap &amp; cloud deployment</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────── */}
      <footer className="py-12 bg-deep mt-auto">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6 pb-8 border-b border-white/[0.06]">
            <div className="flex items-center gap-3">
              <div className="w-7 h-7 rounded-lg bg-surface border border-white/[0.08] flex items-center justify-center">
                <Shield className="w-3.5 h-3.5 text-amber-400" />
              </div>
              <span className="font-display font-bold text-sm tracking-tight text-text-primary">
                Log<span className="text-amber-400">Raven</span>
              </span>
            </div>

            <div className="flex items-center gap-2 text-xs text-text-muted">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span>Platform operational: Sub-15ms parser latency</span>
            </div>

            <div className="flex items-center gap-6 text-xs text-text-muted">
              <Link to="/compliance" className="hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded">
                Compliance directory
              </Link>
              <Link to="/login" className="hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded">
                Console sign in
              </Link>
              <Link to="/register" className="hover:text-text-primary transition-colors focus-visible:ring-2 focus-visible:ring-amber-400 focus-visible:outline-none rounded">
                Create account
              </Link>
            </div>
          </div>

          <div className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-text-muted">
            <div>&copy; 2026 LogRaven Inc. All rights reserved.</div>
            <LegalLinks />
          </div>
        </div>
      </footer>
    </div>
  )
}
