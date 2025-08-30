"""
Packed Context Model for Autonomous Development

Complete packed context model for autonomous agent processing.
"""

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.model.autonomous.model_context_source import ModelContextSource


class ModelPackedContext(BaseModel):
    """Complete packed context for autonomous agent processing."""

    scenario_id: str = Field(..., description="Unique identifier for the scenario")
    problem_domain: str = Field(..., description="Domain category for the problem")
    primary_context: str = Field(..., description="Primary context description")
    related_contexts: list[ModelContextSource] = Field(
        default_factory=list,
        description="List of related context sources",
    )
    code_patterns: list[str] = Field(
        default_factory=list,
        description="Extracted code patterns",
    )
    previous_solutions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Previous solution patterns",
    )
    failure_patterns: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Known failure patterns to avoid",
    )
    success_patterns: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Proven success patterns",
    )
    architecture_constraints: list[str] = Field(
        default_factory=list,
        description="Architectural constraints that must be followed",
    )
    total_context_size: int = Field(
        ...,
        ge=0,
        description="Total size of packed context in tokens",
    )
    relevance_ranking: list[tuple[str, float]] = Field(
        default_factory=list,
        description="File path and relevance score tuples",
    )
    processing_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about context processing",
    )
