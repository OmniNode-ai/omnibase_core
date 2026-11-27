# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The terminal carries the provider's own response id (OMN-25856).

The provider response id is what lets a receipt be checked against the
provider. It is optional so a terminal from an older producer still parses.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.delegation.wire import ModelDelegationResult


def _result(**kwargs: object) -> ModelDelegationResult:
    defaults: dict[str, object] = {
        "correlation_id": uuid4(),
        "task_type": "test",
        "model_used": "some/model",
        "endpoint_url": "https://provider.example/v1/chat/completions",
        "content": "ok",
        "quality_passed": True,
        "quality_score": 1.0,
        "latency_ms": 12,
        "fallback_to_claude": False,
    }
    defaults.update(kwargs)
    return ModelDelegationResult.model_validate(defaults)


@pytest.mark.unit
class TestProviderGenerationId:
    def test_an_old_payload_without_the_field_still_validates(self) -> None:
        old = _result().model_dump(mode="json")
        assert "provider_generation_id" not in old
        assert ModelDelegationResult.model_validate(old).provider_generation_id is None

    def test_a_new_payload_carries_the_id_through_the_wire(self) -> None:
        dumped = _result(provider_generation_id="gen-abc123").model_dump(mode="json")
        assert dumped["provider_generation_id"] == "gen-abc123"
        restored = ModelDelegationResult.model_validate(dumped)
        assert restored.provider_generation_id == "gen-abc123"

    def test_the_field_is_frozen_with_the_rest_of_the_model(self) -> None:
        with pytest.raises(ValidationError):
            setattr(
                _result(provider_generation_id="gen-1"), "provider_generation_id", "x"
            )

    def test_a_blank_id_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            _result(provider_generation_id="   ")
