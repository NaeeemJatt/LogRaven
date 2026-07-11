# LogRaven — Structured Logger
#
# LOG_FORMAT=text (default): colored human-readable lines for dev terminals.
# LOG_FORMAT=json: one JSON object per line for production log aggregation
# (CloudWatch, Loki, etc.).

import json
import logging
import sys


class _JsonFormatter(logging.Formatter):
    """One JSON object per line — safe for log aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


class _ColorFormatter(logging.Formatter):
    """Adds ANSI color to level names for terminal output."""

    COLORS = {
        "DEBUG":    "\033[36m",   # cyan
        "INFO":     "\033[32m",   # green
        "WARNING":  "\033[33m",   # yellow
        "ERROR":    "\033[31m",   # red
        "CRITICAL": "\033[35m",   # magenta
    }
    RESET = "\033[0m"
    GREY  = "\033[90m"            # dark grey for timestamp / name

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        ts    = self.formatTime(record, "%H:%M:%S")
        level = f"{color}{record.levelname[0]}{self.RESET}"   # single letter: I W E
        name  = f"{self.GREY}{record.name}{self.RESET}"
        msg   = record.getMessage()

        # Already-formatted exception info
        exc = ""
        if record.exc_info:
            exc = "\n" + self.formatException(record.exc_info)

        return f"{self.GREY}{ts}{self.RESET} {level} {name}: {msg}{exc}"


def get_logger(name: str) -> logging.Logger:
    # Imported lazily so this module stays importable even if config isn't
    # loadable yet (e.g. tooling that imports utils in isolation).
    from app.config import settings

    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        if str(settings.LOG_FORMAT).lower() == "json":
            handler.setFormatter(_JsonFormatter())
        else:
            handler.setFormatter(_ColorFormatter())
        logger.addHandler(handler)
        logger.propagate = False   # don't double-print via root logger
    logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    return logger
