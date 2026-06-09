# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Bifrost delegation config wire DTOs."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelDelegationShadowConfig(BaseModel):
    """Shadow routing comparison settings."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    enabled: bool = Field(default=False, description="Whether shadow mode is active.")
    policy_version: str = Field(
        default="unknown",
        max_length=128,
        description="Human-readable version of the loaded shadow policy checkpoint.",
    )
    log_sample_rate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Fraction of requests to log shadow decisions for.",
    )
    comparison_logging_enabled: bool = Field(
        default=True,
        description="Whether to emit comparison events for shadow decisions.",
    )
    max_shadow_latency_ms: float = Field(
        default=5.0,
        ge=0.1,
        le=100.0,
        description="Maximum allowed latency for shadow policy evaluation (ms).",
    )
    shadow_label: Literal["SHADOW"] = Field(
        default="SHADOW",
        description="Label applied to all shadow comparison events.",
    )


class ModelDelegationFallbackPolicy(BaseModel):
    """Per-rule fallback behavior when backend attempts fail."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    action: Literal["escalate_to_next_tier", "return_error"] = Field(
        ...,
        description="Action on backend failure: 'escalate_to_next_tier' or 'return_error'.",
    )
    max_retries: int = Field(
        default=1,
        ge=0,
        le=10,
        description="Maximum retry attempts across backends in this rule.",
    )
    on_exhaust: Literal["return_error", "escalate_to_next_tier"] = Field(
        default="return_error",
        description="Behavior when all retries are exhausted.",
    )


class ModelDelegationRoutingRule(BaseModel):
    """Routing rule from task class constraints to ordered backend IDs."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    rule_id: UUID = Field(
        ..., description="Stable UUID for audit logging and provenance."
    )
    priority: int = Field(
        default=100,
        ge=0,
        description="Evaluation order - lower values evaluated first.",
    )
    task_class: str = Field(..., description="Task class this rule targets.")
    # string-version-ok: external contract version string from YAML config, not a ModelSemVer object
    task_class_contract_version: str = Field(
        ...,
        description="Version of the task class contract this rule was authored against.",
    )
    # string-version-ok: external policy version string from YAML config, not a ModelSemVer object
    backend_policy_version: str = Field(
        ...,
        description="Version of the backend policy applied by this rule.",
    )
    match_operation_types: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Operation types this rule matches (empty = any).",
    )
    match_capabilities: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Capabilities the request must declare (empty = any).",
    )
    latency_sla_ms: int | None = Field(
        default=None,
        ge=1,
        description="SLA latency constraint.",
    )
    cost_ceiling_usd_per_1k_tokens: float | None = Field(
        default=None,
        ge=0.0,
        description="Maximum allowed cost per 1K tokens for this rule's backends.",
    )
    backend_ids: tuple[str, ...] = Field(
        ...,
        min_length=1,
        description="Ordered backend IDs to try when this rule matches.",
    )
    fallback_policy: ModelDelegationFallbackPolicy = Field(
        ...,
        description="Failover behavior when backends are exhausted.",
    )
    shadow_policy_id: UUID = Field(
        ..., description="Shadow policy UUID for A/B evaluation."
    )


class ModelDelegationBackendConfig(BaseModel):
    """Backend definition for the Bifrost delegation gateway."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # string-id-ok: backend_id is a human-readable slug (e.g. "local_qwen3"), not a UUID
    backend_id: str = Field(
        ..., min_length=1, description="Stable human-readable slug."
    )
    base_url_env: str | None = Field(
        default=None,
        description="Env var name holding the backend base URL (local backends).",
    )
    endpoint_url: str | None = Field(
        default=None,
        description=(
            "Endpoint URL populated by deploy-time overlay. Null for local "
            "backends until overlay is applied."
        ),
    )
    model_name: str | None = Field(
        default=None,
        description=(
            "Model identifier sent in outbound requests. Null for local "
            "backends resolved at deploy time."
        ),
    )
    api_key_env: str | None = Field(
        default=None,
        description=(
            "Legacy environment variable name holding the backend API key. "
            "Use secret_ref for new backends."
        ),
    )
    api_key_ref: str | None = Field(
        default=None,
        description=(
            "Legacy non-secret API-key reference. Use secret_ref for new backends."
        ),
    )
    secret_ref: str | None = Field(
        default=None,
        description=(
            "Logical secret reference resolved through the lane secret mapping "
            "and ProtocolSecretStore at the effect boundary."
        ),
    )
    extra_headers: dict[str, str] | None = Field(
        default=None,
        description="Optional static HTTP headers required by the backend provider.",
    )
    tier: Literal[
        "local", "frontier_api", "cheap_cloud", "cheap_frontier", "cli_agents"
    ] = Field(
        ...,
        description=(
            "Routing tier. Values verified against live bifrost_delegation.yaml and "
            "routing_tiers.yaml (OMN-12663): "
            "'local' = vLLM on .201; "
            "'frontier_api' = Claude API; "
            "'cheap_cloud' = OpenRouter/Gemini/GLM; "
            "'cheap_frontier' = free-tier frontier models (OMN-12492); "
            "'cli_agents' = subprocess-dispatched CLI agents (OMN-10137)."
        ),
    )
    timeout_ms: int = Field(
        default=30000,
        ge=100,
        le=600000,
        description="Per-backend HTTP timeout in milliseconds.",
    )
    capabilities: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Capabilities this backend supports.",
    )

    @model_validator(mode="after")
    def _validate_secret_ref_fields(self) -> ModelDelegationBackendConfig:
        """Reject ambiguous canonical secret refs while allowing migration aliases."""
        canonical_refs = {
            value
            for value in (self.secret_ref, self.api_key_ref)
            if value is not None and value.strip()
        }
        if len(canonical_refs) > 1:
            msg = "secret_ref and api_key_ref must match when both are declared"
            raise ValueError(msg)
        return self

    @property
    def resolved_secret_ref(self) -> str | None:
        """Return the canonical non-secret reference for this backend."""
        return self.secret_ref or self.api_key_ref or self.api_key_env


