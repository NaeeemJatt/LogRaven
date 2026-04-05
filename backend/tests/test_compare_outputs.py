# LogRaven — parser vs decoder compare metrics

from datetime import datetime

from app.parsers.compare_outputs import compare_event_streams
from app.parsers.normalizer import NormalizedEvent


def test_compare_event_streams_basic() -> None:
    ts = datetime(2024, 1, 1, 12, 0, 0)
    native = [
        NormalizedEvent(
            timestamp=ts,
            source_type="linux_endpoint",
            source_ip="10.0.0.1",
            event_type="auth_failure",
            raw_message="x",
        ),
        NormalizedEvent(
            timestamp=ts,
            source_type="linux_endpoint",
            source_ip="10.0.0.2",
            event_type="auth_failure",
            raw_message="y",
        ),
    ]
    decoder = [
        NormalizedEvent(
            timestamp=ts,
            source_type="linux_endpoint",
            source_ip="10.0.0.1",
            event_type="other",
            raw_message="x",
        ),
        NormalizedEvent(
            timestamp=ts,
            source_type="linux_endpoint",
            source_ip="10.0.0.2",
            event_type="other",
            raw_message="y",
        ),
    ]
    m = compare_event_streams(native, decoder, sample_limit=10)
    assert m["native_event_count"] == 2
    assert m["decoder_event_count"] == 2
    assert m["timestamp_agreement_ratio"] == 1.0
    assert m["source_ip_agreement_ratio"] == 1.0
