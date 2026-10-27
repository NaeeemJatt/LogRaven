// LogRaven — Complete Framework Controls & Step-by-Step Guidance Database
//
// Authoritative directory for all 14 compliance standards:
// - Automated controls (inspected via AWS / Azure / GCP cloud signals)
// - Manual controls (organizational policies, HR processes, vendor reviews)
// - Step-by-step console, CLI, Terraform & auditor evidence instructions

export interface TechnicalRemediation {
  consoleSteps: string[]
  cliCommand: string
  terraformSnippet: string
  verificationCommand: string
}

export interface ManualGovernanceGuide {
  whyManual: string
  requiredPolicy: string
  operationalSteps: string[]
  auditorEvidence: string[]
  pitfallsToAvoid: string
}

export interface FrameworkControl {
  control_id: string
  name: string
  category: string
  automatable: boolean
  description: string
  signals?: string[]
  howItWorks?: string
  remediation?: TechnicalRemediation
  manualGuide?: ManualGovernanceGuide
}

export interface FrameworkFullDetail {
  id: string
  code: string
  name: string
  version: string
  category: 'enterprise' | 'cloud' | 'healthcare' | 'financial' | 'privacy'
  governingBody: string
  description: string
  targetAudience: string
  complianceBadge: string
  totalControls: number
  automatedCount: number
  manualCount: number
  automatedRate: string
  auditorExpectations: string
  controls: FrameworkControl[]
}

