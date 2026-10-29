# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The findings of one shape-gate independence run (OMN-20298)."""

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.validation.model_shape_gate_independence_finding import (
    ModelShapeGateIndependenceFinding,
)

__all__ = ["ModelShapeGateIndependenceReport"]


class ModelShapeGateIndependenceReport(BaseModel):
    """The findings of one shape-gate independence run (OMN-20298)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    findings: tuple[ModelShapeGateIndependenceFinding, ...] = ()
