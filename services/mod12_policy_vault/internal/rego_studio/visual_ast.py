"""Visual AST Schemas for Visual-to-Rego Studio (PRD-MOD-12)."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ConditionNode(BaseModel):
    field: str
    operator: str = "=="  # ==, !=, >, <, >=, <=, contains, in
    value: Any


class VisualRuleAST(BaseModel):
    rule_id: str
    name: str
    resource_type: str
    conditions: List[ConditionNode] = Field(default_factory=list)
    message: Optional[str] = None
    severity: str = "HIGH"
    package_name: str = "lograven.rules.custom"
