import { useState, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Search,
  Play,
  Info,
} from 'lucide-react'

export interface FrameworkDossier {
  id: string
  code: string
  name: string
  version: string
  category: 'enterprise' | 'cloud' | 'healthcare' | 'financial' | 'privacy'
  governingBody: string
  description: string
  targetAudience: string
  totalControls: number
  automatedRate: string
  keyDomains: string[]
  primarySignals: string[]
  auditorExpectations: string
  complianceBadge: string
}

export const FRAMEWORK_CATALOG: FrameworkDossier[] = [
  {
    id: 'soc2',
    code: 'SOC 2',
    name: 'SOC 2 Type II (AICPA Trust Services Criteria)',
    version: '2017 / 2024 Baseline',
    category: 'enterprise',
    governingBody: 'American Institute of CPAs (AICPA)',
    description:
      'The premier security and data protection standard for SaaS and cloud providers. Evaluates internal controls over Security, Availability, Processing Integrity, Confidentiality, and Privacy over an audit observation period.',
    targetAudience: 'B2B SaaS companies, enterprise technology vendors, cloud service providers.',
    totalControls: 11,
    automatedRate: '100% Automated',
    keyDomains: ['Common Criteria (CC6.1-CC6.8)', 'Access Control & MFA', 'Encryption in Transit & Rest', 'Incident Management (CC7.1-CC7.5)'],
    primarySignals: ['IAM MFA Enforcement', 'S3 Bucket Default Encryption', 'CloudTrail Multi-Region Trails', 'Security Group Ingress (Port 22/3389 blocked)', 'KMS Key Auto-Rotation'],
    auditorExpectations: 'Auditors require continuous evidence proving technical controls were consistently operated without unauthorized exceptions across CC6 & CC7.',
    complianceBadge: 'Gold Enterprise Standard',
  },
  {
    id: 'iso27001',
    code: 'ISO 27001',
    name: 'ISO/IEC 27001:2022 (Information Security Management)',
    version: '2022 Revision',
    category: 'enterprise',
    governingBody: 'International Organization for Standardization (ISO)',
    description:
      'The international benchmark for establishing, implementing, maintaining, and continually improving an Information Security Management System (ISMS). Includes Annex A control requirements.',
    targetAudience: 'Global enterprises, regulated software providers, European and worldwide clients.',
    totalControls: 19,
    automatedRate: '84% Automated',
    keyDomains: ['Organizational Controls (A.5)', 'People Controls (A.6)', 'Physical Controls (A.7)', 'Technological Controls (A.8)'],
    primarySignals: ['Identity & Access Governance', 'Cryptographic Controls', 'Vulnerability Management', 'Network Segregation', 'Configuration Logging'],
    auditorExpectations: 'Formal Statement of Applicability (SoA) and continuous evidence proving technical controls are active and routinely evaluated.',
    complianceBadge: 'Global Standard',
  },
  {
    id: 'cis_aws',
    code: 'CIS AWS',
    name: 'CIS Amazon Web Services Foundations Benchmark',
    version: 'v3.0.0',
    category: 'cloud',
    governingBody: 'Center for Internet Security (CIS)',
    description:
      'Consensus-based configuration guidelines for hardening AWS infrastructure. Provides prescriptive, step-by-step security checks across Identity, Logging, Monitoring, and Networking.',
    targetAudience: 'Every organization operating production workloads on AWS.',
    totalControls: 21,
    automatedRate: '100% Automated',
    keyDomains: ['Identity and Access Management', 'Storage & S3', 'Logging & CloudTrail', 'Monitoring & Alarms', 'Networking & VPC'],
    primarySignals: ['Root Account Usage Alerting', 'VPC Flow Logs Enabled', 'No S3 Public Read/Write', 'EBS Default Encryption', 'IAM Password Policy Complexity'],
    auditorExpectations: 'Strict technical compliance reports verifying infrastructure adheres to defense-in-depth baseline configurations.',
    complianceBadge: 'Cloud Hardening Baseline',
  },
  {
    id: 'hipaa',
    code: 'HIPAA',
    name: 'HIPAA Security Rule (Health Insurance Portability & Accountability)',
    version: '45 CFR Part 160 & Part 164',
    category: 'healthcare',
    governingBody: 'U.S. Dept. of Health & Human Services (HHS)',
    description:
      'Establishes national standards to protect individuals’ electronic personal health information (ePHI). Mandates appropriate administrative, physical, and technical safeguards.',
    targetAudience: 'Healthtech platforms, telehealth, medical device software, healthcare providers and Business Associates.',
    totalControls: 12,
    automatedRate: '92% Automated',
    keyDomains: ['Technical Safeguards §164.312', 'Transmission Security', 'Access Controls', 'Audit Controls', 'Integrity Controls'],
    primarySignals: ['AES-256 ePHI Storage Encryption', 'TLS 1.2+ Enforced', 'CloudTrail Immutability', 'Session Timeouts & MFA', 'Automated Daily Backups'],
    auditorExpectations: 'Proof that any cloud resource touching ePHI encrypts data in transit and rest, isolates environments, and logs all data access.',
    complianceBadge: 'Healthcare Mandatory',
  },
  {
    id: 'pci_dss',
    code: 'PCI-DSS',
    name: 'Payment Card Industry Data Security Standard',
    version: 'v4.0.1',
    category: 'financial',
    governingBody: 'PCI Security Standards Council (PCI SSC)',
    description:
      'Global security standard for all entities that store, process, or transmit cardholder data (CHD) and/or sensitive authentication data (SAD). Features heightened zero-trust requirements in v4.0.',
    targetAudience: 'Fintech platforms, payment gateways, e-commerce applications, banking integrations.',
    totalControls: 13,
    automatedRate: '92% Automated',
    keyDomains: ['Network Security Controls', 'Cardholder Data Protection', 'Vulnerability Management', 'Strong Access Control', 'Regular Testing'],
    primarySignals: ['Cardholder Environment Isolation', 'Multi-Factor for All Administrative Access', 'Web Application Firewall Active', 'Key Lifecycle Rotation', 'Immutable Audit Logs'],
    auditorExpectations: 'Rigorous QSA (Qualified Security Assessor) verification and ROC (Report on Compliance) evidence packages.',
    complianceBadge: 'Financial Essential',
  },
  {
    id: 'nist_csf',
    code: 'NIST CSF',
    name: 'NIST Cybersecurity Framework',
    version: 'v2.0',
    category: 'enterprise',
    governingBody: 'National Institute of Standards and Technology (NIST)',
    description:
      'Guidance based on existing standards, guidelines, and practices for organizations to better manage and reduce cybersecurity risk. Version 2.0 adds the critical GOVERN function.',
    targetAudience: 'Critical infrastructure, federal contractors, mid-market and enterprise cybersecurity teams.',
    totalControls: 11,
    automatedRate: '82% Automated',
    keyDomains: ['Govern (GV)', 'Identify (ID)', 'Protect (PR)', 'Detect (DE)', 'Respond (RS)', 'Recover (RC)'],
    primarySignals: ['Asset Visibility & Discovery', 'Continuous Threat Monitoring', 'Access Least Privilege', 'Baseline Configuration Management', 'Disaster Recovery Readiness'],
    auditorExpectations: 'Maturity tier assessments and clear crosswalk alignment to federal cybersecurity mandates.',
    complianceBadge: 'Federal Standard',
  },
  {
    id: 'cis_azure',
    code: 'CIS Azure',
    name: 'CIS Microsoft Azure Foundations Benchmark',
    version: 'v2.1.0',
    category: 'cloud',
    governingBody: 'Center for Internet Security (CIS)',
    description:
      'Prescriptive configuration recommendations for securing Microsoft Azure environments, subscriptions, storage accounts, Entra ID (Azure AD), and virtual networks.',
    targetAudience: 'Enterprises deploying cloud infrastructure on Microsoft Azure.',
    totalControls: 13,
    automatedRate: '100% Automated',
    keyDomains: ['Identity and Access (Entra ID)', 'Microsoft Defender for Cloud', 'Storage Accounts', 'Virtual Machines & Networking', 'Key Vault'],
    primarySignals: ['Storage Account Secure Transfer Required', 'Public Network Access Disabled', 'Defender for Cloud Enabled', 'Network Security Group Rules', 'Key Vault Purge Protection'],
    auditorExpectations: 'Verified Azure tenant scan logs demonstrating adherence to CIS benchmark rules.',
    complianceBadge: 'Azure Cloud Hardening',
  },
  {
    id: 'cis_gcp',
    code: 'CIS GCP',
    name: 'CIS Google Cloud Platform Foundation Benchmark',
    version: 'v3.0.0',
    category: 'cloud',
    governingBody: 'Center for Internet Security (CIS)',
    description:
      'Guidance for establishing a secure baseline configuration for Google Cloud Platform projects, IAM service accounts, Cloud Storage, and Compute Engine.',
    targetAudience: 'Organizations hosting services, data pipelines, and AI workloads on GCP.',
    totalControls: 15,
    automatedRate: '100% Automated',
    keyDomains: ['Identity and Access Management', 'Storage & Cloud Storage', 'Logging & BigQuery', 'Networking & Firewalls', 'Compute Engine'],
    primarySignals: ['Uniform Bucket-Level Access', 'No Service Account Keys Stored', 'VPC Flow Logs Enabled', 'Cloud Audit Logging', 'Shielded VM Protection'],
    auditorExpectations: 'Detailed GCP posture report mapped control-by-control to CIS recommendations.',
    complianceBadge: 'GCP Cloud Hardening',
  },
  {
    id: 'gdpr',
    code: 'GDPR',
    name: 'General Data Protection Regulation Security Controls',
    version: 'Article 32 Baseline',
    category: 'privacy',
    governingBody: 'European Data Protection Board (EDPB)',
    description:
      'Requires controllers and processors to implement technical and organizational measures to ensure a level of security appropriate to personal data risk under Article 32.',
    targetAudience: 'Any business processing or storing personal data of European Union residents.',
    totalControls: 9,
    automatedRate: '78% Automated',
    keyDomains: ['Pseudonymisation & Encryption', 'Ongoing Confidentiality & Integrity', 'Restoration & Availability', 'Regular Testing & Evaluation'],
    primarySignals: ['Database Encryption at Rest', 'Data Residency Geolocation Checks', 'Automated Daily Snapshot Retention', 'Strict RBAC on Personal Data', 'Breach Detection Alerts'],
    auditorExpectations: 'Demonstrable data protection by design and default with verifiable technical proof.',
    complianceBadge: 'Privacy Mandatory',
  },
  {
    id: 'fedramp',
    code: 'FedRAMP',
    name: 'FedRAMP Moderate Baseline',
    version: 'Rev. 5 Moderate',
    category: 'financial',
    governingBody: 'U.S. General Services Administration (GSA)',
    description:
      'Government-wide program that provides a standardized approach to security assessment, authorization, and continuous monitoring for cloud products and services used by federal agencies.',
    targetAudience: 'Cloud software vendors selling to U.S. Federal Government and Department of Defense agencies.',
    totalControls: 11,
    automatedRate: '100% Automated',
    keyDomains: ['Access Control (AC)', 'Audit and Accountability (AU)', 'Configuration Management (CM)', 'System and Communications Protection (SC)'],
    primarySignals: ['FIPS 140-2 Validated Encryption', 'Continuous Diagnostics & Mitigation', 'Least Privilege Role Architecture', 'Centralized Logging & SIEM Integration'],
    auditorExpectations: '3PAO (Third-Party Assessment Organization) audit evidence and System Security Plan (SSP) artifacts.',
    complianceBadge: 'Federal Grade',
  },
  {
    id: 'nist_800_53',
    code: 'NIST 800-53',
    name: 'NIST SP 800-53 Rev. 5 (Security and Privacy Controls)',
    version: 'Rev. 5 Baseline',
    category: 'financial',
    governingBody: 'National Institute of Standards and Technology',
    description:
      'Catalog of security and privacy controls for federal information systems and organizations to protect operations, assets, and individuals from advanced persistent threats.',
    targetAudience: 'Federal contractors, defense industrial base, high-security enterprise systems.',
    totalControls: 16,
    automatedRate: '100% Automated',
    keyDomains: ['Access Control (AC)', 'Audit & Accountability (AU)', 'System & Info Integrity (SI)', 'Identification & Authentication (IA)'],
    primarySignals: ['MFA Enforced Across System', 'Encrypted Backups & KMS', 'Strict Ingress Boundary Protections', 'FIPS Cryptography', 'Continuous Monitoring'],
    auditorExpectations: 'Comprehensive FedRAMP/DoD ATO authorization package and continuous POA&M tracking.',
    complianceBadge: 'Federal Defense Grade',
  },
  {
    id: 'csa_ccm',
    code: 'CSA CCM',
    name: 'Cloud Security Alliance Cloud Controls Matrix v4',
    version: 'v4.0.1',
    category: 'cloud',
    governingBody: 'Cloud Security Alliance (CSA)',
    description:
      'Cybersecurity control framework for cloud computing covering 17 domains, widely used for CSA STAR Level 1 and Level 2 self-assessments and certifications.',
    targetAudience: 'Cloud service providers, SaaS vendors, multi-cloud enterprise architects.',
    totalControls: 11,
    automatedRate: '100% Automated',
    keyDomains: ['Identity & Access (IAM)', 'Data Security & Privacy (DSP)', 'Infrastructure & Virtualization (IVS)', 'Threat & Vulnerability (TVM)'],
    primarySignals: ['Multi-Cloud IAM Least Privilege', 'Cloud Storage Protection', 'Network Micro-segmentation', 'Vulnerability Lifecycle'],
    auditorExpectations: 'Completed CSA STAR Consensus Assessments Initiative Questionnaire (CAIQ) and third-party evidence.',
    complianceBadge: 'CSA STAR Certified',
  },
  {
    id: 'iso27017',
    code: 'ISO 27017',
    name: 'ISO/IEC 27017:2015 (Cloud Security Controls)',
    version: '2015 Baseline',
    category: 'cloud',
    governingBody: 'International Organization for Standardization (ISO)',
    description:
      'Code of practice for information security controls based on ISO/IEC 27002 for cloud services, addressing shared responsibility for cloud service customers and providers.',
    targetAudience: 'SaaS providers, IaaS/PaaS vendors, enterprise cloud consumers.',
    totalControls: 7,
    automatedRate: '86% Automated',
    keyDomains: ['Asset Management in Cloud', 'Virtual Machine Hardening', 'Customer Data Segregation', 'Cloud Service Monitoring'],
    primarySignals: ['Shared Responsibility Isolation', 'Cloud Snapshot Protections', 'Multi-Tenant Segregation', 'Administrative Operation Logging'],
    auditorExpectations: 'ISO 27001 companion audit annex assessing cloud-specific security controls.',
    complianceBadge: 'Cloud Assurance',
  },
  {
    id: 'iso27018',
    code: 'ISO 27018',
    name: 'ISO/IEC 27018:2019 (Protection of PII in Public Clouds)',
    version: '2019 Revision',
    category: 'privacy',
    governingBody: 'International Organization for Standardization (ISO)',
    description:
      'First international standard focusing on the protection of personally identifiable information (PII) in public cloud computing environments acting as PII processors.',
    targetAudience: 'Cloud providers processing PII, privacy-centric SaaS applications.',
    totalControls: 7,
    automatedRate: '100% Automated',
    keyDomains: ['Consent and Choice', 'Data Minimization', 'Disclosure to Third Parties', 'Accountability & Auditability'],
    primarySignals: ['PII Storage Encryption at Rest', 'Strict Boundary Isolation', 'Access Revocation Tracking', 'Audit Logging of PII Access'],
    auditorExpectations: 'Demonstrated technical protection preventing unauthorized cloud processing or secondary use of PII.',
    complianceBadge: 'Cloud Privacy Standard',
  },
]

