# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ModelMemorySnapshot.

Tests comprehensive snapshot functionality including:
- Model instantiation and validation
- Immutability (frozen model)
- with_decision(), with_failure(), with_cost_entry() immutable updates
- compute_content_hash() inclusion/exclusion rules
- Content hash stability and changes
- Parent snapshot lineage tracking
- Serialization and deserialization
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from omnibase_core.enums.enum_decision_type import EnumDecisionType
from omnibase_core.enums.enum_failure_type import EnumFailureType
from omnibase_core.enums.enum_subject_type import EnumSubjectType
from omnibase_core.models.omnimemory.model_cost_entry import ModelCostEntry
from omnibase_core.models.omnimemory.model_cost_ledger import ModelCostLedger
from omnibase_core.models.omnimemory.model_decision_record import ModelDecisionRecord
from omnibase_core.models.omnimemory.model_failure_record import ModelFailureRecord
from omnibase_core.models.omnimemory.model_memory_diff import ModelMemoryDiff
from omnibase_core.models.omnimemory.model_memory_snapshot import ModelMemorySnapshot
from omnibase_core.models.omnimemory.model_subject_ref import ModelSubjectRef

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
def sample_decision() -> ModelDecisionRecord:
    """Create a sample decision record for testing."""
    return ModelDecisionRecord(
        decision_type=EnumDecisionType.MODEL_SELECTION,
        timestamp=datetime.now(UTC),
        options_considered=("gpt-4", "claude-3-opus", "llama-2-70b"),
        chosen_option="gpt-4",
        confidence=0.85,
        input_hash="abc123",
    )


@pytest.fixture
def sample_failure() -> ModelFailureRecord:
    """Create a sample failure record for testing."""
    return ModelFailureRecord(
        timestamp=datetime.now(UTC),
        failure_type=EnumFailureType.TIMEOUT,
        step_context="code_generation",
        error_code="TIMEOUT_001",
        error_message="Operation exceeded 30s timeout",
        model_used="gpt-4",
        retry_attempt=0,
    )


@pytest.fixture
def sample_cost_entry() -> ModelCostEntry:
    """Create a sample cost entry for testing."""
    return ModelCostEntry(
        timestamp=datetime.now(UTC),
        operation="chat_completion",
        model_used="gpt-4",
        tokens_in=100,
        tokens_out=50,
        cost=0.0045,
        cumulative_total=0.0045,
    )


@pytest.fixture
def minimal_snapshot_data(
    sample_subject: ModelSubjectRef,
    sample_cost_ledger: ModelCostLedger,
) -> dict[str, Any]:
    """Minimal required data for creating a snapshot."""
    return {
        "subject": sample_subject,
        "cost_ledger": sample_cost_ledger,
    }


@pytest.fixture
def full_snapshot_data(
    sample_subject: ModelSubjectRef,
    sample_cost_ledger: ModelCostLedger,
    sample_decision: ModelDecisionRecord,
    sample_failure: ModelFailureRecord,
) -> dict[str, Any]:
    """Complete data including all optional fields."""
    return {
        "snapshot_id": uuid4(),
        "version": 2,
        "parent_snapshot_id": uuid4(),
        "corpus_id": uuid4(),
        "subject": sample_subject,
        "decisions": (sample_decision,),
        "failures": (sample_failure,),
        "cost_ledger": sample_cost_ledger,
        "execution_annotations": {"step": "validation", "attempt": 1},
        "schema_version": "1.0.0",
        "content_hash": "",
        "created_at": datetime.now(UTC),
        "tags": ("production", "critical"),
    }


# ============================================================================
# Test: Model Instantiation
# ============================================================================


class TestModelMemorySnapshotInstantiation:
    """Tests for model instantiation and basic functionality."""

    def test_create_with_minimal_data(self, minimal_snapshot_data: dict) -> None:
        """Test creating snapshot with only required fields."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)

        assert isinstance(snapshot.snapshot_id, UUID)
        assert snapshot.version == 1
        assert snapshot.subject == minimal_snapshot_data["subject"]
        assert snapshot.cost_ledger == minimal_snapshot_data["cost_ledger"]

    def test_create_with_full_data(self, full_snapshot_data: dict) -> None:
        """Test creating snapshot with all fields explicitly set."""
        snapshot = ModelMemorySnapshot(**full_snapshot_data)

        assert snapshot.snapshot_id == full_snapshot_data["snapshot_id"]
        assert snapshot.version == 2
        assert snapshot.parent_snapshot_id == full_snapshot_data["parent_snapshot_id"]
        assert snapshot.corpus_id == full_snapshot_data["corpus_id"]
        assert len(snapshot.decisions) == 1
        assert len(snapshot.failures) == 1
        assert snapshot.tags == ("production", "critical")

    def test_auto_generated_snapshot_id(self, minimal_snapshot_data: dict) -> None:
        """Test that snapshot_id is auto-generated when not provided."""
        snapshot1 = ModelMemorySnapshot(**minimal_snapshot_data)
        snapshot2 = ModelMemorySnapshot(**minimal_snapshot_data)

        assert isinstance(snapshot1.snapshot_id, UUID)
        assert isinstance(snapshot2.snapshot_id, UUID)
        assert snapshot1.snapshot_id != snapshot2.snapshot_id  # Each gets unique ID

    def test_default_values(self, minimal_snapshot_data: dict) -> None:
        """Test that default values are properly set."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)

        assert snapshot.version == 1
        assert snapshot.parent_snapshot_id is None
        assert snapshot.corpus_id is None
        assert snapshot.decisions == ()
        assert snapshot.failures == ()
        assert snapshot.execution_annotations == {}
        assert snapshot.schema_version == "1.0.0"
        assert snapshot.tags == ()

    def test_created_at_auto_generated(self, minimal_snapshot_data: dict) -> None:
        """Test that created_at is auto-generated with timezone."""
        before = datetime.now(UTC)
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        after = datetime.now(UTC)

        assert snapshot.created_at is not None
        assert snapshot.created_at.tzinfo is not None
        assert before <= snapshot.created_at <= after


# ============================================================================
# Test: Immutability (Frozen Model)
# ============================================================================


