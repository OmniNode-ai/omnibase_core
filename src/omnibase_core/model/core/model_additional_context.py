"""
Additional Context Model.

Type-safe additional context replacing Dict[str, Any]
with structured context information.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .model_custom_fields import ModelCustomFields
from .model_environment import ModelEnvironment
from .model_feature_flags import ModelFeatureFlags


class ModelAdditionalContext(BaseModel):
    """
    Type-safe additional context replacing Dict[str, Any].

    Provides structured context information with proper typing
    instead of using primitive dict types.
    """

    request_id: Optional[UUID] = Field(None, description="Unique request identifier")
    user_id: Optional[str] = Field(
        None, description="User identifier", pattern="^[a-zA-Z0-9_-]+$"
    )
    session_id: Optional[UUID] = Field(None, description="Session identifier")
    environment: Optional[ModelEnvironment] = Field(
        None, description="Execution environment"
    )
    feature_flags: Optional[ModelFeatureFlags] = Field(
        None, description="Feature flag configuration"
    )
    custom_fields: Optional[ModelCustomFields] = Field(
        None, description="Custom extension fields"
    )
    trace_id: Optional[str] = Field(None, description="Distributed tracing identifier")
    parent_span_id: Optional[str] = Field(
        None, description="Parent span identifier for tracing"
    )

    def has_tracing_context(self) -> bool:
        """Check if tracing context is available."""
        return self.trace_id is not None

    def has_user_context(self) -> bool:
        """Check if user context is available."""
        return self.user_id is not None or self.session_id is not None

    def get_context_summary(self) -> str:
        """Get a summary of available context."""
        contexts = []

        if self.request_id:
            contexts.append(f"request:{str(self.request_id)[:8]}")

        if self.user_id:
            contexts.append(f"user:{self.user_id}")

        if self.environment:
            contexts.append(f"env:{self.environment.name}")

        if self.trace_id:
            contexts.append(f"trace:{self.trace_id[:8]}")

        return " | ".join(contexts) if contexts else "no-context"
