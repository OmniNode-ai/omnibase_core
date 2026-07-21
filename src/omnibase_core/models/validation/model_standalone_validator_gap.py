# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Standalone-workflow validator classification gap model (OMN-14430).

Represents a single gap between the standalone-validator debt registry
(``architecture-handshakes/standalone-validator-debt.yaml``) and the live set of
``.github/workflows/validator-*.yml`` files: an undeclared decorative validator,
or a stale registry entry that no longer matches a live file.

Related ticket: OMN-14430.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelStandaloneValidatorGap"]


class ModelStandaloneValidatorGap(BaseModel):
    """A single standalone-validator-workflow classification gap."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    workflow_file: str = Field(
        description="The .github/workflows/validator-*.yml file name this gap concerns"
    )
    detail: str = Field(description="Human-readable detail describing the gap")
