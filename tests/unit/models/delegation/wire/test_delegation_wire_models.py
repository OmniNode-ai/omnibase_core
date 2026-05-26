# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for graduated delegation wire DTOs (OMN-12126)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from omnibase_core.models.delegation.wire import (
    TASK_DELEGATED_TOPIC_V1,
    EnumBudgetAction,
    ModelBaselineIntent,
    ModelBifrostDelegationConfig,
    ModelBudgetLimits,
    ModelComplianceLoopResult,
    ModelDelegationBackendConfig,
    ModelDelegationConfig,
    ModelDelegationEventEnvelope,
    ModelDelegationFallbackPolicy,
    ModelDelegationRequest,
    ModelDelegationResult,
    ModelDelegationRoutingRule,
    ModelDelegationShadowConfig,
    ModelInferenceIntent,
    ModelInferenceResponseData,
    ModelQualityGateInput,
    ModelQualityGateIntent,
    ModelQualityGateResult,
    ModelRoutingIntent,
    ModelRoutingTier,
    ModelTaskDelegatedEvent,
    ModelTierModel,
    validate_acceptance_criteria,
)


@pytest.mark.unit
class TestModelBudget:
    def test_enum_budget_action_values(self) -> None:
        assert EnumBudgetAction.CONTINUE == "CONTINUE"
        assert EnumBudgetAction.ABORT == "ABORT"

    def test_model_budget_limits_valid(self) -> None:
        b = ModelBudgetLimits(max_tokens=100, max_cost_usd=0.01, max_time_s=30.0)
        assert b.max_tokens == 100

    def test_model_budget_limits_frozen(self) -> None:
        b = ModelBudgetLimits(max_tokens=100, max_cost_usd=0.01, max_time_s=30.0)
        with pytest.raises(Exception):
            b.max_tokens = 200  # type: ignore[misc]


@pytest.mark.unit
class TestModelDelegationRequest:
    def _make(self, **kwargs: object) -> ModelDelegationRequest:
        defaults = {
            "prompt": "Write a test",
            "task_type": "test",
            "correlation_id": uuid.uuid4(),
            "emitted_at": datetime.now(tz=UTC),
        }
        defaults.update(kwargs)
        return ModelDelegationRequest(**defaults)  # type: ignore[arg-type]

    def test_basic_construction(self) -> None:
        r = self._make()
        assert r.task_type == "test"

    def test_compliance_budget_required_when_schema_key_set(self) -> None:
        with pytest.raises(ValueError, match="compliance_budget is required"):
            self._make(output_schema_key="some_schema")

    def test_compliance_budget_accepted_with_schema_key(self) -> None:
        budget = ModelBudgetLimits(max_tokens=500, max_cost_usd=0.05, max_time_s=60.0)
        r = self._make(output_schema_key="some_schema", compliance_budget=budget)
        assert r.output_schema_key == "some_schema"

    def test_invalid_acceptance_criteria(self) -> None:
        with pytest.raises(ValueError, match="unsupported acceptance criteria"):
            self._make(acceptance_criteria=("not_a_real_criterion",))

    def test_valid_acceptance_criteria(self) -> None:
        r = self._make(acceptance_criteria=("response_non_empty",))
        assert "response_non_empty" in r.acceptance_criteria


@pytest.mark.unit
class TestValidateAcceptanceCriteria:
    def test_valid(self) -> None:
        result = validate_acceptance_criteria(("response_non_empty", "plain_text_only"))
        assert "response_non_empty" in result

    def test_max_words_pattern(self) -> None:
        result = validate_acceptance_criteria(("max_words_per_sentence_10",))
        assert result == ("max_words_per_sentence_10",)

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="unsupported"):
            validate_acceptance_criteria(("bad_criterion",))


@pytest.mark.unit
class TestModelDelegationResult:
    def test_construction(self) -> None:
        r = ModelDelegationResult(
            correlation_id=uuid.uuid4(),
            task_type="test",
            model_used="qwen3",
            endpoint_url="http://localhost:8000",
            content="result",
            quality_passed=True,
            quality_score=0.9,
            latency_ms=100,
            fallback_to_claude=False,
        )
        assert r.quality_passed is True
        assert r.escalation_count == 0

    def test_escalation_fields_default(self) -> None:
        r = ModelDelegationResult(
            correlation_id=uuid.uuid4(),
            task_type="test",
            model_used="qwen3",
            endpoint_url="http://localhost:8000",
            content="result",
            quality_passed=True,
            quality_score=0.9,
            latency_ms=100,
            fallback_to_claude=False,
        )
        assert r.escalation_history == ()
        assert r.terminal_failure_reason is None
        assert r.attempts_count == 1


@pytest.mark.unit
class TestModelRoutingIntent:
    def test_construction(self) -> None:
        corr_id = uuid.uuid4()
        req = ModelDelegationRequest(
            prompt="test",
            task_type="test",
            correlation_id=corr_id,
            emitted_at=datetime.now(tz=UTC),
        )
        intent = ModelRoutingIntent(payload=req)
        assert intent.intent == "routing_reducer"
        assert intent.min_tier_name is None

    def test_min_tier_name(self) -> None:
        corr_id = uuid.uuid4()
        req = ModelDelegationRequest(
            prompt="test",
            task_type="test",
            correlation_id=corr_id,
            emitted_at=datetime.now(tz=UTC),
        )
        intent = ModelRoutingIntent(payload=req, min_tier_name="cheap_cloud")
        assert intent.min_tier_name == "cheap_cloud"


