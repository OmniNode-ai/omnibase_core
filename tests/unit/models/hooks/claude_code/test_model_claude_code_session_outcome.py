"""Tests for Claude Code session outcome model.

Validates ModelClaudeCodeSessionOutcome including construction, immutability,
validation, helper methods, serialization, and import paths.
"""

from __future__ import annotations

import json
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.hooks.claude_code.enum_claude_code_session_outcome import (
    EnumClaudeCodeSessionOutcome,
)
from omnibase_core.models.hooks.claude_code.model_claude_code_session_outcome import (
    ModelClaudeCodeSessionOutcome,
)
from omnibase_core.models.services.model_error_details import ModelErrorDetails

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_session_id() -> UUID:
    """Provide a consistent sample session ID for tests."""
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def sample_correlation_id() -> UUID:
    """Provide a consistent sample correlation ID for tests."""
    return UUID("abcdef01-abcd-abcd-abcd-abcdef012345")


# NOTE(OMN-1762): ModelErrorDetails is generic but type parameter unused in test fixtures.
@pytest.fixture
def sample_error_details() -> ModelErrorDetails:  # type: ignore[type-arg]
    """Provide a sample ModelErrorDetails instance for tests."""
    return ModelErrorDetails(
        error_code="TOOL_EXECUTION_FAILED",
        error_type="runtime",
        error_message="File not found during edit operation",
        component="Edit",
        operation="write_file",
    )


@pytest.fixture
def success_outcome(sample_session_id: UUID) -> ModelClaudeCodeSessionOutcome:
    """Provide a successful session outcome for tests."""
    return ModelClaudeCodeSessionOutcome(
        session_id=sample_session_id,
        outcome=EnumClaudeCodeSessionOutcome.SUCCESS,
    )


@pytest.fixture
def failed_outcome(
    sample_session_id: UUID,
    sample_error_details: ModelErrorDetails,  # type: ignore[type-arg] - generic param unused
) -> ModelClaudeCodeSessionOutcome:
    """Provide a failed session outcome with error details for tests."""
    return ModelClaudeCodeSessionOutcome(
        session_id=sample_session_id,
        outcome=EnumClaudeCodeSessionOutcome.FAILED,
        error=sample_error_details,
    )


@pytest.fixture
def abandoned_outcome(sample_session_id: UUID) -> ModelClaudeCodeSessionOutcome:
    """Provide an abandoned session outcome for tests."""
    return ModelClaudeCodeSessionOutcome(
        session_id=sample_session_id,
        outcome=EnumClaudeCodeSessionOutcome.ABANDONED,
    )


@pytest.fixture
def unknown_outcome(sample_session_id: UUID) -> ModelClaudeCodeSessionOutcome:
    """Provide an unknown session outcome for tests."""
    return ModelClaudeCodeSessionOutcome(
        session_id=sample_session_id,
        outcome=EnumClaudeCodeSessionOutcome.UNKNOWN,
    )


# =============================================================================
# Construction Tests
# =============================================================================