class TestModelMemorySnapshotImmutability:
    """Tests for frozen model behavior."""

    def test_model_is_frozen(self, minimal_snapshot_data: dict) -> None:
        """Test that the model is immutable."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)

        with pytest.raises(ValidationError):
            snapshot.version = 999

    def test_cannot_modify_snapshot_id(self, minimal_snapshot_data: dict) -> None:
        """Test that snapshot_id cannot be modified."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)

        with pytest.raises(ValidationError):
            snapshot.snapshot_id = uuid4()

    def test_cannot_modify_decisions(
        self, minimal_snapshot_data: dict, sample_decision: ModelDecisionRecord
    ) -> None:
        """Test that decisions cannot be modified."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)

        with pytest.raises(ValidationError):
            snapshot.decisions = (sample_decision,)

    def test_cannot_modify_failures(
        self, minimal_snapshot_data: dict, sample_failure: ModelFailureRecord
    ) -> None:
        """Test that failures cannot be modified."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)

        with pytest.raises(ValidationError):
            snapshot.failures = (sample_failure,)

    def test_cannot_modify_cost_ledger(
        self, minimal_snapshot_data: dict, sample_cost_ledger: ModelCostLedger
    ) -> None:
        """Test that cost_ledger cannot be modified."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)

        with pytest.raises(ValidationError):
            snapshot.cost_ledger = sample_cost_ledger

    def test_cannot_modify_tags(self, minimal_snapshot_data: dict) -> None:
        """Test that tags cannot be modified."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)

        with pytest.raises(ValidationError):
            snapshot.tags = ("new", "tags")


# ============================================================================
# Test: Field Validation
# ============================================================================


class TestModelMemorySnapshotValidation:
    """Tests for field validation constraints."""

    def test_version_must_be_positive(self, minimal_snapshot_data: dict) -> None:
        """Test that version rejects zero and negative values."""
        minimal_snapshot_data["version"] = 0

        with pytest.raises(ValidationError) as exc_info:
            ModelMemorySnapshot(**minimal_snapshot_data)

        assert "version" in str(exc_info.value)

    def test_version_accepts_positive_values(self, minimal_snapshot_data: dict) -> None:
        """Test that version accepts positive values."""
        for version in [1, 2, 100, 9999]:
            minimal_snapshot_data["version"] = version
            snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
            assert snapshot.version == version

    def test_missing_required_field_subject(
        self, sample_cost_ledger: ModelCostLedger
    ) -> None:
        """Test that missing subject raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMemorySnapshot(cost_ledger=sample_cost_ledger)

        assert "subject" in str(exc_info.value)

    def test_missing_required_field_cost_ledger(
        self, sample_subject: ModelSubjectRef
    ) -> None:
        """Test that missing cost_ledger raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelMemorySnapshot(subject=sample_subject)

        assert "cost_ledger" in str(exc_info.value)


# ============================================================================
# Test: with_decision() Method
# ============================================================================


class TestModelMemorySnapshotWithDecision:
    """Tests for with_decision() immutable update method."""

    def test_with_decision_returns_new_instance(
        self, minimal_snapshot_data: dict, sample_decision: ModelDecisionRecord
    ) -> None:
        """Test that with_decision returns a new snapshot instance."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        new_snapshot = snapshot.with_decision(sample_decision)

        assert new_snapshot is not snapshot
        assert isinstance(new_snapshot, ModelMemorySnapshot)

    def test_with_decision_preserves_original(
        self, minimal_snapshot_data: dict, sample_decision: ModelDecisionRecord
    ) -> None:
        """Test that with_decision does not modify the original snapshot."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        original_decisions = snapshot.decisions

        _ = snapshot.with_decision(sample_decision)

        assert snapshot.decisions == original_decisions

    def test_with_decision_appends_decision(
        self, minimal_snapshot_data: dict, sample_decision: ModelDecisionRecord
    ) -> None:
        """Test that with_decision appends the decision to the tuple."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        new_snapshot = snapshot.with_decision(sample_decision)

        assert len(new_snapshot.decisions) == 1
        assert new_snapshot.decisions[-1] == sample_decision

    def test_multiple_decisions_accumulate(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test that multiple decisions accumulate correctly."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)

        for i in range(3):
            decision = ModelDecisionRecord(
                decision_type=EnumDecisionType.MODEL_SELECTION,
                timestamp=datetime.now(UTC),
                options_considered=(f"option{i}",),
                chosen_option=f"option{i}",
                confidence=0.9 - i * 0.1,
                input_hash=f"hash{i}",
            )
            snapshot = snapshot.with_decision(decision)

        assert len(snapshot.decisions) == 3
        # Verify unique decision_ids
        decision_ids = [d.decision_id for d in snapshot.decisions]
        assert len(set(decision_ids)) == 3

    def test_with_decision_preserves_snapshot_id(
        self, minimal_snapshot_data: dict, sample_decision: ModelDecisionRecord
    ) -> None:
        """Test that with_decision preserves the snapshot_id."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        new_snapshot = snapshot.with_decision(sample_decision)

        assert new_snapshot.snapshot_id == snapshot.snapshot_id

    def test_with_decision_preserves_other_fields(
        self, full_snapshot_data: dict, sample_decision: ModelDecisionRecord
    ) -> None:
        """Test that with_decision preserves other fields."""
        snapshot = ModelMemorySnapshot(**full_snapshot_data)
        new_snapshot = snapshot.with_decision(sample_decision)

        assert new_snapshot.version == snapshot.version
        assert new_snapshot.subject == snapshot.subject
        assert new_snapshot.failures == snapshot.failures
        assert new_snapshot.tags == snapshot.tags


# ============================================================================
# Test: with_failure() Method
# ============================================================================


