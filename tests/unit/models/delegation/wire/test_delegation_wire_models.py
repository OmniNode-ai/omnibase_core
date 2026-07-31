# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for graduated delegation wire DTOs (OMN-12126)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from omnibase_core.models.delegation.wire import (
    TASK_DELEGATED_TOPIC_V1,
    EnumBudgetAction,
    EnumDelegationTerminalFailureCause,
    EnumQualityScoreComparison,
    EnumTierCostType,
    ModelBaselineIntent,
    ModelBifrostDelegationConfig,
    ModelBudgetLimits,
    ModelComplianceLoopResult,
    ModelDelegationBackendConfig,
    ModelDelegationCompleted,
    ModelDelegationConfig,
    ModelDelegationEventEnvelope,
    ModelDelegationFailed,
    ModelDelegationFallbackPolicy,
    ModelDelegationRequest,
    ModelDelegationResult,
    ModelDelegationRoutingRule,
    ModelDelegationShadowConfig,
    ModelInferenceIntent,
    ModelInferenceResponseData,
    ModelPremiumCounterfactual,
    ModelQualityGateInput,
    ModelQualityGateIntent,
    ModelQualityGateResult,
    ModelRoutingIntent,
    ModelRoutingTier,
    ModelTaskDelegatedEvent,
    ModelTierCost,
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

    def test_cloud_completion_shaping_defaults_are_backward_compatible(self) -> None:
        request = self._make()

        assert request.backend_id is None
        assert request.response_contract is None
        assert request.system_prompt is None
        assert request.temperature is None
        assert request.response_format is None
        dumped = request.model_dump()
        for field_name in (
            "backend_id",
            "response_contract",
            "system_prompt",
            "temperature",
            "response_format",
        ):
            assert field_name not in dumped

    def test_cloud_completion_shaping_round_trips_on_canonical_wire(self) -> None:
        response_contract: dict[str, object] = {
            "type": "object",
            "required": ["answer"],
            "properties": {"answer": {"type": "string"}},
        }
        response_format: dict[str, object] = {"type": "json_object"}

        request = self._make(
            backend_id="cloud-gemini-pro",
            response_contract=response_contract,
            system_prompt="Return one JSON object.",
            temperature=0.2,
            response_format=response_format,
        )

        assert request.backend_id == "cloud-gemini-pro"
        assert request.response_contract == response_contract
        assert request.system_prompt == "Return one JSON object."
        assert request.temperature == 0.2
        assert request.response_format == response_format
        dumped = request.model_dump()
        assert dumped["backend_id"] == "cloud-gemini-pro"
        assert dumped["response_contract"] == response_contract
        assert dumped["system_prompt"] == "Return one JSON object."
        assert dumped["temperature"] == pytest.approx(0.2)
        assert dumped["response_format"] == response_format
        assert (
            ModelDelegationRequest.model_validate_json(request.model_dump_json())
            == request
        )

    @pytest.mark.parametrize("temperature", [-0.01, 2.01])
    def test_cloud_completion_shaping_rejects_invalid_temperature(
        self, temperature: float
    ) -> None:
        with pytest.raises(ValidationError):
            self._make(temperature=temperature)

    def test_cloud_completion_shaping_rejects_unsupported_response_format(
        self,
    ) -> None:
        with pytest.raises(ValidationError, match="unsupported response_format"):
            self._make(response_format={"type": "json_schema"})

    def test_cloud_completion_shaping_rejects_non_string_response_format_type(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
            match="response_format type must be a string",
        ):
            self._make(response_format={"type": []})

    @pytest.mark.parametrize("backend_id", [" ", " cloud-gemini-pro"])
    def test_cloud_completion_shaping_rejects_whitespace_backend_id(
        self,
        backend_id: str,
    ) -> None:
        with pytest.raises(
            ValidationError,
            match="backend_id must not be blank or contain surrounding whitespace",
        ):
            self._make(backend_id=backend_id)

    def test_cloud_completion_shaping_rejects_non_json_response_contract(
        self,
    ) -> None:
        with pytest.raises(
            ValidationError,
            match="response_contract must be JSON-serializable",
        ):
            self._make(response_contract={"type": object()})

    def test_context_pack_hash_defaults_to_off_arm(self) -> None:
        r = self._make()
        assert r.context_pack == ""
        assert r.context_pack_hash == ""

    def test_context_pack_hash_is_accepted(self) -> None:
        r = self._make(
            context_pack="Relevant repo facts.",
            context_pack_hash="sha256:abc123",
        )
        assert r.context_pack == "Relevant repo facts."
        assert r.context_pack_hash == "sha256:abc123"

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

    @pytest.mark.unit
    def test_invalid_acceptance_criteria_error_lists_allowed_slugs(self) -> None:
        """Error message must name valid slugs so callers can self-correct (OMN-13542)."""
        with pytest.raises(ValueError) as exc_info:
            self._make(acceptance_criteria=("not_a_real_criterion",))
        msg = str(exc_info.value)
        assert "Allowed slugs:" in msg
        assert "max_words_per_sentence_N" in msg
        # At least one canonical slug must appear in the hint
        assert "response_non_empty" in msg

    @pytest.mark.unit
    def test_invalid_acceptance_criteria_error_quotes_bad_values(self) -> None:
        """Unsupported values are quoted in the error so they are easy to identify."""
        with pytest.raises(ValueError) as exc_info:
            self._make(
                acceptance_criteria=(
                    "Function must be typed with full PEP 604 type annotations",
                    "Must handle HTTP errors",
                )
            )
        msg = str(exc_info.value)
        assert "'Function must be typed with full PEP 604 type annotations'" in msg
        assert "'Must handle HTTP errors'" in msg
        assert "Allowed slugs:" in msg

    @pytest.mark.unit
    def test_i4_strict_code_generation_free_text_criteria_rejected_with_actionable_error(
        self,
    ) -> None:
        """OMN-13542 / OMN-13540 I4: strict code_generation with realistic free-text
        acceptance criteria must fail with a documented, actionable error naming valid
        forms — not an opaque 'unsupported acceptance criteria: <text>' with no guidance.
        """
        free_text_criteria = (
            "Function must be typed with full PEP 604 type annotations",
            "Must handle HTTP errors with appropriate status codes",
            "No global state mutations",
            "All branches covered by at least one test",
            "Docstring uses Google style",
        )
        with pytest.raises(ValueError) as exc_info:
            self._make(
                task_type="code_generation",
                acceptance_criteria=free_text_criteria,
            )
        msg = str(exc_info.value)
        # Error must be actionable: list the allowed set so the caller knows what to use
        assert "Allowed slugs:" in msg, (
            "Error must name the allowed slug set; got: " + msg
        )
        assert "max_words_per_sentence_N" in msg, (
            "Error must document the max_words_per_sentence_N pattern; got: " + msg
        )
        # At least one of the bad inputs must be quoted in the message
        assert any(f"'{c}'" in msg for c in free_text_criteria), (
            "At least one unsupported criterion must be quoted in the error; got: "
            + msg
        )

    def test_valid_acceptance_criteria(self) -> None:
        r = self._make(acceptance_criteria=("response_non_empty",))
        assert "response_non_empty" in r.acceptance_criteria

    def test_overlay_accepts_quality_gate_dod_checks(self) -> None:
        r = self._make(
            quality_contract_mode="replace_task_class",
            acceptance_criteria=(
                "compiles_without_errors",
                "final_artifact_only",
                "no_refusal",
                "uses_pytest_mark_unit",
                "covers_edge_cases",
                "covers_error_paths",
                "follows_codebase_conventions",
                "no_obvious_regressions",
            ),
        )

        assert r.quality_contract_mode == "replace_task_class"
        assert r.acceptance_criteria == (
            "compiles_without_errors",
            "final_artifact_only",
            "no_refusal",
            "uses_pytest_mark_unit",
            "covers_edge_cases",
            "covers_error_paths",
            "follows_codebase_conventions",
            "no_obvious_regressions",
        )

    @pytest.mark.parametrize(
        "task_type",
        [
            "test",
            "document",
            "research",
            "code_generation",
            "code_review",
            "refactor",
            "reasoning",
            "complex_reasoning",
            "planning",
            "review",
            "summarization",
            "agent_delegation",
            "escalation",
        ],
    )
    def test_all_compat_task_types_accepted(self, task_type: str) -> None:
        """All compat task_type values must be accepted (OMN-12663 parity fix).

        OMN-13541: ``code_review`` added — the consumer-facing delegation surface
        (node_delegate_skill_orchestrator.allowed_task_types + the claude/codex
        adapter) already accepts it, so the wire DTO must carry it or the bus
        consumer rejects the command and emits no terminal event (Pattern-B
        timeout, zero inference).
        """
        r = self._make(task_type=task_type)
        assert r.task_type == task_type

    def test_invalid_task_type_rejected(self) -> None:
        """task_type values outside the compat set must be rejected (OMN-12663)."""
        with pytest.raises(Exception):
            self._make(task_type="invalid_task_type")