@pytest.mark.unit
class TestModelClaudeCodeSessionOutcomeConstruction:
    """Test ModelClaudeCodeSessionOutcome construction scenarios."""

    def test_construction_with_required_fields(self, sample_session_id: UUID) -> None:
        """Test valid construction with all required fields only."""
        outcome = ModelClaudeCodeSessionOutcome(
            session_id=sample_session_id,
            outcome=EnumClaudeCodeSessionOutcome.SUCCESS,
        )

        assert outcome.session_id == sample_session_id
        assert outcome.outcome == EnumClaudeCodeSessionOutcome.SUCCESS
        assert outcome.error is None
        assert outcome.correlation_id is None

    def test_construction_with_optional_error_none(
        self, sample_session_id: UUID
    ) -> None:
        """Test construction with explicit None for optional error field."""
        outcome = ModelClaudeCodeSessionOutcome(
            session_id=sample_session_id,
            outcome=EnumClaudeCodeSessionOutcome.FAILED,
            error=None,
        )

        assert outcome.error is None

    def test_construction_with_error_details(
        self,
        sample_session_id: UUID,
        sample_error_details: ModelErrorDetails,  # type: ignore[type-arg] - generic param unused
    ) -> None:
        """Test construction with ModelErrorDetails for error field."""
        outcome = ModelClaudeCodeSessionOutcome(
            session_id=sample_session_id,
            outcome=EnumClaudeCodeSessionOutcome.FAILED,
            error=sample_error_details,
        )

        assert outcome.error is not None
        assert outcome.error.error_code == "TOOL_EXECUTION_FAILED"
        assert outcome.error.error_type == "runtime"
        assert outcome.error.error_message == "File not found during edit operation"
        assert outcome.error.component == "Edit"

    def test_construction_with_correlation_id(
        self, sample_session_id: UUID, sample_correlation_id: UUID
    ) -> None:
        """Test construction with optional correlation_id."""
        outcome = ModelClaudeCodeSessionOutcome(
            session_id=sample_session_id,
            outcome=EnumClaudeCodeSessionOutcome.SUCCESS,
            correlation_id=sample_correlation_id,
        )

        assert outcome.correlation_id == sample_correlation_id

    def test_construction_with_all_fields(
        self,
        sample_session_id: UUID,
        sample_correlation_id: UUID,
        sample_error_details: ModelErrorDetails,  # type: ignore[type-arg] - generic param unused
    ) -> None:
        """Test construction with all fields populated."""
        outcome = ModelClaudeCodeSessionOutcome(
            session_id=sample_session_id,
            outcome=EnumClaudeCodeSessionOutcome.FAILED,
            error=sample_error_details,
            correlation_id=sample_correlation_id,
        )

        assert outcome.session_id == sample_session_id
        assert outcome.outcome == EnumClaudeCodeSessionOutcome.FAILED
        assert outcome.error == sample_error_details
        assert outcome.correlation_id == sample_correlation_id

    def test_construction_all_outcome_values(self, sample_session_id: UUID) -> None:
        """Test that all enum outcome values can be used to construct models."""
        for outcome_value in EnumClaudeCodeSessionOutcome:
            outcome = ModelClaudeCodeSessionOutcome(
                session_id=sample_session_id,
                outcome=outcome_value,
            )

            assert outcome.outcome == outcome_value

    def test_missing_required_session_id_raises_error(self) -> None:
        """Test that missing session_id raises ValidationError."""
        with pytest.raises(ValidationError):
            # Intentionally omit required field to test validation
            ModelClaudeCodeSessionOutcome(
                outcome=EnumClaudeCodeSessionOutcome.SUCCESS,
            )  # type: ignore[call-arg]

    def test_missing_required_outcome_raises_error(
        self, sample_session_id: UUID
    ) -> None:
        """Test that missing outcome raises ValidationError."""
        with pytest.raises(ValidationError):
            # Intentionally omit required field to test validation
            ModelClaudeCodeSessionOutcome(
                session_id=sample_session_id,
            )  # type: ignore[call-arg]


# =============================================================================
# Model Configuration Tests
# =============================================================================


