# LogRaven — File Upload Validators
#
# PURPOSE:
#   Server-side validation for uploaded log files.
#   Client-side validation is UX only — server-side is the security boundary.
#
# VALIDATES:
#   - File extension must be in whitelist: [evtx, csv, log, txt, json]
#   - MIME type must match extension (prevents extension spoofing)
#   - File size must be under tier limit: free=5MB, pro=50MB, team=200MB
#   - source_type must be a valid enum value
#
# RAISES:
#   InvalidFileTypeError (400) if type check fails
#   FileTooLargeError (400) if size exceeds tier limit
#
# TODO Month 1 Week 3: Implement this file.

ALLOWED_EXTENSIONS = {"evtx", "csv", "log", "txt", "json"}

TIER_SIZE_LIMITS = {
    "free": 5 * 1024 * 1024,    # 5MB
    "pro":  50 * 1024 * 1024,   # 50MB
    "team": 200 * 1024 * 1024,  # 200MB
}

VALID_SOURCE_TYPES = {
    "windows_endpoint", "linux_endpoint", "firewall",
    "network", "web_server", "cloudtrail"
}

# TODO: Implement validate_file_upload(file, user) -> None
