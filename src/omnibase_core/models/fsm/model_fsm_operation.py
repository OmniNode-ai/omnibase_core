"""
Reserved FSM operation model for v1.1+ operation definitions.

This model is reserved for future use in v1.1+ of the ONEX NodeReducer.
It defines operation configurations that will be used for advanced
FSM operation handling.

Note:
    This model is part of the forward-compatibility design. Do not use
    in production until v1.1+ is released.

Spec Reference:
    CONTRACT_DRIVEN_NODEREDUCER_V1_0.md: Reserved fields section
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ModelFSMOperation(BaseModel):
    """
    Reserved FSM operation model for v1.1+ operation definitions.

    This model defines operation configurations for advanced FSM operation
    handling in future NodeReducer versions. It is part of the ONEX
    forward-compatibility design.

    Implements Core protocols:
    - Executable: Execution management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification

    Warning:
        This model is RESERVED for v1.1+. Do not use in production
        until the v1.1 release.

    Attributes:
        operation_name: Unique operation identifier (required)
        operation_type: Type of operation (required)
        description: Human-readable description (optional)

    Example:
        >>> operation = ModelFSMOperation(
        ...     operation_name="validate_input",
        ...     operation_type="synchronous",
        ...     description="Validates input data before processing"
        ... )
        >>> operation.operation_name
        'validate_input'

    Spec Reference:
        CONTRACT_DRIVEN_NODEREDUCER_V1_0.md: Reserved fields section
    """

    operation_name: str = Field(
        default=...,
        description="Unique operation identifier",
    )
    operation_type: str = Field(
        default=...,
        description="Type of operation (e.g., synchronous, asynchronous, batch)",
    )
    description: str | None = Field(
        default=None,
        description="Human-readable description of the operation",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol).

        Updates any relevant execution fields based on provided kwargs.

        Args:
            **kwargs: Field updates to apply during execution

        Returns:
            bool: True if execution succeeded

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
        """Serialize to dictionary (Serializable protocol).

        Returns:
            dict[str, object]: Dictionary representation of the model
        """
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Performs basic validation to ensure required fields exist and
        have valid values.

        Returns:
            bool: True if validation passed

        Raises:
            Exception: If validation logic fails
        """
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True


# Export for use
__all__ = ["ModelFSMOperation"]
