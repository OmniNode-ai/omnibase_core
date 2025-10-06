#!/usr/bin/env python3
"""
Node Configuration Model - ONEX Standards Compliant.

Strongly-typed model for node configuration with execution settings, resource limits, and feature flags.
"""

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    pass


class ModelNodeConfiguration(BaseModel):
    """Configuration for a node."""

    # Execution settings
    max_retries: int | None = Field(default=None, description="Maximum retry attempts")
    timeout_seconds: int | None = Field(default=None, description="Execution timeout")
    batch_size: int | None = Field(default=None, description="Batch processing size")
    parallel_execution: bool = Field(
        default=False, description="Enable parallel execution"
    )

    # Resource limits
    max_memory_mb: int | None = Field(
        default=None, description="Maximum memory usage in MB"
    )
    max_cpu_percent: float | None = Field(
        default=None,
        description="Maximum CPU usage percentage",
    )

    # Feature flags
    enable_caching: bool = Field(default=False, description="Enable result caching")
    enable_monitoring: bool = Field(default=True, description="Enable monitoring")
    enable_tracing: bool = Field(default=False, description="Enable detailed tracing")

    # Connection settings
    endpoint: str | None = Field(default=None, description="Service endpoint")
    port: int | None = Field(default=None, description="Service port")
    protocol: str | None = Field(default=None, description="Communication protocol")

    # Custom configuration for extensibility
    custom_settings: dict[str, str] | None = Field(
        default=None,
        description="Custom string settings",
    )
    custom_flags: dict[str, bool] | None = Field(
        default=None,
        description="Custom boolean flags",
    )
    custom_limits: dict[str, int] | None = Field(
        default=None,
        description="Custom numeric limits",
    )