@pytest.mark.unit
class TestValidateAcceptanceCriteria:
    def test_valid(self) -> None:
        result = validate_acceptance_criteria(
            ("response_non_empty", "plain_text_only", "final_artifact_only")
        )
        assert result == (
            "response_non_empty",
            "plain_text_only",
            "final_artifact_only",
        )

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

    def test_structured_quality_evidence_defaults_for_release_compatibility(
        self,
    ) -> None:
        """Older producers can omit the additive quality-evidence fields."""
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

        assert r.required_quality_bar is None
        assert r.score_vs_required_bar is None
        assert r.failed_acceptance_criteria == ()
        dumped = r.model_dump()
        assert "required_quality_bar" not in dumped
        assert "score_vs_required_bar" not in dumped
        assert "failed_acceptance_criteria" not in dumped

    def test_structured_quality_evidence_round_trips_exact_live_case(self) -> None:
        """The 0.867/0.800 canary evidence is machine-readable on the wire."""
        failure = "TASK_MISMATCH: failed step_by_step_explanation"
        r = ModelDelegationResult(
            correlation_id=uuid.uuid4(),
            task_type="reasoning",
            model_used="gemini-2.5-flash",
            endpoint_url="https://generativelanguage.googleapis.com",
            content="result",
            quality_passed=False,
            quality_score=0.867,
            required_quality_bar=0.800,
            score_vs_required_bar=EnumQualityScoreComparison.AT_OR_ABOVE_BAR,
            failed_acceptance_criteria=(failure,),
            latency_ms=100,
            fallback_to_claude=True,
            failure_reason=(
                "acceptance_criteria_failed: actual_score=0.867 "
                "required_bar=0.800 score_vs_bar=at_or_above_bar"
            ),
        )

        dumped = r.model_dump(mode="json")
        assert dumped["required_quality_bar"] == pytest.approx(0.800)
        assert dumped["score_vs_required_bar"] == "at_or_above_bar"
        assert dumped["failed_acceptance_criteria"] == [failure]
        assert ModelDelegationResult.model_validate(dumped) == r

    def test_rejects_required_quality_bar_without_comparison(self) -> None:
        with pytest.raises(
            ValidationError,
            match=(
                "required_quality_bar and score_vs_required_bar must be "
                "provided together"
            ),
        ):
            ModelDelegationResult(
                correlation_id=uuid.uuid4(),
                task_type="reasoning",
                model_used="qwen3",
                endpoint_url="http://localhost:8000",
                content="result",
                quality_passed=False,
                quality_score=0.5,
                required_quality_bar=0.8,
                latency_ms=100,
                fallback_to_claude=True,
            )

    def test_rejects_quality_comparison_without_required_bar(self) -> None:
        with pytest.raises(
            ValidationError,
            match=(
                "required_quality_bar and score_vs_required_bar must be "
                "provided together"
            ),
        ):
            ModelDelegationResult(
                correlation_id=uuid.uuid4(),
                task_type="reasoning",
                model_used="qwen3",
                endpoint_url="http://localhost:8000",
                content="result",
                quality_passed=False,
                quality_score=0.5,
                score_vs_required_bar=EnumQualityScoreComparison.BELOW_BAR,
                latency_ms=100,
                fallback_to_claude=True,
            )

    def test_rejects_failed_acceptance_criteria_when_quality_passed(self) -> None:
        with pytest.raises(
            ValidationError,
            match="quality_passed result cannot carry failed_acceptance_criteria",
        ):
            ModelDelegationResult(
                correlation_id=uuid.uuid4(),
                task_type="reasoning",
                model_used="qwen3",
                endpoint_url="http://localhost:8000",
                content="result",
                quality_passed=True,
                quality_score=0.9,
                failed_acceptance_criteria=("criterion_failed",),
                latency_ms=100,
                fallback_to_claude=False,
            )

    def test_rejects_quality_passed_when_score_is_below_required_bar(self) -> None:
        with pytest.raises(
            ValidationError,
            match="quality_passed result cannot be below required_quality_bar",
        ):
            ModelDelegationResult(
                correlation_id=uuid.uuid4(),
                task_type="reasoning",
                model_used="qwen3",
                endpoint_url="http://localhost:8000",
                content="result",
                quality_passed=True,
                quality_score=0.5,
                required_quality_bar=0.8,
                score_vs_required_bar=EnumQualityScoreComparison.BELOW_BAR,
                latency_ms=100,
                fallback_to_claude=False,
            )

    def test_rejects_failed_quality_above_bar_without_failed_criteria(self) -> None:
        with pytest.raises(
            ValidationError,
            match=(
                "quality-failed result at or above required_quality_bar must "
                "carry failed_acceptance_criteria"
            ),
        ):
            ModelDelegationResult(
                correlation_id=uuid.uuid4(),
                task_type="reasoning",
                model_used="qwen3",
                endpoint_url="http://localhost:8000",
                content="result",
                quality_passed=False,
                quality_score=0.9,
                required_quality_bar=0.8,
                score_vs_required_bar=(EnumQualityScoreComparison.AT_OR_ABOVE_BAR),
                latency_ms=100,
                fallback_to_claude=True,
                failure_reason="legacy prose must not replace structured truth",
            )

    @pytest.mark.parametrize("criterion", ["", "  "])
    def test_rejects_blank_failed_acceptance_criterion(self, criterion: str) -> None:
        with pytest.raises(
            ValidationError,
            match="failed_acceptance_criteria entries must not be blank",
        ):
            ModelDelegationResult(
                correlation_id=uuid.uuid4(),
                task_type="reasoning",
                model_used="qwen3",
                endpoint_url="http://localhost:8000",
                content="result",
                quality_passed=False,
                quality_score=0.9,
                required_quality_bar=0.8,
                score_vs_required_bar=(EnumQualityScoreComparison.AT_OR_ABOVE_BAR),
                failed_acceptance_criteria=(criterion,),
                latency_ms=100,
                fallback_to_claude=True,
            )

    @pytest.mark.parametrize(
        ("score", "bar", "comparison"),
        [
            (0.867, 0.800, EnumQualityScoreComparison.BELOW_BAR),
            (0.500, 0.800, EnumQualityScoreComparison.AT_OR_ABOVE_BAR),
        ],
    )
    def test_rejects_inconsistent_quality_score_comparison(
        self,
        score: float,
        bar: float,
        comparison: EnumQualityScoreComparison,
    ) -> None:
        with pytest.raises(
            ValidationError,
            match="score_vs_required_bar must match quality_score",
        ):
            ModelDelegationResult(
                correlation_id=uuid.uuid4(),
                task_type="reasoning",
                model_used="qwen3",
                endpoint_url="http://localhost:8000",
                content="result",
                quality_passed=False,
                quality_score=score,
                required_quality_bar=bar,
                score_vs_required_bar=comparison,
                latency_ms=100,
                fallback_to_claude=True,
            )

    def test_score_equal_to_bar_is_at_or_above(self) -> None:
        r = ModelDelegationResult(
            correlation_id=uuid.uuid4(),
            task_type="reasoning",
            model_used="qwen3",
            endpoint_url="http://localhost:8000",
            content="result",
            quality_passed=True,
            quality_score=0.8,
            required_quality_bar=0.8,
            score_vs_required_bar=EnumQualityScoreComparison.AT_OR_ABOVE_BAR,
            latency_ms=100,
            fallback_to_claude=False,
        )

        assert r.score_vs_required_bar is EnumQualityScoreComparison.AT_OR_ABOVE_BAR

    def test_terminal_failure_cause_defaults_for_release_compatibility(self) -> None:
        r = ModelDelegationResult(
            correlation_id=uuid.uuid4(),
            task_type="test",
            model_used="qwen3",
            endpoint_url="http://localhost:8000",
            content="",
            quality_passed=False,
            quality_score=0.0,
            latency_ms=100,
            fallback_to_claude=False,
        )

        assert r.terminal_failure_cause is None
        assert "terminal_failure_cause" not in r.model_dump()

    def test_failed_terminal_round_trips_provider_quota_exhausted_cause(
        self,
    ) -> None:
        r = ModelDelegationFailed(
            correlation_id=uuid.uuid4(),
            task_type="refactor",
            model_used="gemini-2.5-flash",
            endpoint_url="https://generativelanguage.googleapis.com",
            content="",
            quality_passed=False,
            quality_score=0.0,
            latency_ms=100,
            fallback_to_claude=False,
            failure_reason="429 RESOURCE_EXHAUSTED",
            terminal_failure_reason="no_higher_tier_available",
            terminal_failure_cause=(
                EnumDelegationTerminalFailureCause.PROVIDER_QUOTA_EXHAUSTED
            ),
        )

        dumped = r.model_dump(mode="json")
        assert dumped["terminal_failure_cause"] == "provider_quota_exhausted"
        assert ModelDelegationFailed.model_validate(dumped) == r

    def test_completed_terminal_rejects_terminal_failure_cause(self) -> None:
        with pytest.raises(
            ValidationError,
            match="completed delegation cannot carry terminal_failure_cause",
        ):
            ModelDelegationCompleted(
                correlation_id=uuid.uuid4(),
                task_type="refactor",
                model_used="gemini-2.5-flash",
                endpoint_url="https://generativelanguage.googleapis.com",
                content="result",
                # Exercise the terminal-class invariant independently of the
                # base quality_passed invariant below.
                quality_passed=False,
                quality_score=0.0,
                latency_ms=100,
                fallback_to_claude=False,
                terminal_failure_cause=(
                    EnumDelegationTerminalFailureCause.PROVIDER_QUOTA_EXHAUSTED
                ),
            )

    def test_completed_terminal_rejects_quality_failed_verdict(self) -> None:
        with pytest.raises(
            ValidationError,
            match="completed delegation requires quality_passed",
        ):
            ModelDelegationCompleted(
                correlation_id=uuid.uuid4(),
                task_type="reasoning",
                model_used="qwen3",
                endpoint_url="http://localhost:8000",
                content="result",
                quality_passed=False,
                quality_score=0.9,
                latency_ms=100,
                fallback_to_claude=False,
            )

    @pytest.mark.parametrize(
        ("field_name", "field_value", "message"),
        [
            (
                "failure_reason",
                "provider failed",
                "completed delegation cannot carry failure_reason",
            ),
            (
                "terminal_failure_reason",
                "no_higher_tier_available",
                "completed delegation cannot carry terminal_failure_reason",
            ),
        ],
    )
    def test_completed_terminal_rejects_failure_state_fields(
        self,
        field_name: str,
        field_value: str,
        message: str,
    ) -> None:
        payload: dict[str, object] = {
            "correlation_id": uuid.uuid4(),
            "task_type": "reasoning",
            "model_used": "qwen3",
            "endpoint_url": "http://localhost:8000",
            "content": "result",
            "quality_passed": True,
            "quality_score": 0.9,
            "latency_ms": 100,
            "fallback_to_claude": False,
            field_name: field_value,
        }
        with pytest.raises(ValidationError, match=message):
            ModelDelegationCompleted.model_validate(payload)

    def test_failed_terminal_rejects_quality_passed_verdict(self) -> None:
        with pytest.raises(
            ValidationError,
            match="failed delegation requires quality_passed=false",
        ):
            ModelDelegationFailed(
                correlation_id=uuid.uuid4(),
                task_type="reasoning",
                model_used="qwen3",
                endpoint_url="http://localhost:8000",
                content="result",
                quality_passed=True,
                quality_score=0.9,
                latency_ms=100,
                fallback_to_claude=False,
            )

    def test_quality_passed_base_result_rejects_terminal_failure_cause(self) -> None:
        """Base-model consumers retain the completed-result invariant."""
        with pytest.raises(
            ValidationError,
            match="completed delegation cannot carry terminal_failure_cause",
        ):
            ModelDelegationResult(
                correlation_id=uuid.uuid4(),
                task_type="refactor",
                model_used="gemini-2.5-flash",
                endpoint_url="https://generativelanguage.googleapis.com",
                content="result",
                quality_passed=True,
                quality_score=0.9,
                latency_ms=100,
                fallback_to_claude=False,
                terminal_failure_cause=(
                    EnumDelegationTerminalFailureCause.PROVIDER_QUOTA_EXHAUSTED
                ),
            )

    def test_context_pack_hash_defaults_to_off_arm(self) -> None:
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
        assert r.context_pack_hash == ""

    def test_context_pack_hash_round_trips(self) -> None:
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
            context_pack_hash="sha256:ctxpack",
        )
        dumped = r.model_dump()
        assert dumped["context_pack_hash"] == "sha256:ctxpack"
        restored = ModelDelegationResult.model_validate(dumped)
        assert restored.context_pack_hash == "sha256:ctxpack"
        assert restored == r

    def test_cost_tier_name_defaults_empty(self) -> None:
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
        assert r.cost_tier_name == ""

    def test_cost_tier_name_round_trips(self) -> None:
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
            cost_tier_name="local",
        )
        dumped = r.model_dump()
        assert dumped["cost_tier_name"] == "local"
        restored = ModelDelegationResult.model_validate(dumped)
        assert restored.cost_tier_name == "local"
        assert restored == r

    def test_rejects_invalid_metric_ranges(self) -> None:
        with pytest.raises(ValidationError):
            ModelDelegationResult(
                correlation_id=uuid.uuid4(),
                task_type="test",
                model_used="qwen3",
                endpoint_url="http://localhost:8000",
                content="result",
                quality_passed=True,
                quality_score=1.1,
                latency_ms=-1,
                fallback_to_claude=False,
            )

    def test_rejects_inconsistent_total_tokens(self) -> None:
        with pytest.raises(ValueError, match="total_tokens must equal"):
            ModelDelegationResult(
                correlation_id=uuid.uuid4(),
                task_type="test",
                model_used="qwen3",
                endpoint_url="http://localhost:8000",
                content="result",
                quality_passed=True,
                quality_score=0.9,
                latency_ms=1,
                prompt_tokens=2,
                completion_tokens=3,
                total_tokens=6,
                fallback_to_claude=False,
            )


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

    def test_excluded_backend_refs_defaults_empty(self) -> None:
        corr_id = uuid.uuid4()
        req = ModelDelegationRequest(
            prompt="test",
            task_type="test",
            correlation_id=corr_id,
            emitted_at=datetime.now(tz=UTC),
        )
        intent = ModelRoutingIntent(payload=req)
        assert intent.excluded_backend_refs == ()

    def test_excluded_backend_refs_round_trips(self) -> None:
        """OMN-14402: same-tier backend fallback threads already-failed backend
        refs so the routing reducer can skip them and select a sibling."""
        corr_id = uuid.uuid4()
        req = ModelDelegationRequest(
            prompt="test",
            task_type="test",
            correlation_id=corr_id,
            emitted_at=datetime.now(tz=UTC),
        )
        intent = ModelRoutingIntent(
            payload=req,
            min_tier_name="local",
            excluded_backend_refs=("local-heavy-reasoning",),
        )
        assert intent.excluded_backend_refs == ("local-heavy-reasoning",)

    def test_rejects_invalid_intent_literal(self) -> None:
        corr_id = uuid.uuid4()
        req = ModelDelegationRequest(
            prompt="test",
            task_type="test",
            correlation_id=corr_id,
            emitted_at=datetime.now(tz=UTC),
        )
        with pytest.raises(ValidationError):
            ModelRoutingIntent(intent="wrong", payload=req)


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
        assert intent.api_key_ref is None

    def test_carries_api_key_reference_not_secret_value(self) -> None:
        intent = ModelInferenceIntent(
            base_url="http://localhost:8000",
            model="qwen3",
            system_prompt="You are helpful.",
            prompt="Write a test",
            max_tokens=512,
            correlation_id=uuid.uuid4(),
            api_key_ref="GEMINI_API_KEY",  # pragma: allowlist secret
        )

        assert intent.api_key_ref == "GEMINI_API_KEY"  # pragma: allowlist secret
        with pytest.raises(ValidationError):
            ModelInferenceIntent(
                base_url="http://localhost:8000",
                model="qwen3",
                system_prompt="You are helpful.",
                prompt="Write a test",
                max_tokens=512,
                correlation_id=uuid.uuid4(),
                api_key="sk-test-secret",  # pragma: allowlist secret
            )

    def test_rejects_invalid_intent_literal(self) -> None:
        with pytest.raises(ValidationError):
            ModelInferenceIntent(
                intent="wrong",
                base_url="http://localhost:8000",
                model="qwen3",
                system_prompt="You are helpful.",
                prompt="Write a test",
                max_tokens=512,
                correlation_id=uuid.uuid4(),
            )

    def test_tenant_id_optional_and_settable(self) -> None:
        # OMN-14280: tenant_id is an optional, top-level, str|None slug that
        # defaults to None (backward-compatible wire) and round-trips verbatim.
        default_intent = ModelInferenceIntent(
            base_url="http://localhost:8000",
            model="qwen3",
            system_prompt="You are helpful.",
            prompt="Write a test",
            max_tokens=512,
            correlation_id=uuid.uuid4(),
        )
        assert default_intent.tenant_id is None

        tenant_intent = ModelInferenceIntent(
            base_url="http://localhost:8000",
            model="qwen3",
            system_prompt="You are helpful.",
            prompt="Write a test",
            max_tokens=512,
            correlation_id=uuid.uuid4(),
            tenant_id="tenant-alpha",
        )
        assert tenant_intent.tenant_id == "tenant-alpha"
        assert tenant_intent.model_dump()["tenant_id"] == "tenant-alpha"

    def test_inference_attempt_id_is_optional_and_round_trips_as_uuid(self) -> None:
        correlation_id = uuid.uuid4()
        default_intent = ModelInferenceIntent(
            base_url="http://localhost:8000",
            model="qwen3",
            system_prompt="You are helpful.",
            prompt="Write a test",
            max_tokens=512,
            correlation_id=correlation_id,
        )
        assert default_intent.inference_attempt_id is None
        assert "inference_attempt_id" not in default_intent.model_dump()

        attempt_id = uuid.uuid4()
        parsed_intent = ModelInferenceIntent.model_validate(
            {
                **default_intent.model_dump(),
                "inference_attempt_id": str(attempt_id),
            }
        )
        assert parsed_intent.inference_attempt_id == attempt_id
        assert isinstance(parsed_intent.inference_attempt_id, uuid.UUID)

    def test_response_format_is_typed_and_optional(self) -> None:
        default_intent = ModelInferenceIntent(
            base_url="http://localhost:8000",
            model="qwen3",
            system_prompt="You are helpful.",
            prompt="Write a test",
            max_tokens=512,
            correlation_id=uuid.uuid4(),
        )
        assert default_intent.response_format is None
        assert "response_format" not in default_intent.model_dump()

        response_format = {"type": "json_object"}
        json_intent = default_intent.model_copy(
            update={"response_format": response_format}
        )
        # model_copy(update=...) does not revalidate, so prove the actual wire
        # parser accepts and round-trips the typed directive.
        json_intent = ModelInferenceIntent.model_validate(json_intent.model_dump())
        assert json_intent.response_format == response_format

        with pytest.raises(ValidationError, match="unsupported response_format"):
            ModelInferenceIntent.model_validate(
                {**default_intent.model_dump(), "response_format": {"type": "text"}}
            )


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

    def test_rejects_negative_routing_limits(self) -> None:
        with pytest.raises(ValidationError):
            ModelTierModel(
                id="qwen3-14b",
                backend_ref="local_qwen3",
                max_context_tokens=0,
            )

        with pytest.raises(ValidationError):
            ModelTierModel(
                id="qwen3-14b",
                backend_ref="local_qwen3",
                max_context_tokens=32768,
                fast_path_threshold_tokens=-1,
            )

        with pytest.raises(ValidationError):
            ModelRoutingTier(name="local", max_retries=-1)

    def test_accepts_typed_cost_model(self) -> None:
        """OMN-13234: ModelRoutingTier carries the typed cost model."""
        tier = ModelRoutingTier(
            name="cheap_cloud",
            cost=ModelTierCost(
                cost_type=EnumTierCostType.METERED,
                rate_per_1k_usd=0.002,
            ),
        )
        assert tier.cost is not None
        assert tier.cost.cost_type is EnumTierCostType.METERED

    def test_cost_defaults_none(self) -> None:
        """A tier not yet migrated to the typed model has cost=None."""
        tier = ModelRoutingTier(name="local")
        assert tier.cost is None


