# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input model for contract dependency computation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.governance.model_contract_entry import ModelContractEntry


class ModelContractDependencyInput(BaseModel):
    """Input to the contract dependency compute node."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    entries: list[ModelContractEntry]
    repo_filter: list[str] = []  # empty = all repos
