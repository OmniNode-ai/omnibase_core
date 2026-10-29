# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Rule data of the node-home ratchet (OMN-21495)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelNodeHomeRules(BaseModel):
    """Which contract declaration admits a node directory, and the refusal text."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    declaration_field: str = Field(
        min_length=1,
        description="Top-level contract.yaml field whose list of strings declares the node's category",
    )
    admitted_declarations: frozenset[str] = Field(
        min_length=1,
        description="Declared categories (validator or validator-support) that admit a node directory",
    )
    remediation: str = Field(
        min_length=1,
        description="Text appended to the node-outside-market message",
    )


__all__ = ["ModelNodeHomeRules"]
