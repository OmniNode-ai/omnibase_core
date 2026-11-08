# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

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

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums import EnumSeverity

# Type alias for rule parameter values to avoid inline union soup.
# Supports common JSON-serializable primitive types.
type RuleParameterValue = str | int | float | bool | list[str]

# Type alias for the parameters dictionary used in validator rules.
type RuleParameterDict = dict[str, RuleParameterValue]


_HANDLER_REFERENCE = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*:[A-Za-z_][A-Za-z0-9_]*"
)


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

    severity: EnumSeverity = Field(
        default=EnumSeverity.ERROR,
        description="Severity level for violations of this rule",
    )

    enabled: bool = Field(
        default=True,
        description="Whether this rule is active",
    )

    parameters: RuleParameterDict | None = Field(
        default=None,
        description="Rule-specific configuration parameters",
    )

    handler: str | None = Field(
        default=None,
        description=(
            "A rule that cannot be data is a handler bound through the contract: "
            "'<dotted.module>:<callable>'. The generic validator resolves it with "
            "resolve_rule_handler; a rule with no handler is judged by its parameters alone."
        ),
    )

    @field_validator("handler")
    @classmethod
    def _handler_is_a_module_callable_reference(cls, value: str | None) -> str | None:
        if value is not None and not _HANDLER_REFERENCE.fullmatch(value):
            raise ValueError(
                f"handler {value!r} is not '<dotted.module>:<callable>' "
                "(a handler is bound by module path and name, never by file path or expression)"
            )
        return value

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_enum_values=False,
        from_attributes=True,
    )


__all__ = ["ModelValidatorRule", "RuleParameterDict", "RuleParameterValue"]
