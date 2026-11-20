# LogRaven — Rule Schema (Unified CSPM & Detection Rules)
# Pydantic models describing YAML rule formats:
# 1. Deterministic CSPM & AWS Log Rules (Non-AI Compliance & Drift Engine)
# 2. Event-level Simple & Threshold Detection Rules (SIEM / Sysmon Pipeline)

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, PrivateAttr, field_validator


# ── Deterministic CSPM & Log Engine Schema Primitives ─────────────────────────

class ExecutionMode(str, Enum):
    """Execution modality matching Qualys TotalCloud control definitions."""
    RUN_TIME = "Run Time"
    BUILD_TIME = "Build Time"
    BUILD_AND_RUN_TIME = "Build & Run Time"
    LOG_CORRELATION = "Correlation rule"


class OperatorType(str, Enum):
    """The 12 pure-Python deterministic comparison operators (0% AI / LLM calls)."""
    EQ = "eq"
    NEQ = "neq"
    IN = "in"
    NOT_IN = "not_in"
    GTE = "gte"
    LTE = "lte"
    REGEX = "regex"
    EXISTS = "exists"
    CIDR_OPEN_WORLD = "cidr_open_world"
    IAM_AST_WILDCARD = "iam_ast_wildcard"
    KMS_CMK_ENCRYPTED = "kms_cmk_encrypted"
    AGE_DAYS_GTE = "age_days_gte"


class ConditionRule(BaseModel):
    """A field-level condition evaluating a target resource state or log event."""
    field_path: str
    operator: OperatorType
    value: Any = None


class DeterministicRuleSpec(BaseModel):
    """Unified specification for deterministic CSPM controls and real-time log rules."""
    rule_id: str
    cid: Optional[str] = None
    title: str
    provider: str = "AWS"
    service: str
    execution_type: ExecutionMode | str = ExecutionMode.BUILD_AND_RUN_TIME
    criticality: str = "HIGH"
    target_source: str = "aws_config_state"  # "aws_config_state" | "aws_cloudtrail_log"
    match_logic: Literal["ALL", "ANY", "NONE"] | str = "ALL"
    conditions: List[ConditionRule] = Field(default_factory=list)
    group_by_fields: List[str] = Field(default_factory=list)
    window_seconds: int = 0
    threshold_count: int = 1
    policies: List[str] = Field(default_factory=list)
    mandates: List[str] = Field(default_factory=list)


class RuleEvaluationResult(BaseModel):
    """Result of evaluating a deterministic rule against a resource or event."""
    rule_id: str
    cid: Optional[str] = None
    title: str
    passed: bool
    evidence: Dict[str, Any] = Field(default_factory=dict)


# ── Existing Detection Rule Schema (Backward Compatibility) ───────────────────

class SimpleCondition(BaseModel):
    """A single field-level condition inside a simple detection rule."""

    field: str
    """NormalizedEvent attribute name or 'extra.<key>' for extra_fields."""

    op: Literal[
        "eq", "neq", "contains", "contains_any", "contains_all",
        "startswith", "endswith", "re", "in", "exists", "not_exists",
    ]
    """Comparison operator."""

    value: Optional[str] = None
    """Single string value (for eq / neq / contains / startswith / endswith / re)."""

    values: Optional[list[str]] = None
    """List of strings (for contains_any / contains_all / in)."""

    negate: bool = False
    """Invert the result of this condition."""

    # Pre-compiled regex — populated in model_post_init, never serialized
    _compiled_re: re.Pattern | None = PrivateAttr(default=None)

    @field_validator("values", mode="before")
    @classmethod
    def coerce_values(cls, v):
        """Accept a comma-separated string as a values list."""
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

    def model_post_init(self, __context: Any) -> None:
        if self.op == "re" and self.value:
            try:
                object.__setattr__(self, "_compiled_re", re.compile(self.value, re.IGNORECASE))
            except re.error:
                pass


class SimpleMatch(BaseModel):
    """Match a rule against individual events."""

    type: Literal["simple"]
    log_type: Optional[str] = None
    """Filter to events whose source_type equals this value."""

    conditions: list[SimpleCondition]
    condition_logic: Literal["and", "or"] = "and"


class ThresholdMatch(BaseModel):
    """Match a rule when N events from the same group occur within a time window."""

    type: Literal["threshold"]
    log_type: Optional[str] = None
    event_type: Optional[str] = None
    """Pre-filter: only consider events of this event_type."""

    group_by: str
    """NormalizedEvent field to group by (e.g. source_ip, username)."""

    count: int
    """Minimum number of events in the window to trigger."""

    window_seconds: int
    """Sliding window size in seconds."""


class RuleDefinition(BaseModel):
    """A complete LogRaven detection rule loaded from a YAML file."""

    id: str
    title: str
    source: str = "lograven"
    log_type: Optional[str] = None
    severity: str = "medium"
    mitre_technique_id: Optional[str] = None
    mitre_tactic: Optional[str] = None
    flag: Optional[str] = None
    """Flag string appended to event.flags on match (underscores, no spaces)."""

    description: str = ""
    enabled: bool = True
    requires_sysmon: bool = False
    """Skip rule if Sysmon is not installed (YAML converter marks these)."""

    match: SimpleMatch | ThresholdMatch
