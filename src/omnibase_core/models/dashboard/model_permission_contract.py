# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""PermissionContract — who may see/act on a UI component or action.

Phase 0 UI contract primitive (OMN-13130, epic OMN-13129; plan
docs/plans/2026-06-13-contract-driven-ui-platform-unified-plan.md §6).

Built on the ``PermissionSpec`` shape. Every disabled state carries a declared
reason — the client never disables silently. Roles are declared as required
scopes; if the viewer lacks a scope, the component/action renders disabled with
``disabled_reason``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelPermissionContract"]


class ModelPermissionContract(BaseModel):
    """Declares the scopes required to view and to act, plus disabled reasons.

    ``view_scopes`` gate visibility; ``act_scopes`` gate interaction. When a
    viewer is permitted to see but not act, the action renders disabled and
    ``disabled_reason`` states why — a declared reason is mandatory, never a
    silent disable.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    permission_id: str = Field(  # string-id-ok: semantic permission label, not a UUID
        ...,
        description="Stable semantic identifier for this permission contract",
        min_length=1,
    )
    view_scopes: tuple[str, ...] = Field(
        default=(),
        description="Scopes required to see the component; empty means visible to all",
    )
    act_scopes: tuple[str, ...] = Field(
        default=(),
        description="Scopes required to act; empty means no extra scope beyond view",
    )
    disabled_reason: str = Field(
        ...,
        description="Declared reason shown when the viewer may see but not act",
        min_length=1,
    )
