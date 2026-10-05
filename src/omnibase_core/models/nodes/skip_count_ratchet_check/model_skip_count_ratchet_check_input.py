# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input model for the pure skip-count ratchet decision."""

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.nodes.skip_count_ratchet_check.model_skip_count_baseline_entry import (
    ModelSkipCountBaselineEntry,
)
from omnibase_core.models.nodes.skip_count_ratchet_check.model_skip_count_observation import (
    ModelSkipCountObservation,
)


class ModelSkipCountRatchetCheckInput(BaseModel):
    """Frozen baseline and observed test records; no implicit disk inputs."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    baseline: ModelSkipCountBaselineEntry
    observation: ModelSkipCountObservation
