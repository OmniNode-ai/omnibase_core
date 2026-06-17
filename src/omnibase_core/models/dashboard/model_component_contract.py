# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ComponentContract — the top-level UI component primitive.

Phase 0 UI contract primitive (OMN-13130, epic OMN-13129; plan
docs/plans/2026-06-13-contract-driven-ui-platform-unified-plan.md §6).

Built on the shipped ``ComponentManifest`` + ``ModelWidgetConfig*`` shapes. A
ComponentContract declares what a component shows, its data bindings, the
actions it emits, the permissions gating it, the evidence it requires, the
component kind a renderer must support, and the empty-state reasons it can
surface. It **composes** the other Phase 0 primitives rather than redefining
them. Additive over ``ModelWidgetConfig`` — no existing manifest breaks.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_empty_state_reason import EnumEmptyStateReason
from omnibase_core.enums.enum_widget_type import EnumWidgetType
from omnibase_core.models.dashboard.model_action_contract import ModelActionContract
from omnibase_core.models.dashboard.model_data_binding_contract import (
    ModelDataBindingContract,
)
from omnibase_core.models.dashboard.model_evidence_requirement_contract import (
    ModelEvidenceRequirementContract,
)
from omnibase_core.models.dashboard.model_permission_contract import (
    ModelPermissionContract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["ModelComponentContract"]


class ModelComponentContract(BaseModel):
    """A platform-neutral declaration of a UI component.

    ``component_kind`` reuses the shipped ``EnumWidgetType`` so a renderer's
    advertised ``supported_component_kinds`` can gate rendering. ``data_bindings``,
    ``actions``, ``evidence_requirements``, and ``permission`` compose the other
    Phase 0 primitives. ``supported_empty_state_reasons`` declares which typed
    reasons this component can surface; the client never blanks silently.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    component_id: str = Field(  # string-id-ok: semantic component label, not a UUID
        ...,
        description="Stable semantic identifier for this component contract",
        min_length=1,
    )
    component_kind: EnumWidgetType = Field(
        ...,
        description="Shipped component kind a renderer must support to render this",
    )
    title: str = Field(
        ...,
        description="Human-readable component title",
        min_length=1,
    )
    contract_version: ModelSemVer = Field(
        ...,
        description="Semantic version of this component contract (additive/versioned)",
    )
    data_bindings: tuple[ModelDataBindingContract, ...] = Field(
        default=(),
        description="Projection bindings this component reads truth from",
    )
    actions: tuple[ModelActionContract, ...] = Field(
        default=(),
        description="Declared command-emitting actions this component exposes",
    )
    evidence_requirements: tuple[ModelEvidenceRequirementContract, ...] = Field(
        default=(),
        description="Evidence required before this component renders or commits",
    )
    permission: ModelPermissionContract | None = Field(
        default=None,
        description="Permission contract gating who may see/act; None means unrestricted",
    )
    supported_empty_state_reasons: tuple[EnumEmptyStateReason, ...] = Field(
        default=(),
        description="Typed empty-state reasons this component can surface",
    )
