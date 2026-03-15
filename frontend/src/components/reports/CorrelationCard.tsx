// LogRaven — Correlation Card Component
//
// PURPOSE:
//   Displays a correlated finding that spans multiple log source files.
//   This is the most important LogRaven finding type.
//   Shown BEFORE individual findings in the report.
//
// LAYOUT:
//   Header: "CORRELATED FINDING" badge | Critical/High severity | source file count
//   Entity: "Entity: 185.220.101.42 (IP)" — the linking entity
//   Timeline: chronological list of events from each source file
//   ATT&CK: technique ID + name
//   Description: narrative explanation of the attack chain
//   Contributing files: badges showing each source type that contributed
//
// PROPS:
//   finding: CorrelatedFinding (includes source_files array)
//
// TODO Month 4 Week 1: Implement this component.

export default function CorrelationCard() {
  return (
    <div className="border-2 border-purple-500 rounded p-4 bg-purple-50">
      Correlation Card — Correlated Finding — TODO Month 4 Week 1
    </div>
  )
}