@pytest.mark.unit
class TestModelInferenceIntent:
    def test_construction(self) -> None:
        intent = ModelInferenceIntent(
            base_url="http://localhost:8000",
            model="qwen3",
            system_prompt="You are helpful.",
            prompt="Write a test",
            max_tokens=512,
            correlation_id=uuid.uuid4(),
        )
        assert intent.intent == "llm_inference"
        assert intent.timeout_seconds == 30.0
        assert intent.api_key is None


@pytest.mark.unit
class TestModelRoutingTier:
    def test_construction(self) -> None:
        tier_model = ModelTierModel(
            id="qwen3-14b",
            backend_ref="local_qwen3",
            max_context_tokens=32768,
            use_for=("test",),
        )
        tier = ModelRoutingTier(name="local", models=(tier_model,))
        assert tier.cost_per_1k_tokens == 0.0
        assert tier.max_retries == 0


@pytest.mark.unit
class TestModelDelegationConfig:
    def test_empty_tiers(self) -> None:
        cfg = ModelDelegationConfig()
        assert cfg.tiers == ()


@pytest.mark.unit
class TestModelQualityGate:
    def test_gate_input_construction(self) -> None:
        corr_id = uuid.uuid4()
        inp = ModelQualityGateInput(
            correlation_id=corr_id,
            task_type="test",
            llm_response_content="This is the response.",
        )
        assert inp.min_response_length == 60

    def test_gate_result_pass(self) -> None:
        result = ModelQualityGateResult(
            correlation_id=uuid.uuid4(),
            passed=True,
            quality_score=0.95,
        )
        assert result.fail_category == "pass"
        assert result.fallback_recommended is False


@pytest.mark.unit
class TestModelComplianceLoopResult:
    def test_construction(self) -> None:
        r = ModelComplianceLoopResult(compliant=True)
        assert r.budget_action == EnumBudgetAction.CONTINUE
        assert r.compliance_attempts == 1


@pytest.mark.unit
class TestModelBifrostDelegationConfig:
    def _make_backend(self) -> ModelDelegationBackendConfig:
        return ModelDelegationBackendConfig(
            backend_id="local_qwen3",
            tier="local",
        )

    def _make_rule(self) -> ModelDelegationRoutingRule:
        return ModelDelegationRoutingRule(
            rule_id=uuid.uuid4(),
            task_class="test",
            task_class_contract_version="1.0.0",
            backend_policy_version="1.0.0",
            backend_ids=("local_qwen3",),
            fallback_policy=ModelDelegationFallbackPolicy(action="return_error"),
            shadow_policy_id=uuid.uuid4(),
        )

    def test_construction(self) -> None:
        cfg = ModelBifrostDelegationConfig(
            config_version="1.0.0",
            schema_version="bifrost/v1",
            backends=(self._make_backend(),),
            routing_rules=(self._make_rule(),),
        )
        assert cfg.circuit_breaker.failure_threshold == 5
        assert cfg.failover.max_attempts == 3
        assert cfg.shadow_mode.enabled is False

    def test_shadow_config_defaults(self) -> None:
        shadow = ModelDelegationShadowConfig()
        assert shadow.shadow_label == "SHADOW"
        assert shadow.log_sample_rate == 1.0


@pytest.mark.unit
class TestModelTaskDelegatedEvent:
    def test_default_topic(self) -> None:
        event = ModelTaskDelegatedEvent(
            timestamp="2026-05-26T00:00:00Z",
            correlation_id=uuid.uuid4(),
            task_type="test",
            delegated_to="local_qwen3",
            quality_gate_passed=True,
        )
        assert event.topic == TASK_DELEGATED_TOPIC_V1
        assert event.escalation_count == 0

    def test_topic_constant(self) -> None:
        assert TASK_DELEGATED_TOPIC_V1 == "onex.evt.omniclaude.task-delegated.v1"


@pytest.mark.unit
class TestModelDelegationEventEnvelope:
    def test_construction(self) -> None:
        result = ModelDelegationResult(
            correlation_id=uuid.uuid4(),
            task_type="test",
            model_used="qwen3",
            endpoint_url="http://localhost:8000",
            content="ok",
            quality_passed=True,
            quality_score=0.9,
            latency_ms=50,
            fallback_to_claude=False,
        )
        envelope = ModelDelegationEventEnvelope(
            topic="onex.evt.omniclaude.task-delegated.v1",
            payload=result,
        )
        assert envelope.topic == "onex.evt.omniclaude.task-delegated.v1"


@pytest.mark.unit
class TestModelInferenceResponseData:
    def test_construction(self) -> None:
        resp = ModelInferenceResponseData(
            correlation_id=uuid.uuid4(),
            content="Generated response.",
            model_used="qwen3-14b",
        )
        assert resp.error_message == ""
        assert resp.latency_ms == 0


@pytest.mark.unit
class TestModelBaselineIntent:
    def test_construction(self) -> None:
        intent = ModelBaselineIntent(
            correlation_id=uuid.uuid4(),
            task_type="test",
            baseline_cost_usd=0.01,
        )
        assert intent.intent == "baseline_comparison"
        assert intent.candidate_cost_usd == 0.0


@pytest.mark.unit
class TestModelQualityGateIntent:
    def test_construction(self) -> None:
        gate_input = ModelQualityGateInput(
            correlation_id=uuid.uuid4(),
            task_type="test",
            llm_response_content="This is a response.",
        )
        intent = ModelQualityGateIntent(payload=gate_input)
        assert intent.intent == "quality_gate"
