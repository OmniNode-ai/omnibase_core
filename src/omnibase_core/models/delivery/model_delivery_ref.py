# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delivery ref facts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_delivery_resolved_kind import EnumDeliveryResolvedKind

__all__ = ["ModelDeliveryRef"]


class ModelDeliveryRef(BaseModel):
    """Immutable delivery ref data."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path_name: str | None = None
    location: str
    consumer_kind: str
    reference_text: str
    resolved_kind: EnumDeliveryResolvedKind
    resolved_target: str | None = None
    first_resolved_target: str | None = None
    automation_names: tuple[str, ...] = ()
    runtime_resolution: bool = False
    candidate_pr_head: str | None = None
    candidate_test_merge_target: str | None = None
    candidate_artifact_digest: str | None = None
    line_number: int | None = None
