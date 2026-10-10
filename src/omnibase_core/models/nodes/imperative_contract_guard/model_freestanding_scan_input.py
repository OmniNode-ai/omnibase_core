# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Request of the freestanding imperative-IO scan."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_reachability import EnumReachability
from omnibase_core.models.nodes.imperative_contract_guard.model_guard_module_source import (
    ModelGuardModuleSource,
)

__all__ = ["ModelFreestandingScanInput"]


class ModelFreestandingScanInput(BaseModel):
    """One freestanding module with the facts the guard already decided about it."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    module: ModelGuardModuleSource
    repo: str = Field(description="Repository name reported on the result.")
    allowlisted: bool = Field(
        default=False, description="The module path is baselined in the allowlist."
    )
    reachability: EnumReachability = Field(
        default=EnumReachability.LIVE,
        description="Reachability of the module from the repository's live entrypoints.",
    )
