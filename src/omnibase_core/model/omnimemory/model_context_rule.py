"""
Context rule models for the OmniMemory context rules engine.

These models define the structure for context injection rules that intelligently
inject relevant context into Claude Code conversations based on patterns,
conditions, and freshness criteria.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class EnumRuleActionType(str, Enum):
    """Types of actions a context rule can perform."""

    INJECT_CONTEXT = "inject_context"
    REPLACE_PATTERN = "replace_pattern"
    ADD_WARNING = "add_warning"
    BLOCK_PATTERN = "block_pattern"
    SUGGEST_ALTERNATIVE = "suggest_alternative"


class EnumRulePriority(str, Enum):
    """Priority levels for context rules."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EnumRuleConditionType(str, Enum):
    """Types of conditions that can trigger a rule."""

    PATTERN_MATCH = "pattern_match"
    CONTEXT_CONTAINS = "context_contains"
    FILE_TYPE = "file_type"
    MODEL_TYPE = "model_type"
    CONVERSATION_DOMAIN = "conversation_domain"
    TOKEN_COUNT = "token_count"
    FRESHNESS_CHECK = "freshness_check"


class ModelRuleCondition(BaseModel):
    """Model for a single rule condition."""

    condition_type: EnumRuleConditionType = Field(
        description="Type of condition to evaluate"
    )
    pattern: str = Field(description="Pattern to match or condition to evaluate")
    operator: str = Field(
        default="equals",
        description="Operator for condition evaluation (equals, contains, regex, etc.)",
    )
    value: Optional[str] = Field(
        default=None,
        description="Value to compare against (optional for some conditions)",
    )
    case_sensitive: bool = Field(
        default=False, description="Whether pattern matching is case sensitive"
    )


class ModelRuleAction(BaseModel):
    """Model for a rule action to be executed."""

    action_type: EnumRuleActionType = Field(description="Type of action to perform")
    content: str = Field(
        description="Content to inject, replace with, or message to display"
    )
    position: str = Field(
        default="before_generation",
        description="When to apply the action (before_generation, after_generation, etc.)",
    )
    priority_boost: int = Field(
        default=0, description="Priority boost for this specific action"
    )


class ModelContextRule(BaseModel):
    """Model for a context injection rule."""

    rule_id: str = Field(description="Unique identifier for the rule")
    name: str = Field(description="Human-readable name for the rule")
    description: str = Field(description="Description of what the rule does")

    # Rule triggering conditions
    conditions: List[ModelRuleCondition] = Field(
        description="List of conditions that must be met to trigger the rule"
    )
    condition_logic: str = Field(
        default="AND", description="Logic for combining conditions (AND, OR, CUSTOM)"
    )

    # Rule actions
    actions: List[ModelRuleAction] = Field(
        description="List of actions to perform when rule is triggered"
    )

    # Rule metadata
    priority: EnumRulePriority = Field(description="Priority level of this rule")
    enabled: bool = Field(
        default=True, description="Whether this rule is currently active"
    )

    # Effectiveness tracking
    hit_count: int = Field(
        default=0, description="Number of times this rule has been triggered"
    )
    success_count: int = Field(
        default=0, description="Number of times this rule led to successful outcomes"
    )
    last_triggered: Optional[datetime] = Field(
        default=None, description="Last time this rule was triggered"
    )

    # Rule lifecycle
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this rule was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this rule was last updated"
    )
    created_by: str = Field(
        default="system", description="Who or what created this rule"
    )

    # Context and targeting
    target_models: List[str] = Field(
        default_factory=list,
        description="List of models this rule applies to (empty = all models)",
    )
    target_domains: List[str] = Field(
        default_factory=list,
        description="List of conversation domains this rule applies to",
    )

    # Freshness and validity
    expires_at: Optional[datetime] = Field(
        default=None, description="When this rule expires (None = never expires)"
    )
    confidence_score: float = Field(
        default=1.0, description="Confidence score for this rule (0.0-1.0)"
    )


class ModelRuleMatchResult(BaseModel):
    """Model for the result of rule matching against context."""

    rule_id: str = Field(description="ID of the rule that was evaluated")
    matched: bool = Field(description="Whether the rule conditions were met")
    confidence: float = Field(description="Confidence score for the match")

    matched_conditions: List[str] = Field(
        default_factory=list, description="List of condition patterns that matched"
    )
    failed_conditions: List[str] = Field(
        default_factory=list, description="List of condition patterns that failed"
    )

    execution_time_ms: float = Field(
        default=0.0, description="Time taken to evaluate this rule in milliseconds"
    )

    context_used: Optional[str] = Field(
        default=None, description="Context that was used for matching"
    )


class ModelRuleExecutionResult(BaseModel):
    """Model for the result of executing rule actions."""

    rule_id: str = Field(description="ID of the rule that was executed")
    success: bool = Field(description="Whether all actions executed successfully")

    executed_actions: List[str] = Field(
        default_factory=list, description="List of actions that were executed"
    )
    failed_actions: List[str] = Field(
        default_factory=list, description="List of actions that failed"
    )

    injected_content: List[str] = Field(
        default_factory=list, description="Content that was injected into the context"
    )

    execution_time_ms: float = Field(
        default=0.0, description="Total execution time in milliseconds"
    )

    tokens_added: int = Field(
        default=0, description="Number of tokens added to the context"
    )

    error_message: Optional[str] = Field(
        default=None, description="Error message if execution failed"
    )


class ModelRuleSetStatus(BaseModel):
    """Model for the status of a complete rule set evaluation."""

    total_rules_evaluated: int = Field(
        description="Total number of rules that were evaluated"
    )
    rules_matched: int = Field(description="Number of rules that matched conditions")
    rules_executed: int = Field(
        description="Number of rules that executed successfully"
    )

    total_execution_time_ms: float = Field(
        description="Total time for all rule evaluation and execution"
    )

    total_tokens_added: int = Field(
        default=0, description="Total tokens added by all executed rules"
    )

    context_size_before: int = Field(description="Context size before rule processing")
    context_size_after: int = Field(description="Context size after rule processing")

    rule_results: List[ModelRuleMatchResult] = Field(
        default_factory=list, description="Individual results for each rule evaluated"
    )

    execution_results: List[ModelRuleExecutionResult] = Field(
        default_factory=list,
        description="Execution results for rules that were triggered",
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this rule set evaluation occurred",
    )
