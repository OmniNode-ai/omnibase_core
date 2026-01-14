# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
ModelSubjectRef - Typed reference for subject identity in memory snapshots.

Defines the ModelSubjectRef model which represents a reference to the subject
(owner) of a memory snapshot. Supports multiple identifier types (UUID or string)
and optional organizational grouping via namespace.

This is a pure data model with no side effects.

.. versionadded:: 0.6.0
    Added as part of OmniMemory subject reference infrastructure (OMN-1238)
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_subject_type import EnumSubjectType


class ModelSubjectRef(BaseModel):
    """Reference to the subject that owns a memory snapshot.

    Provides a type-safe way to identify and reference subjects (owners) of
    memory snapshots. Supports flexible identifier types (UUID or string) and
    optional organizational grouping through namespaces.

    Attributes:
        subject_type: The type of subject (agent, user, workflow, etc.).
        subject_id: Unique identifier for the subject (UUID or string).
        namespace: Optional organizational grouping for multi-tenant scenarios.
        subject_key: Optional human-readable key for the subject.

    Example:
        >>> from uuid import uuid4
        >>> ref = ModelSubjectRef(
        ...     subject_type=EnumSubjectType.AGENT,
        ...     subject_id=uuid4(),
        ...     namespace="production",
        ...     subject_key="data-processor-v2",
        ... )
        >>> ref.subject_type
        <EnumSubjectType.AGENT: 'agent'>

        >>> # With string ID
        >>> ref_str = ModelSubjectRef(
        ...     subject_type=EnumSubjectType.USER,
        ...     subject_id="user-12345",
        ... )
        >>> ref_str.subject_id
        'user-12345'

    .. versionadded:: 0.6.0
        Added as part of OmniMemory subject reference infrastructure (OMN-1238)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # === Required Fields ===

    subject_type: EnumSubjectType = Field(
        ...,
        description="Type of subject (agent, user, workflow, etc.)",
    )

    subject_id: UUID | str = Field(
        ...,
        description="Subject identifier (UUID or string)",
    )

    # === Optional Fields ===

    namespace: str | None = Field(
        default=None,
        description="Optional organizational grouping for multi-tenant scenarios",
    )

    subject_key: str | None = Field(
        default=None,
        description="Human-readable key for the subject",
    )

    # === Validators ===

    @field_validator("subject_id")
    @classmethod
    def validate_subject_id_not_empty(cls, v: UUID | str) -> UUID | str:
        """Ensure string subject_id is not empty.

        Args:
            v: The subject_id value to validate.

        Returns:
            The validated subject_id.

        Raises:
            ValueError: If the subject_id is an empty string.
        """
        if isinstance(v, str) and len(v) == 0:
            raise ValueError(
                "subject_id cannot be an empty string. Provide a non-empty identifier."
            )
        return v

    # === Utility Methods ===

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        parts = [f"{self.subject_type.value}:{self.subject_id}"]
        if self.namespace:
            parts.insert(0, self.namespace)
        return "/".join(parts)

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelSubjectRef(subject_type={self.subject_type!r}, "
            f"subject_id={self.subject_id!r}, "
            f"namespace={self.namespace!r}, "
            f"subject_key={self.subject_key!r})"
        )


# Export for use
__all__ = ["ModelSubjectRef"]
