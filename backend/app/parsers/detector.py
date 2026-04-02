# LogRaven — Log Type Detector

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.utils.exceptions import UnknownLogTypeError

_SYSLOG_RFC3164 = re.compile(
    r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s"
)
_NGINX_COMBINED = re.compile(
    r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}[^\[]*\["
)

# Tie-break when two candidates share similar confidence (content scan order).
_TYPE_PRIORITY = ("windows_event", "cloudtrail", "iis", "syslog", "nginx")

_MAX_LINES = 50


@dataclass(frozen=True)
class LogTypeCandidate:
    log_type: str
    confidence: float
    reasons: tuple[str, ...]


def detect_candidates(file_path: str) -> list[LogTypeCandidate]:
    """
    Return log-type candidates ranked by confidence (highest first).
    Combines extension hints with a bounded head scan of file content.
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".evtx":
        return [
            LogTypeCandidate(
                log_type="windows_event",
                confidence=1.0,
                reasons=("Binary Windows Event Log (.evtx)",),
            )
        ]

    extension_hint: str | None = None
    if ext == ".json":
        extension_hint = "cloudtrail"
    elif ext == ".csv":
        extension_hint = "windows_event"

    hits: dict[str, int] = {k: 0 for k in _TYPE_PRIORITY}
    non_empty = 0

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line:
                    continue
                non_empty += 1

                if "EventID" in line or "<Event " in line:
                    hits["windows_event"] += 1
                if _SYSLOG_RFC3164.match(line):
                    hits["syslog"] += 1
                if '"eventSource"' in line and '"eventName"' in line:
                    hits["cloudtrail"] += 1
                if line.startswith("#Software: Microsoft Internet Information Services"):
                    hits["iis"] += 1
                elif line.startswith("#Fields:") and "cs-method" in line.lower():
                    hits["iis"] += 1
                if _NGINX_COMBINED.match(line):
                    hits["nginx"] += 1

                if non_empty >= _MAX_LINES:
                    break
    except (OSError, PermissionError):
        pass

    denom = max(non_empty, 1)
    scored: dict[str, tuple[float, list[str]]] = {}

    for lt in _TYPE_PRIORITY:
        h = hits[lt]
        if h <= 0:
            continue
        ratio = min(1.0, h / denom)
        conf = min(0.97, 0.38 + 0.62 * ratio)
        reasons: list[str] = [
            f"Content pattern matched {h} non-empty line(s) in first {_MAX_LINES} lines"
        ]
        if extension_hint == lt:
            conf = min(1.0, conf + 0.12)
            reasons.append("File extension agrees with content signal")
        scored[lt] = (conf, reasons)

    # Extension-only hints when scan found no strong content signals
    if extension_hint and extension_hint not in scored:
        reasons = ["No strong content match; using filename extension hint"]
        scored[extension_hint] = (0.48, reasons)

    # Plain-text web-style logs: weak nginx candidate
    if ext in (".log", ".txt", ".access") and "nginx" not in scored:
        scored["nginx"] = (
            0.36,
            ["No specific format matched; generic access-log fallback (.log/.txt/.access)"],
        )

    if not scored:
        if extension_hint:
            return [
                LogTypeCandidate(
                    log_type=extension_hint,
                    confidence=0.52,
                    reasons=("Extension hint only (content scan inconclusive)",),
                )
            ]
        if ext in (".log", ".txt", ".access"):
            return [
                LogTypeCandidate(
                    log_type="nginx",
                    confidence=0.34,
                    reasons=("Last-resort access-log parser for extension",),
                )
            ]
        raise UnknownLogTypeError(f"Could not detect log type for: {file_path}")

    items = [
        LogTypeCandidate(
            log_type=lt,
            confidence=round(min(1.0, data[0]), 4),
            reasons=tuple(data[1]),
        )
        for lt, data in scored.items()
    ]
    items.sort(
        key=lambda c: (-c.confidence, _TYPE_PRIORITY.index(c.log_type) if c.log_type in _TYPE_PRIORITY else 99)
    )
    return items


def detect(file_path: str) -> str:
    """
    Detect the log type of a file (highest-confidence candidate only).
    Raises UnknownLogTypeError if no candidate applies.
    """
    cands = detect_candidates(file_path)
    return cands[0].log_type
