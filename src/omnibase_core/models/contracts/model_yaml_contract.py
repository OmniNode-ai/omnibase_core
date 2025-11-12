from typing import Any, Optional

from pydantic import Field, field_validator

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

"""
YAML Contract Validation Model - ONEX Standards Compliant.

Pydantic model for validating YAML contract files providing:
- Contract version validation with semantic versioning
- Node type classification with EnumNodeType support
- Flexible structure for additional contract data
- Automatic YAML deserialization and validation

This replaces manual YAML field validation with proper Pydantic validation.
"""

from pydantic import BaseModel

from omnibase_core.enums import EnumNodeType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode


class ModelYamlContract(BaseModel):
    """
    YAML contract validation model for basic contract structure validation.

    This model provides validation for the minimum required fields in a YAML contract:
    - contract_version: Semantic version information
    - node_type: Node type classification
    - description: Optional contract description

    Extra fields are ignored to maintain a clean contract structure.
    """

    model_config = {
        "extra": "ignore",  # Ignore extra fields to maintain clean contract structure
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Required fields for contract validation
    contract_version: ModelSemVer = Field(
        default=...,
        description="Contract semantic version specification",
    )

    node_type: EnumNodeType = Field(
        default=...,
        description="Node type classification for 4-node architecture",
    )

    # Optional fields commonly found in contracts
    description: str | None = Field(
        default=None,
        description="Human-readable contract description",
    )

    event_subscriptions: list[dict[str, Any]] | None = Field(
        default=None,
        description="Event subscription patterns for event-driven execution",
    )

    @field_validator("node_type", mode="before")
    @classmethod
    def validate_node_type(cls, value: object) -> EnumNodeType:
        """
        Validate node_type field with proper EnumNodeType conversion.

        Supports:
        - EnumNodeType enum values
        - String values that match EnumNodeType values
        - Legacy "compute" string (maps to COMPUTE)

        Args:
            value: Node type value to validate

        Returns:
            EnumNodeType: Validated enum value

        Raises:
            ModelOnexError: If validation fails
        """
        if isinstance(value, EnumNodeType):
            return value

        if isinstance(value, str):
            # Handle legacy lowercase "compute" mapping
            if value.lower() == "compute":
                return EnumNodeType.COMPUTE

            # Try to match string to EnumNodeType value (case-insensitive)
            value_lower = value.lower()
            try:
                return EnumNodeType(value_lower)
            except ValueError:
                # Try direct name match (case-insensitive)
                for enum_value in EnumNodeType:
                    if enum_value.name.upper() == value.upper():
                        return enum_value

                # Create proper error context
                from omnibase_core.models.common.model_error_context import (
                    ModelErrorContext,
                )
                from omnibase_core.models.common.model_schema_value import (
                    ModelSchemaValue,
                )

                error_context = ModelErrorContext.with_context(
                    {
                        "provided_value": ModelSchemaValue.from_value(value),
                        "valid_options": ModelSchemaValue.from_value(
                            [e.value for e in EnumNodeType],
                        ),
                        "enum_names": ModelSchemaValue.from_value(
                            [e.name for e in EnumNodeType],
                        ),
                    },
                )

                raise ModelOnexError(
                    message=f"Invalid node_type '{value}'. Must be a valid EnumNodeType value.",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=error_context,
                )

        # Create proper error context
        from omnibase_core.models.common.model_error_context import ModelErrorContext
        from omnibase_core.models.common.model_schema_value import ModelSchemaValue

        error_context = ModelErrorContext.with_context(
            {
                "provided_type": ModelSchemaValue.from_value(type(value).__name__),
                "provided_value": ModelSchemaValue.from_value(str(value)),
                "expected_types": ModelSchemaValue.from_value(["EnumNodeType", "str"]),
            },
        )

        raise ModelOnexError(
            message=f"node_type must be an EnumNodeType enum or valid string, got {type(value).__name__}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            details=error_context,
        )

    @classmethod
    def validate_yaml_content(cls, yaml_data: dict[str, object]) -> "ModelYamlContract":
        """
        Validate YAML content using Pydantic model validation.

        This is the primary method for validating YAML contract content,
        replacing manual field checking with proper Pydantic validation.

        Args:
            yaml_data: Dictionary loaded from YAML file

        Returns:
            ModelYamlContract: Validated contract instance

        Raises:
            ValidationError: If validation fails
            ModelOnexError: For custom validation errors
        """
        return cls.model_validate(yaml_data)

    @classmethod
    def from_yaml_dict(cls, yaml_data: dict[str, object]) -> "ModelYamlContract":
        """
        Alternative constructor for YAML dictionary data.

        Args:
            yaml_data: Dictionary loaded from YAML file

        Returns:
            ModelYamlContract: Validated contract instance
        """
        return cls.validate_yaml_content(yaml_data)