class TestModelMemorySnapshotWithFailure:
    """Tests for with_failure() immutable update method."""

    def test_with_failure_returns_new_instance(
        self, minimal_snapshot_data: dict, sample_failure: ModelFailureRecord
    ) -> None:
        """Test that with_failure returns a new snapshot instance."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        new_snapshot = snapshot.with_failure(sample_failure)

        assert new_snapshot is not snapshot
        assert isinstance(new_snapshot, ModelMemorySnapshot)

    def test_with_failure_preserves_original(
        self, minimal_snapshot_data: dict, sample_failure: ModelFailureRecord
    ) -> None:
        """Test that with_failure does not modify the original snapshot."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        original_failures = snapshot.failures

        _ = snapshot.with_failure(sample_failure)

        assert snapshot.failures == original_failures

    def test_with_failure_appends_failure(
        self, minimal_snapshot_data: dict, sample_failure: ModelFailureRecord
    ) -> None:
        """Test that with_failure appends the failure to the tuple."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        new_snapshot = snapshot.with_failure(sample_failure)

        assert len(new_snapshot.failures) == 1
        assert new_snapshot.failures[-1] == sample_failure

    def test_multiple_failures_accumulate(
        self, minimal_snapshot_data: dict[str, Any]
    ) -> None:
        """Test that multiple failures accumulate correctly."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)

        for i in range(3):
            failure = ModelFailureRecord(
                timestamp=datetime.now(UTC),
                failure_type=EnumFailureType.TIMEOUT,
                step_context=f"step_{i}",
                error_code=f"ERR_{i:03d}",
                error_message=f"Error message {i}",
            )
            snapshot = snapshot.with_failure(failure)

        assert len(snapshot.failures) == 3
        # Verify unique failure_ids
        failure_ids = [f.failure_id for f in snapshot.failures]
        assert len(set(failure_ids)) == 3

    def test_with_failure_preserves_snapshot_id(
        self, minimal_snapshot_data: dict, sample_failure: ModelFailureRecord
    ) -> None:
        """Test that with_failure preserves the snapshot_id."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        new_snapshot = snapshot.with_failure(sample_failure)

        assert new_snapshot.snapshot_id == snapshot.snapshot_id


# ============================================================================
# Test: with_cost_entry() Method
# ============================================================================


class TestModelMemorySnapshotWithCostEntry:
    """Tests for with_cost_entry() immutable update method."""

    def test_with_cost_entry_returns_new_instance(
        self, minimal_snapshot_data: dict, sample_cost_entry: ModelCostEntry
    ) -> None:
        """Test that with_cost_entry returns a new snapshot instance."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        new_snapshot = snapshot.with_cost_entry(sample_cost_entry)

        assert new_snapshot is not snapshot
        assert isinstance(new_snapshot, ModelMemorySnapshot)

    def test_with_cost_entry_preserves_original(
        self, minimal_snapshot_data: dict, sample_cost_entry: ModelCostEntry
    ) -> None:
        """Test that with_cost_entry does not modify the original snapshot."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        original_spent = snapshot.cost_ledger.total_spent

        _ = snapshot.with_cost_entry(sample_cost_entry)

        assert snapshot.cost_ledger.total_spent == original_spent

    def test_with_cost_entry_updates_ledger(
        self, minimal_snapshot_data: dict, sample_cost_entry: ModelCostEntry
    ) -> None:
        """Test that with_cost_entry updates the cost ledger."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        new_snapshot = snapshot.with_cost_entry(sample_cost_entry)

        expected_spent = snapshot.cost_ledger.total_spent + sample_cost_entry.cost
        assert new_snapshot.cost_ledger.total_spent == expected_spent

    def test_with_cost_entry_preserves_snapshot_id(
        self, minimal_snapshot_data: dict, sample_cost_entry: ModelCostEntry
    ) -> None:
        """Test that with_cost_entry preserves the snapshot_id."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        new_snapshot = snapshot.with_cost_entry(sample_cost_entry)

        assert new_snapshot.snapshot_id == snapshot.snapshot_id


# ============================================================================
# Test: compute_content_hash() Method
# ============================================================================


class TestModelMemorySnapshotContentHash:
    """Tests for compute_content_hash() and content_hash behavior."""

    def test_compute_content_hash_returns_string(
        self, minimal_snapshot_data: dict
    ) -> None:
        """Test that compute_content_hash returns a hex string."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        content_hash = snapshot.compute_content_hash()

        assert isinstance(content_hash, str)
        assert len(content_hash) == 64  # SHA-256 hex digest is 64 chars

    def test_content_hash_is_deterministic(self, minimal_snapshot_data: dict) -> None:
        """Test that same content produces same hash."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)

        hash1 = snapshot.compute_content_hash()
        hash2 = snapshot.compute_content_hash()

        assert hash1 == hash2

    def test_content_hash_changes_with_decisions(
        self, minimal_snapshot_data: dict, sample_decision: ModelDecisionRecord
    ) -> None:
        """Test that content_hash changes when decisions are added."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        original_hash = snapshot.compute_content_hash()

        new_snapshot = snapshot.with_decision(sample_decision)

        assert new_snapshot.content_hash != original_hash
        assert new_snapshot.content_hash == new_snapshot.compute_content_hash()

    def test_content_hash_changes_with_failures(
        self, minimal_snapshot_data: dict, sample_failure: ModelFailureRecord
    ) -> None:
        """Test that content_hash changes when failures are added."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        original_hash = snapshot.compute_content_hash()

        new_snapshot = snapshot.with_failure(sample_failure)

        assert new_snapshot.content_hash != original_hash

    def test_content_hash_changes_with_cost_entry(
        self, minimal_snapshot_data: dict, sample_cost_entry: ModelCostEntry
    ) -> None:
        """Test that content_hash changes when cost entries are added."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        original_hash = snapshot.compute_content_hash()

        new_snapshot = snapshot.with_cost_entry(sample_cost_entry)

        assert new_snapshot.content_hash != original_hash

    def test_content_hash_changes_with_execution_annotations(
        self,
        sample_subject: ModelSubjectRef,
        sample_cost_ledger: ModelCostLedger,
    ) -> None:
        """Test that content_hash changes when execution_annotations change."""
        snapshot1 = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            execution_annotations={"key": "value1"},
        )
        snapshot2 = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            execution_annotations={"key": "value2"},
        )

        assert snapshot1.compute_content_hash() != snapshot2.compute_content_hash()

    def test_content_hash_changes_with_schema_version(
        self,
        sample_subject: ModelSubjectRef,
        sample_cost_ledger: ModelCostLedger,
    ) -> None:
        """Test that content_hash changes when schema_version changes."""
        snapshot1 = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            schema_version="1.0.0",
        )
        snapshot2 = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            schema_version="2.0.0",
        )

        assert snapshot1.compute_content_hash() != snapshot2.compute_content_hash()

    def test_content_hash_excludes_snapshot_id(
        self, sample_subject: ModelSubjectRef, sample_cost_ledger: ModelCostLedger
    ) -> None:
        """Test that content_hash is NOT affected by snapshot_id."""
        snapshot1 = ModelMemorySnapshot(
            snapshot_id=uuid4(),
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
        )
        snapshot2 = ModelMemorySnapshot(
            snapshot_id=uuid4(),
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
        )

        assert snapshot1.compute_content_hash() == snapshot2.compute_content_hash()

    def test_content_hash_excludes_parent_snapshot_id(
        self, sample_subject: ModelSubjectRef, sample_cost_ledger: ModelCostLedger
    ) -> None:
        """Test that content_hash is NOT affected by parent_snapshot_id."""
        snapshot1 = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            parent_snapshot_id=uuid4(),
        )
        snapshot2 = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            parent_snapshot_id=uuid4(),
        )

        assert snapshot1.compute_content_hash() == snapshot2.compute_content_hash()

    def test_content_hash_excludes_corpus_id(
        self, sample_subject: ModelSubjectRef, sample_cost_ledger: ModelCostLedger
    ) -> None:
        """Test that content_hash is NOT affected by corpus_id."""
        snapshot1 = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            corpus_id=uuid4(),
        )
        snapshot2 = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            corpus_id=uuid4(),
        )

        assert snapshot1.compute_content_hash() == snapshot2.compute_content_hash()

    def test_content_hash_excludes_created_at(
        self, sample_subject: ModelSubjectRef, sample_cost_ledger: ModelCostLedger
    ) -> None:
        """Test that content_hash is NOT affected by created_at."""
        snapshot1 = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
        )
        snapshot2 = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            created_at=datetime(2025, 12, 31, tzinfo=UTC),
        )

        assert snapshot1.compute_content_hash() == snapshot2.compute_content_hash()

    def test_content_hash_excludes_tags(
        self, sample_subject: ModelSubjectRef, sample_cost_ledger: ModelCostLedger
    ) -> None:
        """Test that content_hash is NOT affected by tags."""
        snapshot1 = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            tags=("tag1", "tag2"),
        )
        snapshot2 = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            tags=("tag3", "tag4"),
        )

        assert snapshot1.compute_content_hash() == snapshot2.compute_content_hash()

    def test_content_hash_excludes_subject(
        self, sample_cost_ledger: ModelCostLedger
    ) -> None:
        """Test that content_hash is NOT affected by subject."""
        subject1 = ModelSubjectRef(
            subject_type=EnumSubjectType.AGENT,
            subject_id=uuid4(),
        )
        subject2 = ModelSubjectRef(
            subject_type=EnumSubjectType.USER,
            subject_id=uuid4(),
        )
        snapshot1 = ModelMemorySnapshot(
            subject=subject1,
            cost_ledger=sample_cost_ledger,
        )
        snapshot2 = ModelMemorySnapshot(
            subject=subject2,
            cost_ledger=sample_cost_ledger,
        )

        assert snapshot1.compute_content_hash() == snapshot2.compute_content_hash()

    def test_content_hash_excludes_version(
        self, sample_subject: ModelSubjectRef, sample_cost_ledger: ModelCostLedger
    ) -> None:
        """Test that content_hash is NOT affected by version."""
        snapshot1 = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            version=1,
        )
        snapshot2 = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            version=99,
        )

        assert snapshot1.compute_content_hash() == snapshot2.compute_content_hash()


