# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Trusted registry artifact, supplied independently of overlay rows."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.error_rule_table.model_error_action_contract import (
    ModelErrorActionContract,
)


class ModelErrorActionRegistry(BaseModel):
    """Static node contracts, registered state checks and permanently retired row ids."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    contracts: dict[str, ModelErrorActionContract]
    state_checks: tuple[str, ...]
    retired_ids: frozenset[str] = Field(default_factory=frozenset)
