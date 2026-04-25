# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.subcontracts.model_contract_behavior_spec import (
    ModelContractBehaviorSpec,
)


@pytest.mark.unit
def test_behavior_spec_defaults() -> None:
    spec = ModelContractBehaviorSpec.model_validate({})
    assert spec.max_concurrency is None
    assert spec.execution_timeout_ms is None
    assert spec.retry_attempts == 0
    assert spec.idempotent is False


@pytest.mark.unit
def test_behavior_spec_round_trips() -> None:
    raw = {"max_concurrency": 4, "execution_timeout_ms": 5000}
    spec = ModelContractBehaviorSpec.model_validate(raw)
    assert spec.max_concurrency == 4
    assert spec.execution_timeout_ms == 5000


@pytest.mark.unit
def test_behavior_spec_all_fields() -> None:
    spec = ModelContractBehaviorSpec.model_validate(
        {
            "max_concurrency": 8,
            "execution_timeout_ms": 30000,
            "retry_attempts": 3,
            "idempotent": True,
        }
    )
    assert spec.max_concurrency == 8
    assert spec.execution_timeout_ms == 30000
    assert spec.retry_attempts == 3
    assert spec.idempotent is True


@pytest.mark.unit
def test_behavior_spec_is_frozen() -> None:
    spec = ModelContractBehaviorSpec.model_validate({})
    with pytest.raises((ValidationError, TypeError)):
        spec.max_concurrency = 5  # type: ignore[misc]


@pytest.mark.unit
def test_behavior_spec_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ModelContractBehaviorSpec.model_validate({"unknown_field": "value"})