@pytest.mark.unit
class TestModelTierCost:
    def test_free_local_zero_rate(self) -> None:
        cost = ModelTierCost(cost_type=EnumTierCostType.FREE_LOCAL)
        assert cost.rate_per_1k_usd == 0.0
        assert cost.monthly_cap_usd is None

    def test_free_local_rejects_nonzero_rate(self) -> None:
        with pytest.raises(ValidationError, match="rate_per_1k_usd == 0"):
            ModelTierCost(
                cost_type=EnumTierCostType.FREE_LOCAL,
                rate_per_1k_usd=0.002,
            )

    def test_free_local_rejects_cap(self) -> None:
        with pytest.raises(ValidationError, match="must not declare monthly_cap_usd"):
            ModelTierCost(
                cost_type=EnumTierCostType.FREE_LOCAL,
                monthly_cap_usd=10.0,
            )

    def test_metered_requires_positive_rate(self) -> None:
        with pytest.raises(ValidationError, match="rate_per_1k_usd > 0"):
            ModelTierCost(cost_type=EnumTierCostType.METERED)

    def test_metered_rejects_cap(self) -> None:
        with pytest.raises(ValidationError, match="must not declare monthly_cap_usd"):
            ModelTierCost(
                cost_type=EnumTierCostType.METERED,
                rate_per_1k_usd=0.002,
                monthly_cap_usd=10.0,
            )

    def test_budgeted_requires_cap_and_overage(self) -> None:
        with pytest.raises(ValidationError, match="requires monthly_cap_usd"):
            ModelTierCost(
                cost_type=EnumTierCostType.BUDGETED,
                rate_per_1k_usd=0.001,
            )
        with pytest.raises(ValidationError, match="overage_rate_per_1k_usd > 0"):
            ModelTierCost(
                cost_type=EnumTierCostType.BUDGETED,
                rate_per_1k_usd=0.001,
                monthly_cap_usd=10.0,
            )

    def test_budgeted_valid(self) -> None:
        cost = ModelTierCost(
            cost_type=EnumTierCostType.BUDGETED,
            rate_per_1k_usd=0.001,
            monthly_cap_usd=10.0,
            overage_rate_per_1k_usd=0.003,
        )
        assert cost.monthly_cap_usd == 10.0
        assert cost.overage_rate_per_1k_usd == 0.003

    def test_frozen(self) -> None:
        cost = ModelTierCost(cost_type=EnumTierCostType.FREE_LOCAL)
        with pytest.raises(ValidationError):
            cost.rate_per_1k_usd = 0.5  # type: ignore[misc]


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
        assert inp.response_contract is None
        assert "response_contract" not in inp.model_dump()

    def test_gate_input_carries_caller_response_contract(self) -> None:
        response_contract: dict[str, object] = {
            "type": "object",
            "required": ["answer"],
        }
        inp = ModelQualityGateInput(
            correlation_id=uuid.uuid4(),
            task_type="test",
            llm_response_content='{"answer": "ok"}',
            response_contract=response_contract,
        )

        assert inp.response_contract == response_contract
        assert inp.model_dump()["response_contract"] == response_contract

    def test_gate_input_rejects_non_json_response_contract(self) -> None:
        with pytest.raises(
            ValidationError,
            match="response_contract must be JSON-serializable",
        ):
            ModelQualityGateInput(
                correlation_id=uuid.uuid4(),
                task_type="test",
                llm_response_content='{"answer": "ok"}',
                response_contract={"type": object()},
            )

    def test_gate_input_rejects_negative_min_response_length(self) -> None:
        with pytest.raises(ValidationError):
            ModelQualityGateInput(
                correlation_id=uuid.uuid4(),
                task_type="test",
                llm_response_content="This is the response.",
                min_response_length=-1,
            )

    def test_gate_result_pass(self) -> None:
        result = ModelQualityGateResult(
            correlation_id=uuid.uuid4(),
            passed=True,
            quality_score=0.95,
        )
        assert result.fail_category == "pass"
        assert result.fallback_recommended is False

    def test_rejects_quality_score_outside_unit_interval(self) -> None:
        with pytest.raises(ValidationError):
            ModelQualityGateResult(
                correlation_id=uuid.uuid4(),
                passed=True,
                quality_score=-0.1,
            )


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

    def test_backend_prefers_logical_secret_ref(self) -> None:
        backend = ModelDelegationBackendConfig(
            backend_id="openrouter",
            endpoint_url="https://openrouter.ai/api/v1/chat/completions",
            model_name="openrouter-model",
            tier="cheap_cloud",
            secret_ref="llm.openrouter.api_key",  # pragma: allowlist secret
            api_key_env="OPENROUTER_API_KEY",  # pragma: allowlist secret
        )

        expected_secret_ref = "llm.openrouter.api_key"  # pragma: allowlist secret
        assert backend.resolved_secret_ref == expected_secret_ref

    def test_backend_rejects_conflicting_secret_refs(self) -> None:
        with pytest.raises(ValidationError):
            ModelDelegationBackendConfig(
                backend_id="openrouter",
                endpoint_url="https://openrouter.ai/api/v1/chat/completions",
                model_name="openrouter-model",
                tier="cheap_cloud",
                secret_ref="llm.openrouter.api_key",  # pragma: allowlist secret
                api_key_ref="llm.other.api_key",  # pragma: allowlist secret
            )

    def test_backend_allows_matching_secret_refs_for_migration(self) -> None:
        backend = ModelDelegationBackendConfig(
            backend_id="openrouter",
            endpoint_url="https://openrouter.ai/api/v1/chat/completions",
            model_name="openrouter-model",
            tier="cheap_cloud",
            secret_ref="llm.openrouter.api_key",  # pragma: allowlist secret
            api_key_ref="llm.openrouter.api_key",  # pragma: allowlist secret
        )

        expected_secret_ref = "llm.openrouter.api_key"  # pragma: allowlist secret
        assert backend.resolved_secret_ref == expected_secret_ref

    def test_shadow_config_defaults(self) -> None:
        shadow = ModelDelegationShadowConfig()
        assert shadow.shadow_label == "SHADOW"
        assert shadow.log_sample_rate == 1.0

    def test_rejects_invalid_bifrost_wire_literals(self) -> None:
        with pytest.raises(ValidationError):
            ModelDelegationFallbackPolicy(action="retry_forever")

        with pytest.raises(ValidationError):
            ModelDelegationFallbackPolicy(
                action="return_error",
                on_exhaust="retry_forever",
            )

        with pytest.raises(ValidationError):
            ModelDelegationBackendConfig(backend_id="local_qwen3", tier="unknown")

    def test_all_live_tier_values_accepted(self) -> None:
        """All tier values present in live bifrost_delegation.yaml must be valid (OMN-12663).

        Verified against bifrost_delegation.yaml and routing_tiers.yaml in omnimarket
        and omnibase_infra; values confirmed in D3 trace (OMN-12642).
        """
        live_tiers = (
            "local",
            "frontier_api",
            "cheap_cloud",
            "cheap_frontier",
            "cli_agents",
        )
        for tier in live_tiers:
            backend = ModelDelegationBackendConfig(backend_id=f"test-{tier}", tier=tier)
            assert backend.tier == tier, f"tier={tier!r} round-trip failed"

    def test_previously_missing_tiers_now_accepted(self) -> None:
        """cheap_cloud, cheap_frontier, and cli_agents were the three missing values (OMN-12663)."""
        for tier in ("cheap_cloud", "cheap_frontier", "cli_agents"):
            backend = ModelDelegationBackendConfig(backend_id=f"test-{tier}", tier=tier)
            assert backend.tier == tier


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
        assert event.context_pack_hash == ""

    def test_carries_context_pack_hash(self) -> None:
        event = ModelTaskDelegatedEvent(
            timestamp="2026-05-26T00:00:00Z",
            correlation_id=uuid.uuid4(),
            task_type="test",
            delegated_to="local_qwen3",
            quality_gate_passed=True,
            context_pack_hash="sha256:ctx",
        )
        assert event.context_pack_hash == "sha256:ctx"

    def test_rejects_invalid_topic_and_negative_metrics(self) -> None:
        with pytest.raises(ValidationError):
            ModelTaskDelegatedEvent(
                topic="not.a.registered.topic",
                timestamp="2026-05-26T00:00:00Z",
                correlation_id=uuid.uuid4(),
                task_type="test",
                delegated_to="local_qwen3",
                quality_gate_passed=True,
            )

        with pytest.raises(ValidationError):
            ModelTaskDelegatedEvent(
                timestamp="2026-05-26T00:00:00Z",
                correlation_id=uuid.uuid4(),
                task_type="test",
                delegated_to="local_qwen3",
                quality_gate_passed=True,
                cost_usd=-0.01,
            )

    def test_topic_constant(self) -> None:
        assert TASK_DELEGATED_TOPIC_V1 == "onex.evt.omniclaude.task-delegated.v1"

    def test_premium_counterfactual_default_none(self) -> None:
        event = ModelTaskDelegatedEvent(
            timestamp="2026-05-26T00:00:00Z",
            correlation_id=uuid.uuid4(),
            task_type="test",
            delegated_to="local_qwen3",
            quality_gate_passed=True,
        )
        assert event.premium_counterfactual is None

    def test_carries_premium_counterfactual(self) -> None:
        counterfactual = ModelPremiumCounterfactual(
            model="claude-opus-4-6",
            price_in_per_1k=Decimal("0.015"),
            price_out_per_1k=Decimal("0.075"),
            as_of="2026-02-01",
            tokens_in=1000,
            tokens_out=500,
            counterfactual_cost_usd=Decimal("0.0525"),
        )
        event = ModelTaskDelegatedEvent(
            timestamp="2026-05-26T00:00:00Z",
            correlation_id=uuid.uuid4(),
            task_type="test",
            delegated_to="local_qwen3",
            quality_gate_passed=True,
            cost_usd=0.0,
            cost_savings_usd=0.0525,
            premium_counterfactual=counterfactual,
        )
        assert event.premium_counterfactual is not None
        assert event.premium_counterfactual.model == "claude-opus-4-6"
        assert event.premium_counterfactual.as_of == "2026-02-01"
        # cost_savings_usd is the auditable counterfactual - actual.
        assert event.premium_counterfactual.counterfactual_cost_usd - Decimal(
            str(event.cost_usd)
        ) == Decimal(str(event.cost_savings_usd))


