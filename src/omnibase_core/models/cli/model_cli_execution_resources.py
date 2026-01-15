"""
CLI Execution Resources Model.

Resource limits and constraints for CLI command execution.
Part of the ModelCliExecution restructuring to reduce excessive string fields.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types.type_serializable_value import SerializedDict


class ModelCliExecutionResources(BaseModel):
    """
    CLI execution resource management.

    Contains resource limits, constraints, and user/session tracking
    for CLI command execution without cluttering core execution info.
    Implements Core protocols:
    - Serializable: Data serialization/deserialization
    - Nameable: Name management interface
    - Validatable: Validation and verification
    """

    # Resource limits and configuration
    timeout_seconds: int | None = Field(
        default=None,
        description="Execution timeout",
        ge=1,
    )
    max_memory_mb: int | None = Field(
        default=None,
        description="Memory limit in MB",
        ge=1,
    )
    max_retries: int = Field(default=0, description="Maximum retry attempts", ge=0)
    retry_count: int = Field(default=0, description="Current retry count", ge=0)

    # User and session information
    user_id: UUID | None = Field(default=None, description="User identifier")
    session_id: UUID | None = Field(default=None, description="Session identifier")

    def is_timed_out(self, elapsed_seconds: float) -> bool:
        """Check if execution timed out."""
        if self.timeout_seconds is None:
            return False
        return elapsed_seconds > self.timeout_seconds

    def increment_retry(self) -> bool:
        """Increment retry count and check if more retries available."""
        self.retry_count += 1
        return self.retry_count <= self.max_retries

    def can_attempt_retry(self) -> bool:
        """Check if retries are still available."""
        return self.retry_count < self.max_retries

    def reset_retries(self) -> None:
        """Reset retry counter."""
        self.retry_count = 0

    def set_user_context(self, user_id: UUID, session_id: UUID | None = None) -> None:
        """Set user and session context."""
        self.user_id = user_id
        self.session_id = session_id

    @classmethod
    def create_unlimited(cls) -> ModelCliExecutionResources:
        """Create resources with no limits."""
        return cls()

    @classmethod
    def create_limited(
        cls,
        timeout_seconds: int = 300,
        max_memory_mb: int = 1024,
        max_retries: int = 3,
    ) -> ModelCliExecutionResources:
        """Create resources with specified limits."""
        return cls(
            timeout_seconds=timeout_seconds,
            max_memory_mb=max_memory_mb,
            max_retries=max_retries,
        )

    @classmethod
    def create_quick(cls) -> ModelCliExecutionResources:
        """Create resources for quick operations."""
        return cls(
            timeout_seconds=30,
            max_memory_mb=256,
            max_retries=1,
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def get_name(self) -> str:
        """Get name (Nameable protocol)."""
        # Try common name field patterns
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        return f"Unnamed {self.__class__.__name__}"

    def set_name(self, name: str) -> None:
        """Set name (Nameable protocol)."""
        # Try to set the most appropriate name field
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                setattr(self, field, name)
                return

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Raises:
            Exception: If validation logic fails
        """
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True


# Export for use
__all__ = ["ModelCliExecutionResources"]
