# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from uuid import uuid4

import pytest
from pydantic import ValidationError


def test_attempt_records_metrics() -> None:
    from omnibase_core.models.benchmark import ModelGenerationAttempt

    attempt = ModelGenerationAttempt(
        attempt_number=1,
        provider="google-ai-studio",
        model_id="gemini-flash",
        endpoint_class="cloud_api",
        token_usage_input=1200,
        token_usage_output=800,
        latency_inference_ms=3400,
        contract_passed=True,
        validation_errors=[],
    )
    assert attempt.contract_passed is True
    assert attempt.provider == "google-ai-studio"


def test_benchmark_computed_fields() -> None:
    from omnibase_core.models.benchmark import (
        ModelGenerationAttempt,
        ModelGenerationBenchmark,
    )

    attempts = [
        ModelGenerationAttempt(
            attempt_number=1,
            provider="google-ai-studio",
            model_id="gemini-flash",
            endpoint_class="cloud_api",
            token_usage_input=1200,
            token_usage_output=800,
            latency_inference_ms=3400,
            contract_passed=False,
            validation_errors=["missing output_model"],
        ),
        ModelGenerationAttempt(
            attempt_number=2,
            provider="google-ai-studio",
            model_id="gemini-flash",
            endpoint_class="cloud_api",
            token_usage_input=1500,
            token_usage_output=900,
            latency_inference_ms=4100,
            contract_passed=True,
            validation_errors=[],
        ),
    ]
    benchmark = ModelGenerationBenchmark(
        correlation_id=uuid4(),
        track_id="track_a",
        provider="google-ai-studio",
        model_id="gemini-flash",
        endpoint_class="cloud_api",
        usage_source="ai-studio-metering",
        cost_basis="METERED_API_COST",
        task_description="classify sentiment",
        attempts=attempts,
        total_latency_e2e_ms=14200,
        contract_passed=True,
        cost_inference_usd=0.004,
    )
    assert benchmark.attempt_count == 2
    assert benchmark.cost_to_contract_pass_usd == 0.004


def test_benchmark_failed_cost() -> None:
    from omnibase_core.models.benchmark import ModelGenerationBenchmark

    benchmark = ModelGenerationBenchmark(
        correlation_id=uuid4(),
        track_id="track_b",
        provider="local-vllm",
        model_id="qwen3-coder-30b",
        endpoint_class="local_gpu",
        usage_source="local-token-counter",
        cost_basis="ZERO_MARGINAL_API_COST",
        task_description="classify",
        attempts=[],
        total_latency_e2e_ms=6100,
        contract_passed=False,
        cost_inference_usd=0.0,
    )
    assert benchmark.cost_to_contract_pass_usd == -1.0
    assert benchmark.cost_basis == "ZERO_MARGINAL_API_COST"


def test_receipt_artifact_binding() -> None:
    from omnibase_core.models.benchmark import ModelGenerationReceipt
    from omnibase_core.models.primitives.model_semver import ModelSemVer

    receipt = ModelGenerationReceipt(
        correlation_id=uuid4(),
        task_description="classify sentiment",
        generated_contract_hash="sha256:abc123",
        generated_handler_hash="sha256:def456",
        validation_result_id=uuid4(),
        model_used="gemini-flash",
        provider="google-ai-studio",
        attempts=2,
        mcp_tool_name="classify_sentiment",
        contract_version=ModelSemVer(major=1, minor=0, patch=0),
        invocation_result_hash="sha256:ghi789",
    )
    assert receipt.generated_contract_hash.startswith("sha256:")
    assert receipt.validation_result_id is not None
    assert receipt.contract_version.major == 1


def test_models_frozen() -> None:
    from omnibase_core.models.benchmark import ModelGenerationAttempt

    attempt = ModelGenerationAttempt(
        attempt_number=1,
        provider="test",
        model_id="test",
        endpoint_class="test",
        token_usage_input=0,
        token_usage_output=0,
        latency_inference_ms=0,
        contract_passed=True,
        validation_errors=[],
    )
    with pytest.raises(ValidationError):
        attempt.provider = "changed"  # type: ignore[misc]
