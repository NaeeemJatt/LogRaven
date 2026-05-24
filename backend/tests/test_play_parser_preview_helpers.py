# Tests — PlayParser preview helpers (text lines + line alignment)

import tempfile
from datetime import datetime
from pathlib import Path

from app.parsers.line_align import align_lines_to_events, build_preview_rows_for_parser
from app.parsers.normalizer import NormalizedEvent
from app.parsers.text_lines import read_first_nonblank_lines


def test_read_first_nonblank_lines_skips_blanks():
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False, encoding="utf-8") as f:
        f.write("a\n\n  \nb\n")
        p = f.name
    try:
        lines = read_first_nonblank_lines(p, 10)
        assert lines == ["a", "b"]
        assert read_first_nonblank_lines(p, 1) == ["a"]
    finally:
        Path(p).unlink(missing_ok=True)


def test_align_lines_exact_match():
    line = "Jan  2 12:00:00 h sshd: fail"
    ev = NormalizedEvent(
        timestamp=datetime(2024, 1, 2, 12, 0, 0),
        source_type="linux_endpoint",
        raw_message=line,
        event_type="other",
    )
    pairs = align_lines_to_events([line], [ev])
    assert pairs[0][0] == "exact"
    assert pairs[0][1] is ev


def test_align_lines_index_fallback():
    lines = ["x", "y"]
    evs = [
        NormalizedEvent(timestamp=datetime(2024, 1, 1), source_type="t", raw_message="u1", event_type="other"),
        NormalizedEvent(timestamp=datetime(2024, 1, 1), source_type="t", raw_message="u2", event_type="other"),
    ]
    pairs = align_lines_to_events(lines, evs)
    assert pairs[0][0] == "index"
    assert pairs[1][0] == "index"


def test_build_preview_rows_for_parser_shape():
    line = "ping"
    ev = NormalizedEvent(
        timestamp=datetime(2024, 1, 1, 0, 0, 0),
        source_type="linux_endpoint",
        raw_message=line,
        event_type="other",
    )
    rows = build_preview_rows_for_parser([line], [ev], raw_max_chars=100)
    assert len(rows) == 1
    assert rows[0]["line_no"] == 1
    assert rows[0]["raw"] == line
    assert rows[0]["match"] == "exact"
    assert rows[0]["parsed"]["source_type"] == "linux_endpoint"
