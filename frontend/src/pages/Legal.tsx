// LogRaven — Legal pages (Privacy Policy & Terms of Service)
//
// Public static pages linked from auth footers. One shared shell, two exports.

import { Link } from 'react-router-dom'
import { ShieldCheck, ChevronLeft } from 'lucide-react'
import LegalLinks from '../components/layout/LegalLinks'

function LegalShell({ title, updated, children }: {
  title: string
  updated: string
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-void grid-bg">
      <header className="border-b border-white/[0.06] bg-deep/40 backdrop-blur">
        <div className="px-4 sm:px-6 lg:px-8 py-4 max-w-3xl mx-auto flex items-center justify-between gap-3">
          <Link to="/" className="flex items-center gap-2">
            <span className="w-8 h-8 rounded-lg bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center">
              <ShieldCheck className="w-4 h-4 text-indigo-300" />
            </span>
            <span className="font-display font-bold text-text-primary">LogRaven</span>
          </Link>
          <Link to="/login" className="inline-flex items-center gap-1 text-xs font-mono text-text-muted hover:text-text-secondary transition-colors">
            <ChevronLeft className="w-3 h-3" /> Back to login
          </Link>
        </div>
      </header>

      <main className="px-4 sm:px-6 lg:px-8 py-10 max-w-3xl mx-auto">
        <div className="font-mono text-[10px] text-indigo-400 tracking-[0.18em] uppercase mb-2">Legal</div>
        <h1 className="font-display font-bold text-text-primary text-3xl leading-tight">{title}</h1>
        <p className="font-mono text-[11px] text-text-muted mt-2 mb-8">Last updated: {updated}</p>
        <div className="space-y-8">{children}</div>
        <LegalLinks className="mt-10 border-t border-white/[0.06] pt-6" />
      </main>
    </div>
  )
}

function Section({ heading, children }: { heading: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="font-display font-semibold text-text-primary text-lg mb-2">{heading}</h2>
      <div className="text-sm text-text-secondary leading-relaxed space-y-3">{children}</div>
    </section>
  )
}

export function PrivacyPage() {
  return (
    <LegalShell title="Privacy Policy" updated="July 2026">
      <Section heading="What we collect">
        <p>
          LogRaven stores your account details (email, display name, timezone), the log files you
          upload for analysis, the reports generated from them, and compliance evidence collected
          from cloud accounts you explicitly connect via a read-only role.
        </p>
      </Section>
      <Section heading="How your data is used">
        <p>
          Uploaded logs are processed solely to produce your security findings and reports. When you
          give explicit consent, normalized event fields—including security-relevant hostnames,
          usernames and network addresses when present—may be sent to an external AI provider to
          enrich the investigation. Compliance audits use an external AI provider, when configured,
          to grade sanitized aggregate AWS evidence; starting a compliance audit authorizes that
          processing.
        </p>
      </Section>
      <Section heading="Data isolation and security">
        <p>
          Every investigation, report, and audit is scoped to your account unless you explicitly
          create an expiring audit share link. Sessions use short-lived tokens in httpOnly cookies,
          passwords are hashed with bcrypt, and an insert-only audit trail records selected
          security-sensitive activity for one year before it is purged.
        </p>
      </Section>
      <Section heading="Retention and deletion">
        <p>
          You can delete individual investigations (including their uploaded files and reports) at
          any time, and you can permanently delete your entire account from Profile &amp; Settings —
          this removes your data and stored files. Audit share links expire automatically.
        </p>
      </Section>
      <Section heading="Contact">
        <p>
          Questions about this policy? Email{' '}
          <a href="mailto:support@lograven.io" className="text-indigo-300 hover:text-indigo-200 transition-colors">
            support@lograven.io
          </a>.
        </p>
      </Section>
    </LegalShell>
  )
}

export function TermsPage() {
  return (
    <LegalShell title="Terms of Service" updated="July 2026">
      <Section heading="The service">
        <p>
          LogRaven analyzes the log files you upload and, where connected, cloud account evidence,
          to surface security findings and compliance posture. Analysis output — including
          AI-assisted findings and compliance grades — is decision support, not a guarantee: review
          results with a qualified security professional before acting on or submitting them.
        </p>
      </Section>
      <Section heading="Your responsibilities">
        <p>
          Only upload logs and connect accounts you are authorized to analyze. You are responsible
          for the legality of the data you submit and for safeguarding your account credentials.
          Attempting to access other users' data, probe the service, or bypass plan limits is
          prohibited.
        </p>
      </Section>
      <Section heading="Plans and limits">
        <p>
          Feature limits (upload size, AI analysis volume, daily analyses, correlation) depend on
          your plan tier. Limits may be adjusted with reasonable notice.
        </p>
      </Section>
      <Section heading="Availability and liability">
        <p>
          The service is provided "as is" without warranty of uninterrupted availability. To the
          maximum extent permitted by law, LogRaven is not liable for indirect or consequential
          damages arising from use of the service or reliance on its analysis output.
        </p>
      </Section>
      <Section heading="Contact">
        <p>
          Questions about these terms? Email{' '}
          <a href="mailto:support@lograven.io" className="text-indigo-300 hover:text-indigo-200 transition-colors">
            support@lograven.io
          </a>.
        </p>
      </Section>
    </LegalShell>
  )
}
