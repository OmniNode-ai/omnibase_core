# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A named metric formula frozen into a manifest (OMN-22001)."""

from pydantic import BaseModel, ConfigDict, Field


class ModelManifestMetricFormula(BaseModel):
    """How one metric is computed, written before outcomes are read.

    Attributes:
        metric: Metric name.
        formula: The formula, in words or symbols.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    metric: str = Field(min_length=1)
    formula: str = Field(min_length=1)
