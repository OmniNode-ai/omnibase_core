# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Result model for override application.

.. versionadded:: 0.4.0
    Added Configuration Override Injection (OMN-1205)
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelConfigOverrideResult(BaseModel):
    """
    Result of applying configuration overrides.

    Contains the new (patched) configuration and application metadata.
    Original config is NEVER modified - this contains a new copy.

    Thread Safety:
        Immutable - the patched_config is a deep copy, safe to use concurrently.
    """

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
