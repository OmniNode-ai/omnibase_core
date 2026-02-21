# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Intent cost/latency forecast model.

Represents a pre-execution cost and latency prediction for a given intent class.
These forecasts are produced before execution begins to enable quota management,
user-facing cost estimates, and routing decisions.

Part of the Intent Intelligence Framework (OMN-2486).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.intelligence.enum_intent_class import EnumIntentClass

__all__ = ["ModelIntentCostForecast"]


class ModelIntentCostForecast(BaseModel):
    """Cost/latency prediction before execution.

    Produced by the forecasting subsystem prior to beginning intent execution.
    Enables quota checks, cost transparency, and routing decisions based on
    estimated resource consumption.

    Attributes:
        intent_class: The intent class being forecasted.
        estimated_tokens: Estimated total token consumption (input + output).
        estimated_cost_usd: Estimated cost in US dollars.
        estimated_latency_ms: Estimated execution latency in milliseconds.
        confidence_interval: Width of the 90% confidence interval as a fraction
            of the point estimate (e.g., 0.15 means ±15%).
        forecasted_at: Timestamp when forecast was produced (UTC).
            Callers must inject this value — no ``datetime.now()`` defaults.

    Example:
        >>> from datetime import UTC, datetime
        >>> from omnibase_core.enums.intelligence.enum_intent_class import EnumIntentClass
        >>> forecast = ModelIntentCostForecast(
        ...     intent_class=EnumIntentClass.FEATURE,
        ...     estimated_tokens=4200,
        ...     estimated_cost_usd=0.021,
        ...     estimated_latency_ms=3800,
        ...     confidence_interval=0.2,
        ...     forecasted_at=datetime.now(UTC),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    intent_class: EnumIntentClass = Field(
        description="The intent class being forecasted",
    )
    estimated_tokens: int = Field(
        ge=0,
        description="Estimated total token consumption (input + output)",
    )
    estimated_cost_usd: float = Field(
        ge=0.0,
        description="Estimated cost in US dollars",
    )
    estimated_latency_ms: int = Field(
        ge=0,
        description="Estimated execution latency in milliseconds",
    )
    confidence_interval: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Width of the 90% confidence interval as a fraction of the point estimate "
            "(e.g., 0.15 means ±15%)"
        ),
    )
    forecasted_at: datetime = Field(
        description=(
            "Timestamp when forecast was produced (UTC). "
            "Callers must inject this value — no datetime.now() defaults."
        ),
    )
