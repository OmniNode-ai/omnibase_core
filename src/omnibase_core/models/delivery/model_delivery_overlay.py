# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delivery overlay facts."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.delivery.model_delivery_dependency_mechanism import (
    ModelDeliveryDependencyMechanism,
)
from omnibase_core.models.delivery.model_delivery_discovery_pattern import (
    ModelDeliveryDiscoveryPattern,
)
from omnibase_core.models.delivery.model_delivery_role_permission import (
    ModelDeliveryRolePermission,
)

__all__ = ["ModelDeliveryOverlay"]


class ModelDeliveryOverlay(BaseModel):
    """Immutable delivery overlay data."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    tag_pattern: str
    candidate_tag_pattern: str | None = None
    bump_automation_patterns: tuple[str, ...] = ()
    dependency_mechanisms: tuple[ModelDeliveryDependencyMechanism, ...] = ()
    role_permissions: tuple[ModelDeliveryRolePermission, ...]
    reusable_workflow_consumer_kinds: tuple[str, ...] = ()
    discovery_patterns: tuple[ModelDeliveryDiscoveryPattern, ...] = ()
    consumer_kinds: tuple[str, ...] = Field(min_length=1)

    @field_validator("tag_pattern", "candidate_tag_pattern")
    @classmethod
    def _compiles(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                re.compile(value)
            except re.error as exc:
                raise ValueError(
                    f"tag pattern is not a valid regular expression: {exc}"
                ) from exc
        return value

    @field_validator("bump_automation_patterns")
    @classmethod
    def _all_compile(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        for pattern in value:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(
                    f"bump pattern is not a valid regular expression: {exc}"
                ) from exc
        return value
