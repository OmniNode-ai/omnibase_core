"""
Task Metadata Model

ONEX-compliant task metadata model with string-only values for better type safety.
"""

from typing import Dict

from pydantic import BaseModel, Field


class ModelTaskMetadata(BaseModel):
    """Task metadata model with string-only values for better type safety."""

    category: str = Field(default="general", description="Task category")

    priority_reason: str = Field(
        default="", description="Reason for priority assignment"
    )

    source_system: str = Field(
        default="unknown", description="System that created the task"
    )

    correlation_id: str = Field(default="", description="Correlation ID for tracking")

    business_context: str = Field(
        default="", description="Business context for the task"
    )

    tags: Dict[str, str] = Field(
        default_factory=dict, description="String key-value tags for categorization"
    )
