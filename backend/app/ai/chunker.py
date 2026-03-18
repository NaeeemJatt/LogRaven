# LogRaven — Event Chunker

_SEVERITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "informational": 4,
    "deduplicated": 5,
}


def split_events(events: list, chunk_size: int = 2000, overlap: int = 50) -> list[list]:
    """
    Split events into overlapping chunks for AI processing.
    Overlap prevents missing cross-chunk patterns.

    Example: 5000 events, chunk_size=2000, overlap=50
      chunk1: events[0:2000]
      chunk2: events[1950:3950]
      chunk3: events[3900:5000]
    """
    if not events:
        return []
    if len(events) <= chunk_size:
        return [events]

    chunks = []
    start = 0
    while start < len(events):
        end = start + chunk_size
        chunks.append(events[start:end])
        if end >= len(events):
            break
        start = end - overlap  # step back by overlap to create overlap
    return chunks


def merge_findings(all_findings: list[list]) -> list[dict]:
    """
    Flatten chunk finding lists and deduplicate.
    Deduplication: exact title match — keep the one with higher confidence.
    Return sorted by severity: critical -> high -> medium -> low -> informational.
    """
    flat: list[dict] = []
    for chunk_findings in all_findings:
        if isinstance(chunk_findings, list):
            flat.extend(chunk_findings)

    # Deduplicate by title (case-insensitive)
    best: dict[str, dict] = {}
    for finding in flat:
        if not isinstance(finding, dict):
            continue
        key = (finding.get("title") or "").strip().lower()
        if not key:
            continue
        if key not in best:
            best[key] = finding
        else:
            existing_conf = float(best[key].get("confidence", 0))
            new_conf = float(finding.get("confidence", 0))
            if new_conf > existing_conf:
                best[key] = finding

    deduped = list(best.values())
    deduped.sort(key=lambda f: _SEVERITY_ORDER.get(f.get("severity", "informational"), 4))
    return deduped
