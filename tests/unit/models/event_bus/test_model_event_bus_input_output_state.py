# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""
Tests for ModelEventBusInputOutputState.

Comprehensive tests for event bus input/output state composite model including:
- Construction with valid inputs
- Factory methods
- Status and version checking methods
- Serialization and deserialization
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.models.event_bus.model_event_bus_input_output_state import (
    ModelEventBusInputOutputState,
)
from omnibase_core.models.event_bus.model_event_bus_input_state import (
    ModelEventBusInputState,
)
from omnibase_core.models.event_bus.model_event_bus_output_state import (
    ModelEventBusOutputState,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
class TestModelEventBusInputOutputStateConstruction:
    """Test ModelEventBusInputOutputState construction."""

    def test_create_with_required_fields(self) -> None:
        """Test creating input/output state with required fields."""
        input_state = ModelEventBusInputState(input_field="test")
        output_state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Done",
        )

        state = ModelEventBusInputOutputState(
            input_state=input_state,
            output_state=output_state,
        )

        assert state.input_state is input_state
        assert state.output_state is output_state

    def test_create_requires_input_state(self) -> None:
        """Test that input_state is required."""
        output_state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Done",
        )

        with pytest.raises(ValidationError):
            ModelEventBusInputOutputState(output_state=output_state)  # type: ignore[call-arg]

    def test_create_requires_output_state(self) -> None:
        """Test that output_state is required."""
        input_state = ModelEventBusInputState(input_field="test")

        with pytest.raises(ValidationError):
            ModelEventBusInputOutputState(input_state=input_state)  # type: ignore[call-arg]


@pytest.mark.unit
class TestModelEventBusInputOutputStateStatusMethods:
    """Test ModelEventBusInputOutputState status checking methods."""

    def test_is_successful_true(self) -> None:
        """Test is_successful returns True for success status."""
        input_state = ModelEventBusInputState(input_field="test")
        output_state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Done",
        )

        state = ModelEventBusInputOutputState(
            input_state=input_state,
            output_state=output_state,
        )

        assert state.is_successful() is True

    def test_is_successful_false_for_error(self) -> None:
        """Test is_successful returns False for error status."""
        input_state = ModelEventBusInputState(input_field="test")
        output_state = ModelEventBusOutputState(
            status=EnumOnexStatus.ERROR,
            message="Failed",
        )

        state = ModelEventBusInputOutputState(
            input_state=input_state,
            output_state=output_state,
        )

        assert state.is_successful() is False

    def test_is_successful_false_for_warning(self) -> None:
        """Test is_successful returns False for warning status."""
        input_state = ModelEventBusInputState(input_field="test")
        output_state = ModelEventBusOutputState(
            status=EnumOnexStatus.WARNING,
            message="Warning",
        )

        state = ModelEventBusInputOutputState(
            input_state=input_state,
            output_state=output_state,
        )

        assert state.is_successful() is False


@pytest.mark.unit
class TestModelEventBusInputOutputStateVersionMatch:
    """Test ModelEventBusInputOutputState version matching methods."""

    def test_get_version_match_true(self) -> None:
        """Test get_version_match returns True when versions match."""
        input_state = ModelEventBusInputState(
            version="1.2.3",
            input_field="test",
        )
        output_state = ModelEventBusOutputState(
            version="1.2.3",
            status=EnumOnexStatus.SUCCESS,
            message="Done",
        )

        state = ModelEventBusInputOutputState(
            input_state=input_state,
            output_state=output_state,
        )

        assert state.get_version_match() is True

    def test_get_version_match_false(self) -> None:
        """Test get_version_match returns False when versions differ."""
        input_state = ModelEventBusInputState(
            version="1.0.0",
            input_field="test",
        )
        output_state = ModelEventBusOutputState(
            version="2.0.0",
            status=EnumOnexStatus.SUCCESS,
            message="Done",
        )

        state = ModelEventBusInputOutputState(
            input_state=input_state,
            output_state=output_state,
        )

        assert state.get_version_match() is False

    def test_get_version_match_with_model_semver(self) -> None:
        """Test get_version_match with ModelSemVer instances."""
        version = ModelSemVer(major=1, minor=0, patch=0)

        input_state = ModelEventBusInputState(
            version=version,
            input_field="test",
        )
        output_state = ModelEventBusOutputState(
            version=version,
            status=EnumOnexStatus.SUCCESS,
            message="Done",
        )

        state = ModelEventBusInputOutputState(
            input_state=input_state,
            output_state=output_state,
        )

        assert state.get_version_match() is True


