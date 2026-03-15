// LogRaven — Source Type Selector
//
// PURPOSE:
//   Dropdown to tag each uploaded file with its log source type.
//   Auto-suggests type based on file extension.
//   User can override the auto-detected type.
//
// SOURCE TYPE OPTIONS:
//   windows_endpoint  — Windows Event Log (EVTX)
//   linux_endpoint    — Linux auth.log / syslog
//   firewall          — Palo Alto, Fortinet, Cisco ASA
//   network           — NetFlow, IDS/IPS
//   web_server        — Nginx / Apache
//   cloudtrail        — AWS CloudTrail
//
// AUTO-SUGGEST LOGIC:
//   .evtx -> windows_endpoint
//   .json -> cloudtrail
//   .log / .txt -> linux_endpoint (with manual override encouraged)
//
// PROPS:
//   filename: string (for auto-suggest)
//   value: string
//   onChange: (sourceType: string) => void
//
// TODO Month 1 Week 3: Implement this component.

export default function SourceTypeSelector({ onChange }: { onChange: (t: string) => void }) {
  return (
    <select onChange={e => onChange(e.target.value)} className="border rounded px-2 py-1 text-sm">
      <option value="">Select source type...</option>
      <option value="windows_endpoint">Windows Endpoint</option>
      <option value="linux_endpoint">Linux Endpoint</option>
      <option value="firewall">Firewall</option>
      <option value="network">Network</option>
      <option value="web_server">Web Server</option>
      <option value="cloudtrail">AWS CloudTrail</option>
    </select>
  )
}