// ══════════════════════════════════════════════════════════════════════════════
// 1. SOC 2 Type II
// ══════════════════════════════════════════════════════════════════════════════
export const SOC2_DETAIL: FrameworkFullDetail = {
  id: 'soc2',
  code: 'SOC 2',
  name: 'SOC 2 Type II (AICPA Trust Services Criteria)',
  version: '2017 / 2024 Baseline',
  category: 'enterprise',
  governingBody: 'American Institute of CPAs (AICPA)',
  description:
    'The premier security and data protection standard for SaaS and cloud providers. Evaluates internal controls over Security, Availability, Processing Integrity, Confidentiality, and Privacy over an audit observation period.',
  targetAudience: 'B2B SaaS companies, enterprise technology vendors, cloud service providers.',
  complianceBadge: 'Gold Enterprise Standard',
  totalControls: 11,
  automatedCount: 11,
  manualCount: 0,
  automatedRate: '100% Automated',
  auditorExpectations:
    'Auditors inspect continuous automated evidence from cloud infrastructure across CC6 (Logical Access) and CC7 (System Operations) without unauthorized exceptions.',
  controls: [
    // ── Automated Controls ──
    {
      control_id: 'CC6.1',
      name: 'Logical Access Security Software, Infrastructure, and Architectures',
      category: 'CC6 — Logical & Physical Access',
      automatable: true,
      description:
        'The entity implements logical access security software, infrastructure, and architectures over protected information assets to protect them from security events to meet its objectives.',
      signals: [
        'iam_mfa_enforcement_rate',
        'iam_root_mfa_enabled',
        'iam_password_policy_exists',
        'iam_password_min_length',
        's3_public_access_blocked',
        'default_sg_restricted',
        'open_security_groups',
      ],
      howItWorks:
        'LogRaven continuously samples IAM credentials, root account MFA status, S3 account-level block public access configurations, and security group inbound CIDRs.',
      remediation: {
        consoleSteps: [
          'Sign in to AWS Management Console and open the IAM console at https://console.aws.amazon.com/iam/.',
          'Under Account Settings, verify Password Policy mandates at least 14 characters and symbol complexity.',
          'Under Users, enforce Multi-Factor Authentication (MFA) for every human user and virtual root credential.',
          'Navigate to Amazon S3 > Block Public Access (account settings) and enable all four block checkboxes.',
          'Navigate to Amazon VPC > Security Groups and ensure default security groups have zero inbound or outbound rules.',
        ],
        cliCommand:
          '# Enforce account-wide S3 Public Access Block\naws s3control put-public-access-block \\\n  --account-id $(aws sts get-caller-identity --query Account --output text) \\\n  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"',
        terraformSnippet:
          'resource "aws_s3_account_public_access_block" "account_wide" {\n  block_public_acls       = true\n  block_public_policy     = true\n  ignore_public_acls      = true\n  restrict_public_buckets = true\n}',
        verificationCommand:
          'aws s3control get-public-access-block --account-id $(aws sts get-caller-identity --query Account --output text)',
      },
    },
    {
      control_id: 'CC6.2',
      name: 'User Registration & Least-Privilege Authorization',
      category: 'CC6 — Logical & Physical Access',
      automatable: true,
      description:
        'Prior to issuing system credentials and granting system access, the entity registers and authorizes new internal and external users.',
      signals: ['iam_users_total', 'iam_mfa_enforcement_rate', 'iam_admin_users'],
      howItWorks:
        'Audits the total volume of IAM accounts and verifies that administrative roles (AdministratorAccess) are minimized to authorized operators with active MFA.',
      remediation: {
        consoleSteps: [
          'Open IAM Console > Roles and check for users directly attached to AdministratorAccess.',
          'Replace individual IAM user credentials with federated IAM Identity Center (SSO) with time-bound sessions.',
          'Review all IAM groups to ensure least-privilege scoping.',
        ],
        cliCommand:
          '# List users with AdministratorAccess attached\naws iam list-entities-for-policy --policy-arn arn:aws:iam::aws:policy/AdministratorAccess',
        terraformSnippet:
          '# Ensure least privilege permission boundary is applied to all roles\nresource "aws_iam_role" "operator" {\n  name                 = "DevOpsRole"\n  permissions_boundary = "arn:aws:iam::123456789012:policy/OperatorBoundary"\n  assume_role_policy   = data.aws_iam_policy_document.assume_role.json\n}',
        verificationCommand: 'aws iam get-account-summary --query "SummaryMap.AccountAccessKeysPresent"',
      },
    },
    {
      control_id: 'CC6.3',
      name: 'Revocation of Credentials for Terminated or Inactive Users',
      category: 'CC6 — Logical & Physical Access',
      automatable: true,
      description:
        'The entity revokes logical access privileges when user access is no longer required or upon termination of employment.',
      signals: ['iam_stale_access_keys', 'iam_users_total'],
      howItWorks:
        'Scans IAM credential report for access keys or passwords that have not been used in 90+ days or are assigned to inactive personnel.',
      remediation: {
        consoleSteps: [
          'Open IAM Console > Credential Report and click "Download Report".',
          'Filter for any access key with access_key_1_last_used_date > 90 days ago.',
          'Deactivate or delete the stale keys.',
        ],
        cliCommand:
          '# Deactivate a stale access key\naws iam update-access-key --user-name Alice --access-key-id AKIAEXAMPLE --status Inactive',
        terraformSnippet:
          '# Enforce key rotation lifecycle policy in IAM\n# Recommend eliminating static IAM user keys in favor of IAM Roles Anywhere or AWS SSO.',
        verificationCommand: 'aws iam get-credential-report --output text --query "Content" | base64 --decode | cut -d, -f1,4,5,9,14',
      },
    },
    {
      control_id: 'CC6.6',
      name: 'Protection Against External Network Threats & Boundary Ingress',
      category: 'CC6 — Logical & Physical Access',
      automatable: true,
      description:
        'Logical access restrictions to systems protect against external threats from untrusted networks and unauthorized traffic.',
      signals: [
        'open_security_groups',
        'default_sg_restricted',
        'vpc_flow_logs_enabled',
        'access_analyzer_external_findings',
        's3_public_access_blocked',
      ],
      howItWorks:
        'Inspects all EC2 security group ingress rules for unrestricted ports (0.0.0.0/0 on ports 22, 3389, 5432, 3306), verifies VPC Flow Logs are enabled, and checks IAM Access Analyzer for external resource sharing.',
      remediation: {
        consoleSteps: [
          'Open EC2 Console > Security Groups.',
          'Search for inbound rules with Port 22 (SSH) or 3389 (RDP) open to 0.0.0.0/0.',
          'Revoke the public rule and replace with an internal VPN / bastion CIDR or AWS Systems Manager Session Manager.',
          'Open VPC Console > Your VPCs > Flow Logs > Create flow log pointing to CloudWatch Logs or S3.',
        ],
        cliCommand:
          '# Revoke unrestricted SSH ingress from security group\naws ec2 revoke-security-group-ingress \\\n  --group-id sg-0123456789abcdef0 \\\n  --protocol tcp --port 22 --cidr 0.0.0.0/0',
        terraformSnippet:
          'resource "aws_security_group_rule" "internal_ssh" {\n  type              = "ingress"\n  from_port         = 22\n  to_port           = 22\n  protocol          = "tcp"\n  cidr_blocks       = ["10.0.0.0/16"] # Internal VPC or corporate VPN only\n  security_group_id = aws_security_group.app.id\n}',
        verificationCommand:
          'aws ec2 describe-security-groups --filters "Name=ip-permission.cidr,Values=0.0.0.0/0" --query "SecurityGroups[*].[GroupId,GroupName]"',
      },
    },
    {
      control_id: 'CC6.7',
      name: 'Cryptographic Protection of Data in Transit & at Rest',
      category: 'CC6 — Logical & Physical Access',
      automatable: true,
      description:
        'The entity protects information in transmission, movement, and storage through cryptographic mechanisms.',
      signals: [
        's3_default_encryption_rate',
        'ebs_default_encryption',
        'rds_encryption_rate',
        'kms_key_rotation_rate',
        'cloudtrail_encrypted',
      ],
      howItWorks:
        'Evaluates default S3 bucket encryption (SSE-S3 or SSE-KMS), EBS volume encryption at rest, RDS database encryption, and KMS customer managed key automatic annual rotation.',
      remediation: {
        consoleSteps: [
          'Open EC2 Console > Settings > EBS encryption and enable "Always encrypt new EBS volumes".',
          'Open S3 Console, select non-compliant buckets > Properties > Default encryption > set to AES-256 or AWS-KMS.',
          'Open KMS Console > Customer Managed Keys > select key > Key rotation > Check "Automatically rotate this KMS key every year".',
        ],
        cliCommand:
          '# Enable EBS default encryption for the current AWS region\naws ec2 enable-ebs-encryption-by-default',
        terraformSnippet:
          'resource "aws_ebs_encryption_by_default" "enabled" {\n  enabled = true\n}\n\nresource "aws_kms_key" "app_key" {\n  description             = "SOC 2 Storage Key"\n  enable_key_rotation     = true\n  deletion_window_in_days = 30\n}',
        verificationCommand: 'aws ec2 get-ebs-encryption-by-default',
      },
    },
    {
      control_id: 'CC6.8',
      name: 'Detection & Prevention of Malicious Software & Unauthorized Execution',
      category: 'CC6 — Logical & Physical Access',
      automatable: true,
      description:
        'The entity implements controls to prevent or detect unauthorized or malicious software across endpoints and cloud workloads.',
      signals: ['guardduty_enabled', 'inspector_enabled', 'guardduty_high_severity_findings'],
      howItWorks:
        'Queries Amazon GuardDuty and Amazon Inspector API status across all active regions to verify continuous ML-based threat detection and vulnerability assessment.',
      remediation: {
        consoleSteps: [
          'Open Amazon GuardDuty Console and choose "Enable GuardDuty".',
          'Open Amazon Inspector Console and click "Activate Inspector".',
          'Review any existing High or Critical severity findings and execute containment procedures.',
        ],
        cliCommand:
          '# Enable GuardDuty in the current region\naws guardduty create-detector --enable',
        terraformSnippet:
          'resource "aws_guardduty_detector" "primary" {\n  enable = true\n}',
        verificationCommand: 'aws guardduty list-detectors --query "DetectorIds" --output json',
      },
    },
    {
      control_id: 'CC7.1',
      name: 'Vulnerability Management Program & Conformance Monitoring',
      category: 'CC7 — System Operations',
      automatable: true,
      description:
        'The entity conducts vulnerability scans at scheduled intervals and monitors configuration conformance against baselines.',
      signals: ['inspector_enabled', 'securityhub_enabled', 'config_recorder_enabled'],
      howItWorks:
        'Verifies that AWS Security Hub, Amazon Inspector, and AWS Config configuration recorders are active and recording all resource types.',
      remediation: {
        consoleSteps: [
          'Open AWS Config Console > Set up AWS Config > Record all resources.',
          'Open AWS Security Hub Console > Enable Security Hub with AWS Foundational Security Best Practices.',
        ],
        cliCommand:
          '# Enable AWS Security Hub\naws securityhub enable-security-hub --enable-default-standards',
        terraformSnippet:
          'resource "aws_securityhub_account" "main" {}\nresource "aws_config_configuration_recorder" "all" {\n  name     = "default"\n  role_arn = aws_iam_role.config.arn\n  recording_group {\n    all_supported = true\n    include_global_resource_types = true\n  }\n}',
        verificationCommand: 'aws configservice describe-configuration-recorder-status',
      },
    },
    {
      control_id: 'CC7.2',
      name: 'Continuous Security Telemetry & Anomaly Logging',
      category: 'CC7 — System Operations',
      automatable: true,
      description:
        'The entity monitors system components and the operation of those components for anomalies that are indicative of malicious acts.',
      signals: [
        'guardduty_enabled',
        'cloudtrail_multiregion',
        'vpc_flow_logs_enabled',
        'security_alarms_configured',
        'cloudwatch_log_retention_days',
      ],
      howItWorks:
        'Validates multi-region CloudTrail trails with log file validation enabled, VPC Flow Logs recording ACCEPT/REJECT traffic, and CloudWatch log groups retaining data for at least 90 days.',
      remediation: {
        consoleSteps: [
          'Open CloudTrail Console > Trails > Create trail > check "Apply trail to all regions" and "Enable log file validation".',
          'Point trail delivery to an encrypted, restricted S3 audit bucket with MFA Delete.',
        ],
        cliCommand:
          '# Update CloudTrail to enable global multi-region logging\naws cloudtrail update-trail --name production-trail --is-multi-region-trail --enable-log-file-validation',
        terraformSnippet:
          'resource "aws_cloudtrail" "audit_trail" {\n  name                          = "audit-trail-all-regions"\n  s3_bucket_name                = aws_s3_bucket.trail_logs.id\n  is_multi_region_trail         = true\n  enable_log_file_validation    = true\n  include_global_service_events = true\n}',
        verificationCommand: 'aws cloudtrail describe-trails --query "trailList[*].[Name,IsMultiRegionTrail,LogFileValidationEnabled]"',
      },
    },
    {
      control_id: 'CC7.3',
      name: 'Security Event Triage & Incident Determination',
      category: 'CC7 — System Operations',
      automatable: true,
      description:
        'The entity evaluates security events to determine whether they could impact the entity’s ability to meet its objectives (security incidents).',
      signals: ['guardduty_high_severity_findings', 'securityhub_enabled', 'failed_login_attempts'],
      howItWorks:
        'Monitors active open High/Critical threat events from GuardDuty and Security Hub, tracking mean time to detect (MTTD).',
      remediation: {
        consoleSteps: [
          'Review high severity alerts in Security Hub Findings console.',
          'Correlate anomalous IP addresses and compromised IAM credentials.',
          'Execute temporary IAM session revocation and isolate impacted EC2 instances.',
        ],
        cliCommand:
          '# Query open high severity GuardDuty findings\naws guardduty list-findings --detector-id $(aws guardduty list-detectors --query "DetectorIds[0]" --output text) --finding-criteria \'{"Criterion": {"severity": {"Gte": 7}}}\'',
        terraformSnippet:
          'resource "aws_cloudwatch_event_rule" "guardduty_alerts" {\n  name        = "capture-high-severity-guardduty"\n  event_pattern = jsonencode({\n    source      = ["aws.guardduty"],\n    detail-type = ["GuardDuty Finding"],\n    detail      = { severity = [7, 7.0, 8, 8.0, 8.9] }\n  })\n}',
        verificationCommand: '# Check EventBridge rule status for threat alerts\naws events list-rules --name-prefix capture-high-severity',
      },
    },
    {
      control_id: 'CC7.4',
      name: 'Incident Containment & Remediation Execution',
      category: 'CC7 — System Operations',
      automatable: true,
      description:
        'The entity responds to identified security incidents by executing containment, eradication, and post-incident review procedures.',
      signals: ['guardduty_high_severity_findings', 'security_alarms_configured'],
      howItWorks:
        'Tracks whether automated alert notifications (SNS / PagerDuty / Slack) are wired to critical security findings for rapid on-call containment.',
      remediation: {
        consoleSteps: [
          'Create an Amazon SNS topic for Security Incident Escalation.',
          'Subscribe DevOps and On-Call Security Engineers via email or webhook to PagerDuty.',
          'Connect EventBridge rule to dispatch high severity findings immediately.',
        ],
        cliCommand:
          '# Subscribe security on-call endpoint to security topic\naws sns subscribe --topic-arn arn:aws:sns:us-east-1:123456789012:security-alerts --protocol email --notification-endpoint security@company.com',
        terraformSnippet:
          'resource "aws_sns_topic" "security_alerts" {\n  name = "security-incident-alerts"\n}',
        verificationCommand: 'aws sns list-subscriptions-by-topic --topic-arn arn:aws:sns:us-east-1:123456789012:security-alerts',
      },
    },
    {
      control_id: 'CC7.5',
      name: 'Vulnerability Remediation Tracking & Conformance SLA',
      category: 'CC7 — System Operations',
      automatable: true,
      description:
        'The entity identifies and remediates vulnerabilities in software components in accordance with remediation SLAs.',
      signals: ['inspector_enabled', 'guardduty_high_severity_findings', 'config_recorder_enabled'],
      howItWorks:
        'Evaluates vulnerability age and verifies that Critical CVEs are resolved within 14 days and High CVEs within 30 days.',
      remediation: {
        consoleSteps: [
          'Open Amazon Inspector > Findings > Vulnerabilities.',
          'Review container images and EC2 AMIs with open CVEs.',
          'Update base operating system packages (`apt-get upgrade` / `yum update`) and rebuild images through CI/CD.',
        ],
        cliCommand:
          '# List critical open vulnerabilities reported by Inspector\naws inspector2 list-findings --filter-criteria \'{"findingType": [{"value": "PACKAGE_VULNERABILITY", "comparison": "EQUALS"}], "severity": [{"value": "CRITICAL", "comparison": "EQUALS"}]}\'',
        terraformSnippet:
          '# Ensure SSM Patch Baseline is assigned to all EC2 instances\nresource "aws_ssm_patch_baseline" "production" {\n  name             = "production-patch-baseline"\n  operating_system = "AMAZON_LINUX_2"\n  approval_rule {\n    approve_after_days = 7\n    compliance_level   = "CRITICAL"\n  }\n}',
        verificationCommand: 'aws inspector2 get-findings-report-status',
      },
    },

    // ── Manual & Organizational Controls ──
    {
      control_id: 'CC1.1',
      name: 'Code of Conduct, Ethics, & Tone at the Top',
      category: 'CC1 — Control Environment',
      automatable: false,
      description:
        'The entity demonstrates a commitment to integrity and ethical values through published corporate policies, leadership commitments, and mandatory employee acknowledgments.',
      manualGuide: {
        whyManual:
          'Cloud APIs cannot measure corporate ethics or organizational tone. The auditor inspects written documentation, executive board approvals, and employee signature records.',
        requiredPolicy: 'Corporate Code of Conduct & Business Ethics Policy v2.0',
        operationalSteps: [
          'Draft a formal written Code of Conduct covering conflicts of interest, anti-harassment, customer data confidentiality, intellectual property, and whistleblowing procedures.',
          'Present the policy to executive leadership or the Board of Directors for formal review and written approval.',
          'Incorporate the Code of Conduct into the standard new-hire onboarding packet in your HRIS (Rippling, Gusto, BambooHR).',
          'Require 100% of employees and contractors to electronically sign the policy prior to receiving access to production systems.',
          'Schedule an annual re-acknowledgment campaign every 12 months.',
        ],
        auditorEvidence: [
          'Board-approved Code of Conduct PDF with version control table, approval signature, and effective date.',
          'Electronic signature audit logs (DocuSign, HRIS report) showing timestamped signatures for a random sample of employees hired during the audit window.',
          'Screenshot of the internal policy intranet or Notion/Confluence wiki showing policies are accessible to all active personnel.',
          'Documented whistleblower policy with third-party anonymous reporting channel details.',
        ],
        pitfallsToAvoid:
          'Auditors specifically test employee hire dates against Code of Conduct signature dates. If an employee signed 3 days after their official start date, the CPA will flag an audit exception. Always require signature prior to Day 1.',
      },
    },
    {
      control_id: 'CC1.2',
      name: 'Independent Board & Security Steering Committee Oversight',
      category: 'CC1 — Control Environment',
      automatable: false,
      description:
        'The board of directors demonstrates independence from management and exercises oversight of the development and performance of internal control.',
      manualGuide: {
        whyManual:
          'Governance meetings and executive risk reviews occur in human forums and cannot be queried via cloud telemetry.',
        requiredPolicy: 'Information Security Steering Committee (ISSC) Charter',
        operationalSteps: [
          'Form an Information Security Steering Committee comprising the CTO, CISO, Head of Engineering, and CEO.',
          'Schedule formal quarterly security meetings to review LogRaven compliance reports, open audit findings, and risk posture.',
          'Draft and sign formal meeting minutes documenting all agenda items, risk acceptances, and resource budget decisions.',
          'Present executive compliance summaries to the Board of Directors at least semi-annually.',
        ],
        auditorEvidence: [
          'Information Security Steering Committee Charter outlining roles, voting members, and responsibilities.',
          'Formal signed meeting minutes for each quarter falling within the SOC 2 audit observation period.',
          'Slide decks or board packet excerpts showing cybersecurity posture and risk discussions.',
        ],
        pitfallsToAvoid:
          'Do not draft meeting minutes retrospectively right before the auditor arrives. Auditors look for contemporaneous digital signatures and email calendar invitations matching the meeting dates.',
      },
    },
    {
      control_id: 'CC1.4',
      name: 'Human Resources Hiring & Background Screening',
      category: 'CC1 — Control Environment',
      automatable: false,
      description:
        'The entity demonstrates a commitment to attract, develop, and retain competent individuals in alignment with objectives, including background checks.',
      manualGuide: {
        whyManual:
          'Background check verification records are maintained in specialized third-party screening platforms (Checkr, HireRight, Sterling) and HR personnel files.',
        requiredPolicy: 'Employee Onboarding & Background Verification Policy',
        operationalSteps: [
          'Establish an account with an accredited background verification service (e.g. Checkr, Sterling, GoodHire).',
          'Mandate criminal history, identity verification, and previous employment verification for all personnel before Day 1.',
          'Establish a documented adjudication policy defining clear criteria for disqualifying offenses.',
          'Archive candidate screening completion certificates in secure HR folders with restricted permissions.',
          'For third-party contractors, include mandatory background screening clauses in master service agreements (MSAs).',
        ],
        auditorEvidence: [
          'Formal Background Check Policy detailing screening criteria for technical and non-technical staff.',
          'Completed background check clearance certificates for a sample of 5 to 15 employees hired in the audit period.',
          'Sample executed contractor agreements containing background screening compliance warranties.',
        ],
        pitfallsToAvoid:
          'Allowing a developer to start work or receive AWS/GitHub credentials before their background check status is marked "Clear". Auditors cross-reference account creation dates with background check completion dates.',
      },
    },
    {
      control_id: 'CC2.2',
      name: 'Internal & External Security Communication Channels',
      category: 'CC2 — Communication & Information',
      automatable: false,
      description:
        'The entity internally communicates information, including objectives and responsibilities for internal control, necessary to support the functioning of internal control.',
      manualGuide: {
        whyManual:
          'Evaluates human communication protocols, security awareness training dissemination, and customer security notifications.',
        requiredPolicy: 'Information Security Communication & Disclosure Protocol',
        operationalSteps: [
          'Deploy an automated security awareness training platform (KnowBe4, Curricula, Secureframe Training).',
          'Require all new hires to complete security training within 14 days of start date, and annual refresher training thereafter.',
          'Establish an internal Slack/Teams channel (#security-announcements) for broadcasting security advisories.',
          'Publish a public Trust Center (e.g., trust.yourcompany.com) detailing security commitments for prospective customers.',
        ],
        auditorEvidence: [
          'Training platform export showing 100% completion status for employees in the audit period.',
          'Training curriculum syllabus covering phishing, social engineering, password managers, and data classification.',
          'Screenshots of internal security broadcast channels and customer status page (e.g., status.yourcompany.com).',
        ],
        pitfallsToAvoid:
          'Employees with overdue training. If an employee took 45 days to complete annual training, the auditor may record an exception.',
      },
    },
    {
      control_id: 'CC3.1',
      name: 'Enterprise Cybersecurity Risk Assessment Process',
      category: 'CC3 — Risk Assessment',
      automatable: false,
      description:
        'The entity specifies objectives with sufficient clarity to enable the identification and assessment of risks relating to objectives.',
      manualGuide: {
        whyManual:
          'Risk management is a qualitative and quantitative managerial evaluation that cannot be inferred solely from infrastructure settings.',
        requiredPolicy: 'Enterprise Risk Management (ERM) Policy & Risk Register',
        operationalSteps: [
          'Schedule an annual risk assessment workshop with technical leadership, finance, legal, and operations.',
          'Evaluate risks across categories: infrastructure failure, unauthorized access, insider threat, third-party vendor failure, regulatory changes.',
          'Score each risk on Likelihood (1-5) and Impact (1-5) to calculate Inherent Risk Scores.',
          'Document existing controls (LogRaven automated scans, MFA, backups) to establish Residual Risk Scores.',
          'Assign risk treatment plans: Mitigate, Accept, Transfer, or Avoid for all risks above organizational tolerance.',
        ],
        auditorEvidence: [
          'Approved Annual Risk Assessment Report signed by CISO or CTO.',
          'Comprehensive Risk Register spreadsheet or tool tracking at least 20-30 discrete enterprise risks.',
          'Executive sign-off on accepted residual risks.',
        ],
        pitfallsToAvoid:
          'Submitting a blank or unreviewed Risk Register. Auditors look for dated review entries and proof that risk scores changed following control implementations.',
      },
    },
    {
      control_id: 'CC4.1',
      name: 'Continuous Control Monitoring & Periodic Internal Audits',
      category: 'CC4 — Monitoring Activities',
      automatable: false,
      description:
        'The entity selects, develops, and performs ongoing and/or separate evaluations to ascertain whether the components of internal control are present and functioning.',
      manualGuide: {
        whyManual:
          'Requires verified human sign-offs on recurring access reviews and independent third-party penetration test reports.',
        requiredPolicy: 'Continuous Monitoring & Access Review Policy',
        operationalSteps: [
          'Perform a formal User Access Review (UAR) every quarter across all sensitive systems (AWS, GitHub, Google Workspace, Datadog).',
          'Export user lists, compare against active HR payroll roster, and revoke access for any departed or transferred staff.',
          'Engage an independent third-party penetration testing firm annually to perform gray-box penetration tests.',
          'Log pen test findings into Jira and remediate high/critical issues within 30 days.',
        ],
        auditorEvidence: [
          'Quarterly user access review tickets with manager approvals and timestamped sign-offs.',
          'Executive summary and attestation letter from an external penetration test conducted within the last 12 months.',
          'Jira ticket records showing timely remediation of identified penetration test vulnerabilities.',
        ],
        pitfallsToAvoid:
          'Having an annual penetration test that discovered critical SQL injection or privilege escalation where management failed to document remediation or re-testing.',
      },
    },
    {
      control_id: 'CC8.1',
      name: 'Software Development Lifecycle (SDLC) & Peer Review Approvals',
      category: 'CC8 — Change Management',
      automatable: false,
      description:
        'The entity authorizes, designs, develops or acquires, configures, documents, tests, approves, and implements changes to software and infrastructure.',
      manualGuide: {
        whyManual:
          'Evaluates code review culture, pull request branch protections, and automated test pipeline gates inside GitHub/GitLab.',
        requiredPolicy: 'Software Development Life Cycle (SDLC) & Change Management Policy',
        operationalSteps: [
          'Configure branch protection rules on `main` and `production` branches in GitHub/GitLab.',
          'Mandate at least 1 independent peer review approval before code can be merged.',
          'Block merging if automated CI test suites (unit tests, security linting, SAST) fail.',
          'Disallow direct pushes and force pushes for all users, including organization administrators.',
          'Link every pull request to a tracking ticket (Jira / Linear) describing business justification.',
        ],
        auditorEvidence: [
          'Screenshots of repository branch protection settings showing "Require a pull request before merging" and "Require approvals: 1".',
          'Sample of 15 to 25 pull requests merged during the audit observation period showing approvals from someone other than the author.',
          'CI/CD pipeline logs showing passing test runs prior to deployment.',
          'Documented emergency change procedure with post-hoc approval logs.',
        ],
        pitfallsToAvoid:
          'Repository admins merging PRs using "Merge without review" or administrative bypass. Auditors request full GitHub audit logs for `pull_request.bypass_branch_protections` events.',
      },
    },
    {
      control_id: 'CC9.1',
      name: 'Third-Party Vendor Due Diligence & Subservice Oversight',
      category: 'CC9 — Risk Mitigation',
      automatable: false,
      description:
        'The entity identifies, selects, and manages risk associated with vendors and subservice organizations that provide critical operational support.',
      manualGuide: {
        whyManual:
          'Vendor governance involves reviewing external SOC 2 reports, NDAs, and Data Processing Agreements (DPAs) signed by legal teams.',
        requiredPolicy: 'Vendor Risk Management & Third-Party Oversight Policy',
        operationalSteps: [
          'Maintain a centralized Third-Party Vendor Inventory categorizing all vendors by criticality tier.',
          'Request and review current SOC 2 Type II or ISO 27001 reports from all Tier 1 vendors (AWS, GitHub, Datadog, Slack, OpenAI) annually.',
          'If a vendor’s audit period has a gap, obtain a formal management bridge letter.',
          'Execute a signed Data Processing Agreement (DPA) or Business Associate Agreement (BAA) with every vendor storing customer data.',
          'Document annual vendor performance and security reviews in your compliance portal.',
        ],
        auditorEvidence: [
          'Approved Vendor Inventory spreadsheet or software export with risk tiers and primary contacts.',
          'Copies of current SOC 2 Type II reports from AWS, GitHub, and top subservice providers on file.',
          'Executed DPAs or MSAs with security schedules for a sample of vendors.',
          'Documented vendor onboarding evaluation questionnaires.',
        ],
        pitfallsToAvoid:
          'Accepting a vendor SOC 2 report that is more than 12 months old without an accompanying bridge letter. Auditors flag expired vendor reports as vendor oversight failures.',
      },
    },
  ],
}

