# LogRaven — Log Type Detector

import re
from pathlib import Path

from app.utils.exceptions import UnknownLogTypeError

_SYSLOG_RFC3164 = re.compile(
    r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s"
)
_NGINX_COMBINED = re.compile(
    r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3} - - \["
)


def detect(file_path: str) -> str:
    """
    Detect the log type of a file.
    Phase 1: extension hint. Phase 2: content scan (always wins).
    Returns: windows_event | syslog | cloudtrail | nginx
    Raises: UnknownLogTypeError
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    # Phase 1 — extension hint
    phase1: str | None = None
    if ext == ".evtx":
        phase1 = "windows_event"
    elif ext == ".json":
        phase1 = "cloudtrail"
    elif ext == ".csv":
        phase1 = "windows_event"

    # .evtx is always binary Windows Event Log — no need to read content
    if ext == ".evtx":
        return "windows_event"

    # Phase 2 — read first 50 lines, check content
    lines_read = 0
    try:
        try:
            fh = open(file_path, "r", encoding="utf-8", errors="strict")
        except UnicodeDecodeError:
            fh = open(file_path, "r", encoding="latin-1")

        with fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line:
                    continue
                lines_read += 1

                if "EventID" in line or "<Event " in line:
                    return "windows_event"

                if _SYSLOG_RFC3164.match(line):
                    return "syslog"

                if '"eventSource"' in line and '"eventName"' in line:
                    return "cloudtrail"

                if _NGINX_COMBINED.match(line):
                    return "nginx"

                if lines_read >= 50:
                    break
    except (OSError, PermissionError):
        pass

    # Phase 1 fallback if content scan found nothing conclusive
    if phase1:
        return phase1

    raise UnknownLogTypeError(f"Could not detect log type for: {file_path}")
