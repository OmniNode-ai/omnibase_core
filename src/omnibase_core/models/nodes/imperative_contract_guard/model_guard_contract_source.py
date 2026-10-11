# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One node contract.yaml supplied to the imperative contract guard."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelGuardContractSource"]


class ModelGuardContractSource(BaseModel):
    """A ``src/**/contract.yaml`` whose declared handler modules are live entrypoints."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(
        description="Repository-relative POSIX path of the contract.yaml."
    )
    text: str = Field(description="Full text of the contract.yaml.")
    has_node_py: bool = Field(
        default=False,
        description="Whether a node.py sits beside the contract.yaml (it is then an entrypoint).",
    )
