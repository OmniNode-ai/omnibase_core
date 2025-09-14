"""
Model Workflow Dependency Config - ONEX Standards Compliant Configuration Model.

Strongly-typed configuration model for workflow dependency configuration that eliminates
dict-based config support and enforces structured configuration patterns.

ZERO TOLERANCE: No dict configs or Any types allowed.
"""

from pydantic import BaseModel, Field, field_validator

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError


class ModelWorkflowDependencyConfig(BaseModel):
    """
    Strongly-typed workflow dependency configuration.

    Replaces dict-based model_config with structured configuration model
    that enables proper validation, type safety, and architectural consistency.

    ZERO TOLERANCE: No dict configs or Any types allowed.
    """

    extra_fields_behavior: str = Field(
        default="ignore",
        description="How to handle extra fields in input data",
    )

    use_enum_values: bool = Field(
        default=False,
        description="Whether to use enum values for serialization or keep enum objects",
    )

    validate_assignment: bool = Field(
        default=True,
        description="Whether to validate field assignments after model creation",
    )

    strip_whitespace: bool = Field(
        default=True,
        description="Whether to strip whitespace from string fields",
    )

    frozen: bool = Field(
        default=False,
        description="Whether the model should be immutable after creation",
    )

    populate_by_name: bool = Field(
        default=False,
        description="Whether to populate fields by their field names or aliases",
    )

    use_list: bool = Field(
        default=True,
        description="Whether to use list type for array-like fields",
    )

    json_schema_serialization_defaults_required: bool = Field(
        default=False,
        description="Whether default values should be included in JSON schema",
    )

    @field_validator("extra_fields_behavior")
    @classmethod
    def validate_extra_fields_behavior(cls, v: str) -> str:
        """Validate extra fields behavior is a valid option."""
        valid_behaviors = {"ignore", "allow", "forbid"}

        if v not in valid_behaviors:
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"Invalid extra_fields_behavior '{v}'. Must be one of: {valid_behaviors}",
                context={
                    "context": {
                        "received_value": v,
                        "valid_values": list(valid_behaviors),
                        "onex_principle": "Strong types only - no arbitrary string values",
                    }
                },
            )

        return v

    def to_pydantic_config_dict(self) -> dict[str, any]:
        """
        Convert to Pydantic model_config dictionary format.

        This method provides compatibility with Pydantic's expected config format
        while maintaining strong typing in the configuration definition.

        Returns:
            Dictionary suitable for Pydantic model_config
        """
        return {
            "extra": self.extra_fields_behavior,
            "use_enum_values": self.use_enum_values,
            "validate_assignment": self.validate_assignment,
            "str_strip_whitespace": self.strip_whitespace,
            "frozen": self.frozen,
            "populate_by_name": self.populate_by_name,
            "use_list": self.use_list,
            "json_schema_serialization_defaults_required": self.json_schema_serialization_defaults_required,
        }
