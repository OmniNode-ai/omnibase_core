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
        This model is frozen (immutable) after creation, making it thread-safe
        for concurrent read access. However:

        - **Safe**: Reading any field from multiple threads simultaneously
        - **Safe**: Passing context between threads without synchronization
        - **WARNING**: The ``flags`` dict is mutable even though the model is frozen.
          Do NOT mutate the dict contents after creation - this violates the
          immutability contract and could cause race conditions.

    Attributes:
        mode: Validation mode controlling strictness level (default: STRICT).
        flags: Extensible key-value flags for fine-grained validation control.
            **WARNING**: While the flags field cannot be reassigned, the dict
            contents are still mutable. Callers MUST NOT modify flags after
            context creation.

    Example:
        >>> context = ModelValidationContext()
        >>> context.mode
        <EnumValidationMode.STRICT: 'strict'>

        >>> context = ModelValidationContext(
        ...     mode=EnumValidationMode.PERMISSIVE,
        ...     flags={"skip_schema_validation": True}
        ... )

    Warning:
        Do NOT mutate flags after creation::

            # WRONG - violates immutability contract
            context.flags["new_flag"] = True

            # CORRECT - create new context with updated flags
            new_flags = {**context.flags, "new_flag": True}
            new_context = ModelValidationContext(
                mode=context.mode,
                flags=new_flags,
            )
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
