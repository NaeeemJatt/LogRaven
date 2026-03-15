// LogRaven — Finding Card Component
//
// PURPOSE:
//   Displays a single LogRaven security finding.
//
// LAYOUT:
//   Top row: severity badge | MITRE technique ID (clickable link to ATT&CK) | finding_type badge
//   Title: bold, 1-2 lines
//   Description: plain English, 2-3 sentences
//   IOCs: inline tags (IP addresses, hashes, domains)
//   Remediation: italic, action-oriented
//   Source files: small badges showing which log files contributed
//
// PROPS:
//   finding: FindingSchema
//
// TODO Month 4 Week 1: Implement this component.

export default function FindingCard() {
  return <div className="border rounded p-4">Finding Card — TODO Month 4 Week 1</div>
}