# ============================================================================
# Test: Parent Snapshot Lineage
# ============================================================================


class TestModelMemorySnapshotLineage:
    """Tests for parent snapshot lineage tracking."""

    def test_has_parent_false_when_no_parent(self, minimal_snapshot_data: dict) -> None:
        """Test has_parent returns False when parent_snapshot_id is None."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)

        assert snapshot.has_parent is False

    def test_has_parent_true_when_parent_set(self, minimal_snapshot_data: dict) -> None:
        """Test has_parent returns True when parent_snapshot_id is set."""
        minimal_snapshot_data["parent_snapshot_id"] = uuid4()
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)

        assert snapshot.has_parent is True

    def test_parent_snapshot_id_preserved(self, minimal_snapshot_data: dict) -> None:
        """Test that parent_snapshot_id is correctly stored."""
        parent_id = uuid4()
        minimal_snapshot_data["parent_snapshot_id"] = parent_id
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)

        assert snapshot.parent_snapshot_id == parent_id


# ============================================================================
# Test: Utility Properties
# ============================================================================


class TestModelMemorySnapshotUtilityProperties:
    """Tests for utility properties."""

    def test_decision_count(
        self, minimal_snapshot_data: dict, sample_decision: ModelDecisionRecord
    ) -> None:
        """Test decision_count property."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        assert snapshot.decision_count == 0

        snapshot = snapshot.with_decision(sample_decision)
        assert snapshot.decision_count == 1

        snapshot = snapshot.with_decision(sample_decision)
        assert snapshot.decision_count == 2

    def test_failure_count(
        self, minimal_snapshot_data: dict, sample_failure: ModelFailureRecord
    ) -> None:
        """Test failure_count property."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        assert snapshot.failure_count == 0

        snapshot = snapshot.with_failure(sample_failure)
        assert snapshot.failure_count == 1

        snapshot = snapshot.with_failure(sample_failure)
        assert snapshot.failure_count == 2


# ============================================================================
# Test: Serialization
# ============================================================================


class TestModelMemorySnapshotSerialization:
    """Tests for serialization and deserialization."""

    def test_model_dump(self, minimal_snapshot_data: dict) -> None:
        """Test serialization to dictionary."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        data = snapshot.model_dump()

        assert "snapshot_id" in data
        assert "version" in data
        assert "subject" in data
        assert "cost_ledger" in data
        assert "decisions" in data
        assert "failures" in data

    def test_model_dump_json(self, minimal_snapshot_data: dict) -> None:
        """Test serialization to JSON string."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        json_str = snapshot.model_dump_json()

        assert isinstance(json_str, str)
        assert "snapshot_id" in json_str
        assert "version" in json_str

    def test_round_trip_serialization(self, full_snapshot_data: dict) -> None:
        """Test that model survives serialization round-trip."""
        original = ModelMemorySnapshot(**full_snapshot_data)
        data = original.model_dump()
        restored = ModelMemorySnapshot(**data)

        assert original.snapshot_id == restored.snapshot_id
        assert original.version == restored.version
        assert original.subject == restored.subject
        assert len(original.decisions) == len(restored.decisions)
        assert len(original.failures) == len(restored.failures)

    def test_json_round_trip_serialization(self, minimal_snapshot_data: dict) -> None:
        """Test JSON serialization and deserialization roundtrip."""
        original = ModelMemorySnapshot(**minimal_snapshot_data)

        json_str = original.model_dump_json()
        restored = ModelMemorySnapshot.model_validate_json(json_str)

        assert original.snapshot_id == restored.snapshot_id
        assert original.version == restored.version
        assert original.schema_version == restored.schema_version

    def test_model_dump_contains_all_fields(self, full_snapshot_data: dict) -> None:
        """Test model_dump contains all expected fields."""
        snapshot = ModelMemorySnapshot(**full_snapshot_data)
        data = snapshot.model_dump()

        expected_fields = [
            "snapshot_id",
            "version",
            "parent_snapshot_id",
            "corpus_id",
            "subject",
            "decisions",
            "failures",
            "cost_ledger",
            "execution_annotations",
            "schema_version",
            "content_hash",
            "created_at",
            "tags",
        ]
        for field in expected_fields:
            assert field in data

    def test_model_validate_from_dict(self, minimal_snapshot_data: dict) -> None:
        """Test model validation from dictionary."""
        snapshot = ModelMemorySnapshot.model_validate(minimal_snapshot_data)

        assert snapshot.subject == minimal_snapshot_data["subject"]
        assert snapshot.cost_ledger == minimal_snapshot_data["cost_ledger"]


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestModelMemorySnapshotEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_model_not_hashable_due_to_dict_field(
        self, minimal_snapshot_data: dict
    ) -> None:
        """Test that model is NOT hashable due to execution_annotations dict.

        Note: Models with mutable dict fields cannot be used as dict keys
        or in sets, even when frozen. This is a Pydantic limitation.
        """
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)

        with pytest.raises(TypeError, match="unhashable type"):
            hash(snapshot)

    def test_str_representation(self, minimal_snapshot_data: dict) -> None:
        """Test __str__ method returns string."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        str_repr = str(snapshot)

        assert isinstance(str_repr, str)
        assert "MemorySnapshot" in str_repr

    def test_repr_representation(self, minimal_snapshot_data: dict) -> None:
        """Test __repr__ method returns string with class name."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        repr_str = repr(snapshot)

        assert isinstance(repr_str, str)
        assert "ModelMemorySnapshot" in repr_str

    def test_model_equality(self, minimal_snapshot_data: dict) -> None:
        """Test model equality comparison with identical data."""
        snapshot_id = uuid4()
        created_at = datetime.now(UTC)
        minimal_snapshot_data["snapshot_id"] = snapshot_id
        minimal_snapshot_data["created_at"] = created_at

        snapshot1 = ModelMemorySnapshot(**minimal_snapshot_data)
        snapshot2 = ModelMemorySnapshot(**minimal_snapshot_data)

        assert snapshot1 == snapshot2

    def test_model_inequality_different_snapshot_id(
        self, minimal_snapshot_data: dict
    ) -> None:
        """Test model inequality when snapshot_ids differ."""
        snapshot1 = ModelMemorySnapshot(**minimal_snapshot_data)
        snapshot2 = ModelMemorySnapshot(**minimal_snapshot_data)

        # Different auto-generated snapshot_ids
        assert snapshot1 != snapshot2

    def test_empty_execution_annotations(self, minimal_snapshot_data: dict) -> None:
        """Test snapshot with empty execution_annotations."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)

        assert snapshot.execution_annotations == {}

    def test_complex_execution_annotations(self, minimal_snapshot_data: dict) -> None:
        """Test snapshot with complex nested execution_annotations."""
        minimal_snapshot_data["execution_annotations"] = {
            "step": "validation",
            "attempt": 1,
            "nested": {"key": "value", "list": [1, 2, 3]},
            "boolean": True,
            "null_value": None,
        }
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)

        assert snapshot.execution_annotations["step"] == "validation"
        assert snapshot.execution_annotations["nested"]["key"] == "value"

    def test_tuples_are_immutable(
        self, minimal_snapshot_data: dict, sample_decision: ModelDecisionRecord
    ) -> None:
        """Test that decision/failure tuples are truly immutable."""
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        snapshot = snapshot.with_decision(sample_decision)

        # Tuple should be immutable
        with pytest.raises((TypeError, AttributeError)):
            snapshot.decisions[0] = sample_decision


