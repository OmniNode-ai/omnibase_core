# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Protocol for the canonical host-local runtime skill client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.models.runtime.model_runtime_skill_request import (
        ModelRuntimeSkillRequest,
    )
    from omnibase_core.models.runtime.model_runtime_skill_response import (
        ModelRuntimeSkillResponse,
    )


@runtime_checkable
class ProtocolRuntimeSkillClient(Protocol):
    """Abstract client for runtime-backed skill dispatch."""

    async def dispatch_async(
        self,
        request: ModelRuntimeSkillRequest,
    ) -> ModelRuntimeSkillResponse: ...

    def dispatch_sync(
        self,
        request: ModelRuntimeSkillRequest,
    ) -> ModelRuntimeSkillResponse: ...


__all__ = ["ProtocolRuntimeSkillClient"]