@pytest.mark.unit
class TestModelClaudeCodeSessionOutcomeConfig:
    """Test ModelClaudeCodeSessionOutcome Pydantic configuration."""

    def test_model_is_frozen_immutable(
        self, success_outcome: ModelClaudeCodeSessionOutcome
    ) -> None:
        """Test that model is frozen and rejects attribute assignment."""
        with pytest.raises(ValidationError) as exc_info:
            # Intentionally mutate frozen model to test immutability
            success_outcome.outcome = EnumClaudeCodeSessionOutcome.FAILED  # type: ignore[misc]

        assert (
            "frozen" in str(exc_info.value).lower()
            or "instance is immutable" in str(exc_info.value).lower()
        )

    def test_frozen_session_id_immutable(
        self, success_outcome: ModelClaudeCodeSessionOutcome
    ) -> None:
        """Test that session_id cannot be modified after creation."""
        with pytest.raises(ValidationError) as exc_info:
            # Intentionally mutate frozen model to test immutability
            success_outcome.session_id = uuid4()  # type: ignore[misc]

        assert (
            "frozen" in str(exc_info.value).lower()
            or "instance is immutable" in str(exc_info.value).lower()
        )

    def test_extra_forbid_rejects_unknown_fields(self, sample_session_id: UUID) -> None:
        """Test that extra='forbid' rejects unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            # Intentionally pass unknown field to test extra='forbid' config
            ModelClaudeCodeSessionOutcome(
                session_id=sample_session_id,
                outcome=EnumClaudeCodeSessionOutcome.SUCCESS,
                unknown_field="should_fail",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower() or "unknown_field" in str(
            exc_info.value
        )

    def test_from_attributes_compatibility(self, sample_session_id: UUID) -> None:
        """Test from_attributes=True enables attribute-based construction."""

        class MockOutcomeData:
            session_id = sample_session_id
            outcome = EnumClaudeCodeSessionOutcome.SUCCESS
            error = None
            correlation_id = None

        mock_data = MockOutcomeData()
        outcome = ModelClaudeCodeSessionOutcome.model_validate(mock_data)

        assert outcome.session_id == sample_session_id
        assert outcome.outcome == EnumClaudeCodeSessionOutcome.SUCCESS


# =============================================================================
# Helper Method Tests
# =============================================================================


@pytest.mark.unit
class TestModelClaudeCodeSessionOutcomeHelperMethods:
    """Test helper methods on ModelClaudeCodeSessionOutcome."""

    def test_is_successful_returns_true_for_success(
        self, success_outcome: ModelClaudeCodeSessionOutcome
    ) -> None:
        """Test is_successful returns True for SUCCESS outcome."""
        assert success_outcome.is_successful() is True

    def test_is_successful_returns_false_for_failed(
        self, failed_outcome: ModelClaudeCodeSessionOutcome
    ) -> None:
        """Test is_successful returns False for FAILED outcome."""
        assert failed_outcome.is_successful() is False

    def test_is_successful_returns_false_for_abandoned(
        self, abandoned_outcome: ModelClaudeCodeSessionOutcome
    ) -> None:
        """Test is_successful returns False for ABANDONED outcome."""
        assert abandoned_outcome.is_successful() is False

    def test_is_successful_returns_false_for_unknown(
        self, unknown_outcome: ModelClaudeCodeSessionOutcome
    ) -> None:
        """Test is_successful returns False for UNKNOWN outcome."""
        assert unknown_outcome.is_successful() is False

    def test_is_failure_returns_false_for_success(
        self, success_outcome: ModelClaudeCodeSessionOutcome
    ) -> None:
        """Test is_failure returns False for SUCCESS outcome."""
        assert success_outcome.is_failure() is False

    def test_is_failure_returns_true_for_failed(
        self, failed_outcome: ModelClaudeCodeSessionOutcome
    ) -> None:
        """Test is_failure returns True for FAILED outcome."""
        assert failed_outcome.is_failure() is True

    def test_is_failure_returns_true_for_abandoned(
        self, abandoned_outcome: ModelClaudeCodeSessionOutcome
    ) -> None:
        """Test is_failure returns True for ABANDONED outcome."""
        assert abandoned_outcome.is_failure() is True

    def test_is_failure_returns_false_for_unknown(
        self, unknown_outcome: ModelClaudeCodeSessionOutcome
    ) -> None:
        """Test is_failure returns False for UNKNOWN outcome."""
        assert unknown_outcome.is_failure() is False


# =============================================================================
# String Representation Tests
# =============================================================================


@pytest.mark.unit
class TestModelClaudeCodeSessionOutcomeStringRepresentation:
    """Test __str__ and __repr__ output formats."""

    def test_str_output_format_success(
        self, success_outcome: ModelClaudeCodeSessionOutcome
    ) -> None:
        """Test __str__ output format for successful outcome."""
        result = str(success_outcome)

        assert "SessionOutcome(" in result
        assert "12345678..." in result  # First 8 chars of session_id
        assert "outcome=" in result
        assert "success" in result

    def test_str_output_format_with_error(
        self, failed_outcome: ModelClaudeCodeSessionOutcome
    ) -> None:
        """Test __str__ output format includes error code when present."""
        result = str(failed_outcome)

        assert "SessionOutcome(" in result
        assert "outcome=" in result
        assert "failed" in result
        assert "error=TOOL_EXECUTION_FAILED" in result

    def test_str_output_format_without_error(
        self, abandoned_outcome: ModelClaudeCodeSessionOutcome
    ) -> None:
        """Test __str__ output format excludes error info when None."""
        result = str(abandoned_outcome)

        assert "error=" not in result
        assert "abandoned" in result

    def test_repr_output_format(
        self, success_outcome: ModelClaudeCodeSessionOutcome
    ) -> None:
        """Test __repr__ output format includes all fields."""
        result = repr(success_outcome)

        assert "ModelClaudeCodeSessionOutcome(" in result
        assert "session_id=" in result
        assert "outcome=" in result
        assert "error=" in result
        assert "correlation_id=" in result

    def test_repr_output_format_with_error(
        self, failed_outcome: ModelClaudeCodeSessionOutcome
    ) -> None:
        """Test __repr__ output format with error details."""
        result = repr(failed_outcome)

        assert "ModelClaudeCodeSessionOutcome(" in result
        assert "session_id=" in result
        assert "ModelErrorDetails" in result or "error=" in result

    def test_repr_is_valid_python_expression(self, sample_session_id: UUID) -> None:
        """Test that __repr__ produces a recognizable structure."""
        outcome = ModelClaudeCodeSessionOutcome(
            session_id=sample_session_id,
            outcome=EnumClaudeCodeSessionOutcome.SUCCESS,
        )
        result = repr(outcome)

        # Verify it contains the class name and key attributes
        assert result.startswith("ModelClaudeCodeSessionOutcome(")
        assert result.endswith(")")


# =============================================================================
# Serialization Tests
# =============================================================================


@pytest.mark.unit
class TestModelClaudeCodeSessionOutcomeSerialization:
    """Test serialization and deserialization of ModelClaudeCodeSessionOutcome."""

    def test_model_dump_basic(
        self, success_outcome: ModelClaudeCodeSessionOutcome
    ) -> None:
        """Test model_dump produces valid dictionary output."""
        data = success_outcome.model_dump()

        assert isinstance(data, dict)
        assert data["session_id"] == UUID("12345678-1234-5678-1234-567812345678")
        assert data["outcome"] == EnumClaudeCodeSessionOutcome.SUCCESS
        assert data["error"] is None
        assert data["correlation_id"] is None

    def test_model_dump_with_error(
        self, failed_outcome: ModelClaudeCodeSessionOutcome
    ) -> None:
        """Test model_dump includes error details when present."""
        data = failed_outcome.model_dump()

        assert data["error"] is not None
        assert data["error"]["error_code"] == "TOOL_EXECUTION_FAILED"
        assert data["error"]["error_type"] == "runtime"
        assert data["error"]["error_message"] == "File not found during edit operation"

    def test_model_dump_json_mode(
        self, success_outcome: ModelClaudeCodeSessionOutcome
    ) -> None:
        """Test model_dump with mode='json' produces JSON-serializable output."""
        data = success_outcome.model_dump(mode="json")

        assert isinstance(data, dict)
        assert data["session_id"] == "12345678-1234-5678-1234-567812345678"
        assert data["outcome"] == "success"

    def test_model_dump_json_string(
        self, success_outcome: ModelClaudeCodeSessionOutcome
    ) -> None:
        """Test model_dump_json produces valid JSON string."""
        json_str = success_outcome.model_dump_json()

        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["session_id"] == "12345678-1234-5678-1234-567812345678"
        assert parsed["outcome"] == "success"

    def test_model_validate_from_dict(self) -> None:
        """Test model_validate creates valid model from dictionary."""
        data = {
            "session_id": "abcd1234-abcd-1234-abcd-1234abcd5678",
            "outcome": "failed",
            "error": None,
            "correlation_id": None,
        }

        outcome = ModelClaudeCodeSessionOutcome.model_validate(data)

        assert outcome.session_id == UUID("abcd1234-abcd-1234-abcd-1234abcd5678")
        assert outcome.outcome == EnumClaudeCodeSessionOutcome.FAILED
        assert outcome.error is None

    def test_model_validate_with_error_dict(self) -> None:
        """Test model_validate handles nested error details dict."""
        data = {
            "session_id": "abcd1234-abcd-1234-abcd-1234abcd5678",
            "outcome": "failed",
            "error": {
                "error_code": "TEST_ERROR",
                "error_type": "validation",
                "error_message": "Test error message",
            },
            "correlation_id": None,
        }

        outcome = ModelClaudeCodeSessionOutcome.model_validate(data)

        assert outcome.error is not None
        assert outcome.error.error_code == "TEST_ERROR"
        assert outcome.error.error_type == "validation"

    def test_round_trip_serialization(
        self,
        sample_session_id: UUID,
        sample_correlation_id: UUID,
        sample_error_details: ModelErrorDetails,  # type: ignore[type-arg] - generic param unused
    ) -> None:
        """Test full round-trip serialization preserves data."""
        original = ModelClaudeCodeSessionOutcome(
            session_id=sample_session_id,
            outcome=EnumClaudeCodeSessionOutcome.FAILED,
            error=sample_error_details,
            correlation_id=sample_correlation_id,
        )

        # Serialize to JSON string
        json_str = original.model_dump_json()

        # Deserialize back
        json_data = json.loads(json_str)
        deserialized = ModelClaudeCodeSessionOutcome.model_validate(json_data)

        assert deserialized.session_id == original.session_id
        assert deserialized.outcome == original.outcome
        assert deserialized.correlation_id == original.correlation_id
        assert deserialized.error is not None
        # error is confirmed not None above, but mypy doesn't narrow original.error
        assert deserialized.error.error_code == original.error.error_code  # type: ignore[union-attr]

    def test_deserialization_without_optional_fields(self) -> None:
        """Test deserialization works with only required fields."""
        json_data = {
            "session_id": "12345678-1234-5678-1234-567812345678",
            "outcome": "success",
        }

        outcome = ModelClaudeCodeSessionOutcome.model_validate(json_data)

        assert outcome.session_id == UUID("12345678-1234-5678-1234-567812345678")
        assert outcome.outcome == EnumClaudeCodeSessionOutcome.SUCCESS
        assert outcome.error is None
        assert outcome.correlation_id is None


# =============================================================================
# Import Path Tests
# =============================================================================


@pytest.mark.unit
class TestModelClaudeCodeSessionOutcomeImports:
    """Test that model is importable from all documented paths."""

    def test_importable_from_models_hooks(self) -> None:
        """Test model is importable from omnibase_core.models.hooks."""
        from omnibase_core.models.hooks import ModelClaudeCodeSessionOutcome as Model1

        assert Model1 is ModelClaudeCodeSessionOutcome

    def test_importable_from_models_hooks_claude_code(self) -> None:
        """Test model is importable from omnibase_core.models.hooks.claude_code."""
        from omnibase_core.models.hooks.claude_code import (
            ModelClaudeCodeSessionOutcome as Model2,
        )

        assert Model2 is ModelClaudeCodeSessionOutcome

    def test_importable_from_integrations_claude_code(self) -> None:
        """Test model is importable as ClaudeSessionOutcome from integrations."""
        from omnibase_core.integrations.claude_code import ClaudeSessionOutcome

        # Verify it's the same class (aliased)
        outcome = ClaudeSessionOutcome(
            session_id=uuid4(),
            outcome=EnumClaudeCodeSessionOutcome.SUCCESS,
        )
        assert isinstance(outcome, ModelClaudeCodeSessionOutcome)

    def test_enum_importable_from_integrations(self) -> None:
        """Test enum is importable as ClaudeCodeSessionOutcome from integrations."""
        from omnibase_core.integrations.claude_code import ClaudeCodeSessionOutcome

        # Verify it's the same enum (aliased)
        assert ClaudeCodeSessionOutcome.SUCCESS == EnumClaudeCodeSessionOutcome.SUCCESS
        assert ClaudeCodeSessionOutcome.FAILED == EnumClaudeCodeSessionOutcome.FAILED
