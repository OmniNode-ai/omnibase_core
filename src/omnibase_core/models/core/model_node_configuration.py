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
    max_retries: int | None = Field(None, description="Maximum retry attempts")
    timeout_seconds: int | None = Field(None, description="Execution timeout")
    batch_size: int | None = Field(None, description="Batch processing size")
    parallel_execution: bool = Field(False, description="Enable parallel execution")

    # Resource limits
    max_memory_mb: int | None = Field(None, description="Maximum memory usage in MB")
    max_cpu_percent: float | None = Field(
        None,
        description="Maximum CPU usage percentage",
    )

    # Feature flags
    enable_caching: bool = Field(False, description="Enable result caching")
    enable_monitoring: bool = Field(True, description="Enable monitoring")
    enable_tracing: bool = Field(False, description="Enable detailed tracing")

    # Connection settings
    endpoint: str | None = Field(None, description="Service endpoint")
    port: int | None = Field(None, description="Service port")
    protocol: str | None = Field(None, description="Communication protocol")

    # Custom configuration for extensibility
    custom_settings: dict[str, str] | None = Field(
        None,
        description="Custom string settings",
    )
    custom_flags: dict[str, bool] | None = Field(
        None,
        description="Custom boolean flags",
    )
    custom_limits: dict[str, int] | None = Field(
        None,
        description="Custom numeric limits",
    )
