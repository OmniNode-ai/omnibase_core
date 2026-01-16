"""Validation warning model for pipeline hooks.

Note: This module was moved from omnibase_core.pipeline.models to
omnibase_core.models.pipeline to comply with ONEX repository structure
validation that requires all models in src/omnibase_core/models/.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelValidationWarning(BaseModel):
    """
    Structured warning for validation issues that don't prevent execution.

    Used when hook typing validation is disabled (enforce_hook_typing=False)
    to report type mismatches without failing.

    Thread Safety: This class is thread-safe. Instances are immutable
    (frozen=True) and can be safely shared across threads.
    """

    # TODO(OMN-TBD): [pydantic-v3] Re-evaluate from_attributes=True when Pydantic v3 is released.
    # Workaround for pytest-xdist class identity issues. See model_pipeline_hook.py
    # module docstring for detailed explanation.  [NEEDS TICKET]
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    code: str = Field(
        ...,
        description="Warning code identifier (e.g., 'HOOK_TYPE_MISMATCH')",
    )
    message: str = Field(
        ...,
        description="Human-readable warning message",
    )
    context: dict[str, object] = Field(
        default_factory=dict,
        description="Additional context for the warning",
    )

    @classmethod
    def hook_type_mismatch(
        cls,
        hook_name: str,
        hook_category: str | None,
        contract_category: str,
    ) -> "ModelValidationWarning":
        """Factory for hook type mismatch warnings."""
        return cls(
            code="HOOK_TYPE_MISMATCH",
            message=f"Hook '{hook_name}' category '{hook_category}' doesn't match contract category '{contract_category}'",
            context={
                "hook_name": hook_name,
                "hook_category": hook_category,
                "contract_category": contract_category,
            },
        )


__all__ = [
    "ModelValidationWarning",
]