# ============================================================================
# Test: diff_from() Method
# ============================================================================


class TestModelMemorySnapshotDiffFrom:
    """Tests for diff_from() method."""

    def test_diff_from_returns_model_memory_diff(
        self, minimal_snapshot_data: dict
    ) -> None:
        """Test that diff_from returns a ModelMemoryDiff instance."""
        snapshot1 = ModelMemorySnapshot(**minimal_snapshot_data)
        snapshot2 = ModelMemorySnapshot(**minimal_snapshot_data)

        diff = snapshot2.diff_from(snapshot1)

        assert isinstance(diff, ModelMemoryDiff)

    def test_diff_from_no_changes(
        self,
        sample_subject: ModelSubjectRef,
        sample_cost_ledger: ModelCostLedger,
    ) -> None:
        """Test diff_from with identical content shows no changes."""
        # Create two snapshots with same content but different IDs
        snapshot1 = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
        )
        snapshot2 = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
        )

        diff = snapshot2.diff_from(snapshot1)

        assert len(diff.decisions_added) == 0
        assert len(diff.decisions_removed) == 0
        assert len(diff.failures_added) == 0
        assert diff.cost_delta == 0.0
        assert diff.has_changes is False
        assert diff.summary == "No changes"

    def test_diff_from_decisions_added(
        self,
        sample_subject: ModelSubjectRef,
        sample_cost_ledger: ModelCostLedger,
        sample_decision: ModelDecisionRecord,
    ) -> None:
        """Test diff_from correctly identifies added decisions."""
        base_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
        )
        # Create a new snapshot with a decision (different snapshot_id)
        target_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            decisions=(sample_decision,),
        )

        diff = target_snapshot.diff_from(base_snapshot)

        assert len(diff.decisions_added) == 1
        assert diff.decisions_added[0].decision_id == sample_decision.decision_id
        assert len(diff.decisions_removed) == 0
        assert "1 decision(s) added" in diff.summary

    def test_diff_from_multiple_decisions_added(
        self,
        sample_subject: ModelSubjectRef,
        sample_cost_ledger: ModelCostLedger,
    ) -> None:
        """Test diff_from correctly identifies multiple added decisions."""
        base_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
        )

        # Create multiple unique decisions
        decision1 = ModelDecisionRecord(
            decision_type=EnumDecisionType.MODEL_SELECTION,
            timestamp=datetime.now(UTC),
            options_considered=("option1",),
            chosen_option="option1",
            confidence=0.9,
            input_hash="hash1",
        )
        decision2 = ModelDecisionRecord(
            decision_type=EnumDecisionType.MODEL_SELECTION,
            timestamp=datetime.now(UTC),
            options_considered=("option2",),
            chosen_option="option2",
            confidence=0.8,
            input_hash="hash2",
        )

        # Create a new snapshot with decisions (different snapshot_id)
        target_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            decisions=(decision1, decision2),
        )

        diff = target_snapshot.diff_from(base_snapshot)

        assert len(diff.decisions_added) == 2
        assert "2 decision(s) added" in diff.summary

    def test_diff_from_decisions_removed(
        self, minimal_snapshot_data: dict, sample_decision: ModelDecisionRecord
    ) -> None:
        """Test diff_from correctly identifies removed decisions."""
        # Base has a decision
        base_snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        base_with_decision = base_snapshot.with_decision(sample_decision)

        # Target does not have the decision
        target_snapshot = ModelMemorySnapshot(**minimal_snapshot_data)

        diff = target_snapshot.diff_from(base_with_decision)

        assert len(diff.decisions_removed) == 1
        assert diff.decisions_removed[0] == sample_decision.decision_id
        assert len(diff.decisions_added) == 0
        assert "1 decision(s) removed" in diff.summary

    def test_diff_from_failures_added(
        self,
        sample_subject: ModelSubjectRef,
        sample_cost_ledger: ModelCostLedger,
        sample_failure: ModelFailureRecord,
    ) -> None:
        """Test diff_from correctly identifies added failures."""
        base_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
        )
        # Create a new snapshot with a failure (different snapshot_id)
        target_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            failures=(sample_failure,),
        )

        diff = target_snapshot.diff_from(base_snapshot)

        assert len(diff.failures_added) == 1
        assert diff.failures_added[0].failure_id == sample_failure.failure_id
        assert "1 failure(s) recorded" in diff.summary

    def test_diff_from_multiple_failures_added(
        self,
        sample_subject: ModelSubjectRef,
        sample_cost_ledger: ModelCostLedger,
    ) -> None:
        """Test diff_from correctly identifies multiple added failures."""
        base_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
        )

        failure1 = ModelFailureRecord(
            timestamp=datetime.now(UTC),
            failure_type=EnumFailureType.TIMEOUT,
            step_context="step1",
            error_code="ERR_001",
            error_message="Timeout error",
        )
        failure2 = ModelFailureRecord(
            timestamp=datetime.now(UTC),
            failure_type=EnumFailureType.RATE_LIMIT,
            step_context="step2",
            error_code="ERR_002",
            error_message="Rate limit error",
        )

        # Create a new snapshot with failures (different snapshot_id)
        target_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            failures=(failure1, failure2),
        )

        diff = target_snapshot.diff_from(base_snapshot)

        assert len(diff.failures_added) == 2
        assert "2 failure(s) recorded" in diff.summary

    def test_diff_from_cost_delta_positive(
        self,
        sample_subject: ModelSubjectRef,
        sample_cost_entry: ModelCostEntry,
    ) -> None:
        """Test diff_from correctly computes positive cost delta."""
        base_ledger = ModelCostLedger(budget_total=100.0, total_spent=0.0)
        base_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=base_ledger,
        )

        # Create target with higher cost (different snapshot_id)
        target_ledger = ModelCostLedger(
            budget_total=100.0,
            total_spent=sample_cost_entry.cost,
        )
        target_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=target_ledger,
        )

        diff = target_snapshot.diff_from(base_snapshot)

        assert diff.cost_delta == sample_cost_entry.cost
        assert "+$" in diff.summary
        assert "cost" in diff.summary

    def test_diff_from_cost_delta_negative(
        self, sample_subject: ModelSubjectRef
    ) -> None:
        """Test diff_from correctly computes negative cost delta."""
        # Base has higher cost
        base_ledger = ModelCostLedger(budget_total=100.0, total_spent=50.0)
        base_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=base_ledger,
        )

        # Target has lower cost
        target_ledger = ModelCostLedger(budget_total=100.0, total_spent=30.0)
        target_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=target_ledger,
        )

        diff = target_snapshot.diff_from(base_snapshot)

        assert diff.cost_delta == -20.0
        assert "-$" in diff.summary
        assert "cost" in diff.summary

    def test_diff_from_all_types_of_changes(
        self,
        sample_subject: ModelSubjectRef,
        sample_decision: ModelDecisionRecord,
        sample_failure: ModelFailureRecord,
    ) -> None:
        """Test diff_from with all types of changes at once."""
        # Base snapshot with one decision
        base_ledger = ModelCostLedger(budget_total=100.0, total_spent=10.0)
        base_decision = ModelDecisionRecord(
            decision_type=EnumDecisionType.MODEL_SELECTION,
            timestamp=datetime.now(UTC),
            options_considered=("old_option",),
            chosen_option="old_option",
            confidence=0.7,
            input_hash="old_hash",
        )
        base_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=base_ledger,
            decisions=(base_decision,),
        )

        # Target snapshot: new decision (base decision removed), failure added, cost increased
        target_ledger = ModelCostLedger(budget_total=100.0, total_spent=25.0)
        target_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=target_ledger,
            decisions=(sample_decision,),
            failures=(sample_failure,),
        )

        diff = target_snapshot.diff_from(base_snapshot)

        assert len(diff.decisions_added) == 1
        assert len(diff.decisions_removed) == 1
        assert len(diff.failures_added) == 1
        assert diff.cost_delta == 15.0
        assert "decision(s) added" in diff.summary
        assert "decision(s) removed" in diff.summary
        assert "failure(s) recorded" in diff.summary
        assert "cost" in diff.summary

    def test_diff_from_correct_snapshot_ids(self, minimal_snapshot_data: dict) -> None:
        """Test diff_from returns correct base and target snapshot IDs."""
        base_snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        target_snapshot = ModelMemorySnapshot(**minimal_snapshot_data)

        diff = target_snapshot.diff_from(base_snapshot)

        assert diff.base_snapshot_id == base_snapshot.snapshot_id
        assert diff.target_snapshot_id == target_snapshot.snapshot_id

    def test_diff_from_summary_no_changes(self, minimal_snapshot_data: dict) -> None:
        """Test diff_from summary when there are no changes."""
        snapshot1 = ModelMemorySnapshot(**minimal_snapshot_data)
        snapshot2 = ModelMemorySnapshot(**minimal_snapshot_data)

        diff = snapshot2.diff_from(snapshot1)

        assert diff.summary == "No changes"

    def test_diff_from_summary_multiple_changes(
        self,
        sample_subject: ModelSubjectRef,
        sample_decision: ModelDecisionRecord,
        sample_failure: ModelFailureRecord,
        sample_cost_entry: ModelCostEntry,
    ) -> None:
        """Test diff_from summary with multiple types of changes."""
        base_ledger = ModelCostLedger(budget_total=100.0, total_spent=0.0)
        base_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=base_ledger,
        )

        # Create target with decision, failure, and cost (different snapshot_id)
        target_ledger = ModelCostLedger(
            budget_total=100.0,
            total_spent=sample_cost_entry.cost,
        )
        target_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=target_ledger,
            decisions=(sample_decision,),
            failures=(sample_failure,),
        )

        diff = target_snapshot.diff_from(base_snapshot)

        # Check all parts are in summary separated by semicolons
        assert "1 decision(s) added" in diff.summary
        assert "1 failure(s) recorded" in diff.summary
        assert "cost" in diff.summary
        assert ";" in diff.summary  # Multiple changes separated by semicolons

    def test_diff_from_preserves_decision_order(
        self,
        sample_subject: ModelSubjectRef,
        sample_cost_ledger: ModelCostLedger,
    ) -> None:
        """Test diff_from preserves the order of added decisions."""
        base_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
        )

        decisions = []
        for i in range(3):
            decision = ModelDecisionRecord(
                decision_type=EnumDecisionType.MODEL_SELECTION,
                timestamp=datetime.now(UTC),
                options_considered=(f"option{i}",),
                chosen_option=f"option{i}",
                confidence=0.9 - i * 0.1,
                input_hash=f"hash{i}",
            )
            decisions.append(decision)

        # Create target with decisions in order (different snapshot_id)
        target_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            decisions=tuple(decisions),
        )

        diff = target_snapshot.diff_from(base_snapshot)

        # Verify order is preserved
        for i, added in enumerate(diff.decisions_added):
            assert added.decision_id == decisions[i].decision_id

    def test_diff_from_small_cost_delta_ignored_in_summary(
        self, sample_subject: ModelSubjectRef
    ) -> None:
        """Test diff_from ignores very small cost deltas in summary."""
        # Cost difference smaller than 1e-9 should not appear in summary
        base_ledger = ModelCostLedger(budget_total=100.0, total_spent=10.0)
        base_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=base_ledger,
        )

        # Effectively same cost (difference < 1e-9)
        target_ledger = ModelCostLedger(budget_total=100.0, total_spent=10.0 + 1e-10)
        target_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=target_ledger,
        )

        diff = target_snapshot.diff_from(base_snapshot)

        # Cost delta too small to show
        assert "cost" not in diff.summary
        assert diff.summary == "No changes"


