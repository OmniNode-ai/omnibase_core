"""
Fallback metadata model for ONEX Configuration-Driven Registry System.

This module provides the ModelFallbackMetadata for strongly-typed
metadata configuration for fallback strategies.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelFallbackMetadata(BaseModel):
    """Strongly-typed metadata model for fallback strategy configuration."""

    timeout_multiplier: float = Field(
        default=1.0,
        description="Multiplier for timeout adjustments",
        ge=0.1,
        le=10.0,
    )

    retry_backoff_seconds: int = Field(
        default=5,
        description="Backoff time between retries in seconds",
        ge=1,
        le=300,
    )

    feature_flags: dict[str, bool] = Field(
        default_factory=dict,
        description="Boolean feature flags for fallback behavior",
    )

    custom_properties: dict[str, str] = Field(
        default_factory=dict,
        description="String-based custom configuration properties",
    )

    numeric_settings: dict[str, float] = Field(
        default_factory=dict,
        description="Numeric configuration values",
    )
