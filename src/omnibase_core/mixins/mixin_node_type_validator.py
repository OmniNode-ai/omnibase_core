"""
Node Type Validator Mixin.

Provides shared node_type validation logic for contract models:
- Architecture type to node type mapping
- Flexible input format support (enum, string, architecture type)
- Consistent error handling with ModelOnexError

This implementation does not use Any types.
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import field_validator

from omnibase_core.enums import EnumNodeType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_node_architecture_type import EnumNodeArchitectureType


class MixinNodeTypeValidator:
    """
    Mixin providing shared node_type validation logic for contract models.

    This mixin provides:
    - _ARCH_TO_NODE_TYPE: Mapping from architecture type strings to EnumNodeType
    - validate_node_type_architecture: Field validator for node_type field

    Subclasses should define their own _DEFAULT_NODE_TYPE class variable to specify
    the default node type when EnumNodeArchitectureType is provided.

    This implementation does not use Any types.
    """

    # Mapping from architecture type strings to EnumNodeType
    _ARCH_TO_NODE_TYPE: ClassVar[dict[str, EnumNodeType]] = {
        "compute": EnumNodeType.COMPUTE_GENERIC,
        "effect": EnumNodeType.EFFECT_GENERIC,
        "reducer": EnumNodeType.REDUCER_GENERIC,
        "orchestrator": EnumNodeType.ORCHESTRATOR_GENERIC,
    }

    # Default node type for this contract - subclasses should override
    _DEFAULT_NODE_TYPE: ClassVar[EnumNodeType] = EnumNodeType.COMPUTE_GENERIC

    @field_validator("node_type", mode="before")
    @classmethod
    def validate_node_type_architecture(cls, v: object) -> EnumNodeType:
        """
        Validate and convert node_type field values to EnumNodeType.

        Accepts multiple input formats for flexibility in YAML contracts:
        - EnumNodeArchitectureType enum values (mapped to contract-specific default)
        - EnumNodeType enum values (passed through unchanged)
        - Lowercase architecture type strings: "compute", "effect", "reducer", "orchestrator"
        - Valid EnumNodeType string values (e.g., "COMPUTE_GENERIC")

        Lowercase strings are mapped to their generic node types:
        - "compute" -> EnumNodeType.COMPUTE_GENERIC
        - "effect" -> EnumNodeType.EFFECT_GENERIC
        - "reducer" -> EnumNodeType.REDUCER_GENERIC
        - "orchestrator" -> EnumNodeType.ORCHESTRATOR_GENERIC

        Args:
            v: The raw node_type value from YAML or direct input

        Returns:
            EnumNodeType: The validated and converted node type

        Raises:
            ModelOnexError: If the value is invalid or cannot be converted

        Examples:
            >>> validate_node_type_architecture("compute")
            EnumNodeType.COMPUTE_GENERIC
            >>> validate_node_type_architecture("COMPUTE_GENERIC")
            EnumNodeType.COMPUTE_GENERIC
            >>> validate_node_type_architecture(EnumNodeType.COMPUTE_GENERIC)
            EnumNodeType.COMPUTE_GENERIC
        """
        # Runtime imports to avoid circular import
        from omnibase_core.models.common.model_error_context import ModelErrorContext
        from omnibase_core.models.common.model_schema_value import ModelSchemaValue
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        # Handle EnumNodeArchitectureType - return contract-specific default
        if isinstance(v, EnumNodeArchitectureType):
            return cls._DEFAULT_NODE_TYPE

        # Handle EnumNodeType - pass through unchanged
        if isinstance(v, EnumNodeType):
            return v

        # Handle string input
        if isinstance(v, str):
            # Try architecture type mapping first (lowercase)
            if v.lower() in cls._ARCH_TO_NODE_TYPE:
                return cls._ARCH_TO_NODE_TYPE[v.lower()]
            # Try exact match first, then uppercase (for case-insensitive YAML support)
            try:
                return EnumNodeType(v)
            except ValueError:
                try:
                    return EnumNodeType(v.upper())
                except ValueError as e:
                    raise ModelOnexError(
                        message=f"Invalid node_type: {v}",
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        details=ModelErrorContext.with_context(
                            {
                                "error_type": ModelSchemaValue.from_value("valueerror"),
                                "validation_context": ModelSchemaValue.from_value(
                                    "model_validation",
                                ),
                            },
                        ),
                    ) from e

        # Invalid type
        raise ModelOnexError(
            message=f"Invalid node_type: {v}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            details=ModelErrorContext.with_context(
                {
                    "error_type": ModelSchemaValue.from_value("valueerror"),
                    "validation_context": ModelSchemaValue.from_value(
                        "model_validation",
                    ),
                },
            ),
        )
