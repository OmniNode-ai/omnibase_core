# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input model for the event_registry_drift_check COMPUTE node (OMN-21416)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.event_registry_drift.model_event_registration import (
    ModelEventRegistration,
)
from omnibase_core.models.event_registry_drift.model_event_registry_drift_baseline import (
    ModelEventRegistryDriftBaseline,
)

__all__ = ["ModelEventRegistryDriftCheckInput"]


class ModelEventRegistryDriftCheckInput(BaseModel):
    """Request to compare a producer's declared registrations with an emit registry.

    Attributes:
        source_registrations: Registrations the producer side declares.
        registry_registrations: Registrations the consuming emit registry holds.
        baseline: Divergence declared as intentional.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    source_registrations: tuple[ModelEventRegistration, ...]
    registry_registrations: tuple[ModelEventRegistration, ...]
    baseline: ModelEventRegistryDriftBaseline = Field(
        default_factory=ModelEventRegistryDriftBaseline
    )