export default function FrameworkDirectoryPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')

  const filteredFrameworks = useMemo(() => {
    return FRAMEWORK_CATALOG.filter((fw) => {
      const matchesCategory = selectedCategory === 'all' || fw.category === selectedCategory
      const query = search.toLowerCase().trim()
      const matchesSearch =
        !query ||
        fw.name.toLowerCase().includes(query) ||
        fw.code.toLowerCase().includes(query) ||
        fw.governingBody.toLowerCase().includes(query) ||
        fw.description.toLowerCase().includes(query)
      return matchesCategory && matchesSearch
    })
  }, [search, selectedCategory])

  const categories = [
    { id: 'all', label: 'All Frameworks' },
    { id: 'enterprise', label: 'Enterprise Trust (SOC 2, ISO)' },
    { id: 'cloud', label: 'Cloud Hardening (CIS)' },
    { id: 'healthcare', label: 'Healthcare (HIPAA)' },
    { id: 'financial', label: 'Financial & Federal (PCI, FedRAMP)' },
    { id: 'privacy', label: 'Privacy (GDPR)' },
  ]

  const handleLaunchScan = (frameworkId: string) => {
    navigate(`/compliance?tab=audit&fw=${frameworkId}`)
  }

  return (
    <div className="min-h-screen bg-void text-text-primary p-6 sm:p-8 max-w-7xl mx-auto space-y-8">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 border-b border-white/[0.08] pb-8">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-indigo-500/30 bg-indigo-500/10 mb-3">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
            <span className="font-mono text-[10px] text-indigo-300 uppercase tracking-widest font-semibold">
              Supported Compliance Catalog · 14 Frameworks · 176 Cloud Controls · 94% Automated
            </span>
          </div>
          <h1 className="font-display text-3xl sm:text-4xl font-extrabold tracking-tight text-text-primary">
            Security &amp; Regulatory <span className="gradient-text">Frameworks Directory</span>
          </h1>
          <p className="text-text-secondary text-sm max-w-2xl mt-2 leading-relaxed">
            LogRaven continuously audits 176 cloud infrastructure controls across 14 leading security standards. Collect telemetry in 60s across AWS, Azure, and GCP, then satisfy multiple audits simultaneously with a 3.8x evidence crosswalk.
          </p>
        </div>

        <Link
          to="/compliance?tab=audit"
          className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-400 hover:to-indigo-500 text-white font-semibold text-xs shadow-[0_0_20px_rgba(99,102,241,0.35)] transition-all self-start md:self-auto flex-shrink-0"
        >
          <Play className="w-4 h-4 fill-white" />
          <span>Launch Multi-Framework Audit</span>
        </Link>
      </div>

      {/* Search & Category Filter Bar */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row items-stretch gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-text-muted absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search frameworks by title, standard, or governing body..."
              className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-white/[0.08] bg-surface/70 text-xs text-text-primary placeholder:text-text-muted/60 focus:outline-none focus:border-indigo-500/50"
            />
          </div>
        </div>

        {/* Category Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 custom-scrollbar">
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-all border ${
                selectedCategory === cat.id
                  ? 'border-indigo-500/40 bg-indigo-500/20 text-indigo-200 shadow-[0_0_12px_rgba(99,102,241,0.2)]'
                  : 'border-white/[0.06] bg-white/[0.02] text-text-muted hover:text-text-secondary hover:bg-white/[0.04]'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Frameworks Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {filteredFrameworks.map((fw) => (
          <motion.div
            key={fw.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-2xl border border-white/[0.08] bg-surface/60 hover:border-indigo-500/30 hover:bg-surface/90 transition-all duration-200 p-6 flex flex-col justify-between group shadow-lg"
          >
            <div>
              {/* Header row */}
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="min-w-0 pr-2">
                  <h2 className="font-display font-bold text-base text-text-primary group-hover:text-indigo-200 transition-colors leading-snug">
                    {fw.name}
                  </h2>
                  <div className="font-mono text-[10px] text-text-muted mt-1">
                    {fw.governingBody} · {fw.version}
                  </div>
                </div>

                <span className="px-2 py-0.5 rounded-md text-[10px] font-mono font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 whitespace-nowrap flex-shrink-0">
                  {fw.automatedRate}
                </span>
              </div>

              {/* Description */}
              <p className="text-xs text-text-secondary leading-relaxed mb-4">
                {fw.description}
              </p>

              {/* Target Audience Pill */}
              <div className="mb-4 p-2.5 rounded-xl bg-black/20 border border-white/[0.04] text-[11px] text-text-muted flex items-start gap-2">
                <Info className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0 mt-0.5" />
                <span><strong>Who needs it:</strong> {fw.targetAudience}</span>
              </div>

              {/* Key Domains Tags */}
              <div className="space-y-1.5 mb-5">
                <div className="font-mono text-[10px] uppercase tracking-wider text-text-muted font-medium">
                  Audited Control Domains:
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {fw.keyDomains.map((domain) => (
                    <span
                      key={domain}
                      className="px-2 py-1 rounded-lg text-[10px] font-mono border border-white/[0.06] bg-white/[0.02] text-text-secondary"
                    >
                      {domain}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Bottom Card Actions */}
            <div className="pt-4 border-t border-white/[0.06] flex items-center justify-between gap-3">
              <span className="font-mono text-xs text-text-muted">
                <strong className="text-text-primary">{fw.totalControls}</strong> Controls Tested
              </span>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => navigate(`/compliance/frameworks/${fw.id}`)}
                  className="px-3.5 py-1.5 rounded-xl border border-white/[0.08] hover:border-indigo-500/30 bg-white/[0.02] hover:bg-indigo-500/10 text-text-secondary hover:text-indigo-200 text-xs font-medium transition-colors"
                >
                  View Details
                </button>
                <button
                  onClick={() => handleLaunchScan(fw.id)}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-indigo-500/20 hover:bg-indigo-500/30 border border-indigo-500/40 text-indigo-200 text-xs font-semibold transition-all"
                >
                  <Play className="w-3 h-3 fill-indigo-300 text-indigo-300" />
                  <span>Scan Framework</span>
                </button>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
