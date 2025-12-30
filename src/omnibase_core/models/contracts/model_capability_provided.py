# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
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
        """Validate capability name format."""
        v = v.strip()
        if not v:
            raise ValueError("Capability name cannot be empty")

        # Capability names should be lowercase with underscores
        if not all(c.isalnum() or c == "_" for c in v):
            raise ValueError(
                f"Capability name must contain only alphanumeric characters "
                f"and underscores: {v}"
            )

        return v

    def matches(self, requirement_name: str) -> bool:
        """Check if this capability matches a requirement name.

        Args:
            requirement_name: Name of the required capability.

        Returns:
            True if names match (case-insensitive).
        """
        return self.name.lower() == requirement_name.lower()

    def __repr__(self) -> str:
        """Return a concise representation for debugging."""
        version_str = f", version={self.version!r}" if self.version else ""
        return f"ModelCapabilityProvided(name={self.name!r}{version_str})"
