import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace

from app.parsers.normalizer import NormalizedEvent
from app.rules.engine import (
    _run_builtin_rules,
    _run_builtin_rules_with_matches,
    rule_matches_to_findings,
    run_rules_with_matches,
)
from app.rules.evaluator import RuleMatch, run_yaml_rules_with_matches
from app.rules.schema import (
    RuleDefinition,
    SimpleCondition,
    SimpleMatch,
    ThresholdMatch,
)
from app.tasks.process_investigation import (
    _build_report_summary,
    _build_source_labels,
    _merge_rule_and_ai_findings,
)


def _event(
    *,
    timestamp: datetime,
    source_type: str = "linux_endpoint",
    event_type: str = "auth_failure",
    source_ip: str = "203.0.113.10",
    raw_message: str = "failed login",
) -> NormalizedEvent:
    return NormalizedEvent(
        timestamp=timestamp,
        source_type=source_type,
        event_type=event_type,
        source_ip=source_ip,
        raw_message=raw_message,
    )


def _simple_rule(*, rule_id: str = "simple-1", flag: str = "shared_flag") -> RuleDefinition:
    return RuleDefinition(
        id=rule_id,
        title="Suspicious Login",
        severity="high",
        description="A suspicious login was observed.",
        mitre_technique_id="T1110",
        mitre_tactic="credential-access",
        flag=flag,
        match=SimpleMatch(
            type="simple",
            log_type="linux_endpoint",
            conditions=[SimpleCondition(field="event_type", op="eq", value="auth_failure")],
        ),
    )


def _threshold_rule(*, flag: str = "shared_flag") -> RuleDefinition:
    return RuleDefinition(
        id="threshold-1",
        title="Repeated Login Failures",
        severity="critical",
        description="Repeated authentication failures crossed the threshold.",
        mitre_technique_id="T1110.001",
        mitre_tactic="credential-access",
        flag=flag,
        match=ThresholdMatch(
            type="threshold",
            log_type="linux_endpoint",
            event_type="auth_failure",
            group_by="source_ip",
            count=2,
            window_seconds=60,
        ),
    )


def test_simple_and_threshold_rules_collect_matches_independently_of_shared_flags():
    start = datetime(2026, 7, 10, 12, 0, 0)
    events = [
        _event(timestamp=start),
        _event(timestamp=start + timedelta(seconds=10)),
        _event(timestamp=start + timedelta(minutes=5)),
    ]

    returned_events, matches = run_yaml_rules_with_matches(
        events,
        [_simple_rule(), _threshold_rule()],
    )

    assert returned_events is events
    assert [match.rule.id for match in matches] == ["simple-1", "threshold-1"]
    assert [len(match.events) for match in matches] == [3, 2]


def test_builtin_high_brute_force_emits_one_aggregated_match():
    start = datetime(2026, 7, 10, 12, 0, 0)
    events = [
        _event(timestamp=start + timedelta(seconds=index), source_ip="203.0.113.10")
        for index in range(5)
    ] + [
        _event(timestamp=start + timedelta(seconds=index), source_ip="203.0.113.20")
        for index in range(5)
    ]

    returned, matches = _run_builtin_rules_with_matches(events)

    assert returned is events
    assert [match.rule.id for match in matches] == [
        "lr-builtin-core-brute-force-high"
    ]
    assert len(matches[0].events) == 10


def test_builtin_high_volume_is_critical_only_not_double_counted():
    start = datetime(2026, 7, 10, 12, 0, 0)
    events = [
        _event(timestamp=start + timedelta(seconds=index), source_ip="203.0.113.10")
        for index in range(21)
    ]

    _, matches = _run_builtin_rules_with_matches(events)

    assert [match.rule.id for match in matches] == [
        "lr-builtin-core-brute-force-critical"
    ]
    assert len(matches[0].events) == 21
    assert all(event.severity_hint == "critical" for event in events)


def test_builtin_flag_rules_emit_lateral_and_sensitive_matches():
    lateral = _event(timestamp=datetime(2026, 7, 10, 12, 0, 0), event_type="other")
    lateral.flags = ["lateral_movement_candidate"]
    sensitive = _event(timestamp=datetime(2026, 7, 10, 12, 0, 1), event_type="other")
    sensitive.flags = ["sensitive_action"]

    _, matches = _run_builtin_rules_with_matches([lateral, sensitive])

    assert [match.rule.id for match in matches] == [
        "lr-builtin-core-lateral-movement",
        "lr-builtin-core-sensitive-action",
    ]
    assert [match.events for match in matches] == [[lateral], [sensitive]]
    assert lateral.severity_hint == sensitive.severity_hint == "high"


