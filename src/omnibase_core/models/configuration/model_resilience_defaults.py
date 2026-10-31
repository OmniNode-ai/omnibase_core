# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Resilience timings read from the packaged ``resilience_defaults.yaml`` (OMN-21740)."""

from __future__ import annotations

from functools import cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from ruamel.yaml import YAML

__all__ = ["ModelResilienceDefaults"]

_CONTRACT_PATH = Path(__file__).parent / "resilience_defaults.yaml"


class ModelResilienceDefaults(BaseModel):
    """Retry, backoff, breaker, throttling and pool timings the models fall back to.

    Attributes:
        retry_config: Backoff seconds of the ``ModelRetryConfig`` presets.
        retry_policy: Delays and reset timeout of the ``ModelRetryPolicy`` factories.
        circuit_breaker: Open-state timeouts of the ``ModelCircuitBreaker`` presets.
        throttling: Delays and queue timeout of the ``ModelThrottlingBehavior`` presets.
        connection_pool: Timeouts of the ``ModelConnectionPool`` presets.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    class ModelRetryPreset(BaseModel):
        """Attempts and backoff of one ``ModelRetryConfig`` factory preset."""

        model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

        max_attempts: int = Field(ge=1)
        backoff_seconds: float = Field(ge=0)

    class ModelRetryConfigDefaults(BaseModel):
        """Presets of the ``ModelRetryConfig`` factory methods."""

        model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

        conservative: ModelResilienceDefaults.ModelRetryPreset
        standard: ModelResilienceDefaults.ModelRetryPreset
        aggressive: ModelResilienceDefaults.ModelRetryPreset
        fast_fail: ModelResilienceDefaults.ModelRetryPreset
        linear_backoff_seconds: float = Field(ge=0)

    class ModelRetryPolicyDefaults(BaseModel):
        """Delays and reset timeout of the ``ModelRetryPolicy`` factory methods."""

        model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

        base_delay_seconds: float = Field(ge=0)
        fixed_delay_seconds: float = Field(ge=0)
        http_base_delay_seconds: float = Field(ge=0)
        database_base_delay_seconds: float = Field(ge=0)
        circuit_breaker_reset_seconds: float = Field(ge=0)

    class ModelCircuitBreakerDefaults(BaseModel):
        """Open-state timeouts of the ``ModelCircuitBreaker`` presets."""

        model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

        fast_fail_open_seconds: int = Field(ge=0)
        resilient_open_seconds: int = Field(ge=0)

    class ModelDelayProfile(BaseModel):
        """A base and a maximum delay in milliseconds."""

        model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

        base_delay_ms: int = Field(ge=0)
        max_delay_ms: int = Field(ge=0)

    class ModelThrottlingDefaults(BaseModel):
        """Delays and queue timeout of the ``ModelThrottlingBehavior`` presets."""

        model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

        graceful_delay: ModelResilienceDefaults.ModelDelayProfile
        graceful_delay_multiplier: float = Field(gt=0)
        adaptive: ModelResilienceDefaults.ModelDelayProfile
        queue_wait_seconds: int = Field(ge=0)

    class ModelPoolPreset(BaseModel):
        """Timeouts of one ``ModelConnectionPool`` preset."""

        model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

        operation_seconds: int = Field(ge=0)
        retry_delay_seconds: int = Field(ge=0)
        pool_wait_seconds: int | None = Field(default=None, ge=0)

    class ModelConnectionPoolDefaults(BaseModel):
        """The timeouts of every ``ModelConnectionPool`` preset."""

        model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

        single_connection: ModelResilienceDefaults.ModelPoolPreset
        small_pool: ModelResilienceDefaults.ModelPoolPreset
        large_pool: ModelResilienceDefaults.ModelPoolPreset
        aggressive_retry: ModelResilienceDefaults.ModelPoolPreset
        quick_timeout: ModelResilienceDefaults.ModelPoolPreset

    retry_config: ModelRetryConfigDefaults
    retry_policy: ModelRetryPolicyDefaults
    circuit_breaker: ModelCircuitBreakerDefaults
    throttling: ModelThrottlingDefaults
    connection_pool: ModelConnectionPoolDefaults

    @classmethod
    def load(cls) -> ModelResilienceDefaults:
        """The defaults of the packaged contract, read once."""
        return _load_packaged()


@cache
def _load_packaged() -> ModelResilienceDefaults:
    with _CONTRACT_PATH.open(encoding="utf-8") as contract:
        return ModelResilienceDefaults.model_validate(YAML(typ="safe").load(contract))
