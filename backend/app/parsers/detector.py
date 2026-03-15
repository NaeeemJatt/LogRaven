# LogRaven — Log Type Detector
#
# PURPOSE:
#   Auto-detects the log format of an uploaded file.
#   Two-phase detection: file extension first, then content analysis.
#   Phase 2 always overrides Phase 1 (content is more reliable).
#
# DETECTION LOGIC:
#   Phase 1 (extension):
#     .evtx -> windows_event (tentative)
#     .json -> cloudtrail (tentative)
#     .log, .txt, .csv -> inconclusive
#
#   Phase 2 (content — reads first 50 lines):
#     EventID field present -> windows_event (overrides Phase 1)
#     RFC3164 syslog pattern -> syslog
#     JSON with eventSource + eventName keys -> cloudtrail
#     Combined log format IP pattern -> nginx
#
# RETURNS: one of "windows_event" | "syslog" | "cloudtrail" | "nginx"
# RAISES:  UnknownLogTypeError if neither phase identifies the format
#
# TODO Month 2 Week 1: Implement this file.

from app.utils.exceptions import UnknownLogTypeError


def detect(file_path: str) -> str:
    """
    Detect the log type of a file.
    Returns: windows_event | syslog | cloudtrail | nginx
    Raises: UnknownLogTypeError
    """
    # TODO: Implement two-phase detection
    raise UnknownLogTypeError(f"Could not detect log type for: {file_path}")
