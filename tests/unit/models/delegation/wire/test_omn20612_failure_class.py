# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-20612: the delegation failure class travels typed on the inference response."""

from __future__ import annotations

from uuid import uuid4

import pytest

from omnibase_core.enums.enum_delegation_failure_class import (
    EnumDelegationFailureClass,
)
from omnibase_core.models.delegation.wire.model_orchestrator_intents import (
    ModelInferenceResponseData,
)


def _build(**extra: object) -> ModelInferenceResponseData:
    return ModelInferenceResponseData(
        correlation_id=uuid4(), content="", model_used="m", **extra
    )


@pytest.mark.unit
def test_failure_class_defaults_to_none() -> None:
    assert _build().failure_class is None


@pytest.mark.unit
def test_failure_class_round_trips_through_json() -> None:
    data = _build(failure_class=EnumDelegationFailureClass.PROVIDER_BILLING)
    restored = ModelInferenceResponseData.model_validate_json(data.model_dump_json())
    assert restored.failure_class is EnumDelegationFailureClass.PROVIDER_BILLING


@pytest.mark.unit
def test_failure_class_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        ModelInferenceResponseData.model_validate(
            {
                "correlation_id": str(uuid4()),
                "content": "",
                "model_used": "m",
                "failure_class": "not_a_class",
            }
        )
