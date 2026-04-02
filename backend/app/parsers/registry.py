# LogRaven — Parser key → class registry (single source for pipeline + PlayParser)

from app.parsers.base import BaseParser
from app.parsers.cloudtrail import CloudTrailParser
from app.parsers.nginx import NginxParser
from app.parsers.syslog import SyslogParser
from app.parsers.windows_event import WindowsEventParser

PARSER_REGISTRY: dict[str, type[BaseParser]] = {
    "windows_event": WindowsEventParser,
    "syslog": SyslogParser,
    "cloudtrail": CloudTrailParser,
    "nginx": NginxParser,
    "iis": NginxParser,  # NginxParser handles IIS W3C internally
}

PARSER_KEYS: tuple[str, ...] = tuple(PARSER_REGISTRY.keys())