@pytest.mark.unit
class TestModelPremiumCounterfactual:
    """Auditable pinned premium counterfactual provenance (OMN-13355)."""

    def _make(self, **overrides: object) -> ModelPremiumCounterfactual:
        kwargs: dict[str, object] = {
            "model": "claude-opus-4-6",
            "price_in_per_1k": Decimal("0.015"),
            "price_out_per_1k": Decimal("0.075"),
            "as_of": "2026-02-01",
            "tokens_in": 1000,
            "tokens_out": 500,
            "counterfactual_cost_usd": Decimal("0.0525"),
        }
        kwargs.update(overrides)
        return ModelPremiumCounterfactual(**kwargs)  # type: ignore[arg-type]

    def test_provenance_fields_present(self) -> None:
        cf = self._make()
        assert cf.model == "claude-opus-4-6"
        assert cf.price_in_per_1k == Decimal("0.015")
        assert cf.price_out_per_1k == Decimal("0.075")
        assert cf.as_of == "2026-02-01"
        assert cf.tokens_in == 1000
        assert cf.tokens_out == 500
        assert cf.counterfactual_cost_usd == Decimal("0.0525")
        assert cf.pricing_source == "pricing_manifest"
        assert cf.measured is False

    def test_cost_is_recomputable(self) -> None:
        cf = self._make()
        recomputed = (
            cf.price_in_per_1k * Decimal(cf.tokens_in)
            + cf.price_out_per_1k * Decimal(cf.tokens_out)
        ) / Decimal("1000")
        assert recomputed == cf.counterfactual_cost_usd

    def test_rejects_inconsistent_cost(self) -> None:
        with pytest.raises(ValidationError):
            self._make(counterfactual_cost_usd=Decimal("99.0"))

    def test_frozen(self) -> None:
        cf = self._make()
        with pytest.raises(ValidationError):
            cf.model = "gpt-4o"  # type: ignore[misc]

    def test_calibration_measured_flag(self) -> None:
        cf = self._make(pricing_source="calibration", measured=True)
        assert cf.measured is True
        assert cf.pricing_source == "calibration"


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

    def test_rejects_invalid_topic(self) -> None:
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
        with pytest.raises(ValidationError):
            ModelDelegationEventEnvelope(topic="not.a.topic", payload=result)


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

    def test_rejects_negative_metrics(self) -> None:
        with pytest.raises(ValidationError):
            ModelInferenceResponseData(
                correlation_id=uuid.uuid4(),
                content="Generated response.",
                model_used="qwen3-14b",
                latency_ms=-1,
            )

        with pytest.raises(ValidationError):
            ModelInferenceResponseData(
                correlation_id=uuid.uuid4(),
                content="Generated response.",
                model_used="qwen3-14b",
                prompt_tokens=-1,
            )

    def test_tenant_id_optional_and_settable(self) -> None:
        # OMN-14280: tenant_id round-trips the owning tenant back to the
        # orchestrator; optional + defaults to None for backward compatibility.
        default_resp = ModelInferenceResponseData(
            correlation_id=uuid.uuid4(),
            content="Generated response.",
            model_used="qwen3-14b",
        )
        assert default_resp.tenant_id is None

        tenant_resp = ModelInferenceResponseData(
            correlation_id=uuid.uuid4(),
            content="Generated response.",
            model_used="qwen3-14b",
            tenant_id="tenant-alpha",
        )
        assert tenant_resp.tenant_id == "tenant-alpha"

    def test_inference_attempt_id_is_optional_and_round_trips_as_uuid(self) -> None:
        default_resp = ModelInferenceResponseData(
            correlation_id=uuid.uuid4(),
            content="Generated response.",
            model_used="qwen3-14b",
        )
        assert default_resp.inference_attempt_id is None
        assert "inference_attempt_id" not in default_resp.model_dump()

        attempt_id = uuid.uuid4()
        parsed_resp = ModelInferenceResponseData.model_validate(
            {
                **default_resp.model_dump(),
                "inference_attempt_id": str(attempt_id),
            }
        )
        assert parsed_resp.inference_attempt_id == attempt_id
        assert isinstance(parsed_resp.inference_attempt_id, uuid.UUID)


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

    def test_rejects_invalid_intent_and_negative_tokens(self) -> None:
        with pytest.raises(ValidationError):
            ModelBaselineIntent(
                intent="wrong",
                correlation_id=uuid.uuid4(),
                task_type="test",
                baseline_cost_usd=0.01,
            )

        with pytest.raises(ValidationError):
            ModelBaselineIntent(
                correlation_id=uuid.uuid4(),
                task_type="test",
                baseline_cost_usd=0.01,
                prompt_tokens=-1,
            )


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

    def test_rejects_invalid_intent_literal(self) -> None:
        gate_input = ModelQualityGateInput(
            correlation_id=uuid.uuid4(),
            task_type="test",
            llm_response_content="This is a response.",
        )
        with pytest.raises(ValidationError):
            ModelQualityGateIntent(intent="wrong", payload=gate_input)
