// LogRaven — File Upload Drop Zone
//
// PURPOSE:
//   Drag-and-drop file upload area for adding log files to an investigation.
//   Supports multiple files dropped at once.
//   Client-side validation: file type and size before uploading.
//
// BEHAVIOR:
//   - Drag over: highlight zone with blue border
//   - Drop: validate each file, show SourceTypeSelector for each
//   - Click: open file browser (accepts same extension whitelist)
//   - Each accepted file shows preview: filename, size, SourceTypeSelector, remove button
//
// PROPS:
//   investigationId: string
//   onFileAdded: (file: InvestigationFile) => void
//   disabled: boolean (true when investigation is not in draft state)
//
// TODO Month 1 Week 3: Implement this component.

export default function FileUploadZone({ disabled = false }: { disabled?: boolean }) {
  return (
    <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
      <p className="text-gray-500">Drop log files here</p>
      <p className="text-sm text-gray-400 mt-1">EVTX, CSV, LOG, TXT, JSON — TODO</p>
    </div>
  )
}
