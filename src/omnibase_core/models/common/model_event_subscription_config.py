"""
Typed event subscription configuration model.

This module provides strongly-typed configuration for event subscription patterns.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelEventSubscriptionConfig(BaseModel):
    """
    Typed event subscription configuration.

    Replaces list[dict[str, Any]] event_subscriptions field in ModelYamlContract
    with explicit typed fields for event subscriptions.
    """

    model_config = ConfigDict(extra="forbid")

    event_type: str = Field(
        ...,
        description="Event type pattern to subscribe to",
    )
    filter_expression: str | None = Field(
        default=None,
        description="Filter expression for event matching",
    )
    handler: str | None = Field(
        default=None,
        description="Handler method or function name",
    )
    priority: int = Field(
        default=0,
        description="Subscription priority (0-100, higher = more urgent)",
        ge=0,
        le=100,
    )
    batch_size: int | None = Field(
        default=None,
        description="Batch size for batched processing",
        ge=1,
    )
    timeout_ms: int | None = Field(
        default=None,
        description="Processing timeout in milliseconds",
        ge=0,
    )


__all__ = ["ModelEventSubscriptionConfig"]
