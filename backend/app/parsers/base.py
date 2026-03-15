# LogRaven — Abstract Base Parser
#
# PURPOSE:
#   Defines the interface all LogRaven parsers must implement.
#   Provides shared utility methods inherited by all parsers.
#
# REQUIRED METHOD:
#   parse(file_path: str) -> List[NormalizedEvent]
#     Must be implemented by every parser subclass.
#     Must stream the file — never load entirely into memory.
#     Must never raise on malformed individual lines — skip and log warning.
#
# SHARED UTILITIES (inherited by all parsers):
#   _stream_lines(file_path) -> Iterator[str]
#     Streams file line by line. UTF-8 with latin-1 fallback.
#   _safe_parse_timestamp(raw: str) -> datetime | None
#     Tries multiple timestamp formats. Returns None if all fail.
#   _log_skip(line: str, reason: str) -> None
#     Logs skipped lines as DEBUG. Never raises.
#
# TODO Month 2 Week 1: Implement this file.

from abc import ABC, abstractmethod
from typing import Iterator
from app.parsers.normalizer import NormalizedEvent


class BaseParser(ABC):

    @abstractmethod
    def parse(self, file_path: str) -> list[NormalizedEvent]:
        """Parse a log file and return normalized events."""
        pass

    def _stream_lines(self, file_path: str) -> Iterator[str]:
        """Stream file line by line with encoding fallback. Never loads full file."""
        # TODO: Implement UTF-8 with latin-1 fallback
        pass

    def _safe_parse_timestamp(self, raw: str):
        """Try multiple timestamp formats. Return datetime or None."""
        # TODO: Implement multi-format timestamp parsing
        pass

    def _log_skip(self, line: str, reason: str) -> None:
        """Log a skipped line as DEBUG."""
        # TODO: Use structured logger
        pass