@pytest.mark.unit
class TestModelEventBusInputOutputStateOperationSummary:
    """Test ModelEventBusInputOutputState operation summary methods."""

    def test_get_operation_summary_successful(self) -> None:
        """Test get_operation_summary for successful operation."""
        input_state = ModelEventBusInputState(
            version="1.0.0",
            input_field="test",
        )
        output_state = ModelEventBusOutputState(
            version="1.0.0",
            status=EnumOnexStatus.SUCCESS,
            message="Operation completed",
        )

        state = ModelEventBusInputOutputState(
            input_state=input_state,
            output_state=output_state,
        )

        summary = state.get_operation_summary()

        assert summary["input_version"] == "1.0.0"
        assert summary["output_version"] == "1.0.0"
        assert summary["status"] == "success"
        assert summary["message"] == "Operation completed"
        assert summary["version_match"] is True
        assert summary["successful"] is True

    def test_get_operation_summary_failed(self) -> None:
        """Test get_operation_summary for failed operation."""
        input_state = ModelEventBusInputState(
            version="1.0.0",
            input_field="test",
        )
        output_state = ModelEventBusOutputState(
            version="1.0.0",
            status=EnumOnexStatus.ERROR,
            message="Operation failed",
        )

        state = ModelEventBusInputOutputState(
            input_state=input_state,
            output_state=output_state,
        )

        summary = state.get_operation_summary()

        assert summary["status"] == "error"
        assert summary["successful"] is False

    def test_get_operation_summary_version_mismatch(self) -> None:
        """Test get_operation_summary with version mismatch."""
        input_state = ModelEventBusInputState(
            version="1.0.0",
            input_field="test",
        )
        output_state = ModelEventBusOutputState(
            version="2.0.0",
            status=EnumOnexStatus.SUCCESS,
            message="Done",
        )

        state = ModelEventBusInputOutputState(
            input_state=input_state,
            output_state=output_state,
        )

        summary = state.get_operation_summary()

        assert summary["input_version"] == "1.0.0"
        assert summary["output_version"] == "2.0.0"
        assert summary["version_match"] is False


@pytest.mark.unit
class TestModelEventBusInputOutputStateFactoryMethods:
    """Test ModelEventBusInputOutputState factory methods."""

    def test_create_from_versions(self) -> None:
        """Test create_from_versions factory method."""
        state = ModelEventBusInputOutputState.create_from_versions(
            input_version="1.0.0",
            output_version="1.0.0",
            input_field="test_input",
            status="success",
            message="Done",
        )

        assert state.input_state.input_field == "test_input"
        assert state.output_state.message == "Done"
        assert state.is_successful() is True

    def test_create_from_versions_with_model_semver(self) -> None:
        """Test create_from_versions with ModelSemVer."""
        version = ModelSemVer(major=2, minor=1, patch=0)

        state = ModelEventBusInputOutputState.create_from_versions(
            input_version=version,
            output_version=version,
            input_field="test",
            status="success",
            message="Complete",
        )

        assert state.input_state.version == version
        assert state.output_state.version == version

    def test_create_successful(self) -> None:
        """Test create_successful factory method."""
        state = ModelEventBusInputOutputState.create_successful(
            version="1.0.0",
            input_field="test_input",
        )

        assert state.is_successful() is True
        assert state.get_version_match() is True
        assert "successfully" in state.output_state.message

    def test_create_successful_with_custom_message(self) -> None:
        """Test create_successful with custom message."""
        state = ModelEventBusInputOutputState.create_successful(
            version="1.0.0",
            input_field="test",
            message="Custom success message",
        )

        assert state.output_state.message == "Custom success message"

    def test_create_failed(self) -> None:
        """Test create_failed factory method."""
        state = ModelEventBusInputOutputState.create_failed(
            version="1.0.0",
            input_field="test_input",
            error_message="Something went wrong",
        )

        assert state.is_successful() is False
        assert state.output_state.message == "Something went wrong"


