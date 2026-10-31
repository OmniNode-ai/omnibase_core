# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Preset and default timings read from the packaged ``service_timings.yaml`` (OMN-21796).

The numbers live in ``service_timings.yaml`` beside this module. Every field is required and
the model refuses an unknown key, so a timing missing from the contract fails the load instead
of silently falling back to a literal in code. Call sites read the timings through
``packaged_service_timings()``.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.utils.util_safe_yaml_loader import load_and_validate_yaml_model

_PACKAGED_CONTRACT = Path(__file__).with_name("service_timings.yaml")


class ModelServiceTimings(BaseModel):
    """Preset and default timings declared by the packaged contract."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    session_minimal_idle_minutes: int = Field(
        gt=0, description="Idle timeout of the minimal session policy."
    )
    session_strict_idle_minutes: int = Field(
        gt=0, description="Idle timeout of the strict session policy."
    )
    session_strict_fresh_auth_minutes: int = Field(
        gt=0, description="Fresh-authentication window of the strict session policy."
    )
    session_maximum_idle_minutes: int = Field(
        gt=0, description="Idle timeout of the maximum-security session policy."
    )
    session_maximum_absolute_minutes: int = Field(
        gt=0, description="Absolute timeout of the maximum-security session policy."
    )
    session_maximum_fresh_auth_minutes: int = Field(
        gt=0,
        description="Fresh-authentication window of the maximum-security session policy.",
    )
    session_maximum_warn_before_minutes: int = Field(
        gt=0,
        description="Warning lead time before timeout in the maximum-security session policy.",
    )
    health_production_check_interval_seconds: int = Field(
        gt=0, description="Check interval of the production health metadata preset."
    )
    health_development_check_interval_seconds: int = Field(
        gt=0, description="Check interval of the development health metadata preset."
    )
    health_maintenance_check_interval_seconds: int = Field(
        gt=0,
        description="Check interval of the maintenance-mode health metadata preset.",
    )
    cli_limited_wait_seconds: int = Field(
        gt=0, description="Default timeout of limited CLI execution resources."
    )
    cli_quick_wait_seconds: int = Field(
        gt=0, description="Timeout of quick CLI execution resources."
    )
    database_service_connection_wait_seconds: int = Field(
        gt=0, description="Connection timeout of the database external service preset."
    )
    database_service_health_check_wait_seconds: int = Field(
        gt=0,
        description="Health check timeout of the database external service preset.",
    )
    file_destination_flush_interval_ms: int = Field(
        gt=0, description="Default flush interval of a file event destination."
    )
    kafka_destination_flush_interval_ms: int = Field(
        gt=0, description="Default flush interval of a Kafka event destination."
    )
    dedup_default_ttl_hours: int = Field(
        gt=0, description="Default TTL of deduplication entries."
    )
    discover_tools_wait_seconds: float = Field(
        gt=0, description="Default wait of a tool discovery request."
    )
    high_priority_input_wait_seconds: int = Field(
        gt=0, description="Default timeout of a high priority event bus input state."
    )
    output_retry_delay_seconds: int = Field(
        gt=0, description="Default delay before the retry of an event bus output state."
    )
    compute_cache_default_ttl_minutes: int = Field(
        gt=0, description="Default TTL of the compute cache."
    )
    node_execution_default_wait_seconds: int = Field(
        gt=0, description="Timeout of the node execution settings preset."
    )
    replay_retry_delay_ms: float = Field(
        gt=0, description="Default delay between corpus replay retries."
    )
    aliveness_probe_wait_seconds: int = Field(
        gt=0, description="Default budget of the runtime aliveness probe."
    )
    restricted_connection_wait_seconds: int = Field(
        gt=0, description="Connection timeout of the restrictive network policy preset."
    )
    secret_cache_ttl_seconds: int = Field(
        gt=0, description="Secret cache TTL of the cached secret configuration preset."
    )
    trust_policy_max_cache_ttl_seconds: int = Field(
        gt=0, description="Upper bound of a trust policy cache TTL."
    )

    @classmethod
    def packaged(cls) -> ModelServiceTimings:
        """The timings declared by the packaged ``service_timings.yaml``."""
        return packaged_service_timings()


@cache
def packaged_service_timings() -> ModelServiceTimings:
    """The packaged timings, read once; the short name keeps call sites on one line."""
    return load_and_validate_yaml_model(_PACKAGED_CONTRACT, ModelServiceTimings)
