# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Success metrics model for YAML schema validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.types.typed_dict_performance_targets import (
    TypedDictPerformanceTargets,
)


class ModelSuccessMetrics(BaseModel):
    """Success metrics definitions.

    Defines how agent success is measured including performance
    targets and intelligence-enhanced outcomes.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    performance_targets: TypedDictPerformanceTargets | None = None
    intelligence_enhanced_outcomes: list[str] | None = None


__all__ = ["ModelSuccessMetrics"]
