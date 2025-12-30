"""Validation warning model for pipeline hooks."""

from pydantic import BaseModel, ConfigDict, Field


class ModelValidationWarning(BaseModel):
    """
    Structured warning for validation issues that don't prevent execution.

    Used when hook typing validation is disabled (enforce_hook_typing=False)
    to report type mismatches without failing.
    """

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
        hook_id: str,
        hook_category: str | None,
        contract_category: str,
    ) -> "ModelValidationWarning":
        """Factory for hook type mismatch warnings."""
        return cls(
            code="HOOK_TYPE_MISMATCH",
            message=f"Hook '{hook_id}' category '{hook_category}' doesn't match contract category '{contract_category}'",
            context={
                "hook_id": hook_id,
                "hook_category": hook_category,
                "contract_category": contract_category,
            },
        )