# ============================================================================
# Test: Performance
# ============================================================================


@pytest.mark.slow
class TestModelMemorySnapshotPerformance:
    """Performance tests to catch algorithmic complexity issues."""

    def test_diff_from_large_decision_set(
        self,
        sample_subject: ModelSubjectRef,
        sample_cost_ledger: ModelCostLedger,
    ) -> None:
        """Test diff_from with 1000+ decisions completes in reasonable time.

        This test guards against O(n^2) regressions in the diff algorithm.
        The current implementation uses set operations which should be O(n).
        With 1000 decisions, O(n) should complete in milliseconds while
        O(n^2) would take significantly longer.
        """
        import time

        num_decisions = 1000

        # Create 1000 unique decisions for base snapshot
        base_decisions = tuple(
            ModelDecisionRecord(
                decision_type=EnumDecisionType.MODEL_SELECTION,
                timestamp=datetime.now(UTC),
                options_considered=(f"base_option_{i}",),
                chosen_option=f"base_option_{i}",
                confidence=0.5,
                input_hash=f"base_hash_{i}",
            )
            for i in range(num_decisions)
        )

        # Create 1000 different decisions for target snapshot
        # All different from base to maximize diff work
        target_decisions = tuple(
            ModelDecisionRecord(
                decision_type=EnumDecisionType.MODEL_SELECTION,
                timestamp=datetime.now(UTC),
                options_considered=(f"target_option_{i}",),
                chosen_option=f"target_option_{i}",
                confidence=0.5,
                input_hash=f"target_hash_{i}",
            )
            for i in range(num_decisions)
        )

        base_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            decisions=base_decisions,
        )
        target_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            decisions=target_decisions,
        )

        start = time.perf_counter()
        diff = target_snapshot.diff_from(base_snapshot)
        elapsed = time.perf_counter() - start

        # O(n) algorithm should complete in well under 1 second for 1000 items
        # O(n^2) with 1000 items would take significantly longer
        # Using 1.0 second as a generous threshold to avoid flaky tests
        assert elapsed < 1.0, (
            f"diff_from took {elapsed:.3f}s for {num_decisions} decisions, "
            f"may indicate O(n^2) complexity regression"
        )

        # Verify correctness - all decisions should show as added/removed
        assert len(diff.decisions_added) == num_decisions
        assert len(diff.decisions_removed) == num_decisions
        assert diff.has_changes is True

    def test_diff_from_large_decision_set_with_overlap(
        self,
        sample_subject: ModelSubjectRef,
        sample_cost_ledger: ModelCostLedger,
    ) -> None:
        """Test diff_from with partial overlap in large decision sets.

        Tests the more realistic scenario where base and target share
        some decisions. This exercises the set intersection logic.
        """
        import time

        num_decisions = 1000
        overlap_count = 500

        # Create shared decisions (will be in both snapshots)
        shared_decisions = [
            ModelDecisionRecord(
                decision_type=EnumDecisionType.MODEL_SELECTION,
                timestamp=datetime.now(UTC),
                options_considered=(f"shared_option_{i}",),
                chosen_option=f"shared_option_{i}",
                confidence=0.5,
                input_hash=f"shared_hash_{i}",
            )
            for i in range(overlap_count)
        ]

        # Create unique decisions for base (not in target)
        base_only_decisions = [
            ModelDecisionRecord(
                decision_type=EnumDecisionType.MODEL_SELECTION,
                timestamp=datetime.now(UTC),
                options_considered=(f"base_only_{i}",),
                chosen_option=f"base_only_{i}",
                confidence=0.5,
                input_hash=f"base_only_hash_{i}",
            )
            for i in range(num_decisions - overlap_count)
        ]

        # Create unique decisions for target (not in base)
        target_only_decisions = [
            ModelDecisionRecord(
                decision_type=EnumDecisionType.MODEL_SELECTION,
                timestamp=datetime.now(UTC),
                options_considered=(f"target_only_{i}",),
                chosen_option=f"target_only_{i}",
                confidence=0.5,
                input_hash=f"target_only_hash_{i}",
            )
            for i in range(num_decisions - overlap_count)
        ]

        base_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            decisions=tuple(shared_decisions + base_only_decisions),
        )
        target_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            decisions=tuple(shared_decisions + target_only_decisions),
        )

        start = time.perf_counter()
        diff = target_snapshot.diff_from(base_snapshot)
        elapsed = time.perf_counter() - start

        # Should complete quickly with O(n) complexity
        assert elapsed < 1.0, (
            f"diff_from took {elapsed:.3f}s for {num_decisions} decisions with overlap, "
            f"may indicate O(n^2) complexity regression"
        )

        # Verify correctness
        # Target has target_only decisions added (not in base)
        assert len(diff.decisions_added) == num_decisions - overlap_count
        # Base had base_only decisions removed (not in target)
        assert len(diff.decisions_removed) == num_decisions - overlap_count
        assert diff.has_changes is True

    def test_diff_from_large_failure_set(
        self,
        sample_subject: ModelSubjectRef,
        sample_cost_ledger: ModelCostLedger,
    ) -> None:
        """Test diff_from with 1000+ failures completes in reasonable time.

        Similar to decision test but exercises the failure diff logic.
        """
        import time

        num_failures = 1000

        # Create failures for target (none in base)
        target_failures = tuple(
            ModelFailureRecord(
                timestamp=datetime.now(UTC),
                failure_type=EnumFailureType.TIMEOUT,
                step_context=f"step_{i}",
                error_code=f"ERR_{i:04d}",
                error_message=f"Error message {i}",
            )
            for i in range(num_failures)
        )

        base_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
        )
        target_snapshot = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            failures=target_failures,
        )

        start = time.perf_counter()
        diff = target_snapshot.diff_from(base_snapshot)
        elapsed = time.perf_counter() - start

        # Should complete quickly with O(n) complexity
        assert elapsed < 1.0, (
            f"diff_from took {elapsed:.3f}s for {num_failures} failures, "
            f"may indicate O(n^2) complexity regression"
        )

        # Verify correctness
        assert len(diff.failures_added) == num_failures
        assert diff.has_changes is True


