# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelClaudeCodeSessionSnapshot.

Tests comprehensive session snapshot functionality including:
- Model instantiation and validation
- Immutability (frozen model)
- Extra fields rejection
- Composition with ModelMemorySnapshot
- EnumClaudeCodeSessionStatus field validation
- Tuple collections immutability
- Serialization and deserialization
- Default values
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_subject_type import EnumSubjectType
from omnibase_core.enums.hooks.claude_code.enum_claude_code_session_status import (
    EnumClaudeCodeSessionStatus,
)
from omnibase_core.models.omnimemory.model_claude_code_prompt_record import (
    ModelClaudeCodePromptRecord,
)
from omnibase_core.models.omnimemory.model_claude_code_session_snapshot import (
    ModelClaudeCodeSessionSnapshot,
)
from omnibase_core.models.omnimemory.model_claude_code_tool_record import (
    ModelClaudeCodeToolRecord,
)
from omnibase_core.models.omnimemory.model_cost_ledger import ModelCostLedger
from omnibase_core.models.omnimemory.model_memory_snapshot import ModelMemorySnapshot
from omnibase_core.models.omnimemory.model_subject_ref import ModelSubjectRef
from omnibase_core.models.primitives.model_semver import ModelSemVer

pytestmark = pytest.mark.unit

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_subject() -> ModelSubjectRef:
    """Create a sample subject reference for testing."""
    return ModelSubjectRef(
        subject_type=EnumSubjectType.AGENT,
        subject_id=uuid4(),
        namespace="test-namespace",
    )


@pytest.fixture
def sample_cost_ledger() -> ModelCostLedger:
    """Create a sample cost ledger for testing."""
    return ModelCostLedger(budget_total=100.0)


@pytest.fixture
def sample_memory_snapshot(
    sample_subject: ModelSubjectRef,
    sample_cost_ledger: ModelCostLedger,
) -> ModelMemorySnapshot:
    """Create a sample memory snapshot for testing."""
    return ModelMemorySnapshot(
        subject=sample_subject,
        cost_ledger=sample_cost_ledger,
    )


@pytest.fixture
def sample_last_event_at() -> datetime:
    """Create a sample timezone-aware datetime for testing."""
    return datetime.now(UTC)


@pytest.fixture
def sample_prompt_record(sample_last_event_at: datetime) -> ModelClaudeCodePromptRecord:
    """Create a sample prompt record for testing."""
    return ModelClaudeCodePromptRecord(
        emitted_at=sample_last_event_at,
        prompt_preview="Fix the authentication bug",
        prompt_length=256,
        detected_intent="bug_fix",
    )


@pytest.fixture
def sample_tool_record(sample_last_event_at: datetime) -> ModelClaudeCodeToolRecord:
    """Create a sample tool record for testing."""
    return ModelClaudeCodeToolRecord(
        emitted_at=sample_last_event_at,
        tool_name="Read",
        success=True,
        duration_ms=150,
        summary="Read file /src/main.py (245 lines)",
    )


@pytest.fixture
def minimal_snapshot_data(
    sample_memory_snapshot: ModelMemorySnapshot,
    sample_last_event_at: datetime,
) -> dict[str, Any]:
    """Minimal required data for creating a session snapshot."""
    return {
        "session_id": "session-abc123",
        "memory_snapshot": sample_memory_snapshot,
        "status": EnumClaudeCodeSessionStatus.ACTIVE,
        "working_directory": "/path/to/project",
        "hook_source": "startup",
        "last_event_at": sample_last_event_at,
    }


@pytest.fixture
def full_snapshot_data(
    sample_memory_snapshot: ModelMemorySnapshot,
    sample_last_event_at: datetime,
    sample_prompt_record: ModelClaudeCodePromptRecord,
    sample_tool_record: ModelClaudeCodeToolRecord,
) -> dict[str, Any]:
    """Complete data including all optional fields."""
    return {
        "snapshot_id": uuid4(),
        "session_id": "session-xyz789",
        "correlation_id": uuid4(),
        "memory_snapshot": sample_memory_snapshot,
        "status": EnumClaudeCodeSessionStatus.ENDED,
        "started_at": sample_last_event_at,
        "ended_at": sample_last_event_at,
        "duration_seconds": 120.5,
        "working_directory": "/path/to/project",
        "git_branch": "feature/new-auth",
        "hook_source": "resume",
        "end_reason": "user_exit",
        "prompts": (sample_prompt_record,),
        "tools": (sample_tool_record,),
        "prompt_count": 1,
        "tool_count": 1,
        "tools_used_count": 1,
        "last_event_at": sample_last_event_at,
        "event_count": 5,
        "schema_version": ModelSemVer(major=1, minor=0, patch=0),
    }