class ModelDelegationCircuitBreakerConfig(BaseModel):
    """Circuit breaker settings applying to all Bifrost backends."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    failure_threshold: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Consecutive failures that open the circuit.",
    )
    window_seconds: int = Field(
        default=30,
        ge=1,
        le=3600,
        description="Cooldown duration after circuit opens, in seconds.",
    )


class ModelDelegationFailoverConfig(BaseModel):
    """Gateway-level failover settings."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum backend attempts per request.",
    )
    backoff_base_ms: int = Field(
        default=500,
        ge=0,
        le=10000,
        description="Base exponential backoff delay in milliseconds.",
    )


class ModelBifrostDelegationConfig(BaseModel):
    """Bifrost delegation gateway configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # string-version-ok: config_version is a semver string from YAML, not a ModelSemVer object
    config_version: str = Field(..., description="Semver config version.")
    # string-version-ok: schema_version is a format identifier string, not a ModelSemVer object
    schema_version: str = Field(
        ..., description="Schema identifier for this config format."
    )
    backends: tuple[ModelDelegationBackendConfig, ...] = Field(
        ...,
        min_length=1,
        description="Backend definitions with deployed endpoint URLs.",
    )
    routing_rules: tuple[ModelDelegationRoutingRule, ...] = Field(
        ...,
        min_length=1,
        description="Routing rules evaluated in ascending priority order.",
    )
    default_backends: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Fallback backend IDs when no routing rule matches.",
    )
    circuit_breaker: ModelDelegationCircuitBreakerConfig = Field(
        default_factory=ModelDelegationCircuitBreakerConfig,
        description="Circuit breaker settings applying to all backends.",
    )
    failover: ModelDelegationFailoverConfig = Field(
        default_factory=ModelDelegationFailoverConfig,
        description="Gateway-level failover settings.",
    )
    shadow_mode: ModelDelegationShadowConfig = Field(
        default_factory=ModelDelegationShadowConfig,
        description="Shadow mode configuration for delegation A/B testing.",
    )


__all__: list[str] = [
    "ModelBifrostDelegationConfig",
    "ModelDelegationBackendConfig",
    "ModelDelegationCircuitBreakerConfig",
    "ModelDelegationFailoverConfig",
    "ModelDelegationFallbackPolicy",
    "ModelDelegationRoutingRule",
    "ModelDelegationShadowConfig",
]
