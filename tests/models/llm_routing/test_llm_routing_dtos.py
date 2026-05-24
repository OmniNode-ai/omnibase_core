# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for shared LLM routing DTOs in omnibase_core.models.llm_routing."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.llm_routing.enum_route_rejection_reason import (
    EnumRouteRejectionReason,
)
from omnibase_core.models.llm_routing.model_route_rejected import ModelRouteRejected
from omnibase_core.models.llm_routing.model_route_request import ModelRouteRequest
from omnibase_core.models.llm_routing.model_route_resolved import ModelRouteResolved


@pytest.mark.unit
class TestModelRouteRequest:
    def test_valid_construction(self) -> None:
        req = ModelRouteRequest(
            logical_model_key="qwen3-coder-30b",
            role="fixer",
            correlation_id="corr-1",
        )
        assert req.logical_model_key == "qwen3-coder-30b"
        assert req.role == "fixer"
        assert req.correlation_id == "corr-1"
        assert req.require_healthy is True

    def test_require_healthy_optional(self) -> None:
        req = ModelRouteRequest(
            logical_model_key="qwen3-coder-30b",
            role="fixer",
            correlation_id="corr-2",
            require_healthy=False,
        )
        assert req.require_healthy is False

    def test_frozen(self) -> None:
        req = ModelRouteRequest(
            logical_model_key="qwen3-coder-30b",
            role="fixer",
            correlation_id="corr-3",
        )
        with pytest.raises((ValidationError, TypeError)):
            req.role = "reviewer"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelRouteRequest(  # type: ignore[call-arg]
                logical_model_key="qwen3-coder-30b",
                role="fixer",
                correlation_id="corr-4",
                unknown_field="bad",
            )


@pytest.mark.unit
class TestModelRouteResolved:
    def test_valid_construction(self) -> None:
        resolved = ModelRouteResolved(
            logical_model_key="qwen3-coder-30b",
            model_key="qwen3-coder-30b",
            endpoint_url="http://192.168.86.201:8000",
            model_id="cyankiwi/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit",
            provider="local",
            correlation_id="corr-5",
        )
        assert resolved.endpoint_url == "http://192.168.86.201:8000"
        assert resolved.was_fallback is False
        assert resolved.context_window == 0

    def test_fallback_flag(self) -> None:
        resolved = ModelRouteResolved(
            logical_model_key="qwen3-coder-30b",
            model_key="claude-sonnet-4-6",
            endpoint_url="https://api.anthropic.com",
            model_id="claude-sonnet-4-6",
            provider="anthropic",
            correlation_id="corr-6",
            was_fallback=True,
        )
        assert resolved.was_fallback is True

    def test_context_window_ge_zero(self) -> None:
        with pytest.raises(ValidationError):
            ModelRouteResolved(
                logical_model_key="qwen3-coder-30b",
                model_key="qwen3-coder-30b",
                endpoint_url="http://localhost:8000",
                model_id="model-id",
                provider="local",
                correlation_id="corr-7",
                context_window=-1,
            )


@pytest.mark.unit
class TestModelRouteRejected:
    def test_unknown_key_rejection(self) -> None:
        rejected = ModelRouteRejected(
            logical_model_key="nonexistent-model",
            rejection_reason=EnumRouteRejectionReason.UNKNOWN_KEY,
            correlation_id="corr-8",
        )
        assert rejected.rejection_reason == EnumRouteRejectionReason.UNKNOWN_KEY
        assert rejected.attempts == 1

    def test_fallback_exhausted(self) -> None:
        rejected = ModelRouteRejected(
            logical_model_key="qwen3-coder-30b",
            rejection_reason=EnumRouteRejectionReason.FALLBACK_EXHAUSTED,
            detail="Both primary and fallback unreachable",
            correlation_id="corr-9",
            attempts=3,
        )
        assert rejected.rejection_reason == EnumRouteRejectionReason.FALLBACK_EXHAUSTED
        assert rejected.attempts == 3
        assert rejected.detail == "Both primary and fallback unreachable"

    def test_attempts_ge_one(self) -> None:
        with pytest.raises(ValidationError):
            ModelRouteRejected(
                logical_model_key="model",
                rejection_reason=EnumRouteRejectionReason.ENDPOINT_UNAVAILABLE,
                correlation_id="corr-10",
                attempts=0,
            )


@pytest.mark.unit
class TestEnumRouteRejectionReason:
    def test_all_values_present(self) -> None:
        expected = {
            "UNKNOWN_KEY",
            "ENDPOINT_UNAVAILABLE",
            "POLICY_REJECTED",
            "FALLBACK_EXHAUSTED",
        }
        actual = {e.value for e in EnumRouteRejectionReason}
        assert actual == expected

    def test_str_values(self) -> None:
        assert EnumRouteRejectionReason.UNKNOWN_KEY == "UNKNOWN_KEY"
        assert EnumRouteRejectionReason.POLICY_REJECTED == "POLICY_REJECTED"


@pytest.mark.unit
class TestLlmRoutingModuleExports:
    def test_package_init_exports(self) -> None:
        from omnibase_core.models.llm_routing import (
            EnumRouteRejectionReason,
            ModelRouteRejected,
            ModelRouteRequest,
            ModelRouteResolved,
        )

        assert EnumRouteRejectionReason is not None
        assert ModelRouteRejected is not None
        assert ModelRouteRequest is not None
        assert ModelRouteResolved is not None
