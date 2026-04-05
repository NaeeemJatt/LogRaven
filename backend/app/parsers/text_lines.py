# LogRaven — read first N non-blank text lines (same semantics as decoder stream).

from __future__ import annotations


def read_first_nonblank_lines(path: str, max_lines: int) -> list[str]:
    """
    UTF-8 with replacement, rstrip newlines, skip empty/whitespace-only lines.
    Matches behavior used in decoder stream_decode.
    """
    if max_lines <= 0:
        return []
    out: list[str] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                s = raw.rstrip("\n\r")
                if not s.strip():
                    continue
                out.append(s)
                if len(out) >= max_lines:
                    break
    except OSError:
        return []
    return out
