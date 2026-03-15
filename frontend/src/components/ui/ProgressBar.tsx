// LogRaven — Analysis Progress Bar
// Stepped progress bar for JobStatus page.
// Steps: Queued -> Parsing -> Rule Engine -> Correlation -> AI Analysis -> Report -> Done
// TODO Month 1 Week 3: Implement.

export default function ProgressBar({ stage }: { stage: string }) {
  return (
    <div className="w-full bg-gray-200 rounded-full h-2">
      <div className="bg-blue-600 h-2 rounded-full w-1/4 transition-all" />
    </div>
  )
}
