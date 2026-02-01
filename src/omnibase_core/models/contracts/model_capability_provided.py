"""
Capability Provided Model.

Declaration of capabilities that a handler/contract provides as outputs.
Part of the contract patching system for OMN-1126.

Related:
    - OMN-1126: ModelContractPatch & Patch Validation
    - OMN-1152: ModelCapabilityDependency (inputs)

.. versionadded:: 0.4.0
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.validation.validator_utils import is_valid_onex_name

__all__ = [
    "ModelCapabilityProvided",
]


class ModelCapabilityProvided(BaseModel):
    """Declaration of capabilities that a handler/contract provides.

    Capability provided declarations specify what capabilities a handler
    or contract makes available to consumers. These are matched against
    ModelCapabilityDependency requirements during contract resolution.

    Attributes:
        name: Capability identifier (e.g., "event_emit", "http_response").
        version: Optional capability version (e.g., "1.0.0").
        description: Optional human-readable description.

    Example:
        >>> cap = ModelCapabilityProvided(
        ...     name="event_emit",
        ...     version="1.0.0",
        ...     description="Emits domain events to the event bus",
        ... )

    See Also:
        - ModelContractPatch: Uses this for capability_outputs__add field
        - ModelCapabilityDependency (OMN-1152): For capability requirements
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(
        ...,
        min_length=1,
        description=(
            "Capability identifier (e.g., 'event_emit', 'http_response'). "
            "Used for capability matching and routing. "
            "Leading/trailing whitespace is automatically stripped."
        ),
    )

    version: str | None = Field(
        default=None,
        description="Capability version constraint (e.g., '1.0.0').",
    )

    description: str | None = Field(
        default=None,
        description="Human-readable description of the capability.",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and normalize capability name format.

        Capability names must be non-empty and contain only alphanumeric
        characters and underscores. Leading and trailing whitespace is
        stripped before validation. Names are normalized to lowercase for
        consistent matching across the system.

        Uses shared validation utilities from omnibase_core.validation.

        Args:
            v: The raw capability name string.

        Returns:
            The validated, stripped, and lowercased capability name.

        Raises:
            ValueError: If the name is empty or contains invalid characters.
        """
        v = v.strip()
        if not v:
            raise ValueError("Capability name cannot be empty")

        # Use shared ONEX name validation (alphanumeric + underscores)
        if not is_valid_onex_name(v):
            raise ValueError(
                f"Capability name must contain only alphanumeric characters "
                f"and underscores: {v}"
            )

        # Normalize to lowercase for consistent matching
        return v.lower()

    def matches(self, requirement_name: str) -> bool:
        """Check if this capability matches a requirement name.

        Performs case-insensitive comparison. The requirement_name is
        lowercased before comparison since self.name is already stored
        in lowercase (normalized during validation).

        Args:
            requirement_name: Name of the required capability.

        Returns:
            True if names match (case-insensitive).
        """
        # self.name is already lowercase (normalized in validate_name)
        return self.name == requirement_name.lower()

    def __repr__(self) -> str:
        """Return a concise representation for debugging."""
        version_str = f", version={self.version!r}" if self.version else ""
        return f"ModelCapabilityProvided(name={self.name!r}{version_str})"
