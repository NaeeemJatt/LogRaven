# LogRaven — Frontend Pages Specification

## pages/Landing.tsx
Public page. No auth required.
Sections: Hero (tagline + CTA), How It Works (3 steps), Features, Pricing.
CTA: "Get LogRaven" -> links to Register page.

## pages/Auth/Login.tsx + Register.tsx
Login: email + password form. On success: store tokens, redirect to Dashboard.
Register: email + password + confirm. On success: auto-login, redirect to Dashboard.
Error handling: show API error messages inline.

## pages/Dashboard.tsx
Shows list of all user investigations sorted by created_at desc.
Table columns: name, status badge, file count, severity badge (highest found), date, Actions.
Actions: View, Delete.
Empty state: illustration + "Create your first investigation" button.
Top section: usage stats (uploads used vs plan limit).

## pages/NewInvestigation.tsx
Form: investigation name input.
On submit: POST /api/v1/investigations, redirect to Investigation detail page.

## pages/Investigation.tsx
Shows investigation detail with file upload zone.
FileUploadZone: drag-and-drop or click-to-browse.
Each uploaded file shows: filename, SourceTypeSelector dropdown, size, remove button.
SourceTypeSelector: auto-suggests type from file extension.
Run Analysis button: disabled until at least 1 file uploaded.
On Run Analysis: POST /api/v1/investigations/{id}/analyze, redirect to JobStatus page.

## pages/JobStatus.tsx
Receives investigation_id from navigation state.
Uses useJobStatus hook — polls GET /api/v1/investigations/{id}/status every 3 seconds.
Shows stepped progress bar: Queued -> Parsing -> Rule Engine -> Correlation -> AI Analysis -> Building Report -> Done.
Each step highlights as backend progresses (stored in Redis, returned in status response).
On complete: auto-navigate to /report/{report_id} after 1.5 second delay.
On failed: show error state with retry option.

## pages/Report.tsx
Fetches report with useReport(report_id).
Sections in order:
  1. Header: LogRaven branding, investigation name, date, top severity badge.
  2. Executive summary paragraph.
  3. Severity distribution: SeverityChart pie chart.
  4. Correlated findings (shown first — highest priority): each as CorrelationCard.
  5. Individual file findings: each as FindingCard sorted by severity.
  6. MITRE ATT&CK matrix: MitreMatrix component.
  7. IOC table: IOCTable component.
  8. DownloadButton: calls reports.getDownloadUrl(), opens PDF URL.