@pytest.mark.unit
class TestModelEventBusInputOutputStateSerialization:
    """Test ModelEventBusInputOutputState serialization."""

    def test_model_dump(self) -> None:
        """Test model_dump() serialization."""
        input_state = ModelEventBusInputState(input_field="test")
        output_state = ModelEventBusOutputState(
            status=EnumOnexStatus.SUCCESS,
            message="Done",
        )

        state = ModelEventBusInputOutputState(
            input_state=input_state,
            output_state=output_state,
        )

        data = state.model_dump()

        assert isinstance(data, dict)
        assert "input_state" in data
        assert "output_state" in data
        assert data["input_state"]["input_field"] == "test"
        assert data["output_state"]["message"] == "Done"

    def test_model_validate(self) -> None:
        """Test model_validate() deserialization."""
        data = {
            "input_state": {
                "input_field": "test_input",
            },
            "output_state": {
                "status": "success",
                "message": "Complete",
            },
        }

        state = ModelEventBusInputOutputState.model_validate(data)

        assert state.input_state.input_field == "test_input"
        assert state.output_state.message == "Complete"

    def test_serialization_roundtrip(self) -> None:
        """Test serialization and deserialization roundtrip."""
        original = ModelEventBusInputOutputState.create_successful(
            version="1.2.3",
            input_field="test_input",
        )

        data = original.model_dump()
        restored = ModelEventBusInputOutputState.model_validate(data)

        assert restored.input_state.input_field == original.input_state.input_field
        assert restored.output_state.message == original.output_state.message
        assert restored.is_successful() == original.is_successful()

    def test_json_serialization(self) -> None:
        """Test JSON serialization."""
        state = ModelEventBusInputOutputState.create_successful(
            version="1.0.0",
            input_field="test",
        )

        json_data = state.model_dump_json()

        assert isinstance(json_data, str)
        assert "input_state" in json_data
        assert "output_state" in json_data


@pytest.mark.unit
class TestModelEventBusInputOutputStateEdgeCases:
    """Test ModelEventBusInputOutputState edge cases."""

    def test_access_nested_input_properties(self) -> None:
        """Test accessing nested input state properties."""
        state = ModelEventBusInputOutputState.create_successful(
            version="1.0.0",
            input_field="test_input",
        )

        assert state.input_state.input_field == "test_input"
        assert state.input_state.priority == "normal"

    def test_access_nested_output_properties(self) -> None:
        """Test accessing nested output state properties."""
        state = ModelEventBusInputOutputState.create_successful(
            version="1.0.0",
            input_field="test",
        )

        assert state.output_state.status == EnumOnexStatus.SUCCESS
        assert state.output_state.is_successful() is True

    def test_model_copy(self) -> None:
        """Test model_copy() creates independent copy."""
        original = ModelEventBusInputOutputState.create_successful(
            version="1.0.0",
            input_field="test",
        )

        copied = original.model_copy(deep=True)

        assert copied is not original
        assert copied.input_state is not original.input_state
        assert copied.output_state is not original.output_state

    def test_nested_validation_propagates(self) -> None:
        """Test that validation errors in nested states propagate."""
        with pytest.raises((ValidationError, Exception)):
            ModelEventBusInputOutputState.create_from_versions(
                input_version="1.0.0",
                output_version="1.0.0",
                input_field="",  # Empty input field should fail
                status="success",
                message="Done",
            )
