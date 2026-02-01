"""
Example context data model.

Clean, strongly-typed replacement for dict[str, Any] in example context data.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_context_type import EnumContextType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_environment import EnumEnvironment
from omnibase_core.enums.enum_execution_trigger import EnumExecutionTrigger
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelExampleContextData(BaseModel):
    """
    Clean model for example context data.

    Replaces dict[str, Any] with structured context model.
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Core context fields
    context_type: EnumContextType = Field(
        default=EnumContextType.USER,
        description="Type of context",
    )
    environment: EnumEnvironment = Field(
        default=EnumEnvironment.DEVELOPMENT,
        description="Environment context",
    )

    # Execution context
    execution_mode: EnumExecutionTrigger = Field(
        default=EnumExecutionTrigger.AUTO,
        description="Execution trigger mode",
    )
    timeout_seconds: float = Field(default=30.0, description="Timeout in seconds")

    # Environment variables and settings
    environment_variables: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables",
    )

    # Configuration context - using str values for simplicity and type safety
    configuration_overrides: dict[str, str] = Field(
        default_factory=dict,
        description="Configuration overrides (string values)",
    )

    # User and session context
    user_id: UUID | None = Field(default=None, description="UUID of the user")
    user_display_name: str = Field(default="", description="Human-readable user name")
    session_id: UUID | None = Field(default=None, description="Session identifier")

    # Additional metadata
    tags: list[str] = Field(default_factory=list, description="Context tags")
    notes: str = Field(default="", description="Additional context notes")

    # Version info
    schema_version: ModelSemVer | None = Field(
        default=None,
        description="Schema version for validation",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, TypeError, ValueError) as e:
            raise ModelOnexError(
                message=f"Operation failed: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (AttributeError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e


__all__ = ["ModelExampleContextData"]
