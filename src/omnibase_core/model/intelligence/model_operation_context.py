"""
Operation context model - Strongly typed operation context structure.

Replaces Dict[str, Any] usage with strongly typed operation context information.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ModelOperationContext(BaseModel):
    """Strongly typed operation context."""

    operation_id: str = Field(description="Unique operation identifier")
    operation_type: str = Field(description="Type of operation being performed")
    initiator_id: Optional[str] = Field(
        default=None, description="Who initiated the operation"
    )
    parent_operation_id: Optional[str] = Field(
        default=None, description="Parent operation if nested"
    )
    execution_environment: str = Field(description="Environment where operation runs")
    resource_constraints: List[str] = Field(
        default_factory=list, description="Resource constraints for operation"
    )
    security_context: Optional[str] = Field(
        default=None, description="Security context identifier"
    )
    started_at: datetime = Field(
        default_factory=datetime.utcnow, description="Operation start time"
    )
    expected_duration_seconds: Optional[int] = Field(
        default=None, description="Expected operation duration"
    )
