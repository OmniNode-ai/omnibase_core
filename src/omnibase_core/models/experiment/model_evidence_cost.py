# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Cost fields of an evidence snapshot: measured, or unknown, plus a labelled estimate (OMN-22001)."""

from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.experiment.model_evidence_cost_estimate import (
    ModelEvidenceCostEstimate,
)


class ModelEvidenceCost(BaseModel):
    """What the run cost. Unknown stays unknown and is never zero.

    A measured amount carries its source and unit. An estimate sits in its own
    field with its price date and never fills the measured amount.

    Attributes:
        measured_amount: Measured cost, or None when it was not measured.
        measurement_source: Where the measurement came from.
        unit: Unit of the measured amount.
        unknown: True exactly when there is no measured amount.
        estimate: Separately labelled estimate with its price date.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    measured_amount: Decimal | None = Field(default=None, ge=Decimal(0))
    measurement_source: str | None = Field(default=None, min_length=1)
    unit: str | None = Field(default=None, min_length=1)
    unknown: bool = True
    estimate: ModelEvidenceCostEstimate | None = None

    @model_validator(mode="after")
    def _unknown_flag_follows_the_measurement(self) -> Self:
        if self.measured_amount is None:
            if not self.unknown:
                raise ValueError("unknown must be True when nothing was measured")
            return self
        if self.unknown:
            raise ValueError("unknown must be False when an amount was measured")
        if self.measurement_source is None:
            raise ValueError("a measured amount needs its measurement source")
        if self.unit is None:
            raise ValueError("a measured amount needs its unit")
        return self
