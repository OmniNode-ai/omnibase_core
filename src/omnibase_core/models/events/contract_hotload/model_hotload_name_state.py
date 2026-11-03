# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""What one runtime has observed and serves for one contract name (OMN-21226)."""

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.events.contract_hotload.model_hotload_observed_entry import (
    ModelHotloadObservedEntry,
)
from omnibase_core.models.events.contract_hotload.model_hotload_served_entry import (
    ModelHotloadServedEntry,
)

__all__ = ["ModelHotloadNameState"]


class ModelHotloadNameState(BaseModel):
    """The observed and the served entry of one owned name.

    Attributes:
        observed: What the runtime has folded for the name.
        served: What it has wired, or ``None`` when nothing is served (after a
            removal, or while a first load is refused).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    observed: ModelHotloadObservedEntry
    served: ModelHotloadServedEntry | None
