// LogRaven — Investigation Detail Page
//
// PURPOSE:
//   Shows the investigation with its file list.
//   Allows uploading additional files and starting analysis.
//
// SECTIONS:
//   Header: investigation name + status badge
//   FileUploadZone: drag-and-drop area (only shown when status=draft)
//   FileList: uploaded files with source type badges and status
//   Run Analysis button: disabled until status=draft and >= 1 file
//
// KEY COMPONENT:
//   SourceTypeSelector per file — auto-suggests type from extension,
//   user can override. Type is sent with file to POST .../files
//
// TODO Month 1 Week 3: Implement this page.

export default function Investigation() {
  return <div>LogRaven Investigation Detail — TODO Month 1 Week 3</div>
}
