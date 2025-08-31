"""
Rule configuration models for OmniMemory system.

Represents rule configuration data loaded from YAML/JSON files.
"""

from pydantic import BaseModel, Field


class ModelActionConfig(BaseModel):
    """Configuration for a rule action from config file."""

    action_type: str = Field(..., description="Type of action")
    content: str = Field(..., description="Action content")
    pattern: str | None = Field(None, description="Pattern for replacement actions")
    parameters: dict[str, str] | None = Field(
        None,
        description="Additional parameters",
    )


class ModelConditionConfig(BaseModel):
    """Configuration for a rule condition from config file."""

    condition_type: str = Field(..., description="Type of condition")
    pattern: str | None = Field(None, description="Pattern to match")
    operator: str | None = Field(None, description="Comparison operator")
    value_str: str | None = Field(None, description="String comparison value")
    value_int: int | None = Field(None, description="Integer comparison value")
    value_float: float | None = Field(None, description="Float comparison value")
    case_sensitive: bool = Field(
        default=True,
        description="Whether matching is case sensitive",
    )
    negate: bool = Field(default=False, description="Whether to negate the condition")


class ModelRuleConfig(BaseModel):
    """Configuration for a single rule from config file."""

    name: str = Field(..., description="Rule name")
    description: str | None = Field(None, description="Rule description")
    enabled: bool = Field(default=True, description="Whether rule is enabled")
    priority: str = Field(default="MEDIUM", description="Rule priority")
    conditions: list[ModelConditionConfig] = Field(..., description="Rule conditions")
    condition_operator: str = Field(
        default="AND",
        description="How to combine conditions",
    )
    actions: list[ModelActionConfig] = Field(..., description="Rule actions")
    tags: list[str] = Field(default_factory=list, description="Rule tags")
    category: str | None = Field(None, description="Rule category")


class ModelRuleSetConfig(BaseModel):
    """Configuration for a set of rules from config file."""

    version: str = Field(..., description="Configuration version")
    name: str = Field(..., description="Rule set name")
    description: str | None = Field(None, description="Rule set description")
    rules: list[ModelRuleConfig] = Field(..., description="List of rules")
