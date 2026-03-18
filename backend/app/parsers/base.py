# LogRaven — Abstract Base Parser

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterator

from app.parsers.normalizer import NormalizedEvent
from app.utils.logger import get_logger

logger = get_logger(__name__)

_TIMESTAMP_FORMATS = [
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%b %d %H:%M:%S",
    "%b  %d %H:%M:%S",
    "%d/%b/%Y:%H:%M:%S %z",
]


class BaseParser(ABC):

    @abstractmethod
    def parse(self, file_path: str) -> list[NormalizedEvent]:
        """Parse a log file and return normalized events. Must stream — never load full file."""

    def _stream_lines(self, file_path: str) -> Iterator[str]:
        """Stream file line by line. UTF-8 with latin-1 fallback. Never loads full file."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="strict") as fh:
                for line in fh:
                    yield line.rstrip("\n\r")
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="latin-1") as fh:
                for line in fh:
                    yield line.rstrip("\n\r")

    def _safe_parse_timestamp(self, raw: str) -> datetime | None:
        """Try multiple timestamp formats. Returns datetime or None if all fail."""
        if not raw:
            return None
        raw = raw.strip()
        for fmt in _TIMESTAMP_FORMATS:
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        return None

    def _log_skip(self, line: str, reason: str) -> None:
        """Log a skipped line at DEBUG level. Never raises."""
        logger.debug("Skipping line [%s]: %.120s", reason, line)
