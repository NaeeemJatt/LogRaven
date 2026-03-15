# LogRaven — Nginx / Apache Access Log Parser
#
# PURPOSE:
#   Parses Nginx combined log format and Apache combined log format.
#   Both formats are structurally identical — one parser handles both.
#
# FORMAT:
#   IP - - [DD/Mon/YYYY:HH:MM:SS +tz] "METHOD /path HTTP/1.1" status bytes "referer" "ua"
#
# KEY FIELDS EXTRACTED:
#   remote_addr, time_local, method, request_path, protocol,
#   status_code, body_bytes, referer, user_agent
#
# DETECTION FLAGS:
#   scanning: 50+ requests from same IP within 60 seconds
#   4xx_spike: 20+ 4xx responses from same IP
#   injection_attempt: SQL keywords or path traversal sequences in URL
#   scanner_ua: matches known scanner User-Agent signatures
#
# TODO Month 2 Week 1: Implement this file.

from app.parsers.base import BaseParser
from app.parsers.normalizer import NormalizedEvent


class NginxParser(BaseParser):

    def parse(self, file_path: str) -> list[NormalizedEvent]:
        # TODO: Stream lines, parse with combined log regex
        # TODO: Calculate request rates per IP per 60-second window
        # TODO: Apply detection flags
        return []
