# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Validation warning model for pipeline hooks."""

from pydantic import BaseModel, ConfigDict, Field


class ModelValidationWarning(BaseModel):
    """
    Structured warning for validation issues that don't prevent execution.

    Used when hook typing validation is disabled (enforce_hook_typing=False)
    to report type mismatches without failing.

    Thread Safety: This class is thread-safe. Instances are immutable
    (frozen=True) and can be safely shared across threads.
    """

    # TODO(pydantic-v3): Re-evaluate from_attributes=True when Pydantic v3 is released.
    # Workaround for pytest-xdist class identity issues. See model_pipeline_hook.py
    # module docstring for detailed explanation.
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