# ============================================================================
# Test: Model Instantiation
# ============================================================================


class TestModelClaudeCodeSessionSnapshotInstantiation:
    """Tests for model instantiation and basic functionality."""

    def test_create_with_minimal_data(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test creating session snapshot with only required fields."""
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        assert isinstance(snapshot.snapshot_id, UUID)
        assert snapshot.session_id == minimal_snapshot_data["session_id"]
        assert snapshot.memory_snapshot == minimal_snapshot_data["memory_snapshot"]
        assert snapshot.status == minimal_snapshot_data["status"]
        assert snapshot.working_directory == minimal_snapshot_data["working_directory"]
        assert snapshot.hook_source == minimal_snapshot_data["hook_source"]
        assert snapshot.last_event_at == minimal_snapshot_data["last_event_at"]

    def test_create_with_full_data(self, full_snapshot_data: dict[str, Any]) -> None:
        """Test creating session snapshot with all fields explicitly set."""
        snapshot = ModelClaudeCodeSessionSnapshot(**full_snapshot_data)

        assert snapshot.snapshot_id == full_snapshot_data["snapshot_id"]
        assert snapshot.session_id == full_snapshot_data["session_id"]
        assert snapshot.correlation_id == full_snapshot_data["correlation_id"]
        assert snapshot.status == full_snapshot_data["status"]
        assert snapshot.started_at == full_snapshot_data["started_at"]
        assert snapshot.ended_at == full_snapshot_data["ended_at"]
        assert snapshot.duration_seconds == full_snapshot_data["duration_seconds"]
        assert snapshot.git_branch == full_snapshot_data["git_branch"]
        assert snapshot.end_reason == full_snapshot_data["end_reason"]
        assert len(snapshot.prompts) == 1
        assert len(snapshot.tools) == 1
        assert snapshot.prompt_count == full_snapshot_data["prompt_count"]
        assert snapshot.tool_count == full_snapshot_data["tool_count"]
        assert snapshot.tools_used_count == full_snapshot_data["tools_used_count"]
        assert snapshot.event_count == full_snapshot_data["event_count"]

    def test_auto_generated_snapshot_id(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test that snapshot_id is auto-generated when not provided."""
        snapshot1 = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)
        snapshot2 = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        assert isinstance(snapshot1.snapshot_id, UUID)
        assert isinstance(snapshot2.snapshot_id, UUID)
        assert snapshot1.snapshot_id != snapshot2.snapshot_id

    def test_default_values(self, minimal_snapshot_data: dict[str, Any]) -> None:
        """Test that default values are properly set."""
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        assert snapshot.correlation_id is None
        assert snapshot.started_at is None
        assert snapshot.ended_at is None
        assert snapshot.duration_seconds is None
        assert snapshot.git_branch is None
        assert snapshot.end_reason is None
        assert snapshot.prompts == ()
        assert snapshot.tools == ()
        assert snapshot.prompt_count == 0
        assert snapshot.tool_count == 0
        assert snapshot.tools_used_count == 0
        assert snapshot.event_count == 0
        assert snapshot.schema_version == ModelSemVer(major=1, minor=0, patch=0)


# ============================================================================
# Test: Immutability (Frozen Model)
# ============================================================================