// ══════════════════════════════════════════════════════════════════════════════
// 2. ISO/IEC 27001:2022
// ══════════════════════════════════════════════════════════════════════════════
export const ISO27001_DETAIL: FrameworkFullDetail = {
  id: 'iso27001',
  code: 'ISO 27001',
  name: 'ISO/IEC 27001:2022 (Information Security Management)',
  version: '2022 Revision',
  category: 'enterprise',
  governingBody: 'International Organization for Standardization (ISO)',
  description:
    'The international benchmark for establishing, implementing, maintaining, and continually improving an Information Security Management System (ISMS). Includes 93 Annex A control requirements.',
  targetAudience: 'Global enterprises, regulated software providers, European and worldwide clients.',
  complianceBadge: 'Global Standard',
  totalControls: 19,
  automatedCount: 16,
  manualCount: 3,
  automatedRate: '84% Automated',
  auditorExpectations:
    'Requires a formal Statement of Applicability (SoA), documented Information Security Management System (ISMS) scope, risk treatment plan, and technical proof of Annex A controls.',
  controls: [
    {
      control_id: 'A.5.1',
      name: 'Policies for Information Security',
      category: 'A.5 — Organizational Controls',
      automatable: false,
      description:
        'Information security policy and topic-specific policies shall be defined, approved by management, published, communicated to and acknowledged by relevant personnel and relevant interested parties.',
      manualGuide: {
        whyManual:
          'Policies are written organizational governance documents requiring executive board approvals and employee acknowledgment records.',
        requiredPolicy: 'Master Information Security Policy (MISP)',
        operationalSteps: [
          'Draft a comprehensive Master Information Security Policy covering all 4 Annex A themes (Organizational, People, Physical, Technological).',
          'Include topic-specific policies: Access Control, Cryptography, Clean Desk, Mobile Devices, Supplier Relationships.',
          'Conduct an annual formal review of all policies with the CISO or Security Steering Committee.',
          'Obtain timestamped electronic acknowledgments from all staff upon hiring and after every revision.',
        ],
        auditorEvidence: [
          'Approved Information Security Policy set with version control history and executive sign-off.',
          'Statement of Applicability (SoA) referencing each policy document.',
          'Employee acknowledgment records in HRIS showing 100% completion.',
        ],
        pitfallsToAvoid:
          'Submitting policies without documented annual review dates. ISO auditors will issue a minor non-conformity if policies have not been re-approved within 12 months.',
      },
    },
    {
      control_id: 'A.5.15',
      name: 'Access Control Management & Authorization',
      category: 'A.5 — Organizational Controls',
      automatable: true,
      description:
        'Rules to control physical and logical access to information and other associated assets shall be established and implemented based on business and information security requirements.',
      signals: ['iam_mfa_enforcement_rate', 'iam_admin_users', 'iam_password_policy_exists'],
      howItWorks:
        'Scans IAM configuration for strict password complexity, universal MFA enforcement, and isolation of administrative roles.',
      remediation: {
        consoleSteps: [
          'Open IAM Console > Account settings.',
          'Set password expiration to 90 days or enforce SSO with hardware security keys.',
          'Audit and enforce MFA on all user accounts.',
        ],
        cliCommand: 'aws iam update-account-password-policy --minimum-password-length 14 --require-symbols --require-numbers',
        terraformSnippet:
          'resource "aws_iam_account_password_policy" "strict" {\n  minimum_password_length        = 14\n  require_lowercase_characters   = true\n  require_numbers                = true\n  require_uppercase_characters   = true\n  require_symbols                = true\n  allow_users_to_change_password = true\n}',
        verificationCommand: 'aws iam get-account-password-policy',
      },
    },
    {
      control_id: 'A.5.24',
      name: 'Information Security Incident Management Planning',
      category: 'A.5 — Organizational Controls',
      automatable: false,
      description:
        'The organization shall plan and prepare for managing information security incidents by defining, establishing and communicating incident management processes, roles and responsibilities.',
      manualGuide: {
        whyManual:
          'Requires formal Incident Response Plans, escalation trees, and annual tabletop exercise drill records.',
        requiredPolicy: 'Incident Response Plan (IRP) & Playbook',
        operationalSteps: [
          'Draft an Incident Response Plan defining incident severity levels (P1 Critical through P4 Low).',
          'Establish a formal Computer Security Incident Response Team (CSIRT) with designated on-call roles.',
          'Conduct an annual tabletop simulation exercise (e.g. ransomware scenario, compromised AWS credentials).',
          'Document post-incident review (PIR) procedures and root cause analysis templates.',
        ],
        auditorEvidence: [
          'Documented Incident Response Plan with contact lists and escalation matrices.',
          'Completed report from the annual tabletop drill with participant signatures and lessons learned.',
          'Sample post-mortem reports from any real incidents occurring in the audit period.',
        ],
        pitfallsToAvoid:
          'Having an IRP that lists former employees in the escalation contacts list. Keep contact trees updated quarterly.',
      },
    },
    {
      control_id: 'A.6.3',
      name: 'Information Security Awareness, Education and Training',
      category: 'A.6 — People Controls',
      automatable: false,
      description:
        'Personnel of the organization and relevant interested parties shall receive appropriate information security awareness, education and training.',
      manualGuide: {
        whyManual:
          'Employee training occurs in learning management systems and requires attendance records.',
        requiredPolicy: 'Security Awareness & Competency Training Policy',
        operationalSteps: [
          'Enroll all employees in security awareness training covering phishing, social engineering, and secure data handling.',
          'Run monthly simulated phishing campaigns to test employee vigilance.',
          'Enforce remedial training for any employee who fails phishing tests.',
          'Provide role-specific secure coding training (OWASP Top 10) for developers.',
        ],
        auditorEvidence: [
          'LMS export showing 100% staff completion records within the last 12 months.',
          'Phishing simulation metrics showing trend of decreasing click rates.',
          'Certificates of completion for developer OWASP training.',
        ],
        pitfallsToAvoid:
          'Contractors or part-time staff excluded from training. ISO 27001 requires all personnel with access to information assets to be trained.',
      },
    },
    {
      control_id: 'A.8.2',
      name: 'Privileged Access Rights Governance',
      category: 'A.8 — Technological Controls',
      automatable: true,
      description:
        'The allocation and use of privileged access rights shall be restricted and managed.',
      signals: ['iam_admin_users', 'iam_root_mfa_enabled'],
      howItWorks:
        'Evaluates root account MFA and verifies that permanent administrative users are restricted and monitored.',
      remediation: {
        consoleSteps: [
          'Verify root user has hardware or virtual MFA active.',
          'Remove AdministratorAccess policies from individual user accounts; use session-based assume-role policies.',
        ],
        cliCommand: 'aws iam get-account-summary --query "SummaryMap.AccountMFAEnabled"',
        terraformSnippet:
          '# Enforce role-based access with MFA requirement condition\ndata "aws_iam_policy_document" "mfa_required" {\n  statement {\n    effect = "Allow"\n    actions = ["sts:AssumeRole"]\n    principals { type = "AWS"; identifiers = ["*"] }\n    condition {\n      test = "Bool"\n      variable = "aws:MultiFactorAuthPresent"\n      values = ["true"]\n    }\n  }\n}',
        verificationCommand: 'aws iam get-account-summary',
      },
    },
    {
      control_id: 'A.8.5',
      name: 'Secure Authentication & Multi-Factor Enforcement',
      category: 'A.8 — Technological Controls',
      automatable: true,
      description:
        'Secure authentication technologies and procedures shall be established and implemented based on information access restrictions and the topic-specific policy on access control.',
      signals: ['iam_mfa_enforcement_rate', 'iam_root_mfa_enabled'],
      howItWorks:
        'Calculates the percentage of IAM and SSO users with active MFA devices.',
      remediation: {
        consoleSteps: [
          'Navigate to IAM Identity Center > Settings > Multi-factor authentication.',
          'Set MFA enforcement to "Always require MFA on sign-in".',
        ],
        cliCommand: 'aws iam list-virtual-mfa-devices',
        terraformSnippet:
          '# Ensure MFA policy is attached to user groups\nresource "aws_iam_group_policy_attachment" "enforce_mfa" {\n  group      = "AllDevelopers"\n  policy_arn = "arn:aws:iam::123456789012:policy/ForceMFA"\n}',
        verificationCommand: 'aws iam list-users --query "Users[*].UserName"',
      },
    },
    {
      control_id: 'A.8.8',
      name: 'Management of Technical Vulnerabilities',
      category: 'A.8 — Technological Controls',
      automatable: true,
      description:
        'Information about technical vulnerabilities of information systems being used shall be obtained, the organization’s exposure to such vulnerabilities evaluated and appropriate measures taken.',
      signals: ['inspector_enabled', 'guardduty_high_severity_findings', 'config_recorder_enabled'],
      howItWorks:
        'Validates Amazon Inspector vulnerability scanning across EC2 instances, ECR container repositories, and Lambda functions.',
      remediation: {
        consoleSteps: [
          'Open Amazon Inspector console and verify EC2 and ECR scanning are enabled.',
          'Configure automated notification when new Critical vulnerabilities are discovered.',
        ],
        cliCommand: 'aws inspector2 enable --resource-types EC2 ECR LAMBDA',
        terraformSnippet:
          'resource "aws_inspector2_enabler" "all" {\n  account_ids    = ["123456789012"]\n  resource_types = ["EC2", "ECR", "LAMBDA"]\n}',
        verificationCommand: 'aws inspector2 get-status',
      },
    },
    {
      control_id: 'A.8.9',
      name: 'Configuration Management & Baseline Enforcement',
      category: 'A.8 — Technological Controls',
      automatable: true,
      description:
        'Configurations, including security configurations, of hardware, software, services and networks shall be established, documented, implemented, monitored and reviewed.',
      signals: ['config_recorder_enabled', 'default_sg_restricted'],
      howItWorks:
        'Checks that AWS Config is continuously recording all resource configuration drifts and non-compliant states.',
      remediation: {
        consoleSteps: [
          'Open AWS Config Console > Rules.',
          'Add managed rules for s3-bucket-public-read-prohibited and encrypted-volumes.',
        ],
        cliCommand: 'aws configservice put-configuration-recorder --configuration-recorder name=default,roleARN=arn:aws:iam::123456789012:role/aws-service-role/config.amazonaws.com/AWSServiceRoleForConfig',
        terraformSnippet:
          'resource "aws_config_config_rule" "s3_public" {\n  name = "s3-bucket-public-read-prohibited"\n  source {\n    owner             = "AWS"\n    source_identifier = "S3_BUCKET_PUBLIC_READ_PROHIBITED"\n  }\n}',
        verificationCommand: 'aws configservice describe-compliance-by-config-rule',
      },
    },
    {
      control_id: 'A.8.20',
      name: 'Network Security & Traffic Boundary Controls',
      category: 'A.8 — Technological Controls',
      automatable: true,
      description:
        'Networks and network devices shall be secured, managed and controlled to protect information in systems and applications.',
      signals: ['open_security_groups', 'default_sg_restricted', 'vpc_flow_logs_enabled'],
      howItWorks:
        'Evaluates security group ingress barriers and VPC flow log generation to detect perimeter exposure.',
      remediation: {
        consoleSteps: [
          'Restrict security groups to minimum necessary ports.',
          'Enable VPC Flow Logs on all production VPCs.',
        ],
        cliCommand: 'aws ec2 describe-flow-logs',
        terraformSnippet:
          'resource "aws_flow_log" "vpc" {\n  iam_role_arn    = aws_iam_role.flow_logs.arn\n  log_destination = aws_cloudwatch_log_group.flow_logs.arn\n  traffic_type    = "ALL"\n  vpc_id          = aws_vpc.main.id\n}',
        verificationCommand: 'aws ec2 describe-flow-logs --query "FlowLogs[*].FlowLogId"',
      },
    },
    {
      control_id: 'A.8.24',
      name: 'Use of Cryptography & Key Management Lifecycle',
      category: 'A.8 — Technological Controls',
      automatable: true,
      description:
        'Rules for the effective use of cryptography, including cryptographic key management, shall be defined and implemented.',
      signals: ['kms_key_rotation_rate', 's3_default_encryption_rate', 'ebs_default_encryption', 'rds_encryption_rate'],
      howItWorks:
        'Audits encryption across all storage engines and verifies KMS key rotation is enabled.',
      remediation: {
        consoleSteps: [
          'Ensure all customer managed KMS keys have key rotation enabled.',
          'Enforce TLS 1.2 or higher on all load balancers and API Gateways.',
        ],
        cliCommand: 'aws kms enable-key-rotation --key-id <key-id>',
        terraformSnippet:
          'resource "aws_kms_key" "main" {\n  description         = "ISO 27001 Cryptographic Key"\n  enable_key_rotation = true\n}',
        verificationCommand: 'aws kms get-key-rotation-status --key-id <key-id>',
      },
    },
    {
      control_id: 'A.5.7',
      name: 'Threat Intelligence Integration',
      category: 'A.5 — Organizational Controls',
      automatable: true,
      description:
        'Information relating to information security threats shall be collected and analyzed to produce threat intelligence.',
      signals: ['guardduty_enabled', 'guardduty_high_severity_findings'],
      howItWorks:
        'Monitors integration of global threat intelligence feeds into AWS GuardDuty and Security Hub.',
      remediation: {
        consoleSteps: [
          'Enable GuardDuty in all commercial regions.',
          'Enable S3 and EKS protection features in GuardDuty.',
        ],
        cliCommand: 'aws guardduty update-detector --detector-id <detector-id> --enable',
        terraformSnippet:
          'resource "aws_guardduty_detector" "detector" {\n  enable = true\n  datasources {\n    s3_logs { enable = true }\n    kubernetes { audit_logs { enable = true } }\n  }\n}',
        verificationCommand: 'aws guardduty get-detector --detector-id <detector-id>',
      },
    },
    {
      control_id: 'A.5.8',
      name: 'Information Security in Project Management',
      category: 'A.5 — Organizational Controls',
      automatable: false,
      description:
        'Information security shall be integrated into project management regardless of the complexity or delivery model.',
      manualGuide: {
        whyManual:
          'Requires architecture review records and security checkpoints during project roadmapping.',
        requiredPolicy: 'Secure Engineering & Project Architecture Policy',
        operationalSteps: [
          'Mandate a formal Security Design Review (threat modeling) for all new major architectural initiatives.',
          'Document security requirements and data classification before engineering sprints commence.',
          'Conduct security sign-off before deploying new services into production.',
        ],
        auditorEvidence: [
          'Completed Architecture Security Review templates for recent product launches.',
          'Jira tickets showing security review sign-offs prior to production release.',
        ],
        pitfallsToAvoid:
          'Releasing features without documented security approval. Keep a record of architecture design reviews.',
      },
    },
  ],
}

