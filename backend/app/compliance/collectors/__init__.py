# LogRaven — Compliance evidence collectors
#
# The base CloudTrail/IAM/GuardDuty collectors live in app.compliance.aws_collector
# (kept for backward compatibility). This package adds the deep AWS collectors that
# broaden the evidence base so one collection run can grade many frameworks.

from app.compliance.collectors.aws_extended import collect_extended_evidence  # noqa: F401

__all__ = ["collect_extended_evidence"]