# ============================================================================
# Test: Integration Scenarios
# ============================================================================


class TestModelMemorySnapshotIntegration:
    """Integration tests for realistic usage scenarios."""

    def test_full_snapshot_lifecycle(
        self,
        minimal_snapshot_data: dict,
        sample_decision: ModelDecisionRecord,
        sample_failure: ModelFailureRecord,
        sample_cost_entry: ModelCostEntry,
    ) -> None:
        """Test a complete snapshot lifecycle with multiple operations."""
        # Create initial snapshot
        snapshot = ModelMemorySnapshot(**minimal_snapshot_data)
        assert snapshot.decision_count == 0
        assert snapshot.failure_count == 0

        # Add decisions
        snapshot = snapshot.with_decision(sample_decision)
        snapshot = snapshot.with_decision(sample_decision)
        assert snapshot.decision_count == 2

        # Add failures
        snapshot = snapshot.with_failure(sample_failure)
        assert snapshot.failure_count == 1

        # Add cost
        snapshot = snapshot.with_cost_entry(sample_cost_entry)
        assert snapshot.cost_ledger.total_spent == sample_cost_entry.cost

        # Verify content hash is present
        assert len(snapshot.content_hash) == 64

    def test_snapshot_lineage_chain(
        self,
        sample_subject: ModelSubjectRef,
        sample_cost_ledger: ModelCostLedger,
        sample_decision: ModelDecisionRecord,
    ) -> None:
        """Test creating a chain of snapshots with lineage."""
        # Create first snapshot
        snapshot1 = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            version=1,
        )

        # Create second snapshot with parent reference
        snapshot2 = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            version=2,
            parent_snapshot_id=snapshot1.snapshot_id,
        )

        # Create third snapshot with parent reference
        snapshot3 = ModelMemorySnapshot(
            subject=sample_subject,
            cost_ledger=sample_cost_ledger,
            version=3,
            parent_snapshot_id=snapshot2.snapshot_id,
        )

        assert snapshot1.has_parent is False
        assert snapshot2.has_parent is True
        assert snapshot2.parent_snapshot_id == snapshot1.snapshot_id
        assert snapshot3.parent_snapshot_id == snapshot2.snapshot_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
