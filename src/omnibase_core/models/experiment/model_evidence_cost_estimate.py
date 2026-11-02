# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A cost estimate, labelled apart from any measurement (OMN-22001)."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ModelEvidenceCostEstimate(BaseModel):
    """An estimated cost with the date of the price it used. Never a measurement.

    Attributes:
        amount: Estimated amount.
        unit: Unit of the amount.
        price_date: Date of the price list the estimate used.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    amount: Decimal = Field(ge=Decimal(0))
    unit: str = Field(min_length=1)
    price_date: date
