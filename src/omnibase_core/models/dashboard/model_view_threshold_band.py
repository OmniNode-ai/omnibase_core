# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One band of a view threshold policy (OMN-21999).

A band covers the half-open interval ``[threshold.value, upper_exclusive)``. The
lower edge, the colour token and the label are a ``ModelMetricThreshold``, reused
as it stands; the band adds the upper edge and the severity the band names.
"""

from __future__ import annotations

import math
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_status_severity import EnumStatusSeverity
from omnibase_core.models.dashboard.model_metric_threshold import ModelMetricThreshold

__all__ = ["ModelViewThresholdBand"]


class ModelViewThresholdBand(BaseModel):
    """A value range with the severity it names.

    Attributes:
        threshold: Lower edge (inclusive), colour token and label of the band.
        upper_exclusive: Upper edge (exclusive). ``None`` means the band has no
            upper edge; a policy allows that on its last band only.
        severity: The severity a value inside the band is given.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    threshold: ModelMetricThreshold = Field(
        ..., description="Inclusive lower edge, colour token and label of the band"
    )
    upper_exclusive: float | None = Field(
        default=None,
        allow_inf_nan=False,
        description="Exclusive upper edge; None means the band has no upper edge",
    )
    severity: EnumStatusSeverity = Field(
        ..., description="Severity a value inside this band is given"
    )

    @property
    def lower_inclusive(self) -> float:
        """Inclusive lower edge of the band."""
        return self.threshold.value

    @model_validator(mode="after")
    def validate_extent(self) -> Self:
        """Require finite edges and a non-empty interval.

        Raises:
            ValueError: If the lower edge is not finite, or ``upper_exclusive``
                is not above it.
        """
        lower = self.threshold.value
        if not math.isfinite(lower):
            raise ValueError(f"threshold.value must be finite, got {lower}")
        if self.upper_exclusive is not None and self.upper_exclusive <= lower:
            raise ValueError(
                f"upper_exclusive ({self.upper_exclusive}) must be above "
                f"threshold.value ({lower})"
            )
        return self
