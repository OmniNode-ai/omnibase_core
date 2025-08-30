"""
Rule configuration models for OmniMemory system.

Represents rule configuration data loaded from YAML/JSON files.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelActionConfig(BaseModel):
    """Configuration for a rule action from config file."""

    action_type: str = Field(..., description="Type of action")
    content: str = Field(..., description="Action content")
    pattern: Optional[str] = Field(None, description="Pattern for replacement actions")
    parameters: Optional[dict[str, str]] = Field(
        None, description="Additional parameters"
    )


class ModelConditionConfig(BaseModel):
    """Configuration for a rule condition from config file."""

    condition_type: str = Field(..., description="Type of condition")
    pattern: Optional[str] = Field(None, description="Pattern to match")
    operator: Optional[str] = Field(None, description="Comparison operator")
    value_str: Optional[str] = Field(None, description="String comparison value")
    value_int: Optional[int] = Field(None, description="Integer comparison value")
    value_float: Optional[float] = Field(None, description="Float comparison value")
    case_sensitive: bool = Field(
        default=True, description="Whether matching is case sensitive"
    )
    negate: bool = Field(default=False, description="Whether to negate the condition")


class ModelRuleConfig(BaseModel):
    """Configuration for a single rule from config file."""

    name: str = Field(..., description="Rule name")
    description: Optional[str] = Field(None, description="Rule description")
    enabled: bool = Field(default=True, description="Whether rule is enabled")
    priority: str = Field(default="MEDIUM", description="Rule priority")
    conditions: List[ModelConditionConfig] = Field(..., description="Rule conditions")
    condition_operator: str = Field(
        default="AND", description="How to combine conditions"
    )
    actions: List[ModelActionConfig] = Field(..., description="Rule actions")
    tags: List[str] = Field(default_factory=list, description="Rule tags")
    category: Optional[str] = Field(None, description="Rule category")


class ModelRuleSetConfig(BaseModel):
    """Configuration for a set of rules from config file."""

    version: str = Field(..., description="Configuration version")
    name: str = Field(..., description="Rule set name")
    description: Optional[str] = Field(None, description="Rule set description")
    rules: List[ModelRuleConfig] = Field(..., description="List of rules")