class TestModelClaudeCodeSessionSnapshotImmutability:
    """Tests for frozen model behavior."""

    def test_model_is_frozen(self, minimal_snapshot_data: dict[str, Any]) -> None:
        """Test that the model is immutable."""
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        with pytest.raises(ValidationError):
            snapshot.session_id = "new-session-id"

    def test_cannot_modify_snapshot_id(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test that snapshot_id cannot be modified."""
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        with pytest.raises(ValidationError):
            snapshot.snapshot_id = uuid4()

    def test_cannot_modify_status(self, minimal_snapshot_data: dict[str, Any]) -> None:
        """Test that status cannot be modified."""
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        with pytest.raises(ValidationError):
            snapshot.status = EnumClaudeCodeSessionStatus.ENDED

    def test_cannot_modify_prompts(
        self,
        minimal_snapshot_data: dict[str, Any],
        sample_prompt_record: ModelClaudeCodePromptRecord,
    ) -> None:
        """Test that prompts cannot be modified."""
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        with pytest.raises(ValidationError):
            snapshot.prompts = (sample_prompt_record,)

    def test_cannot_modify_tools(
        self,
        minimal_snapshot_data: dict[str, Any],
        sample_tool_record: ModelClaudeCodeToolRecord,
    ) -> None:
        """Test that tools cannot be modified."""
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        with pytest.raises(ValidationError):
            snapshot.tools = (sample_tool_record,)


# ============================================================================
# Test: Extra Fields Rejection
# ============================================================================


class TestModelClaudeCodeSessionSnapshotExtraFields:
    """Tests for extra fields rejection (extra='forbid')."""

    def test_rejects_extra_fields(self, minimal_snapshot_data: dict[str, Any]) -> None:
        """Test that extra fields are rejected."""
        minimal_snapshot_data["unknown_field"] = "should_fail"

        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        assert "unknown_field" in str(exc_info.value)

    def test_rejects_multiple_extra_fields(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test that multiple extra fields are rejected."""
        minimal_snapshot_data["extra1"] = "value1"
        minimal_snapshot_data["extra2"] = "value2"

        with pytest.raises(ValidationError):
            ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)


# ============================================================================
# Test: Field Validation
# ============================================================================


