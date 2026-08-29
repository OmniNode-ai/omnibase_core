# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Status item configuration model.

A tile on a status grid. Before OMN-16884 this carried ``key``, ``label``, and
``icon`` and nothing else — it could not say whether the thing it named was
healthy, could not carry the number an operator actually reads (a depth, a
count, a rate), and left severity to a colour looked up in the grid's own hex
map. The system-health board D4 makes the platform's first contract-native
widget was therefore inexpressible.

It now carries an upstream **verdict** (severity + the upstream status string +
the policy that decided it) and an optional numeric **secondary**. It carries no
colour: severity resolves through the theme by token name, never by a literal in
a config.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.dashboard.model_severity_verdict import ModelSeverityVerdict
from omnibase_core.models.dashboard.model_status_secondary import ModelStatusSecondary

__all__ = ("ModelStatusItemConfig",)


class ModelStatusItemConfig(BaseModel):
    """One tile: what it names, what upstream says about it, and its number.

    ``verdict`` is required. A tile that cannot say what it is reporting is a
    label, not a status indicator, and the board exists to show what is broken.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    key: str = Field(..., min_length=1, description="Data key for this status item")
    label: str = Field(..., min_length=1, description="Display label")
    icon: str | None = Field(
        default=None,
        min_length=1,
        description=(
            "Icon identifier for the thing being monitored (a database, a "
            "queue). Distinct from the severity icon, which comes from the "
            "grid's severity role and is never optional."
        ),
    )
    verdict: ModelSeverityVerdict = Field(
        ...,
        description=(
            "Upstream severity verdict for this tile, with the policy that "
            "produced it. Computed upstream; never inferred by the client."
        ),
    )
    secondary: ModelStatusSecondary | None = Field(
        default=None,
        description=(
            "Numeric secondary displayed alongside the status (count, depth, "
            "rate). None where the tile's truth is the verdict alone."
        ),
    )
