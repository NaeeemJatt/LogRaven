// LogRaven — PDF Download Button
//
// PURPOSE:
//   Triggers download of the lograven-report-{uuid}.pdf
//
// BEHAVIOR:
//   1. Call reports.getDownloadUrl(report_id) -> GET /api/v1/reports/{id}/download
//   2. Response: {download_url: "http://localhost:8000/files/reports/..."}
//   3. Open download_url in new tab (browser handles PDF download)
//
// TODO Month 4 Week 1: Implement.

export default function DownloadButton({ reportId }: { reportId: string }) {
  return (
    <button className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
      Download PDF Report
    </button>
  )
}
