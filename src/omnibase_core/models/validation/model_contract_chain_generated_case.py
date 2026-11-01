# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed contract-chain generated case."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class ModelContractChainGeneratedCase(BaseModel):
    """Parity scenario scaffold, parametrized over the named overlay profiles.

    A committed scaffold is binding evidence, not proof of execution.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["stub_rows", "node_operation"]
    node: str = ""
    operation: str = ""
    fixture: dict[str, JsonValue] = Field(default_factory=dict)
    allowed_differences: tuple[str, ...] = ()
    obligation_ref: str
    overlays: tuple[str, ...] = ()