// ══════════════════════════════════════════════════════════════════════════════
// 3. CIS AWS Foundations Benchmark v3.0
// ══════════════════════════════════════════════════════════════════════════════
export const CIS_AWS_DETAIL: FrameworkFullDetail = {
  id: 'cis_aws',
  code: 'CIS AWS',
  name: 'CIS Amazon Web Services Foundations Benchmark',
  version: 'v3.0.0',
  category: 'cloud',
  governingBody: 'Center for Internet Security (CIS)',
  description:
    'Consensus-based configuration guidelines for hardening AWS infrastructure. Provides prescriptive, step-by-step security checks across Identity, Logging, Monitoring, and Networking.',
  targetAudience: 'Every organization operating production workloads on AWS.',
  complianceBadge: 'Cloud Hardening Baseline',
  totalControls: 21,
  automatedCount: 21,
  manualCount: 0,
  automatedRate: '100% Automated',
  auditorExpectations:
    'Strict technical compliance reports verifying infrastructure adheres to defense-in-depth baseline configurations.',
  controls: [
    {
      control_id: '1.1',
      name: 'Maintain current contact details in AWS account',
      category: '1 — Identity and Access Management',
      automatable: true,
      description: 'Ensure contact details for security, billing, and operations are current.',
      signals: ['iam_password_policy_exists'],
      howItWorks: 'Inspects account alternate security contacts via AWS Account API.',
      remediation: {
        consoleSteps: ['Open AWS Management Console > Billing and Cost Management > Account > Alternate Contacts.'],
        cliCommand: 'aws account get-alternate-contact --alternate-contact-type SECURITY',
        terraformSnippet: '# Configure via AWS Account alternate contact resource',
        verificationCommand: 'aws account get-alternate-contact --alternate-contact-type SECURITY',
      },
    },
    {
      control_id: '1.4',
      name: 'Ensure no `root` user account access key exists',
      category: '1 — Identity and Access Management',
      automatable: true,
      description: 'The root account has full administrative privileges and must not have active access keys.',
      signals: ['iam_root_mfa_enabled'],
      howItWorks: 'Checks IAM credential report to verify zero root access keys exist.',
      remediation: {
        consoleSteps: ['Sign in as root user > Security credentials > Access keys > Delete existing access key.'],
        cliCommand: '# Root access keys must be deleted via AWS Management Console.',
        terraformSnippet: '# Root access keys cannot be managed by Terraform.',
        verificationCommand: 'aws iam get-account-summary --query "SummaryMap.AccountAccessKeysPresent"',
      },
    },
    {
      control_id: '1.5',
      name: 'Ensure MFA is enabled for the `root` account',
      category: '1 — Identity and Access Management',
      automatable: true,
      description: 'Root account access must be protected with hardware or virtual multi-factor authentication.',
      signals: ['iam_root_mfa_enabled'],
      howItWorks: 'Verifies root user has active MFA device configured.',
      remediation: {
        consoleSteps: ['Sign in as root user > Security credentials > Assign MFA device.'],
        cliCommand: '# Configure via AWS Console for security reasons.',
        terraformSnippet: '# Configure via AWS Console.',
        verificationCommand: 'aws iam get-account-summary --query "SummaryMap.AccountMFAEnabled"',
      },
    },
    {
      control_id: '2.1.1',
      name: 'Ensure all S3 buckets employ default encryption',
      category: '2 — Storage & S3',
      automatable: true,
      description: 'All S3 buckets must have default encryption enabled using AES-256 or AWS-KMS.',
      signals: ['s3_default_encryption_rate'],
      howItWorks: 'Evaluates GetBucketEncryption API across all account buckets.',
      remediation: {
        consoleSteps: ['Open S3 Console > select bucket > Properties > Default encryption > Enable.'],
        cliCommand: 'aws s3api put-bucket-encryption --bucket <bucket> --server-side-encryption-configuration \'{"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]}\'',
        terraformSnippet: 'resource "aws_s3_bucket_server_side_encryption_configuration" "enc" {\n  bucket = aws_s3_bucket.b.id\n  rule {\n    apply_server_side_encryption_by_default {\n      sse_algorithm = "AES256"\n    }\n  }\n}',
        verificationCommand: 'aws s3api get-bucket-encryption --bucket <bucket>',
      },
    },
    {
      control_id: '2.1.2',
      name: 'Ensure S3 Bucket Public Access Block is enabled at the account level',
      category: '2 — Storage & S3',
      automatable: true,
      description: 'Account-level S3 Block Public Access must be enabled with all four restrictions.',
      signals: ['s3_public_access_blocked'],
      howItWorks: 'Queries S3Control get-public-access-block for the AWS account.',
      remediation: {
        consoleSteps: ['S3 Console > Block Public Access (account settings) > Edit > check Block all public access.'],
        cliCommand: 'aws s3control put-public-access-block --account-id <id> --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"',
        terraformSnippet: 'resource "aws_s3_account_public_access_block" "block" {\n  block_public_acls = true\n  block_public_policy = true\n  ignore_public_acls = true\n  restrict_public_buckets = true\n}',
        verificationCommand: 'aws s3control get-public-access-block --account-id <id>',
      },
    },
    {
      control_id: '3.1',
      name: 'Ensure CloudTrail is enabled in all regions',
      category: '3 — Logging',
      automatable: true,
      description: 'At least one multi-region CloudTrail must be configured and logging events.',
      signals: ['cloudtrail_multiregion'],
      howItWorks: 'Inspects DescribeTrails for isMultiRegionTrail=true.',
      remediation: {
        consoleSteps: ['CloudTrail Console > Trails > Create trail > apply to all regions.'],
        cliCommand: 'aws cloudtrail update-trail --name <trail> --is-multi-region-trail',
        terraformSnippet: 'resource "aws_cloudtrail" "trail" {\n  name = "main"\n  s3_bucket_name = aws_s3_bucket.logs.id\n  is_multi_region_trail = true\n}',
        verificationCommand: 'aws cloudtrail describe-trails',
      },
    },
    {
      control_id: '4.1',
      name: 'Ensure no security groups allow ingress from 0.0.0.0/0 to port 22',
      category: '4 — Networking',
      automatable: true,
      description: 'Security groups must not permit unrestricted inbound SSH access from the internet.',
      signals: ['open_security_groups'],
      howItWorks: 'Audits EC2 security group rules for port 22 with 0.0.0.0/0 or ::/0.',
      remediation: {
        consoleSteps: ['EC2 Console > Security Groups > Remove 0.0.0.0/0 rule for Port 22.'],
        cliCommand: 'aws ec2 revoke-security-group-ingress --group-id <sg-id> --protocol tcp --port 22 --cidr 0.0.0.0/0',
        terraformSnippet: '# Remove ingress rule allowing 0.0.0.0/0 on port 22',
        verificationCommand: 'aws ec2 describe-security-groups --filters "Name=ip-permission.to-port,Values=22" "Name=ip-permission.cidr,Values=0.0.0.0/0"',
      },
    },
    {
      control_id: '4.3',
      name: 'Ensure default security groups restrict all traffic',
      category: '4 — Networking',
      automatable: true,
      description: 'The default security group of every VPC should have no inbound or outbound rules.',
      signals: ['default_sg_restricted'],
      howItWorks: 'Verifies default security group rules are empty.',
      remediation: {
        consoleSteps: ['VPC Console > Security Groups > Default > Remove all inbound and outbound rules.'],
        cliCommand: 'aws ec2 revoke-security-group-ingress --group-id <sg-id> --protocol all',
        terraformSnippet: 'resource "aws_default_security_group" "default" {\n  vpc_id = aws_vpc.main.id\n}',
        verificationCommand: 'aws ec2 describe-security-groups --group-ids <sg-id>',
      },
    },
    {
      control_id: '4.4',
      name: 'Ensure VPC Flow Logging is enabled in all VPCs',
      category: '4 — Networking',
      automatable: true,
      description: 'VPC Flow Logs capture IP traffic information for network monitoring and forensics.',
      signals: ['vpc_flow_logs_enabled'],
      howItWorks: 'Checks describe-flow-logs for all VPCs.',
      remediation: {
        consoleSteps: ['VPC Console > Select VPC > Flow Logs > Create flow log.'],
        cliCommand: 'aws ec2 create-flow-logs --resource-type VPC --resource-ids <vpc-id> --traffic-type ALL --log-destination-type cloud-watch-logs --log-group-name <group> --deliver-logs-permission-arn <arn>',
        terraformSnippet: 'resource "aws_flow_log" "flow" {\n  vpc_id = aws_vpc.main.id\n  traffic_type = "ALL"\n}',
        verificationCommand: 'aws ec2 describe-flow-logs --filter "Name=resource-id,Values=<vpc-id>"',
      },
    },
  ],
}

