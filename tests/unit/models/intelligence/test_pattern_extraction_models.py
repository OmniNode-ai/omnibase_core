# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for pattern extraction models (OMN-1587).

Tests comprehensive pattern extraction model functionality including:
- EnumPatternKind enum with StrValueHelper behavior
- ModelPatternWarning for non-fatal extraction warnings
- ModelPatternError for structured error handling
- ModelPatternRecord for individual pattern data
- ModelPatternExtractionInput with data source validation
- ModelPatternExtractionOutput with pattern count validation

All models are frozen (immutable) and use extra="forbid".
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumPatternKind
from omnibase_core.models.intelligence import (
    ModelPatternError,
    ModelPatternExtractionInput,
    ModelPatternExtractionOutput,
    ModelPatternRecord,
    ModelPatternWarning,
)
from omnibase_core.models.primitives import ModelSemVer

pytestmark = pytest.mark.unit


# ============================================================================
# Test: EnumPatternKind
# ============================================================================


class TestEnumPatternKind:
    """Tests for EnumPatternKind enum."""

    def test_all_five_values_exist(self) -> None:
        """Test that all expected enum values exist."""
        expected_values = {
            "FILE_ACCESS",
            "ERROR",
            "ARCHITECTURE",
            "TOOL_USAGE",
            "TOOL_FAILURE",
        }
        actual_values = {member.name for member in EnumPatternKind}

        assert actual_values == expected_values
        assert EnumPatternKind.TOOL_FAILURE.value == "tool_failure"

    def test_str_helper_returns_value(self) -> None:
        """Test that StrValueHelper makes str() return the value."""
        assert str(EnumPatternKind.FILE_ACCESS) == "file_access"
        assert str(EnumPatternKind.ERROR) == "error"
        assert str(EnumPatternKind.ARCHITECTURE) == "architecture"
        assert str(EnumPatternKind.TOOL_USAGE) == "tool_usage"
        assert str(EnumPatternKind.TOOL_FAILURE) == "tool_failure"

    def test_values_are_unique(self) -> None:
        """Test that all enum values are unique."""
        values = [member.value for member in EnumPatternKind]
        assert len(values) == len(set(values))

    def test_value_attribute_matches_str(self) -> None:
        """Test that .value attribute matches str() output."""
        for member in EnumPatternKind:
            assert str(member) == member.value

    def test_enum_is_string_based(self) -> None:
        """Test that enum members are string instances."""
        for member in EnumPatternKind:
            assert isinstance(member.value, str)

    def test_can_compare_with_string(self) -> None:
        """Test that enum value equals the string value."""
        assert EnumPatternKind.FILE_ACCESS.value == "file_access"
        assert EnumPatternKind.ERROR.value == "error"


# ============================================================================
# Test: ModelPatternWarning
# ============================================================================


class TestModelPatternWarning:
    """Tests for ModelPatternWarning model."""

    def test_create_with_required_fields(self) -> None:
        """Test creating warning with only required fields."""
        warning = ModelPatternWarning(
            code="INCOMPLETE_SESSION",
            message="Session data is incomplete",
        )

        assert warning.code == "INCOMPLETE_SESSION"
        assert warning.message == "Session data is incomplete"
        assert warning.context == {}

    def test_create_with_all_fields(self) -> None:
        """Test creating warning with all fields."""
        warning = ModelPatternWarning(
            code="LOW_CONFIDENCE",
            message="Some patterns have low confidence",
            context={"threshold": 0.6, "actual": 0.45},
        )

        assert warning.code == "LOW_CONFIDENCE"
        assert warning.message == "Some patterns have low confidence"
        assert warning.context["threshold"] == 0.6
        assert warning.context["actual"] == 0.45

    def test_frozen_immutability_code(self) -> None:
        """Test that code cannot be modified."""
        warning = ModelPatternWarning(code="TEST", message="Test warning")

        with pytest.raises(ValidationError):
            warning.code = "MODIFIED"

    def test_frozen_immutability_message(self) -> None:
        """Test that message cannot be modified."""
        warning = ModelPatternWarning(code="TEST", message="Test warning")

        with pytest.raises(ValidationError):
            warning.message = "Modified message"

    def test_frozen_immutability_context(self) -> None:
        """Test that context cannot be reassigned."""
        warning = ModelPatternWarning(code="TEST", message="Test warning")

        with pytest.raises(ValidationError):
            warning.context = {"new": "data"}

    def test_context_defaults_to_empty_dict(self) -> None:
        """Test that context uses default_factory for empty dict."""
        w1 = ModelPatternWarning(code="TEST1", message="Test 1")
        w2 = ModelPatternWarning(code="TEST2", message="Test 2")

        assert w1.context == {}
        assert w2.context == {}

    def test_code_min_length_validation(self) -> None:
        """Test that code requires at least 1 character."""
        # Valid single character
        warning = ModelPatternWarning(code="X", message="Test")
        assert warning.code == "X"

        # Empty string should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternWarning(code="", message="Test")

        assert "code" in str(exc_info.value)

    def test_message_min_length_validation(self) -> None:
        """Test that message requires at least 1 character."""
        # Valid single character
        warning = ModelPatternWarning(code="TEST", message="X")
        assert warning.message == "X"

        # Empty string should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternWarning(code="TEST", message="")

        assert "message" in str(exc_info.value)

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternWarning(
                code="TEST",
                message="Test",
                extra_field="not_allowed",  # type: ignore[call-arg]
            )

        assert "extra_field" in str(exc_info.value)

    def test_context_with_nested_structure(self) -> None:
        """Test context with nested JSON-compatible structure."""
        warning = ModelPatternWarning(
            code="COMPLEX",
            message="Complex context",
            context={
                "level1": {"level2": {"value": 42}},
                "list_data": [1, 2, 3],
                "nullable": None,
            },
        )

        # Access nested structures with proper type narrowing
        level1 = warning.context["level1"]
        assert isinstance(level1, dict)
        level2 = level1["level2"]
        assert isinstance(level2, dict)
        assert level2["value"] == 42

        assert warning.context["list_data"] == [1, 2, 3]
        assert warning.context["nullable"] is None


