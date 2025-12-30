# SPDX-FileCopyrightText: 2025 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0

"""
Validation context model for contract validation.

This model provides context information for validation operations,
including the validation mode and extensible flags for customizing
validation behavior.

Pattern: Model<Name> - Pydantic model for validation context
Node Type: N/A (Data Model)
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_validation_mode import EnumValidationMode

__all__ = ["ModelValidationContext"]


class ModelValidationContext(BaseModel):
    """
    Context for validation operations.

    Provides configuration for validation behavior including the validation
    mode and extensible flags for customizing specific validation rules.

    Thread Safety:
        This model is frozen (immutable) after creation.

    Attributes:
        mode: Validation mode controlling strictness level (default: STRICT).
        flags: Extensible key-value flags for fine-grained validation control.

    Example:
        >>> context = ModelValidationContext()
        >>> context.mode
        <EnumValidationMode.STRICT: 'strict'>

        >>> context = ModelValidationContext(
        ...     mode=EnumValidationMode.PERMISSIVE,
        ...     flags={"skip_schema_validation": True}
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    mode: EnumValidationMode = Field(
        default=EnumValidationMode.STRICT,
        description="Validation mode controlling strictness level",
    )
    flags: dict[str, bool] = Field(
        default_factory=dict,
        description="Extensible flags for fine-grained validation control",
    )
