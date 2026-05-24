# LogRaven — upload sniff for routing (extension + magic + sample lines).

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_SYSLOG_RFC3164 = re.compile(
    r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s"
)

# PCAP classic / nanosecond magic
_PCAP_MAGICS = (
    b"\xd4\xc3\xb2\xa1",
    b"\xa1\xb2\xc3\xd4",
    b"\x4d\x3c\xb2\xa1",
    b"\xa1\xb2\x3c\x4d",
)


@dataclass
class SniffResult:
    extension: str
    is_binary_evtx: bool
    is_pcap: bool
    decoder_eligible: bool
    suggested_log_format: str | None
    looks_like_jsonl: bool
    looks_like_iis_w3c: bool
    sample_lines: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _read_head_bytes(path: Path, n: int = 8192) -> bytes:
    try:
        with open(path, "rb") as fh:
            return fh.read(n)
    except OSError:
        return b""


def _read_sample_text_lines(path: Path, max_lines: int = 80, max_chars: int = 64_000) -> list[str]:
    lines: list[str] = []
    buf = 0
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                line = raw.rstrip("\n\r")
                if line.strip():
                    lines.append(line)
                    buf += len(line)
                    if len(lines) >= max_lines or buf >= max_chars:
                        break
    except (OSError, UnicodeError):
        return lines
    return lines


def sniff_upload(file_path: str) -> SniffResult:
    path = Path(file_path)
    ext = path.suffix.lower()
    notes: list[str] = []

    head = _read_head_bytes(path)
    is_pcap = len(head) >= 4 and head[:4] in _PCAP_MAGICS
    # EVTX: common container magic "ElfFile" at offset 0 (4 bytes 0x45 0x6c 0x66 0x46) — check loose
    is_evtx_ext = ext == ".evtx"
    is_evtx_magic = head[:4] == b"Elf\x00" or head[:4] == b"ElfF" or (len(head) >= 8 and head[0:4] == b"\x45\x6c\x66\x00")

    if is_pcap:
        notes.append("pcap_magic")
        return SniffResult(
            extension=ext,
            is_binary_evtx=False,
            is_pcap=True,
            decoder_eligible=False,
            suggested_log_format=None,
            looks_like_jsonl=False,
            looks_like_iis_w3c=False,
            notes=notes,
        )

    if is_evtx_ext or is_evtx_magic:
        notes.append("evtx_binary")
        return SniffResult(
            extension=ext,
            is_binary_evtx=True,
            is_pcap=False,
            decoder_eligible=False,
            suggested_log_format=None,
            looks_like_jsonl=False,
            looks_like_iis_w3c=False,
            notes=notes,
        )

    lines = _read_sample_text_lines(path)
    looks_jsonl = False
    looks_iis = False
    syslog_hits = 0
    for line in lines[:50]:
        s = line.strip()
        if not s:
            continue
        if s.startswith("{") and '"eventName"' in s and '"eventSource"' in s:
            looks_jsonl = True
        if s.startswith("{") and s.endswith("}"):
            looks_jsonl = True
        if line.startswith("#Software: Microsoft Internet Information Services") or (
            line.startswith("#Fields:") and "cs-method" in line.lower()
        ):
            looks_iis = True
        if _SYSLOG_RFC3164.match(line):
            syslog_hits += 1

    suggested: str | None = None
    if looks_iis:
        suggested = "iis"
    elif looks_jsonl:
        suggested = "json"
    elif syslog_hits >= 1:
        suggested = "syslog"
    elif ext in (".log", ".txt", ".csv"):
        suggested = "syslog"

    # Line-oriented events the decoder manager can ingest via Logtest
    if not lines:
        decoder_eligible = False
    elif ext == ".csv" and not looks_jsonl:
        decoder_eligible = False
        notes.append("csv_native_preferred")
    else:
        decoder_eligible = (
            looks_jsonl
            or looks_iis
            or syslog_hits >= 1
            or ext in (".log", ".txt")
            or (ext == ".json" and len(lines) >= 1 and lines[0].lstrip().startswith("{"))
        )

    return SniffResult(
        extension=ext,
        is_binary_evtx=False,
        is_pcap=False,
        decoder_eligible=decoder_eligible,
        suggested_log_format=suggested,
        looks_like_jsonl=looks_jsonl,
        looks_like_iis_w3c=looks_iis,
        sample_lines=lines[:20],
        notes=notes,
    )