# ============================================================================
# Test: ModelPatternError
# ============================================================================


class TestModelPatternError:
    """Tests for ModelPatternError model."""

    def test_create_with_required_fields(self) -> None:
        """Test creating error with required fields."""
        error = ModelPatternError(
            code="SESSION_NOT_FOUND",
            message="Session does not exist",
            recoverable=True,
        )

        assert error.code == "SESSION_NOT_FOUND"
        assert error.message == "Session does not exist"
        assert error.recoverable is True
        assert error.context == {}

    def test_create_with_all_fields(self) -> None:
        """Test creating error with all fields."""
        error = ModelPatternError(
            code="DATABASE_ERROR",
            message="Failed to query database",
            recoverable=False,
            context={"table": "sessions", "error_code": 1045},
        )

        assert error.code == "DATABASE_ERROR"
        assert error.message == "Failed to query database"
        assert error.recoverable is False
        assert error.context["table"] == "sessions"
        assert error.context["error_code"] == 1045

    def test_frozen_immutability(self) -> None:
        """Test that the model is immutable."""
        error = ModelPatternError(code="TEST", message="Test", recoverable=True)

        with pytest.raises(ValidationError):
            error.code = "MODIFIED"

        with pytest.raises(ValidationError):
            error.recoverable = False

    def test_context_defaults_to_empty_dict(self) -> None:
        """Test that context uses default_factory for empty dict."""
        e1 = ModelPatternError(code="E1", message="Error 1", recoverable=True)
        e2 = ModelPatternError(code="E2", message="Error 2", recoverable=False)

        assert e1.context == {}
        assert e2.context == {}

    def test_recoverable_is_required(self) -> None:
        """Test that recoverable has no default and is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternError(code="TEST", message="Test")  # type: ignore[call-arg]

        assert "recoverable" in str(exc_info.value)

    def test_recoverable_true(self) -> None:
        """Test error with recoverable=True."""
        error = ModelPatternError(
            code="TIMEOUT", message="Request timed out", recoverable=True
        )
        assert error.recoverable is True

    def test_recoverable_false(self) -> None:
        """Test error with recoverable=False."""
        error = ModelPatternError(
            code="FATAL", message="Fatal error", recoverable=False
        )
        assert error.recoverable is False

    def test_code_min_length_validation(self) -> None:
        """Test that code requires at least 1 character."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternError(code="", message="Test", recoverable=True)

        assert "code" in str(exc_info.value)

    def test_message_min_length_validation(self) -> None:
        """Test that message requires at least 1 character."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternError(code="TEST", message="", recoverable=True)

        assert "message" in str(exc_info.value)

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternError(
                code="TEST",
                message="Test",
                recoverable=True,
                unknown_field="bad",  # type: ignore[call-arg]
            )

        assert "unknown_field" in str(exc_info.value)


# ============================================================================
# Test: ModelPatternRecord
# ============================================================================


class TestModelPatternRecord:
    """Tests for ModelPatternRecord model."""

    @pytest.fixture
    def valid_record_data(self) -> dict:
        """Minimal valid data for creating a pattern record."""
        return {
            "pattern_id": uuid4(),
            "kind": EnumPatternKind.FILE_ACCESS,
            "confidence": 0.85,
            "occurrences": 5,
            "description": "Files A and B are frequently accessed together",
        }

    def test_create_with_required_fields(self, valid_record_data: dict) -> None:
        """Test creating record with only required fields."""
        record = ModelPatternRecord(**valid_record_data)

        assert record.pattern_id == valid_record_data["pattern_id"]
        assert record.kind == EnumPatternKind.FILE_ACCESS
        assert record.confidence == 0.85
        assert record.occurrences == 5
        assert "Files A and B" in record.description
        assert record.evidence == []
        assert record.metadata == {}

    def test_create_with_all_fields(self, valid_record_data: dict) -> None:
        """Test creating record with all fields."""
        valid_record_data["evidence"] = ["session-1", "session-2", "file.py"]
        valid_record_data["metadata"] = {"source": "analysis", "version": 1}

        record = ModelPatternRecord(**valid_record_data)

        assert len(record.evidence) == 3
        assert "session-1" in record.evidence
        assert record.metadata["source"] == "analysis"
        assert record.metadata["version"] == 1

    def test_confidence_valid_at_lower_bound(self, valid_record_data: dict) -> None:
        """Test confidence at lower bound (0.0)."""
        valid_record_data["confidence"] = 0.0
        record = ModelPatternRecord(**valid_record_data)
        assert record.confidence == 0.0

    def test_confidence_valid_at_upper_bound(self, valid_record_data: dict) -> None:
        """Test confidence at upper bound (1.0)."""
        valid_record_data["confidence"] = 1.0
        record = ModelPatternRecord(**valid_record_data)
        assert record.confidence == 1.0

    def test_confidence_invalid_below_lower_bound(
        self, valid_record_data: dict
    ) -> None:
        """Test confidence below lower bound fails."""
        valid_record_data["confidence"] = -0.1

        with pytest.raises(ValidationError) as exc_info:
            ModelPatternRecord(**valid_record_data)

        assert "confidence" in str(exc_info.value)

    def test_confidence_invalid_above_upper_bound(
        self, valid_record_data: dict
    ) -> None:
        """Test confidence above upper bound fails."""
        valid_record_data["confidence"] = 1.1

        with pytest.raises(ValidationError) as exc_info:
            ModelPatternRecord(**valid_record_data)

        assert "confidence" in str(exc_info.value)

    def test_occurrences_valid_at_minimum(self, valid_record_data: dict) -> None:
        """Test occurrences at minimum value (1)."""
        valid_record_data["occurrences"] = 1
        record = ModelPatternRecord(**valid_record_data)
        assert record.occurrences == 1

    def test_occurrences_invalid_below_minimum(self, valid_record_data: dict) -> None:
        """Test occurrences below minimum fails."""
        valid_record_data["occurrences"] = 0

        with pytest.raises(ValidationError) as exc_info:
            ModelPatternRecord(**valid_record_data)

        assert "occurrences" in str(exc_info.value)

    def test_occurrences_negative_fails(self, valid_record_data: dict) -> None:
        """Test negative occurrences fails."""
        valid_record_data["occurrences"] = -1

        with pytest.raises(ValidationError) as exc_info:
            ModelPatternRecord(**valid_record_data)

        assert "occurrences" in str(exc_info.value)

    def test_evidence_defaults_to_empty_list(self, valid_record_data: dict) -> None:
        """Test that evidence uses default_factory for empty list."""
        r1 = ModelPatternRecord(**valid_record_data)
        r2 = ModelPatternRecord(**valid_record_data)

        assert r1.evidence == []
        assert r2.evidence == []

    def test_metadata_defaults_to_empty_dict(self, valid_record_data: dict) -> None:
        """Test that metadata uses default_factory for empty dict."""
        r1 = ModelPatternRecord(**valid_record_data)
        r2 = ModelPatternRecord(**valid_record_data)

        assert r1.metadata == {}
        assert r2.metadata == {}

    def test_uses_enum_pattern_kind(self, valid_record_data: dict) -> None:
        """Test that kind field uses EnumPatternKind."""
        for kind in EnumPatternKind:
            valid_record_data["kind"] = kind
            record = ModelPatternRecord(**valid_record_data)
            assert record.kind == kind
            assert isinstance(record.kind, EnumPatternKind)

    def test_kind_from_string_value(self, valid_record_data: dict) -> None:
        """Test that kind can be created from string value."""
        valid_record_data["kind"] = "error"
        record = ModelPatternRecord(**valid_record_data)
        assert record.kind == EnumPatternKind.ERROR

    def test_frozen_immutability(self, valid_record_data: dict) -> None:
        """Test that the model is immutable."""
        record = ModelPatternRecord(**valid_record_data)

        with pytest.raises(ValidationError):
            record.confidence = 0.5

        with pytest.raises(ValidationError):
            record.occurrences = 10

    def test_description_min_length_validation(self, valid_record_data: dict) -> None:
        """Test that description requires at least 1 character."""
        valid_record_data["description"] = ""

        with pytest.raises(ValidationError) as exc_info:
            ModelPatternRecord(**valid_record_data)

        assert "description" in str(exc_info.value)

    def test_extra_fields_forbidden(self, valid_record_data: dict) -> None:
        """Test that extra fields are rejected."""
        valid_record_data["unknown"] = "value"

        with pytest.raises(ValidationError) as exc_info:
            ModelPatternRecord(**valid_record_data)

        assert "unknown" in str(exc_info.value)

    def test_pattern_id_as_uuid(self, valid_record_data: dict) -> None:
        """Test that pattern_id is a UUID."""
        record = ModelPatternRecord(**valid_record_data)
        assert isinstance(record.pattern_id, UUID)

    def test_pattern_id_from_string(self, valid_record_data: dict) -> None:
        """Test that pattern_id can be created from string."""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        valid_record_data["pattern_id"] = uuid_str
        record = ModelPatternRecord(**valid_record_data)
        assert str(record.pattern_id) == uuid_str


# ============================================================================
# Test: ModelPatternExtractionInput
# ============================================================================


class TestModelPatternExtractionInput:
    """Tests for ModelPatternExtractionInput model."""

    def test_create_with_session_ids(self) -> None:
        """Test creating input with session_ids."""
        input_model = ModelPatternExtractionInput(
            session_ids=["session-1", "session-2"],
        )

        assert input_model.session_ids == ["session-1", "session-2"]
        assert input_model.raw_events is None
        assert input_model.kinds is None
        assert input_model.min_occurrences == 2
        assert input_model.min_confidence == 0.6

    def test_create_with_raw_events(self) -> None:
        """Test creating input with raw_events."""
        raw_events: list[dict[str, str]] = [
            {"type": "file_access", "path": "/a.py"},
            {"type": "error", "message": "failed"},
        ]
        input_model = ModelPatternExtractionInput(
            # NOTE: List[dict[str, str]] is compatible with List[JsonType] at runtime
            raw_events=raw_events,  # type: ignore[arg-type]
        )

        assert input_model.session_ids == []
        assert input_model.raw_events == raw_events

    def test_validation_fails_when_both_empty(self) -> None:
        """Test that validation fails when both session_ids and raw_events are empty."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternExtractionInput(session_ids=[], raw_events=None)

        assert "data source" in str(exc_info.value).lower()

    def test_validation_fails_with_no_data_source(self) -> None:
        """Test validation fails with no data source provided."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternExtractionInput()

        assert "data source" in str(exc_info.value).lower()

    def test_validation_fails_with_empty_raw_events(self) -> None:
        """Test validation fails with empty raw_events list."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternExtractionInput(session_ids=[], raw_events=[])

        assert "data source" in str(exc_info.value).lower()

    def test_min_confidence_valid_at_lower_bound(self) -> None:
        """Test min_confidence at lower bound (0.0)."""
        input_model = ModelPatternExtractionInput(
            session_ids=["s1"],
            min_confidence=0.0,
        )
        assert input_model.min_confidence == 0.0

    def test_min_confidence_valid_at_upper_bound(self) -> None:
        """Test min_confidence at upper bound (1.0)."""
        input_model = ModelPatternExtractionInput(
            session_ids=["s1"],
            min_confidence=1.0,
        )
        assert input_model.min_confidence == 1.0

    def test_min_confidence_invalid_below_lower_bound(self) -> None:
        """Test min_confidence below lower bound fails."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternExtractionInput(
                session_ids=["s1"],
                min_confidence=-0.1,
            )

        assert "min_confidence" in str(exc_info.value)

    def test_min_confidence_invalid_above_upper_bound(self) -> None:
        """Test min_confidence above upper bound fails."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternExtractionInput(
                session_ids=["s1"],
                min_confidence=1.1,
            )

        assert "min_confidence" in str(exc_info.value)

    def test_min_occurrences_valid_at_minimum(self) -> None:
        """Test min_occurrences at minimum value (1)."""
        input_model = ModelPatternExtractionInput(
            session_ids=["s1"],
            min_occurrences=1,
        )
        assert input_model.min_occurrences == 1

    def test_min_occurrences_invalid_below_minimum(self) -> None:
        """Test min_occurrences below minimum fails."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternExtractionInput(
                session_ids=["s1"],
                min_occurrences=0,
            )

        assert "min_occurrences" in str(exc_info.value)

    def test_schema_version_is_model_semver(self) -> None:
        """Test that schema_version is ModelSemVer."""
        input_model = ModelPatternExtractionInput(session_ids=["s1"])

        assert isinstance(input_model.schema_version, ModelSemVer)
        assert input_model.schema_version.major == 1
        assert input_model.schema_version.minor == 0
        assert input_model.schema_version.patch == 0

    def test_custom_schema_version(self) -> None:
        """Test providing custom schema_version."""
        custom_version = ModelSemVer(major=2, minor=1, patch=3)
        input_model = ModelPatternExtractionInput(
            session_ids=["s1"],
            schema_version=custom_version,
        )

        assert input_model.schema_version.major == 2
        assert input_model.schema_version.minor == 1
        assert input_model.schema_version.patch == 3

    def test_kinds_filtering_none_means_all(self) -> None:
        """Test that kinds=None means extract all kinds."""
        input_model = ModelPatternExtractionInput(
            session_ids=["s1"],
            kinds=None,
        )
        assert input_model.kinds is None

    def test_kinds_filtering_specific_kinds(self) -> None:
        """Test that kinds can specify a list of specific kinds."""
        input_model = ModelPatternExtractionInput(
            session_ids=["s1"],
            kinds=[EnumPatternKind.FILE_ACCESS, EnumPatternKind.ERROR],
        )

        assert input_model.kinds is not None
        assert len(input_model.kinds) == 2
        assert EnumPatternKind.FILE_ACCESS in input_model.kinds
        assert EnumPatternKind.ERROR in input_model.kinds

    def test_correlation_id_optional(self) -> None:
        """Test that correlation_id is optional."""
        input_model = ModelPatternExtractionInput(session_ids=["s1"])
        assert input_model.correlation_id is None

    def test_correlation_id_as_uuid(self) -> None:
        """Test correlation_id as UUID."""
        test_uuid = uuid4()
        input_model = ModelPatternExtractionInput(
            session_ids=["s1"],
            correlation_id=test_uuid,
        )
        assert input_model.correlation_id == test_uuid
        assert isinstance(input_model.correlation_id, UUID)

    def test_time_window_filtering(self) -> None:
        """Test time window filtering fields."""
        start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 2, 0, 0, 0, tzinfo=UTC)

        input_model = ModelPatternExtractionInput(
            session_ids=["s1"],
            time_window_start=start,
            time_window_end=end,
        )

        assert input_model.time_window_start == start
        assert input_model.time_window_end == end

    def test_frozen_immutability(self) -> None:
        """Test that the model is immutable."""
        input_model = ModelPatternExtractionInput(session_ids=["s1"])

        with pytest.raises(ValidationError):
            input_model.min_confidence = 0.9

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPatternExtractionInput(
                session_ids=["s1"],
                unknown_field="bad",  # type: ignore[call-arg]
            )

        assert "unknown_field" in str(exc_info.value)

    def test_source_snapshot_id_optional(self) -> None:
        """Test that source_snapshot_id is optional."""
        snapshot_uuid = uuid4()
        input_model = ModelPatternExtractionInput(
            session_ids=["s1"],
            source_snapshot_id=snapshot_uuid,
        )
        assert input_model.source_snapshot_id == snapshot_uuid

    # -------------------------------------------------------------------------
    # Time Window Validation Tests
    # -------------------------------------------------------------------------

    def test_time_window_validation_start_less_than_end(self) -> None:
        """Test that time_window_start < time_window_end is valid."""
        start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 2, 0, 0, 0, tzinfo=UTC)

        input_model = ModelPatternExtractionInput(
            session_ids=["s1"],
            time_window_start=start,
            time_window_end=end,
        )

        assert input_model.time_window_start == start
        assert input_model.time_window_end == end

    def test_time_window_validation_start_equals_end_fails(self) -> None:
        """Test that time_window_start == time_window_end fails validation."""
        same_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            ModelPatternExtractionInput(
                session_ids=["s1"],
                time_window_start=same_time,
                time_window_end=same_time,
            )

        assert "time_window_start" in str(exc_info.value)

    def test_time_window_validation_start_greater_than_end_fails(self) -> None:
        """Test that time_window_start > time_window_end fails validation."""
        start = datetime(2025, 1, 2, 0, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            ModelPatternExtractionInput(
                session_ids=["s1"],
                time_window_start=start,
                time_window_end=end,
            )

        assert "time_window_start" in str(exc_info.value)

    def test_time_window_validation_only_start_provided(self) -> None:
        """Test that providing only time_window_start is valid."""
        start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)

        input_model = ModelPatternExtractionInput(
            session_ids=["s1"],
            time_window_start=start,
        )

        assert input_model.time_window_start == start
        assert input_model.time_window_end is None

    def test_time_window_validation_only_end_provided(self) -> None:
        """Test that providing only time_window_end is valid."""
        end = datetime(2025, 1, 2, 0, 0, 0, tzinfo=UTC)

        input_model = ModelPatternExtractionInput(
            session_ids=["s1"],
            time_window_end=end,
        )

        assert input_model.time_window_start is None
        assert input_model.time_window_end == end


# ============================================================================
# Test: ModelPatternExtractionOutput
# ============================================================================


class TestModelPatternExtractionOutput:
    """Tests for ModelPatternExtractionOutput model."""

    @pytest.fixture
    def minimal_output_data(self) -> dict:
        """Minimal valid data for creating an output model."""
        return {
            "success": True,
            "total_patterns_found": 0,
            "processing_time_ms": 150.5,
            "sessions_analyzed": 3,
        }

    @pytest.fixture
    def sample_pattern_record(self) -> ModelPatternRecord:
        """Sample pattern record for testing."""
        return ModelPatternRecord(
            pattern_id=uuid4(),
            kind=EnumPatternKind.FILE_ACCESS,
            confidence=0.9,
            occurrences=5,
            description="Test pattern",
        )

    def test_create_with_required_fields(self, minimal_output_data: dict) -> None:
        """Test creating output with required fields."""
        output = ModelPatternExtractionOutput(**minimal_output_data)

        assert output.success is True
        assert output.total_patterns_found == 0
        assert output.processing_time_ms == 150.5
        assert output.sessions_analyzed == 3
        assert output.deterministic is False
        assert output.events_scanned == 0
        assert output.warnings == []
        assert output.errors == []
        assert output.correlation_id is None

    def test_patterns_by_kind_has_stable_shape(self, minimal_output_data: dict) -> None:
        """Test that patterns_by_kind has all kinds present."""
        output = ModelPatternExtractionOutput(**minimal_output_data)

        # All EnumPatternKind values should be keys
        for kind in EnumPatternKind:
            assert kind in output.patterns_by_kind
            assert output.patterns_by_kind[kind] == []

    def test_patterns_by_kind_with_patterns(
        self, minimal_output_data: dict, sample_pattern_record: ModelPatternRecord
    ) -> None:
        """Test patterns_by_kind with actual patterns."""
        patterns_by_kind: dict[EnumPatternKind, list[ModelPatternRecord]] = {
            kind: [] for kind in EnumPatternKind
        }
        patterns_by_kind[EnumPatternKind.FILE_ACCESS] = [sample_pattern_record]

        minimal_output_data["patterns_by_kind"] = patterns_by_kind
        minimal_output_data["total_patterns_found"] = 1

        output = ModelPatternExtractionOutput(**minimal_output_data)

        assert len(output.patterns_by_kind[EnumPatternKind.FILE_ACCESS]) == 1
        assert output.patterns_by_kind[EnumPatternKind.ERROR] == []

    def test_total_patterns_found_validation_matches(
        self, minimal_output_data: dict, sample_pattern_record: ModelPatternRecord
    ) -> None:
        """Test that total_patterns_found must match actual count."""
        patterns_by_kind: dict[EnumPatternKind, list[ModelPatternRecord]] = {
            kind: [] for kind in EnumPatternKind
        }
        patterns_by_kind[EnumPatternKind.FILE_ACCESS] = [sample_pattern_record]

        minimal_output_data["patterns_by_kind"] = patterns_by_kind
        minimal_output_data["total_patterns_found"] = 1  # Correct count

        output = ModelPatternExtractionOutput(**minimal_output_data)
        assert output.total_patterns_found == 1

    def test_total_patterns_found_validation_fails_on_mismatch(
        self, minimal_output_data: dict, sample_pattern_record: ModelPatternRecord
    ) -> None:
        """Test that mismatched total_patterns_found raises error."""
        patterns_by_kind: dict[EnumPatternKind, list[ModelPatternRecord]] = {
            kind: [] for kind in EnumPatternKind
        }
        patterns_by_kind[EnumPatternKind.FILE_ACCESS] = [sample_pattern_record]

        minimal_output_data["patterns_by_kind"] = patterns_by_kind
        minimal_output_data["total_patterns_found"] = 5  # Wrong count

        with pytest.raises(ValidationError) as exc_info:
            ModelPatternExtractionOutput(**minimal_output_data)

        error_str = str(exc_info.value)
        assert "total_patterns_found" in error_str or "does not match" in error_str

    def test_warnings_defaults_to_empty_list(self, minimal_output_data: dict) -> None:
        """Test that warnings defaults to empty list."""
        output = ModelPatternExtractionOutput(**minimal_output_data)
        assert output.warnings == []

    def test_errors_defaults_to_empty_list(self, minimal_output_data: dict) -> None:
        """Test that errors defaults to empty list."""
        output = ModelPatternExtractionOutput(**minimal_output_data)
        assert output.errors == []

    def test_warnings_with_values(self, minimal_output_data: dict) -> None:
        """Test output with warnings."""
        warning = ModelPatternWarning(
            code="LOW_DATA",
            message="Insufficient data for analysis",
        )
        minimal_output_data["warnings"] = [warning]

        output = ModelPatternExtractionOutput(**minimal_output_data)

        assert len(output.warnings) == 1
        assert output.warnings[0].code == "LOW_DATA"

    def test_errors_with_values(self, minimal_output_data: dict) -> None:
        """Test output with errors."""
        error = ModelPatternError(
            code="SESSION_ERROR",
            message="Failed to load session",
            recoverable=True,
        )
        minimal_output_data["errors"] = [error]

        output = ModelPatternExtractionOutput(**minimal_output_data)

        assert len(output.errors) == 1
        assert output.errors[0].code == "SESSION_ERROR"
        assert output.errors[0].recoverable is True

    def test_schema_version_is_model_semver(self, minimal_output_data: dict) -> None:
        """Test that schema_version is ModelSemVer."""
        output = ModelPatternExtractionOutput(**minimal_output_data)

        assert isinstance(output.schema_version, ModelSemVer)
        assert output.schema_version.major == 1
        assert output.schema_version.minor == 0
        assert output.schema_version.patch == 0

    def test_frozen_immutability(self, minimal_output_data: dict) -> None:
        """Test that the model is immutable."""
        output = ModelPatternExtractionOutput(**minimal_output_data)

        with pytest.raises(ValidationError):
            output.success = False

        with pytest.raises(ValidationError):
            output.total_patterns_found = 99

    def test_extra_fields_forbidden(self, minimal_output_data: dict) -> None:
        """Test that extra fields are rejected."""
        minimal_output_data["unknown"] = "bad"

        with pytest.raises(ValidationError) as exc_info:
            ModelPatternExtractionOutput(**minimal_output_data)

        assert "unknown" in str(exc_info.value)

    def test_correlation_id_optional(self, minimal_output_data: dict) -> None:
        """Test that correlation_id is optional."""
        test_uuid = uuid4()
        minimal_output_data["correlation_id"] = test_uuid

        output = ModelPatternExtractionOutput(**minimal_output_data)
        assert output.correlation_id == test_uuid

    def test_source_snapshot_id_optional(self, minimal_output_data: dict) -> None:
        """Test that source_snapshot_id is optional."""
        snapshot_uuid = uuid4()
        minimal_output_data["source_snapshot_id"] = snapshot_uuid

        output = ModelPatternExtractionOutput(**minimal_output_data)
        assert output.source_snapshot_id == snapshot_uuid

    def test_deterministic_flag(self, minimal_output_data: dict) -> None:
        """Test deterministic flag."""
        minimal_output_data["deterministic"] = True

        output = ModelPatternExtractionOutput(**minimal_output_data)
        assert output.deterministic is True

    def test_events_scanned_field(self, minimal_output_data: dict) -> None:
        """Test events_scanned field."""
        minimal_output_data["events_scanned"] = 1000

        output = ModelPatternExtractionOutput(**minimal_output_data)
        assert output.events_scanned == 1000

    def test_events_scanned_validation_non_negative(
        self, minimal_output_data: dict
    ) -> None:
        """Test events_scanned must be non-negative."""
        minimal_output_data["events_scanned"] = -1

        with pytest.raises(ValidationError) as exc_info:
            ModelPatternExtractionOutput(**minimal_output_data)

        assert "events_scanned" in str(exc_info.value)

    def test_processing_time_ms_validation_non_negative(
        self, minimal_output_data: dict
    ) -> None:
        """Test processing_time_ms must be non-negative."""
        minimal_output_data["processing_time_ms"] = -1.0

        with pytest.raises(ValidationError) as exc_info:
            ModelPatternExtractionOutput(**minimal_output_data)

        assert "processing_time_ms" in str(exc_info.value)

    def test_sessions_analyzed_validation_non_negative(
        self, minimal_output_data: dict
    ) -> None:
        """Test sessions_analyzed must be non-negative."""
        minimal_output_data["sessions_analyzed"] = -1

        with pytest.raises(ValidationError) as exc_info:
            ModelPatternExtractionOutput(**minimal_output_data)

        assert "sessions_analyzed" in str(exc_info.value)

    def test_success_false_with_errors(self, minimal_output_data: dict) -> None:
        """Test output with success=False and errors."""
        minimal_output_data["success"] = False
        minimal_output_data["errors"] = [
            ModelPatternError(
                code="FATAL",
                message="Extraction failed",
                recoverable=False,
            )
        ]

        output = ModelPatternExtractionOutput(**minimal_output_data)

        assert output.success is False
        assert len(output.errors) == 1

    # -------------------------------------------------------------------------
    # Patterns By Kind Completeness Tests
    # -------------------------------------------------------------------------

    def test_patterns_by_kind_missing_keys_fails(
        self, minimal_output_data: dict
    ) -> None:
        """Test that partial patterns_by_kind dict fails with clear error."""
        # Only provide one key, missing the others
        partial_patterns: dict[EnumPatternKind, list[ModelPatternRecord]] = {
            EnumPatternKind.FILE_ACCESS: [],
        }
        minimal_output_data["patterns_by_kind"] = partial_patterns

        with pytest.raises(ValidationError) as exc_info:
            ModelPatternExtractionOutput(**minimal_output_data)

        error_str = str(exc_info.value)
        assert "patterns_by_kind must contain all EnumPatternKind keys" in error_str
        assert "Missing:" in error_str

    def test_patterns_by_kind_all_keys_required(
        self, minimal_output_data: dict
    ) -> None:
        """Test that all EnumPatternKind keys must be present."""
        # Provide all but one key
        almost_complete: dict[EnumPatternKind, list[ModelPatternRecord]] = {
            EnumPatternKind.FILE_ACCESS: [],
            EnumPatternKind.ERROR: [],
            EnumPatternKind.ARCHITECTURE: [],
            EnumPatternKind.TOOL_FAILURE: [],
            # Missing: TOOL_USAGE
        }
        minimal_output_data["patterns_by_kind"] = almost_complete

        with pytest.raises(ValidationError) as exc_info:
            ModelPatternExtractionOutput(**minimal_output_data)

        error_str = str(exc_info.value)
        assert "TOOL_USAGE" in error_str


# ============================================================================
# Test: Serialization Round-Trip
# ============================================================================


class TestSerializationRoundTrip:
    """Tests for serialization and deserialization of pattern models."""

    def test_pattern_record_round_trip(self) -> None:
        """Test ModelPatternRecord serialization round-trip."""
        original = ModelPatternRecord(
            pattern_id=uuid4(),
            kind=EnumPatternKind.ARCHITECTURE,
            confidence=0.88,
            occurrences=12,
            description="Module coupling pattern",
            evidence=["mod_a.py", "mod_b.py"],
            metadata={"layer": "domain", "coupling": "high"},
        )

        data = original.model_dump()
        restored = ModelPatternRecord.model_validate(data)

        assert original.pattern_id == restored.pattern_id
        assert original.kind == restored.kind
        assert original.confidence == restored.confidence
        assert original.evidence == restored.evidence

    def test_pattern_extraction_input_round_trip(self) -> None:
        """Test ModelPatternExtractionInput serialization round-trip."""
        original = ModelPatternExtractionInput(
            session_ids=["s1", "s2"],
            correlation_id=uuid4(),
            kinds=[EnumPatternKind.ERROR, EnumPatternKind.TOOL_USAGE],
            min_confidence=0.75,
            min_occurrences=3,
        )

        data = original.model_dump()
        restored = ModelPatternExtractionInput.model_validate(data)

        assert original.session_ids == restored.session_ids
        assert original.correlation_id == restored.correlation_id
        assert original.kinds == restored.kinds
        assert original.min_confidence == restored.min_confidence

    def test_pattern_extraction_output_round_trip(self) -> None:
        """Test ModelPatternExtractionOutput serialization round-trip."""
        pattern = ModelPatternRecord(
            pattern_id=uuid4(),
            kind=EnumPatternKind.FILE_ACCESS,
            confidence=0.95,
            occurrences=8,
            description="Co-access pattern",
        )

        patterns_by_kind: dict[EnumPatternKind, list[ModelPatternRecord]] = {
            kind: [] for kind in EnumPatternKind
        }
        patterns_by_kind[EnumPatternKind.FILE_ACCESS] = [pattern]

        original = ModelPatternExtractionOutput(
            success=True,
            patterns_by_kind=patterns_by_kind,
            total_patterns_found=1,
            processing_time_ms=250.0,
            sessions_analyzed=5,
            correlation_id=uuid4(),
        )

        data = original.model_dump()
        restored = ModelPatternExtractionOutput.model_validate(data)

        assert original.success == restored.success
        assert original.total_patterns_found == restored.total_patterns_found
        assert original.correlation_id == restored.correlation_id
        assert len(restored.patterns_by_kind[EnumPatternKind.FILE_ACCESS]) == 1

    def test_json_round_trip(self) -> None:
        """Test JSON serialization round-trip."""
        original = ModelPatternWarning(
            code="TEST_WARNING",
            message="Test message for JSON round-trip",
            context={"key": "value", "number": 42},
        )

        json_str = original.model_dump_json()
        restored = ModelPatternWarning.model_validate_json(json_str)

        assert original.code == restored.code
        assert original.message == restored.message
        assert original.context == restored.context


# ============================================================================
# Test: Model Equality
# ============================================================================


class TestModelEquality:
    """Tests for model equality comparisons."""

    def test_pattern_warning_equality(self) -> None:
        """Test ModelPatternWarning equality."""
        w1 = ModelPatternWarning(code="TEST", message="Test message")
        w2 = ModelPatternWarning(code="TEST", message="Test message")

        assert w1 == w2

    def test_pattern_warning_inequality(self) -> None:
        """Test ModelPatternWarning inequality."""
        w1 = ModelPatternWarning(code="TEST1", message="Test message")
        w2 = ModelPatternWarning(code="TEST2", message="Test message")

        assert w1 != w2

    def test_pattern_error_equality(self) -> None:
        """Test ModelPatternError equality."""
        e1 = ModelPatternError(code="ERR", message="Error", recoverable=True)
        e2 = ModelPatternError(code="ERR", message="Error", recoverable=True)

        assert e1 == e2

    def test_pattern_record_equality_with_same_uuid(self) -> None:
        """Test ModelPatternRecord equality with same UUID."""
        test_uuid = uuid4()
        r1 = ModelPatternRecord(
            pattern_id=test_uuid,
            kind=EnumPatternKind.ERROR,
            confidence=0.8,
            occurrences=3,
            description="Test",
        )
        r2 = ModelPatternRecord(
            pattern_id=test_uuid,
            kind=EnumPatternKind.ERROR,
            confidence=0.8,
            occurrences=3,
            description="Test",
        )

        assert r1 == r2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
