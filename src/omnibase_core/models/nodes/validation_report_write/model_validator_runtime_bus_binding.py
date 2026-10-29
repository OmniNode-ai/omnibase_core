# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The bus binding of a validator-runtime overlay (OMN-21529)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelValidatorRuntimeBusBinding"]


class ModelValidatorRuntimeBusBinding(BaseModel):
    """Which bus the validator runtime binds: the one thing the overlays differ in."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    implementation: str = Field(
        pattern=r"^[A-Za-z_][\w.]*:[A-Za-z_]\w*$",
        description="Bus class as 'module:Class'.",
    )
    constructor: str | None = Field(
        default=None,
        description="Class method that builds the bus; the class itself when absent.",
    )
    argument: str | None = Field(
        default=None,
        description="One argument for the constructor; '${env.NAME}' references expand.",
    )
