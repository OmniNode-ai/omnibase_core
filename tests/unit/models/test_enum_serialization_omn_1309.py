# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Serialization snapshot tests for OMN-1309 enum refactoring.

These tests verify that JSON serialization output remains byte-for-byte
identical after replacing hardcoded status strings with enum references.

Related: OMN-1309
"""

import pytest

from omnibase_core.enums.enum_action_status import EnumActionStatus
from omnibase_core.enums.enum_circuit_breaker_state import EnumCircuitBreakerState
from omnibase_core.models.configuration.model_circuit_breaker import ModelCircuitBreaker
from omnibase_core.models.core.model_action_metadata import ModelActionMetadata


@pytest.mark.unit
class TestCircuitBreakerSerialization:
    """Verify ModelCircuitBreaker serialization remains unchanged."""

    def test_state_serializes_to_lowercase_closed(self) -> None:
        """State 'closed' serializes to lowercase string."""
        model = ModelCircuitBreaker(state="closed")
        data = model.model_dump()
        assert data["state"] == "closed"

        json_str = model.model_dump_json()
        assert '"state":"closed"' in json_str.replace(" ", "")

    def test_state_serializes_to_lowercase_open(self) -> None:
        """State 'open' serializes to lowercase string."""
        model = ModelCircuitBreaker(state="open")
        data = model.model_dump()
        assert data["state"] == "open"

    def test_state_serializes_to_lowercase_half_open(self) -> None:
        """State 'half_open' serializes to lowercase string."""
        model = ModelCircuitBreaker(state="half_open")
        data = model.model_dump()
        assert data["state"] == "half_open"

    def test_enum_input_serializes_identically(self) -> None:
        """Enum input produces identical output to string input."""
        string_model = ModelCircuitBreaker(state="open")
        enum_model = ModelCircuitBreaker(state=EnumCircuitBreakerState.OPEN)

        assert string_model.model_dump() == enum_model.model_dump()
        assert string_model.model_dump_json() == enum_model.model_dump_json()

    @pytest.mark.parametrize("state", ["closed", "open", "half_open"])
    def test_roundtrip_preserves_value(self, state: str) -> None:
        """JSON roundtrip preserves exact state value."""
        model = ModelCircuitBreaker(state=state)
        json_str = model.model_dump_json()
        restored = ModelCircuitBreaker.model_validate_json(json_str)
        assert restored.state == state


@pytest.mark.unit
class TestActionMetadataSerialization:
    """Verify ModelActionMetadata serialization remains unchanged."""

    def test_status_serializes_to_lowercase_created(self) -> None:
        """Status 'created' serializes to lowercase string."""
        model = ModelActionMetadata(status="created")
        data = model.model_dump()
        assert data["status"] == "created"

    def test_status_serializes_to_lowercase_running(self) -> None:
        """Status 'running' serializes to lowercase string."""
        model = ModelActionMetadata(status="running")
        data = model.model_dump()
        assert data["status"] == "running"

    def test_enum_input_serializes_identically(self) -> None:
        """Enum input produces identical output to string input."""
        string_model = ModelActionMetadata(status="completed")
        enum_model = ModelActionMetadata(status=EnumActionStatus.COMPLETED)

        # Compare just the status field to avoid timestamp differences
        assert string_model.status == enum_model.status
        assert string_model.model_dump()["status"] == enum_model.model_dump()["status"]

    @pytest.mark.parametrize("status", ["created", "running", "completed", "failed"])
    def test_roundtrip_preserves_value(self, status: str) -> None:
        """JSON roundtrip preserves exact status value.

        Note: ModelActionMetadata uses EnumGeneralStatus (not EnumActionStatus),
        which does not include "ready" as a valid value.
        """
        model = ModelActionMetadata(status=status)
        json_str = model.model_dump_json()
        restored = ModelActionMetadata.model_validate_json(json_str)
        assert restored.status == status

    def test_mark_methods_use_correct_values(self) -> None:
        """Verify mark_* methods set correct lowercase values."""
        model = ModelActionMetadata()
        assert model.status == "created"

        model.mark_started()
        assert model.status == "running"

        model.mark_completed()
        assert model.status == "completed"

        # Test mark_failed on fresh model
        model2 = ModelActionMetadata()
        from omnibase_core.models.core.model_error_details import ModelErrorDetails

        model2.mark_failed(
            ModelErrorDetails(
                error_code="TEST_ERROR",
                error_type="runtime",
                error_message="test error",
            )
        )
        assert model2.status == "failed"
