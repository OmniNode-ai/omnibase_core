"""
Result model for override application.

.. versionadded:: 0.4.0
    Added Configuration Override Injection (OMN-1205)
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelConfigOverrideResult"]


class ModelConfigOverrideResult(BaseModel):
    """
    Result of applying configuration overrides.

    Contains the new (patched) configuration and application metadata.
    Original config is NEVER modified - this contains a new copy.

    Thread Safety:
        Immutable - the patched_config is a deep copy, safe to use concurrently.
    """

    # from_attributes=True: Enables construction from ORM/dataclass instances
    # and ensures pytest-xdist compatibility across worker processes where
    # class identity may differ due to independent imports.
    # See CLAUDE.md "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    success: bool = Field(..., description="Whether all overrides were applied")
    patched_config: Any = Field(
        ..., description="New config with overrides applied (deep copy)"
    )
    overrides_applied: int = Field(
        default=0, description="Number of overrides successfully applied"
    )
    paths_created: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Paths that were created (did not exist before)",
    )
    errors: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Any errors during override application",
    )
