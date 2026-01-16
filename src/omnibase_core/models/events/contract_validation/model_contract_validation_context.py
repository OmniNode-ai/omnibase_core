"""
Contract validation context model.

This model provides context information for contract validation operations,
including the validation mode and extensible flags for customizing
validation behavior.

Note:
    This module was renamed from ``model_validation_context.py`` to
    ``model_contract_validation_context.py`` to avoid filename collision
    with ``omnibase_core.models.context.model_validation_context``.

Pattern: Model<Name> - Pydantic model for validation context
Node Type: N/A (Data Model)

Note:
    This class was renamed from ModelValidationContext to
    ModelContractValidationContext to avoid naming collision with
    ModelValidationContext in models/context/model_validation_context.py,
    which is used for field-level validation context (field_name, expected, actual).

    A legacy alias (``ModelValidationContext = ModelContractValidationContext``)
    was intentionally removed to prevent import ambiguity. Code that previously
    used the alias should be updated to use ``ModelContractValidationContext``
    explicitly.

See Also:
    :class:`omnibase_core.models.context.ModelValidationContext`:
        Field-level validation context (different model, different purpose).
    :class:`omnibase_core.models.validation.ModelContractValidationEvent`:
        Lightweight validation lifecycle events for internal state machines.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_validation_mode import EnumValidationMode

__all__ = ["ModelContractValidationContext"]


class ModelContractValidationContext(BaseModel):
    """
    Context for contract validation operations.

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
        >>> context = ModelContractValidationContext()
        >>> context.mode
        <EnumValidationMode.STRICT: 'strict'>

        >>> context = ModelContractValidationContext(
        ...     mode=EnumValidationMode.PERMISSIVE,
        ...     flags={"skip_schema_validation": True}
        ... )

    Warning:
        Do NOT mutate flags after creation::

            # WRONG - violates immutability contract
            context.flags["new_flag"] = True

            # CORRECT - create new context with updated flags
            new_flags = {**context.flags, "new_flag": True}
            new_context = ModelContractValidationContext(
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
