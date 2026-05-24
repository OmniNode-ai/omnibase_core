# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Shared LLM routing DTOs for cross-repo consumption.

ModelRouteRequest, ModelRouteResolved, and ModelRouteRejected are the
canonical wire models for the node_model_router event bus topics:
  onex.evt.omnimarket.model-route-resolved.v1
  onex.evt.omnimarket.model-route-rejected.v1
"""

from omnibase_core.models.llm_routing.enum_route_rejection_reason import (
    EnumRouteRejectionReason,
)
from omnibase_core.models.llm_routing.model_route_rejected import ModelRouteRejected
from omnibase_core.models.llm_routing.model_route_request import ModelRouteRequest
from omnibase_core.models.llm_routing.model_route_resolved import ModelRouteResolved

__all__ = [
    "EnumRouteRejectionReason",
    "ModelRouteRejected",
    "ModelRouteRequest",
    "ModelRouteResolved",
]