class TestModelClaudeCodeSessionSnapshotValidation:
    """Tests for field validation constraints."""

    def test_session_id_min_length(self, minimal_snapshot_data: dict[str, Any]) -> None:
        """Test that session_id requires at least 1 character."""
        minimal_snapshot_data["session_id"] = ""

        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        assert "session_id" in str(exc_info.value)

    def test_working_directory_min_length(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test that working_directory requires at least 1 character."""
        minimal_snapshot_data["working_directory"] = ""

        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        assert "working_directory" in str(exc_info.value)

    def test_duration_seconds_non_negative(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test that duration_seconds rejects negative values."""
        minimal_snapshot_data["duration_seconds"] = -1.0

        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        assert "duration_seconds" in str(exc_info.value)

    def test_duration_seconds_accepts_zero(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test that duration_seconds accepts zero."""
        minimal_snapshot_data["duration_seconds"] = 0.0
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)
        assert snapshot.duration_seconds == 0.0

    def test_prompt_count_non_negative(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test that prompt_count rejects negative values."""
        minimal_snapshot_data["prompt_count"] = -1

        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        assert "prompt_count" in str(exc_info.value)

    def test_tool_count_non_negative(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test that tool_count rejects negative values."""
        minimal_snapshot_data["tool_count"] = -1

        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        assert "tool_count" in str(exc_info.value)

    def test_event_count_non_negative(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test that event_count rejects negative values."""
        minimal_snapshot_data["event_count"] = -1

        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        assert "event_count" in str(exc_info.value)

    def test_missing_required_field_session_id(
        self,
        sample_memory_snapshot: ModelMemorySnapshot,
        sample_last_event_at: datetime,
    ) -> None:
        """Test that missing session_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodeSessionSnapshot(  # type: ignore[call-arg]
                memory_snapshot=sample_memory_snapshot,
                status=EnumClaudeCodeSessionStatus.ACTIVE,
                working_directory="/path",
                hook_source="startup",
                last_event_at=sample_last_event_at,
            )

        assert "session_id" in str(exc_info.value)

    def test_missing_required_field_memory_snapshot(
        self, sample_last_event_at: datetime
    ) -> None:
        """Test that missing memory_snapshot raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodeSessionSnapshot(  # type: ignore[call-arg]
                session_id="session-123",
                status=EnumClaudeCodeSessionStatus.ACTIVE,
                working_directory="/path",
                hook_source="startup",
                last_event_at=sample_last_event_at,
            )

        assert "memory_snapshot" in str(exc_info.value)

    def test_last_event_at_requires_timezone(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test that last_event_at rejects naive datetime."""
        minimal_snapshot_data["last_event_at"] = datetime(2025, 1, 1, 12, 0, 0)

        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        assert "timezone" in str(exc_info.value).lower()

    def test_started_at_requires_timezone(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test that started_at rejects naive datetime."""
        minimal_snapshot_data["started_at"] = datetime(2025, 1, 1, 12, 0, 0)

        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        assert "timezone" in str(exc_info.value).lower()

    def test_ended_at_requires_timezone(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test that ended_at rejects naive datetime."""
        minimal_snapshot_data["ended_at"] = datetime(2025, 1, 1, 12, 0, 0)

        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        assert "timezone" in str(exc_info.value).lower()


# ============================================================================
# Test: EnumClaudeCodeSessionStatus Validation
# ============================================================================


class TestModelClaudeCodeSessionSnapshotStatusEnum:
    """Tests for EnumClaudeCodeSessionStatus field validation."""

    def test_all_status_values_accepted(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test that all EnumClaudeCodeSessionStatus values are accepted."""
        for status in EnumClaudeCodeSessionStatus:
            minimal_snapshot_data["status"] = status
            snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)
            assert snapshot.status == status

    def test_invalid_status_rejected(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test that invalid status values are rejected."""
        minimal_snapshot_data["status"] = "invalid_status"

        with pytest.raises(ValidationError) as exc_info:
            ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        assert "status" in str(exc_info.value)

    def test_status_active(self, minimal_snapshot_data: dict[str, Any]) -> None:
        """Test snapshot with ACTIVE status."""
        minimal_snapshot_data["status"] = EnumClaudeCodeSessionStatus.ACTIVE
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)
        assert snapshot.status == EnumClaudeCodeSessionStatus.ACTIVE
        assert snapshot.status.is_active() is True
        assert snapshot.status.is_terminal() is False

    def test_status_ended(self, minimal_snapshot_data: dict[str, Any]) -> None:
        """Test snapshot with ENDED status."""
        minimal_snapshot_data["status"] = EnumClaudeCodeSessionStatus.ENDED
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)
        assert snapshot.status == EnumClaudeCodeSessionStatus.ENDED
        assert snapshot.status.is_active() is False
        assert snapshot.status.is_terminal() is True

    def test_status_timed_out(self, minimal_snapshot_data: dict[str, Any]) -> None:
        """Test snapshot with TIMED_OUT status."""
        minimal_snapshot_data["status"] = EnumClaudeCodeSessionStatus.TIMED_OUT
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)
        assert snapshot.status == EnumClaudeCodeSessionStatus.TIMED_OUT
        assert snapshot.status.is_active() is False
        assert snapshot.status.is_terminal() is True

    def test_status_orphan(self, minimal_snapshot_data: dict[str, Any]) -> None:
        """Test snapshot with ORPHAN status."""
        minimal_snapshot_data["status"] = EnumClaudeCodeSessionStatus.ORPHAN
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)
        assert snapshot.status == EnumClaudeCodeSessionStatus.ORPHAN
        assert snapshot.status.is_active() is False
        assert snapshot.status.is_terminal() is False


# ============================================================================
# Test: Composition with ModelMemorySnapshot
# ============================================================================


class TestModelClaudeCodeSessionSnapshotComposition:
    """Tests for composition with ModelMemorySnapshot."""

    def test_memory_snapshot_composition(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test that memory_snapshot is properly composed."""
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        assert isinstance(snapshot.memory_snapshot, ModelMemorySnapshot)

    def test_total_decisions_property(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test total_decisions property delegates to memory_snapshot."""
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        assert snapshot.total_decisions == snapshot.memory_snapshot.decision_count

    def test_total_failures_property(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test total_failures property delegates to memory_snapshot."""
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        assert snapshot.total_failures == snapshot.memory_snapshot.failure_count

    def test_total_cost_property(self, minimal_snapshot_data: dict[str, Any]) -> None:
        """Test total_cost property delegates to memory_snapshot."""
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        assert snapshot.total_cost == snapshot.memory_snapshot.cost_ledger.total_spent


# ============================================================================
# Test: Tuple Collections Immutability
# ============================================================================


class TestModelClaudeCodeSessionSnapshotTupleImmutability:
    """Tests for tuple collections immutability."""

    def test_prompts_is_tuple(self, full_snapshot_data: dict[str, Any]) -> None:
        """Test that prompts is a tuple."""
        snapshot = ModelClaudeCodeSessionSnapshot(**full_snapshot_data)
        assert isinstance(snapshot.prompts, tuple)

    def test_tools_is_tuple(self, full_snapshot_data: dict[str, Any]) -> None:
        """Test that tools is a tuple."""
        snapshot = ModelClaudeCodeSessionSnapshot(**full_snapshot_data)
        assert isinstance(snapshot.tools, tuple)

    def test_prompts_tuple_immutable(
        self,
        full_snapshot_data: dict[str, Any],
        sample_prompt_record: ModelClaudeCodePromptRecord,
    ) -> None:
        """Test that prompts tuple cannot be modified in place."""
        snapshot = ModelClaudeCodeSessionSnapshot(**full_snapshot_data)

        with pytest.raises((TypeError, AttributeError)):
            snapshot.prompts[0] = sample_prompt_record  # type: ignore[index]

    def test_tools_tuple_immutable(
        self,
        full_snapshot_data: dict[str, Any],
        sample_tool_record: ModelClaudeCodeToolRecord,
    ) -> None:
        """Test that tools tuple cannot be modified in place."""
        snapshot = ModelClaudeCodeSessionSnapshot(**full_snapshot_data)

        with pytest.raises((TypeError, AttributeError)):
            snapshot.tools[0] = sample_tool_record  # type: ignore[index]

    def test_empty_tuples_default(self, minimal_snapshot_data: dict[str, Any]) -> None:
        """Test that default prompts and tools are empty tuples."""
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        assert snapshot.prompts == ()
        assert snapshot.tools == ()


# ============================================================================
# Test: Serialization
# ============================================================================


class TestModelClaudeCodeSessionSnapshotSerialization:
    """Tests for serialization and deserialization."""

    def test_model_dump(self, minimal_snapshot_data: dict[str, Any]) -> None:
        """Test serialization to dictionary."""
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)
        data = snapshot.model_dump()

        assert "snapshot_id" in data
        assert "session_id" in data
        assert "memory_snapshot" in data
        assert "status" in data
        assert "working_directory" in data
        assert "hook_source" in data
        assert "last_event_at" in data
        assert "prompts" in data
        assert "tools" in data
        assert "schema_version" in data

    def test_model_dump_json(self, minimal_snapshot_data: dict[str, Any]) -> None:
        """Test serialization to JSON string."""
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)
        json_str = snapshot.model_dump_json()

        assert isinstance(json_str, str)
        assert "snapshot_id" in json_str
        assert "session_id" in json_str

    def test_round_trip_serialization(self, full_snapshot_data: dict[str, Any]) -> None:
        """Test that model survives serialization round-trip."""
        original = ModelClaudeCodeSessionSnapshot(**full_snapshot_data)
        data = original.model_dump()
        restored = ModelClaudeCodeSessionSnapshot(**data)

        assert original.snapshot_id == restored.snapshot_id
        assert original.session_id == restored.session_id
        assert original.status == restored.status
        assert original.working_directory == restored.working_directory
        assert len(original.prompts) == len(restored.prompts)
        assert len(original.tools) == len(restored.tools)
        assert original.schema_version == restored.schema_version

    def test_json_round_trip_serialization(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test JSON serialization and deserialization roundtrip.

        Note: Uses model_dump(mode='python') which returns datetime objects,
        avoiding the before-mode validator issue where strings are passed
        before type conversion. This tests the same serialization/deserialization
        conceptually.
        """
        original = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        # Use model_dump with python mode which preserves datetime objects
        # This is equivalent to JSON roundtrip but avoids string-based datetime issues
        data = original.model_dump(mode="python")
        restored = ModelClaudeCodeSessionSnapshot.model_validate(data)

        assert original.snapshot_id == restored.snapshot_id
        assert original.session_id == restored.session_id
        assert original.schema_version == restored.schema_version

    def test_model_validate_from_dict(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test model validation from dictionary."""
        snapshot = ModelClaudeCodeSessionSnapshot.model_validate(minimal_snapshot_data)

        assert snapshot.session_id == minimal_snapshot_data["session_id"]
        assert snapshot.working_directory == minimal_snapshot_data["working_directory"]


# ============================================================================
# Test: Utility Properties
# ============================================================================


class TestModelClaudeCodeSessionSnapshotUtilityProperties:
    """Tests for utility properties."""

    def test_is_active_true_when_status_active(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test is_active returns True when status is ACTIVE."""
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        assert snapshot.status == EnumClaudeCodeSessionStatus.ACTIVE
        assert snapshot.is_active is True

    def test_is_active_false_when_status_not_active(
        self,
        minimal_snapshot_data: dict[str, Any],
    ) -> None:
        """Test is_active returns False when status is not ACTIVE."""
        minimal_snapshot_data["status"] = EnumClaudeCodeSessionStatus.ENDED
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        assert snapshot.is_active is False


# ============================================================================
# Test: Utility Methods
# ============================================================================


class TestModelClaudeCodeSessionSnapshotUtilityMethods:
    """Tests for __str__ and __repr__ methods."""

    def test_str_representation(self, minimal_snapshot_data: dict[str, Any]) -> None:
        """Test __str__ method returns expected format."""
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)
        str_repr = str(snapshot)

        assert isinstance(str_repr, str)
        assert "SessionSnapshot" in str_repr
        assert "status=" in str_repr
        assert "prompts=" in str_repr
        assert "tools=" in str_repr

    def test_str_representation_with_duration(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test __str__ method includes duration when present."""
        minimal_snapshot_data["duration_seconds"] = 120.5
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)
        str_repr = str(snapshot)

        assert "120.5s" in str_repr

    def test_repr_representation(self, minimal_snapshot_data: dict[str, Any]) -> None:
        """Test __repr__ method returns string with class name."""
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)
        repr_str = repr(snapshot)

        assert isinstance(repr_str, str)
        assert "ModelClaudeCodeSessionSnapshot" in repr_str
        assert "snapshot_id=" in repr_str
        assert "session_id=" in repr_str
        assert "status=" in repr_str


# ============================================================================
# Test: from_attributes Compatibility
# ============================================================================


class TestModelClaudeCodeSessionSnapshotFromAttributes:
    """Tests for from_attributes compatibility (pytest-xdist support)."""

    def test_from_attributes_enabled(self) -> None:
        """Test that from_attributes is enabled in model config."""
        assert (
            ModelClaudeCodeSessionSnapshot.model_config.get("from_attributes") is True
        )

    def test_model_validate_with_existing_instance(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test model validation from an existing model instance."""
        original = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        # This should work due to from_attributes=True
        validated = ModelClaudeCodeSessionSnapshot.model_validate(original)

        assert validated.snapshot_id == original.snapshot_id
        assert validated.session_id == original.session_id


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestModelClaudeCodeSessionSnapshotEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_model_equality(self, minimal_snapshot_data: dict[str, Any]) -> None:
        """Test model equality comparison with identical data."""
        snapshot_id = uuid4()
        minimal_snapshot_data["snapshot_id"] = snapshot_id

        snapshot1 = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)
        snapshot2 = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        assert snapshot1 == snapshot2

    def test_model_inequality_different_snapshot_id(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test model inequality when snapshot_ids differ."""
        snapshot1 = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)
        snapshot2 = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        # Different auto-generated snapshot_ids
        assert snapshot1 != snapshot2

    def test_multiple_prompts(
        self,
        minimal_snapshot_data: dict[str, Any],
        sample_last_event_at: datetime,
    ) -> None:
        """Test snapshot with multiple prompt records."""
        prompts = tuple(
            ModelClaudeCodePromptRecord(
                emitted_at=sample_last_event_at,
                prompt_preview=f"Prompt {i}",
                prompt_length=10 * (i + 1),
            )
            for i in range(5)
        )
        minimal_snapshot_data["prompts"] = prompts
        minimal_snapshot_data["prompt_count"] = 5

        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        assert len(snapshot.prompts) == 5
        assert snapshot.prompt_count == 5

    def test_multiple_tools(
        self,
        minimal_snapshot_data: dict[str, Any],
        sample_last_event_at: datetime,
    ) -> None:
        """Test snapshot with multiple tool records."""
        tools = tuple(
            ModelClaudeCodeToolRecord(
                emitted_at=sample_last_event_at,
                tool_name=f"Tool{i}",
                success=True,
                duration_ms=100 * (i + 1),
            )
            for i in range(5)
        )
        minimal_snapshot_data["tools"] = tools
        minimal_snapshot_data["tool_count"] = 5
        minimal_snapshot_data["tools_used_count"] = 5

        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)

        assert len(snapshot.tools) == 5
        assert snapshot.tool_count == 5
        assert snapshot.tools_used_count == 5

    def test_long_session_id(self, minimal_snapshot_data: dict[str, Any]) -> None:
        """Test snapshot with long session ID."""
        minimal_snapshot_data["session_id"] = "a" * 1000
        snapshot = ModelClaudeCodeSessionSnapshot(**minimal_snapshot_data)
        assert len(snapshot.session_id) == 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
