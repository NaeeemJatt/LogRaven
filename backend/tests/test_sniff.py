# LogRaven — upload sniff routing tests

from pathlib import Path

from app.parsers.sniff import sniff_upload


def test_sniff_syslog_log_decoder_eligible(tmp_path: Path) -> None:
    p = tmp_path / "auth.log"
    p.write_text(
        "Jan 10 10:00:00 myhost sshd[1234]: Failed password for root from 192.168.1.1\n",
        encoding="utf-8",
    )
    r = sniff_upload(str(p))
    assert r.decoder_eligible
    assert r.suggested_log_format == "syslog"
    assert not r.is_pcap
    assert not r.is_binary_evtx


def test_sniff_evtx_not_decoder_eligible(tmp_path: Path) -> None:
    p = tmp_path / "security.evtx"
    p.write_bytes(b"\x00" * 64)
    r = sniff_upload(str(p))
    assert r.is_binary_evtx
    assert not r.decoder_eligible
