"""
ModelPayloadMetric - Typed payload for metric recording intents.

This module provides the ModelPayloadMetric model for structured metric
recording from Reducers. The Effect node receives the intent and sends
the metric to the configured metrics backend.

Design Pattern:
    Reducers emit this payload when a metric should be recorded.
    This separation ensures Reducer purity - the Reducer declares the
    desired outcome without performing the actual side effect.

Thread Safety:
    All payloads are immutable (frozen=True) after creation, making them
    thread-safe for concurrent read access.

Example:
    >>> from omnibase_core.models.reducer.payloads import ModelPayloadMetric
    >>>
    >>> payload = ModelPayloadMetric(
    ...     name="http.request.duration",
    ...     value=0.125,
    ...     metric_type="histogram",
    ...     labels={"method": "GET", "path": "/api/users"},
    ...     unit="seconds",
    ... )

See Also:
    omnibase_core.models.reducer.payloads.ModelIntentPayloadBase: Base class
    omnibase_core.models.reducer.payloads.model_protocol_intent_payload: Protocol for intent payloads
"""

from typing import Literal

from pydantic import Field

from omnibase_core.models.reducer.payloads.model_intent_payload_base import (
    ModelIntentPayloadBase,
)

# Public API - listed immediately after imports per Python convention
__all__ = ["ModelPayloadMetric"]


class ModelPayloadMetric(ModelIntentPayloadBase):
    """Payload for metric recording intents.

    Emitted by Reducers when a metric should be recorded. The Effect node
    executes this intent by sending the metric to the configured metrics backend.

    Supports various metric types (counter, gauge, histogram) with labels for
    dimensional data and value for the metric reading.

    Attributes:
        intent_type: Discriminator literal for intent routing. Always "record_metric".
            Placed first for optimal union type resolution performance.
        name: Metric name following naming conventions (e.g., "requests.total").
        value: Numeric value for the metric reading.
        metric_type: Type of metric (counter, gauge, histogram, summary).
        labels: Dimensional labels for metric filtering and aggregation.
        unit: Optional unit of measurement (e.g., "seconds", "bytes").

    Example:
        >>> payload = ModelPayloadMetric(
        ...     name="http.request.duration",
        ...     value=0.125,
        ...     metric_type="histogram",
        ...     labels={"method": "GET", "path": "/api/users"},
        ...     unit="seconds",
        ... )
    """

    # NOTE: Discriminator field is placed FIRST for optimal union type resolution.
    intent_type: Literal["record_metric"] = Field(
        default="record_metric",
        description=(
            "Discriminator literal for intent routing. Used by Pydantic's "
            "discriminated union to dispatch to the correct Effect handler."
        ),
    )

    name: str = Field(
        ...,
        description=(
            "Metric name following naming conventions. Use dot notation for "
            "namespacing. Example: 'http.request.duration', 'cache.hits.total'."
        ),
        min_length=1,
        max_length=256,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_.]*$",
    )

    value: float = Field(
        ...,
        description="Numeric value for the metric reading.",
    )

    metric_type: Literal["counter", "gauge", "histogram", "summary"] = Field(
        default="gauge",
        description=(
            "Type of metric. Counter for cumulative values, gauge for point-in-time "
            "values, histogram for distributions, summary for quantiles."
        ),
    )

    labels: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Dimensional labels for metric filtering and aggregation. Keys and "
            "values should be short strings. Example: {'method': 'GET'}."
        ),
    )

    unit: str | None = Field(
        default=None,
        description=(
            "Optional unit of measurement for the metric value. Examples: "
            "'seconds', 'bytes', 'requests', 'percent'."
        ),
        max_length=32,
    )