def test_builtin_dedup_only_events_do_not_emit_rule_matches():
    start = datetime(2026, 7, 10, 12, 0, 0)
    events = [
        _event(
            timestamp=start + timedelta(seconds=index),
            event_type="other",
            raw_message="duplicate",
        )
        for index in range(3)
    ]

    returned, matches = _run_builtin_rules_with_matches(events)

    assert matches == []
    assert _run_builtin_rules([]) == []
    assert returned[1].severity_hint == "deduplicated"


def test_duplicate_matching_events_produce_one_aggregated_finding_per_rule():
    start = datetime(2026, 7, 10, 12, 0, 0)
    events = [
        _event(timestamp=start, raw_message="duplicate"),
        _event(timestamp=start + timedelta(seconds=1), raw_message="duplicate"),
    ]
    _, matches = run_yaml_rules_with_matches(events, [_simple_rule()])

    findings = rule_matches_to_findings(
        matches,
        {
            id(events[0]): "auth-a.log",
            id(events[1]): "auth-b.log",
        },
    )

    assert len(findings) == 1
    assert findings[0] == {
        "severity": "high",
        "title": "Suspicious Login",
        "description": (
            "A suspicious login was observed.\n\n"
            "Matched 2 events from 2026-07-10T12:00:00 to 2026-07-10T12:00:01."
        ),
        "mitre_technique_id": "T1110",
        "mitre_technique_name": None,
        "mitre_tactic": "credential-access",
        "iocs": [],
        "remediation": None,
        "finding_type": "single",
        "confidence": 1.0,
        "source_files": ["auth-a.log", "auth-b.log"],
        "match_count": 2,
        "first_seen": "2026-07-10T12:00:00",
        "last_seen": "2026-07-10T12:00:01",
        "rule_id": "simple-1",
    }


def test_duplicate_upload_names_remain_distinct_in_finding_source_files():
    first_id = uuid.UUID("11111111-0000-0000-0000-000000000001")
    second_id = uuid.UUID("22222222-0000-0000-0000-000000000002")
    files = [
        SimpleNamespace(id=first_id, filename="auth.log"),
        SimpleNamespace(id=second_id, filename="auth.log"),
    ]
    labels = _build_source_labels(files)
    events = [
        _event(timestamp=datetime(2026, 7, 10, 12, 0, 0)),
        _event(timestamp=datetime(2026, 7, 10, 12, 0, 1)),
    ]

    findings = rule_matches_to_findings(
        [RuleMatch(rule=_simple_rule(), events=events)],
        {
            id(events[0]): labels[str(first_id)],
            id(events[1]): labels[str(second_id)],
        },
    )

    assert findings[0]["source_files"] == [
        "auth.log [11111111]",
        "auth.log [22222222]",
    ]


def test_dedup_flag_does_not_create_rule_findings(monkeypatch):
    event = _event(timestamp=datetime(2026, 7, 10, 12, 0, 0))
    event.flags = ["deduplicated"]
    monkeypatch.setattr("app.rules.loader.get_rules", lambda: [])

    returned_events, matches = run_rules_with_matches([event])

    assert returned_events == [event]
    assert matches == []
    assert rule_matches_to_findings(matches, {id(event): "source.log"}) == []


def test_rule_findings_merge_before_ai_and_remove_normalized_rule_ai_duplicates():
    rule = {
        "title": "  Suspicious   Login ",
        "mitre_technique_id": "t1110",
        "severity": "high",
        "finding_type": "single",
        "source_files": ["auth-a.log"],
    }
    duplicate_ai = {
        "title": "suspicious login",
        "mitre_technique_id": "T1110",
        "severity": "critical",
        "finding_type": "single",
        "source_files": ["auth-a.log"],
    }
    different_source_ai = {
        **duplicate_ai,
        "source_files": ["auth-b.log"],
    }
    unique_ai = {
        "title": "New persistence",
        "mitre_technique_id": "T1053.005",
        "severity": "medium",
        "finding_type": "single",
        "source_files": ["auth-a.log"],
    }
    correlated_ai = {
        **duplicate_ai,
        "finding_type": "correlated",
        "source_files": ["auth-a.log", "cloud.json"],
    }

    single, correlated = _merge_rule_and_ai_findings(
        [rule],
        [duplicate_ai, different_source_ai, unique_ai],
        [correlated_ai],
    )

    assert single == [rule, different_source_ai, unique_ai]
    assert correlated == [correlated_ai]


def test_rules_only_report_summary_counts_deterministic_findings():
    summary = _build_report_summary([{"title": "Rule finding"}], [])

    assert "Found 1 individual finding" in summary
    assert "no findings" not in summary.lower()
