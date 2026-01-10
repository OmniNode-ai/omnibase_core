"""
Validator Rule Model.

Schema version: v1.0.0

Individual validation rule configuration model for file-based validators.
Defines a single validation rule with its severity, enabled state,
and optional rule-specific parameters.

This model is used by ModelValidatorSubcontract to configure
individual validation rules within a validator.

Instances are immutable after creation (frozen=True), enabling safe sharing
across threads without synchronization.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_validation_severity import EnumValidationSeverity


class ModelValidatorRule(BaseModel):
    """
    Individual validation rule configuration.

    Defines a single validation rule with its severity, enabled state,
    and optional rule-specific parameters.

    Schema Version:
        v1.0.0 - Initial version.

    Immutability and Thread Safety:
        This model uses frozen=True (Pydantic ConfigDict), making instances
        immutable after creation. This provides thread safety guarantees.

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # ONEX_EXCLUDE: string_id - human-readable rule identifier for YAML config
    rule_id: str = Field(
        ...,
        description="Unique identifier for this rule",
        min_length=1,
    )

    description: str = Field(
        ...,
        description="Human-readable description of what this rule checks",
        min_length=1,
    )

    severity: EnumValidationSeverity = Field(
        default=EnumValidationSeverity.ERROR,
        description="Severity level for violations of this rule",
    )

    enabled: bool = Field(
        default=True,
        description="Whether this rule is active",
    )

    parameters: dict[str, str | int | float | bool | list[str]] | None = Field(
        default=None,
        description="Rule-specific configuration parameters",
    )

    model_config = ConfigDict(
        extra="ignore",
        frozen=True,
        use_enum_values=False,
        from_attributes=True,
    )


__all__ = ["ModelValidatorRule"]
