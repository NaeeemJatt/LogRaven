"""Schemas for actionable compliance remediation guides."""

from pydantic import BaseModel, Field


class RemediationGuide(BaseModel):
    """Actionable step-by-step remediation guide for non-passing compliance controls."""

    control_id: str
    title: str
    threat_rationale: str
    estimated_time_minutes: int = Field(default=5, ge=1)
    console_steps: list[str] = Field(default_factory=list)
    aws_cli_command: str = ""
    terraform_snippet: str = ""
    verification_command: str = ""
