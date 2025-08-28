"""
Event Input State Model.

Type-safe model for input state in event metadata,
replacing Dict[str, Any] usage with proper model.
"""

from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase.core.models.model_semver import ModelSemVer


class ModelEventInputState(BaseModel):
    """
    Type-safe input state for event metadata.

    Replaces Dict[str, Any] with structured model for better validation
    and type safety.
    """

    action: Optional[str] = Field(None, description="Action being performed")
    parameters: Dict[str, Union[str, int, bool, float, List[str]]] = Field(
        default_factory=dict, description="Action parameters"
    )
    node_version: Optional[ModelSemVer] = Field(
        None, description="Node version for this input"
    )
    correlation_id: Optional[UUID] = Field(
        None, description="Correlation ID for tracing"
    )
    timeout_ms: Optional[int] = Field(None, description="Execution timeout", ge=0)

    def get_parameter(self, key: str, default: Any = None) -> Any:
        """Get parameter value with default."""
        return self.parameters.get(key, default)
