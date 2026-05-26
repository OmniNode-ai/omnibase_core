# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelRoutingDecision and ModelRoutingDegradedEvent."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.routing.model_routing_decision import (
    EnumCapabilityTier,
    EnumProvider,
    EnumRetryType,
    EnumRiskLevel,
    ModelRoutingDecision,
)
from omnibase_core.models.routing.model_routing_degraded_event import (
    ModelRoutingDegradedEvent,
)


@pytest.mark.unit
class TestModelRoutingDecision:
    def test_minimal_valid(self) -> None:
        decision = ModelRoutingDecision(
            selected_model="qwen3-coder-30b",
            capability_tier=EnumCapabilityTier.LOCAL,
            provider=EnumProvider.LOCAL_VLLM,
        )
        assert decision.selected_model == "qwen3-coder-30b"
        assert decision.retry_type == EnumRetryType.NONE
        assert decision.risk_level == EnumRiskLevel.LOW
        assert decision.fallback_model is None

    def test_fallback_model_required_when_retry_type_fallback(self) -> None:
        with pytest.raises(ValidationError, match="fallback_model is required"):
            ModelRoutingDecision(
                selected_model="qwen3-coder-30b",
                capability_tier=EnumCapabilityTier.LOCAL,
                provider=EnumProvider.LOCAL_VLLM,
                retry_type=EnumRetryType.FALLBACK_MODEL,
                fallback_model=None,
            )

    def test_fallback_model_must_be_none_when_not_fallback_retry(self) -> None:
        with pytest.raises(ValidationError, match="fallback_model must be None"):
            ModelRoutingDecision(
                selected_model="qwen3-coder-30b",
                capability_tier=EnumCapabilityTier.LOCAL,
                provider=EnumProvider.LOCAL_VLLM,
                retry_type=EnumRetryType.SAME_MODEL,
                fallback_model="claude-3-5-haiku",
            )

    def test_with_fallback_model(self) -> None:
        decision = ModelRoutingDecision(
            selected_model="qwen3-coder-30b",
            capability_tier=EnumCapabilityTier.LOCAL,
            provider=EnumProvider.LOCAL_VLLM,
            retry_type=EnumRetryType.FALLBACK_MODEL,
            fallback_model="claude-3-5-haiku",
            risk_level=EnumRiskLevel.HIGH,
        )
        assert decision.fallback_model == "claude-3-5-haiku"
        assert decision.risk_level == EnumRiskLevel.HIGH

    def test_exploration_score_bounds(self) -> None:
        with pytest.raises(ValidationError):
            ModelRoutingDecision(
                selected_model="m",
                capability_tier=EnumCapabilityTier.MID_FRONTIER,
                provider=EnumProvider.ANTHROPIC,
                exploration_score=1.5,
            )

    def test_cost_estimate_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            ModelRoutingDecision(
                selected_model="m",
                capability_tier=EnumCapabilityTier.EXPENSIVE_FRONTIER,
                provider=EnumProvider.OPENAI,
                cost_estimate_usd=-0.01,
            )

    def test_frozen(self) -> None:
        decision = ModelRoutingDecision(
            selected_model="m",
            capability_tier=EnumCapabilityTier.LOCAL,
            provider=EnumProvider.LOCAL_VLLM,
        )
        with pytest.raises(ValidationError):
            decision.selected_model = "other"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelRoutingDecision(
                selected_model="m",
                capability_tier=EnumCapabilityTier.LOCAL,
                provider=EnumProvider.LOCAL_VLLM,
                unknown_field="x",  # type: ignore[call-arg]
            )

    def test_all_providers_and_tiers(self) -> None:
        for provider in EnumProvider:
            for tier in EnumCapabilityTier:
                d = ModelRoutingDecision(
                    selected_model="m",
                    capability_tier=tier,
                    provider=provider,
                )
                assert d.provider == provider
                assert d.capability_tier == tier


@pytest.mark.unit
class TestModelRoutingDegradedEvent:
    def test_valid(self) -> None:
        event = ModelRoutingDegradedEvent(
            primary="qwen3-coder-30b",
            reason="consecutive timeouts",
            attempts=3,
            elapsed_ms=1500.0,
            model_key="qwen3-coder-30b",
            correlation_id="corr-001",
        )
        assert event.primary == "qwen3-coder-30b"
        assert event.attempts == 3
        assert event.merge_sha == ""
        assert event.gate_name == ""

    def test_attempts_must_be_at_least_one(self) -> None:
        with pytest.raises(ValidationError):
            ModelRoutingDegradedEvent(
                primary="m",
                reason="r",
                attempts=0,
                elapsed_ms=100.0,
                model_key="m",
                correlation_id="c",
            )

    def test_elapsed_ms_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            ModelRoutingDegradedEvent(
                primary="m",
                reason="r",
                attempts=1,
                elapsed_ms=-1.0,
                model_key="m",
                correlation_id="c",
            )

    def test_optional_fields(self) -> None:
        event = ModelRoutingDegradedEvent(
            primary="m",
            reason="r",
            attempts=1,
            elapsed_ms=0.0,
            model_key="m",
            correlation_id="c",
            merge_sha="abc123",
            gate_name="handler_score_models",
        )
        assert event.merge_sha == "abc123"
        assert event.gate_name == "handler_score_models"

    def test_frozen(self) -> None:
        event = ModelRoutingDegradedEvent(
            primary="m",
            reason="r",
            attempts=1,
            elapsed_ms=0.0,
            model_key="m",
            correlation_id="c",
        )
        with pytest.raises(ValidationError):
            event.primary = "other"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelRoutingDegradedEvent(
                primary="m",
                reason="r",
                attempts=1,
                elapsed_ms=0.0,
                model_key="m",
                correlation_id="c",
                bogus="x",  # type: ignore[call-arg]
            )
