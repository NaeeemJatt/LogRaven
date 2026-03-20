# LogRaven — Structured Logger

import logging
import os
import sys


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
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_ColorFormatter())
        logger.addHandler(handler)
        logger.propagate = False   # don't double-print via root logger
    level = logging.DEBUG if os.getenv("DEBUG", "").lower() in ("true", "1") else logging.INFO
    logger.setLevel(level)
    return logger
