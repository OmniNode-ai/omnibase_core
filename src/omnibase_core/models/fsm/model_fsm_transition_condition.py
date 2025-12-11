from __future__ import annotations

"""
FSM Transition Condition Model for guard conditions.

Defines condition specifications for FSM state transitions, including
condition types, expressions, and validation logic for determining
valid state transitions.

Specification Reference: docs/architecture/CONTRACT_DRIVEN_NODEREDUCER_V1_0.md
"""

from pydantic import BaseModel, Field


class ModelFSMTransitionCondition(BaseModel):
    """
    Condition specification for FSM state transitions.

    Defines condition types, expressions, and validation logic
    for determining valid state transitions.

    Implements Core protocols:
    - Executable: Execution management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification

    v1.0 Reserved Fields (parsed but NOT executed):
        - retry_count: Parsed, but condition retry NOT executed until v1.1
        - timeout_ms: Parsed, but condition timeout NOT executed until v1.1

    Setting these fields in v1.0 contracts will NOT change runtime behavior.

    Specification Reference: docs/architecture/CONTRACT_DRIVEN_NODEREDUCER_V1_0.md
    """

    condition_name: str = Field(
        default=...,
        description="Unique condition identifier",
    )

    condition_type: str = Field(
        default=...,
        description="Type of condition (expression, custom)",
    )

    expression: str = Field(
        default=...,
        description="3-token expression (field operator value)",
    )

    required: bool = Field(
        default=True,
        description="If false, errors treated as False",
    )

    error_message: str | None = Field(
        default=None,
        description="Custom error message",
    )

    retry_count: int | None = Field(
        default=None,
        description="Reserved for v1.1+",
    )

    timeout_ms: int | None = Field(
        default=None,
        description="Reserved for v1.1+",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol).

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If execution logic fails
        """
        # Update any relevant execution fields
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def serialize(self) -> dict[str, object]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Raises:
            Exception: If validation logic fails
        """
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True


# Export for use
__all__ = ["ModelFSMTransitionCondition"]
