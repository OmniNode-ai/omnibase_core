from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.models.services.model_custom_fields import ModelCustomFields

from .model_environment import ModelEnvironment
from .model_feature_flags import ModelFeatureFlags

"\nAdditional Context Model.\n\nType-safe additional context replacing Dict[str, Any]\nwith structured context information.\n"


class ModelAdditionalContext(BaseModel):
    """
    Type-safe additional context replacing Dict[str, Any].

    Provides structured context information with proper typing
    instead of using primitive dict[str, Any]types.
    """

    request_id: UUID | None = Field(
        default=None, description="Unique request identifier"
    )
    user_id: UUID | None = Field(
        default=None, description="User identifier", pattern="^[a-zA-Z0-9_-]+$"
    )
    session_id: UUID | None = Field(default=None, description="Session identifier")
    environment: ModelEnvironment | None = Field(
        default=None, description="Execution environment"
    )
    feature_flags: ModelFeatureFlags | None = Field(
        default=None, description="Feature flag configuration"
    )
    custom_fields: ModelCustomFields | None = Field(
        default=None, description="Custom extension fields"
    )
    trace_id: UUID | None = Field(
        default=None, description="Distributed tracing identifier"
    )
    parent_span_id: UUID | None = Field(
        default=None, description="Parent span identifier for tracing"
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
            contexts.append(f"trace:{str(self.trace_id)[:8]}")
        return " | ".join(contexts) if contexts else "no-context"
