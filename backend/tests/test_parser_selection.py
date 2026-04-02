# LogRaven — Parser detection ranking and parse quality

import tempfile
from pathlib import Path

import pytest

from app.parsers.detector import LogTypeCandidate, detect, detect_candidates
from app.parsers.normalizer import NormalizedEvent
from app.parsers.quality import PARSE_QUALITY_SUFFICIENT, assess_parse_quality
from app.parsers.syslog import SyslogParser
from app.utils.exceptions import UnknownLogTypeError


def test_detect_candidates_syslog_ranked_high():
    body = (
        "Jan 15 10:00:01 host sshd[123]: Accepted publickey\n"
        "Jan 15 10:00:02 host crond[1]: (root) CMD (/usr/bin/true)\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False, encoding="utf-8") as tmp:
        tmp.write(body)
        path = tmp.name
    try:
        cands = detect_candidates(path)
        assert len(cands) >= 1
        assert cands[0].log_type == "syslog"
        assert cands[0].confidence >= 0.5
        assert any("pattern" in r.lower() for r in cands[0].reasons)
    finally:
        Path(path).unlink(missing_ok=True)


def test_detect_evtx_single_candidate():
    with tempfile.NamedTemporaryFile(suffix=".evtx", delete=False) as tmp:
        path = tmp.name
    try:
        c = detect_candidates(path)
        assert len(c) == 1
        assert c[0] == LogTypeCandidate(
            log_type="windows_event",
            confidence=1.0,
            reasons=("Binary Windows Event Log (.evtx)",),
        )
        assert detect(path) == "windows_event"
    finally:
        Path(path).unlink(missing_ok=True)


def test_detect_unknown_raises():
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
        path = tmp.name
    try:
        Path(path).write_text("not a log\n", encoding="utf-8")
        with pytest.raises(UnknownLogTypeError):
            detect_candidates(path)
    finally:
        Path(path).unlink(missing_ok=True)


def test_assess_parse_quality_empty():
    q = assess_parse_quality([])
    assert q.score == 0.0
    assert "no_events" in q.warnings


def test_assess_parse_quality_structured_events():
    from datetime import datetime, timezone

    evs = [
        NormalizedEvent(
            timestamp=datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc),
            source_type="linux_endpoint",
            source_ip="10.0.0.1",
            event_type="auth",
        ),
        NormalizedEvent(
            timestamp=datetime(2024, 6, 1, 12, 1, tzinfo=timezone.utc),
            source_type="linux_endpoint",
            username="root",
            event_type="process",
        ),
    ]
    q = assess_parse_quality(evs)
    assert q.score >= PARSE_QUALITY_SUFFICIENT
    assert q.structured_ratio >= 0.9


def test_syslog_parser_produces_passing_quality():
    body = "Jan 15 10:00:01 myhost sshd[1]: test\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False, encoding="utf-8") as tmp:
        tmp.write(body)
        path = tmp.name
    try:
        cands = detect_candidates(path)
        events = SyslogParser().parse(path)
        q = assess_parse_quality(events)
        assert len(events) >= 1
        assert cands[0].log_type == "syslog"
        assert q.score >= 0.2
    finally:
        Path(path).unlink(missing_ok=True)
