# LogRaven — AWS CloudTrail Parser
#
# PURPOSE:
#   Parses AWS CloudTrail JSON log files.
#   Handles both the standard Records array format and single-event files.
#
# FORMAT:
#   Standard: {"Records": [{event1}, {event2}, ...]}
#   Single:   {eventTime, eventSource, eventName, ...}
#
# KEY FIELDS EXTRACTED:
#   eventTime, eventSource, eventName, sourceIPAddress,
#   userIdentity (type, arn, accountId), errorCode
#
# DETECTION FLAGS:
#   sensitive_action: IAM policy changes, security group modifications,
#                     root account usage, access key creation
#   failed_api_call: any event with errorCode field populated
#   cross_account: events where userIdentity.accountId differs from normal
#
# NOTE: CloudTrail files are typically <20MB. Load full JSON is acceptable.
#       No line-by-line streaming needed for this format.
#
# TODO Month 2 Week 3: Implement this file.

from app.parsers.base import BaseParser
from app.parsers.normalizer import NormalizedEvent


class CloudTrailParser(BaseParser):

    def parse(self, file_path: str) -> list[NormalizedEvent]:
        # TODO: Load JSON, handle Records array or single event
        # TODO: Extract all key fields per event
        # TODO: Apply detection flags
        return []
