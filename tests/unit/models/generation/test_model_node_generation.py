# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from uuid import uuid4

import pytest
from pydantic import ValidationError


def test_request_requires_fields() -> None:
    from omnibase_core.models.generation import ModelNodeGenerationRequest

    req = ModelNodeGenerationRequest(
        task_description="Classify review sentiment",
        correlation_id=str(uuid4()),
    )
    assert req.target_node_type == "compute"
    assert req.max_attempts == 2
    assert req.generation_timeout_seconds == 60


def test_request_rejects_non_compute() -> None:
    from omnibase_core.models.generation import ModelNodeGenerationRequest

    with pytest.raises(ValidationError):
        ModelNodeGenerationRequest(
            task_description="foo",
            correlation_id=str(uuid4()),
            target_node_type="orchestrator",
        )


def test_result_structured_artifacts() -> None:
    from omnibase_core.models.generation import ModelNodeGenerationResult

    result = ModelNodeGenerationResult(
        node_name="node_sentiment_classifier",
        contract_yaml="name: node_sentiment_classifier\ncontract_version: '1.0.0'\nnode_type: compute\n",
        handler_source="def handle(input): return {'sentiment': 'positive'}",
        artifact_paths=[".onex_state/hackathon/generated/test/contract.yaml"],
        generated_contract_hash="sha256:abc123def456",
        generated_handler_hash="sha256:789ghi012jkl",
        stdout="Generated successfully",
        stderr="",
        returncode=0,
    )
    assert result.generated_contract_hash.startswith("sha256:")
    assert result.returncode == 0
    assert result.node_name == "node_sentiment_classifier"


def test_result_frozen() -> None:
    from omnibase_core.models.generation import ModelNodeGenerationResult

    result = ModelNodeGenerationResult(
        node_name="test",
        contract_yaml="",
        handler_source="",
        artifact_paths=[],
        generated_contract_hash="sha256:x",
        generated_handler_hash="sha256:y",
        stdout="",
        stderr="",
        returncode=0,
    )
    with pytest.raises(ValidationError):
        result.node_name = "changed"  # type: ignore[misc]


def test_request_frozen() -> None:
    from omnibase_core.models.generation import ModelNodeGenerationRequest

    req = ModelNodeGenerationRequest(
        task_description="test",
        correlation_id=str(uuid4()),
    )
    with pytest.raises(ValidationError):
        req.task_description = "changed"  # type: ignore[misc]


def test_request_validation_timeout_default() -> None:
    from omnibase_core.models.generation import ModelNodeGenerationRequest

    req = ModelNodeGenerationRequest(
        task_description="test",
        correlation_id=str(uuid4()),
    )
    assert req.validation_timeout_seconds == 15


def test_request_extra_fields_forbidden() -> None:
    from omnibase_core.models.generation import ModelNodeGenerationRequest

    with pytest.raises(ValidationError):
        ModelNodeGenerationRequest(
            task_description="test",
            correlation_id=str(uuid4()),
            unknown_field="oops",
        )


def test_result_extra_fields_forbidden() -> None:
    from omnibase_core.models.generation import ModelNodeGenerationResult

    with pytest.raises(ValidationError):
        ModelNodeGenerationResult(
            node_name="test",
            contract_yaml="",
            handler_source="",
            artifact_paths=[],
            generated_contract_hash="sha256:x",
            generated_handler_hash="sha256:y",
            stdout="",
            stderr="",
            returncode=0,
            unknown_field="oops",
        )