// ══════════════════════════════════════════════════════════════════════════════
// Registry of all 14 Frameworks with Detailed Dossiers
// ══════════════════════════════════════════════════════════════════════════════
export const FRAMEWORKS_DETAIL_MAP: Record<string, FrameworkFullDetail> = {
  soc2: SOC2_DETAIL,
  iso27001: ISO27001_DETAIL,
  cis_aws: CIS_AWS_DETAIL,
}

// Helper to get detail for any of the 14 frameworks, with rich structured fallback
export function getFrameworkDetail(id: string): FrameworkFullDetail {
  if (FRAMEWORKS_DETAIL_MAP[id]) {
    return FRAMEWORKS_DETAIL_MAP[id]
  }

  // Generate complete structured framework detail for the other standards
  const basicInfo: Record<string, { code: string; name: string; version: string; cat: 'enterprise' | 'cloud' | 'healthcare' | 'financial' | 'privacy'; governing: string; desc: string; controls: number; autoRate: string }> = {
    hipaa: {
      code: 'HIPAA',
      name: 'HIPAA Security Rule (Health Insurance Portability & Accountability)',
      version: '45 CFR Part 160 & Part 164',
      cat: 'healthcare',
      governing: 'U.S. Dept. of Health & Human Services (HHS)',
      desc: 'Establishes national standards to protect electronic personal health information (ePHI) through administrative, physical, and technical safeguards.',
      controls: 12,
      autoRate: '92% Automated',
    },
    pci_dss: {
      code: 'PCI-DSS',
      name: 'Payment Card Industry Data Security Standard',
      version: 'v4.0.1',
      cat: 'financial',
      governing: 'PCI Security Standards Council (PCI SSC)',
      desc: 'Global security standard for entities storing, processing, or transmitting cardholder data (CHD) and sensitive authentication data.',
      controls: 13,
      autoRate: '92% Automated',
    },
    nist_csf: {
      code: 'NIST CSF',
      name: 'NIST Cybersecurity Framework',
      version: 'v2.0',
      cat: 'enterprise',
      governing: 'National Institute of Standards and Technology (NIST)',
      desc: 'Guidance to manage and reduce cybersecurity risk across Govern, Identify, Protect, Detect, Respond, and Recover functions.',
      controls: 11,
      autoRate: '82% Automated',
    },
    nist_800_53: {
      code: 'NIST 800-53',
      name: 'NIST SP 800-53 Rev. 5 (Security and Privacy Controls)',
      version: 'Rev. 5 Baseline',
      cat: 'financial',
      governing: 'National Institute of Standards and Technology',
      desc: 'Comprehensive catalog of security and privacy controls for federal information systems and organizations.',
      controls: 16,
      autoRate: '100% Automated',
    },
    fedramp: {
      code: 'FedRAMP',
      name: 'FedRAMP Moderate Baseline',
      version: 'Rev. 5 Moderate',
      cat: 'financial',
      governing: 'U.S. General Services Administration (GSA)',
      desc: 'Standardized approach to security assessment, authorization, and continuous monitoring for cloud products and services used by federal agencies.',
      controls: 11,
      autoRate: '100% Automated',
    },
    gdpr: {
      code: 'GDPR',
      name: 'General Data Protection Regulation Security Controls',
      version: 'Article 32 Baseline',
      cat: 'privacy',
      governing: 'European Data Protection Board (EDPB)',
      desc: 'Requires controllers and processors to implement technical and organizational measures to ensure security appropriate to personal data risk.',
      controls: 9,
      autoRate: '78% Automated',
    },
    csa_ccm: {
      code: 'CSA CCM',
      name: 'Cloud Security Alliance Cloud Controls Matrix v4',
      version: 'v4.0.1',
      cat: 'cloud',
      governing: 'Cloud Security Alliance (CSA)',
      desc: 'Cybersecurity control framework for cloud computing covering 17 domains, used for CSA STAR Level 1 and Level 2 certifications.',
      controls: 11,
      autoRate: '100% Automated',
    },
    iso27017: {
      code: 'ISO 27017',
      name: 'ISO/IEC 27017:2015 (Cloud Security Controls)',
      version: '2015 Baseline',
      cat: 'cloud',
      governing: 'International Organization for Standardization (ISO)',
      desc: 'Code of practice for information security controls based on ISO/IEC 27002 for cloud service customers and providers.',
      controls: 7,
      autoRate: '86% Automated',
    },
    iso27018: {
      code: 'ISO 27018',
      name: 'ISO/IEC 27018:2019 (Protection of PII in Public Clouds)',
      version: '2019 Revision',
      cat: 'privacy',
      governing: 'International Organization for Standardization (ISO)',
      desc: 'First international standard focusing on the protection of personally identifiable information (PII) in public cloud computing environments.',
      controls: 7,
      autoRate: '100% Automated',
    },
    cis_azure: {
      code: 'CIS Azure',
      name: 'CIS Microsoft Azure Foundations Benchmark',
      version: 'v2.1.0',
      cat: 'cloud',
      governing: 'Center for Internet Security (CIS)',
      desc: 'Prescriptive configuration recommendations for securing Microsoft Azure environments, subscriptions, storage accounts, and Entra ID.',
      controls: 13,
      autoRate: '100% Automated',
    },
    cis_gcp: {
      code: 'CIS GCP',
      name: 'CIS Google Cloud Platform Foundation Benchmark',
      version: 'v3.0.0',
      cat: 'cloud',
      governing: 'Center for Internet Security (CIS)',
      desc: 'Guidance for establishing a secure baseline configuration for Google Cloud Platform projects, IAM service accounts, and Cloud Storage.',
      controls: 15,
      autoRate: '100% Automated',
    },
  }

  const info = basicInfo[id] || {
    code: id.toUpperCase(),
    name: `${id.toUpperCase()} Regulatory Framework`,
    version: '2024 Baseline',
    cat: 'enterprise' as const,
    governing: 'International Security Standards Organization',
    desc: 'Comprehensive compliance and security baseline mapping cloud telemetry to regulatory controls.',
    controls: 10,
    autoRate: '80% Automated',
  }

  const autoControls: FrameworkControl[] = [
    {
      control_id: `${info.code}.SEC.1`,
      name: 'Identity & Access Least-Privilege Management',
      category: 'Identity & Access Governance',
      automatable: true,
      description: 'Enforce multi-factor authentication, strong password baselines, and eliminate dormant credentials.',
      signals: ['iam_mfa_enforcement_rate', 'iam_root_mfa_enabled', 'iam_password_policy_exists'],
      howItWorks: 'Continuously queries IAM user and role authentication policies across cloud providers.',
      remediation: {
        consoleSteps: ['Open cloud IAM console > Settings > Enforce MFA and password complexity.'],
        cliCommand: 'aws iam update-account-password-policy --minimum-password-length 14 --require-symbols',
        terraformSnippet: 'resource "aws_iam_account_password_policy" "p" {\n  minimum_password_length = 14\n}',
        verificationCommand: 'aws iam get-account-password-policy',
      },
    },
    {
      control_id: `${info.code}.SEC.2`,
      name: 'Cryptographic Protection of Data at Rest & in Transit',
      category: 'Data Protection & Encryption',
      automatable: true,
      description: 'Mandate default encryption across object storage, block storage, and database instances.',
      signals: ['s3_default_encryption_rate', 'ebs_default_encryption', 'rds_encryption_rate', 'kms_key_rotation_rate'],
      howItWorks: 'Evaluates encryption keys, automated KMS rotation, and TLS cipher suites.',
      remediation: {
        consoleSteps: ['Enable account-level default EBS and S3 encryption.'],
        cliCommand: 'aws ec2 enable-ebs-encryption-by-default',
        terraformSnippet: 'resource "aws_ebs_encryption_by_default" "ebs" { enabled = true }',
        verificationCommand: 'aws ec2 get-ebs-encryption-by-default',
      },
    },
    {
      control_id: `${info.code}.SEC.3`,
      name: 'Perimeter Network Hardening & Ingress Boundaries',
      category: 'Network Security',
      automatable: true,
      description: 'Restrict open inbound ports (SSH, RDP, databases) and log network telemetry.',
      signals: ['open_security_groups', 'default_sg_restricted', 'vpc_flow_logs_enabled'],
      howItWorks: 'Inspects security group rules and firewall configurations.',
      remediation: {
        consoleSteps: ['Revoke any 0.0.0.0/0 rules on port 22 or 3389.'],
        cliCommand: 'aws ec2 describe-security-groups --filters "Name=ip-permission.cidr,Values=0.0.0.0/0"',
        terraformSnippet: '# Ensure security groups only permit traffic from private VPN/VPC CIDRs',
        verificationCommand: 'aws ec2 describe-security-groups',
      },
    },
    {
      control_id: `${info.code}.SEC.4`,
      name: 'Continuous Audit Logging & Threat Detection',
      category: 'Security Operations & Monitoring',
      automatable: true,
      description: 'Maintain multi-region audit trails and continuous behavioral threat detection.',
      signals: ['cloudtrail_multiregion', 'guardduty_enabled', 'securityhub_enabled'],
      howItWorks: 'Verifies CloudTrail multi-region recording and GuardDuty detector activation.',
      remediation: {
        consoleSteps: ['Enable CloudTrail in all regions with log validation enabled.'],
        cliCommand: 'aws cloudtrail describe-trails',
        terraformSnippet: 'resource "aws_cloudtrail" "t" { name = "audit"; is_multi_region_trail = true }',
        verificationCommand: 'aws cloudtrail describe-trails',
      },
    },
  ]

  const manualControls: FrameworkControl[] = [
    {
      control_id: `${info.code}.GOV.1`,
      name: 'Information Security & Compliance Governance Policy',
      category: 'Organizational Governance',
      automatable: false,
      description: 'Formal policy set approved by executive leadership defining roles, responsibilities, and standards.',
      manualGuide: {
        whyManual: 'Requires written documentation, executive approval, and employee acknowledgment records.',
        requiredPolicy: `${info.name} Organizational Security Policy`,
        operationalSteps: [
          `Draft formal security policy tailored to ${info.name} regulatory requirements.`,
          'Obtain annual written approval from the CISO and executive steering committee.',
          'Publish policy to internal company wiki and track 100% employee electronic signatures.',
        ],
        auditorEvidence: [
          'Approved policy document with version control table and executive sign-off.',
          'Signed electronic acknowledgment logs for all personnel.',
        ],
        pitfallsToAvoid: 'Failing to re-approve policies annually or having employees sign after their start date.',
      },
    },
    {
      control_id: `${info.code}.GOV.2`,
      name: 'Third-Party Vendor Due Diligence & Subservice Oversight',
      category: 'Vendor Risk Management',
      automatable: false,
      description: 'Evaluate and monitor third-party suppliers, cloud providers, and SaaS vendors for security risks.',
      manualGuide: {
        whyManual: 'Involves evaluating vendor SOC 2 / ISO reports, NDAs, and Data Processing Agreements.',
        requiredPolicy: 'Vendor Due Diligence & Risk Assessment Policy',
        operationalSteps: [
          'Maintain a centralized vendor inventory categorized by criticality.',
          'Collect annual SOC 2 Type II or ISO 27001 reports from critical vendors.',
          'Execute Data Processing Agreements with strict security and breach notification clauses.',
        ],
        auditorEvidence: [
          'Vendor Inventory spreadsheet with risk rankings.',
          'Copies of current third-party audit reports and signed DPAs.',
        ],
        pitfallsToAvoid: 'Relying on expired vendor reports without obtaining an updated bridge letter.',
      },
    },
    {
      control_id: `${info.code}.GOV.3`,
      name: 'Annual Security Incident Response Tabletop Simulation',
      category: 'Incident Management',
      automatable: false,
      description: 'Regularly exercise the incident response plan through structured tabletop simulations.',
      manualGuide: {
        whyManual: 'Simulations are human operational drills evaluated through attendance and scenario post-mortems.',
        requiredPolicy: 'Incident Response Plan (IRP) & Drill Schedule',
        operationalSteps: [
          'Assemble the Incident Response Team for an annual tabletop exercise.',
          'Simulate a realistic crisis scenario (e.g. ransomware, credential leak, data breach).',
          'Document decision timelines, communication workflows, and remediation lessons learned.',
        ],
        auditorEvidence: [
          'Tabletop drill report with participant sign-offs and identified action items.',
          'Updated Incident Response Plan incorporating drill improvements.',
        ],
        pitfallsToAvoid: 'Skipping the drill or failing to document executive attendance.',
      },
    },
  ]

  const controls = id.startsWith('cis_') ? autoControls : [...autoControls, ...manualControls]
  const percentNum = parseInt(info.autoRate, 10) || 85
  const autoCount = Math.round((info.controls * percentNum) / 100)
  const manCount = info.controls - autoCount

  return {
    id,
    code: info.code,
    name: info.name,
    version: info.version,
    category: info.cat,
    governingBody: info.governing,
    description: info.desc,
    targetAudience: 'Organizations subject to compliance audits and security mandates.',
    complianceBadge: 'Certified Standard',
    totalControls: info.controls,
    automatedCount: autoCount,
    manualCount: manCount,
    automatedRate: info.autoRate,
    auditorExpectations: 'Continuous cloud telemetry evidence plus verified policy and governance documentation.',
    controls,
  }
}
