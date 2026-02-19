# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelCostLedger.

Tests comprehensive ledger functionality including:
- Model instantiation and validation
- Immutability (frozen model)
- with_entry() immutable updates
- Budget threshold checking
- Escalation tracking
- Serialization and deserialization
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from omnibase_core.errors import OnexError
from omnibase_core.models.omnimemory import ModelCostEntry, ModelCostLedger

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_entry() -> ModelCostEntry:
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
def sample_entry_large() -> ModelCostEntry:
    """Create a larger cost entry for threshold testing."""
    return ModelCostEntry(
        timestamp=datetime.now(UTC),
        operation="chat_completion",
        model_used="gpt-4-turbo",
        tokens_in=5000,
        tokens_out=2000,
        cost=50.0,
        cumulative_total=50.0,
    )


@pytest.fixture
def minimal_ledger_data() -> dict:
    """Minimal required data for creating a ledger."""
    return {"budget_total": 100.0}


@pytest.fixture
def full_ledger_data(sample_entry: ModelCostEntry) -> dict:
    """Complete data including all optional fields."""
    return {
        "ledger_id": uuid4(),
        "budget_total": 100.0,
        "budget_remaining": 90.0,
        "entries": (sample_entry,),
        "total_spent": 10.0,
        "escalation_count": 1,
        "last_escalation_reason": "High priority task",
        "warning_threshold": 0.75,
        "hard_ceiling": 0.95,
    }


# ============================================================================
# Test: Model Instantiation
# ============================================================================


class TestModelCostLedgerInstantiation:
    """Tests for model instantiation and basic functionality."""

    def test_create_with_minimal_data(self, minimal_ledger_data: dict) -> None:
        """Test creating ledger with only required fields."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        assert ledger.budget_total == 100.0
        assert isinstance(ledger.ledger_id, UUID)

    def test_create_with_full_data(self, full_ledger_data: dict) -> None:
        """Test creating ledger with all fields explicitly set."""
        ledger = ModelCostLedger(**full_ledger_data)

        assert ledger.ledger_id == full_ledger_data["ledger_id"]
        assert ledger.budget_total == 100.0
        assert ledger.budget_remaining == 90.0
        assert ledger.total_spent == 10.0
        assert ledger.escalation_count == 1
        assert ledger.last_escalation_reason == "High priority task"
        assert ledger.warning_threshold == 0.75
        assert ledger.hard_ceiling == 0.95
        assert len(ledger.entries) == 1

    def test_auto_generated_ledger_id(self, minimal_ledger_data: dict) -> None:
        """Test that ledger_id is auto-generated when not provided."""
        ledger1 = ModelCostLedger(**minimal_ledger_data)
        ledger2 = ModelCostLedger(**minimal_ledger_data)

        assert isinstance(ledger1.ledger_id, UUID)
        assert isinstance(ledger2.ledger_id, UUID)
        assert ledger1.ledger_id != ledger2.ledger_id  # Each gets unique ID

    def test_default_values(self, minimal_ledger_data: dict) -> None:
        """Test that default values are properly set."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        assert ledger.entries == ()
        assert ledger.total_spent == 0.0
        assert ledger.escalation_count == 0
        assert ledger.last_escalation_reason is None
        assert ledger.warning_threshold == 0.8
        assert ledger.hard_ceiling == 1.0

    def test_default_budget_remaining_computed(self, minimal_ledger_data: dict) -> None:
        """Test that budget_remaining defaults to budget_total when not provided."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        # When total_spent is 0, budget_remaining should equal budget_total
        assert ledger.budget_remaining == ledger.budget_total

    def test_various_budget_total_values(self) -> None:
        """Test various valid budget_total values."""
        budgets = [0.01, 1.0, 100.0, 10000.0, 999999.99]
        for budget in budgets:
            ledger = ModelCostLedger(budget_total=budget)
            assert ledger.budget_total == budget


# ============================================================================
# Test: Immutability (Frozen Model)
# ============================================================================


class TestModelCostLedgerImmutability:
    """Tests for frozen model behavior."""

    def test_model_is_frozen(self, minimal_ledger_data: dict) -> None:
        """Test that the model is immutable."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - mypy correctly flags assignment to frozen attr
            ledger.budget_total = 999.99  # type: ignore[misc]

    def test_cannot_modify_budget_total(self, minimal_ledger_data: dict) -> None:
        """Test that budget_total cannot be modified."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - mypy correctly flags assignment to frozen attr
            ledger.budget_total = 200.0  # type: ignore[misc]

    def test_cannot_modify_entries(
        self, minimal_ledger_data: dict, sample_entry: ModelCostEntry
    ) -> None:
        """Test that entries cannot be modified."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - mypy correctly flags assignment to frozen attr
            ledger.entries = (sample_entry,)  # type: ignore[misc]

    def test_cannot_modify_total_spent(self, minimal_ledger_data: dict) -> None:
        """Test that total_spent cannot be modified."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - mypy correctly flags assignment to frozen attr
            ledger.total_spent = 50.0  # type: ignore[misc]

    def test_cannot_modify_ledger_id(self, minimal_ledger_data: dict) -> None:
        """Test that ledger_id cannot be modified."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - mypy correctly flags assignment to frozen attr
            ledger.ledger_id = uuid4()  # type: ignore[misc]

    def test_cannot_modify_budget_remaining(self, minimal_ledger_data: dict) -> None:
        """Test that budget_remaining cannot be modified."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - mypy correctly flags assignment to frozen attr
            ledger.budget_remaining = 50.0  # type: ignore[misc]

    def test_cannot_modify_escalation_count(self, minimal_ledger_data: dict) -> None:
        """Test that escalation_count cannot be modified."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - mypy correctly flags assignment to frozen attr
            ledger.escalation_count = 5  # type: ignore[misc]

    def test_cannot_modify_warning_threshold(self, minimal_ledger_data: dict) -> None:
        """Test that warning_threshold cannot be modified."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - mypy correctly flags assignment to frozen attr
            ledger.warning_threshold = 0.5  # type: ignore[misc]


# ============================================================================
# Test: Field Validation
# ============================================================================


class TestModelCostLedgerValidation:
    """Tests for field validation constraints."""

    def test_budget_total_must_be_positive(self) -> None:
        """Test that budget_total rejects zero and negative values."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCostLedger(budget_total=0.0)

        assert "budget_total" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ModelCostLedger(budget_total=-1.0)

        assert "budget_total" in str(exc_info.value)

    def test_warning_threshold_must_be_valid_lower_bound(self) -> None:
        """Test that warning_threshold rejects values <= 0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCostLedger(budget_total=100.0, warning_threshold=0.0)

        assert "warning_threshold" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ModelCostLedger(budget_total=100.0, warning_threshold=-0.5)

        assert "warning_threshold" in str(exc_info.value)

    def test_warning_threshold_must_be_valid_upper_bound(self) -> None:
        """Test that warning_threshold rejects values > 1."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCostLedger(budget_total=100.0, warning_threshold=1.1)

        assert "warning_threshold" in str(exc_info.value)

    def test_warning_threshold_valid_range(self) -> None:
        """Test valid warning_threshold values."""
        # Note: warning_threshold must be < hard_ceiling (default 1.0)
        # so we test values below 1.0, or explicitly set hard_ceiling
        valid_thresholds = [0.01, 0.5, 0.8, 0.99]
        for threshold in valid_thresholds:
            ledger = ModelCostLedger(budget_total=100.0, warning_threshold=threshold)
            assert ledger.warning_threshold == threshold

        # Test warning_threshold=1.0 with explicit hard_ceiling > 1.0
        ledger = ModelCostLedger(
            budget_total=100.0, warning_threshold=1.0, hard_ceiling=1.5
        )
        assert ledger.warning_threshold == 1.0

    def test_hard_ceiling_must_be_valid_lower_bound(self) -> None:
        """Test that hard_ceiling rejects values <= 0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCostLedger(budget_total=100.0, hard_ceiling=0.0)

        assert "hard_ceiling" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ModelCostLedger(budget_total=100.0, hard_ceiling=-0.5)

        assert "hard_ceiling" in str(exc_info.value)

    def test_hard_ceiling_must_exceed_warning_threshold(self) -> None:
        """Test that hard_ceiling must be > warning_threshold."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCostLedger(budget_total=100.0, warning_threshold=0.8, hard_ceiling=0.5)

        error_str = str(exc_info.value)
        assert "hard_ceiling" in error_str or "warning_threshold" in error_str

    def test_hard_ceiling_equal_to_warning_threshold_rejected(self) -> None:
        """Test that hard_ceiling cannot equal warning_threshold."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCostLedger(budget_total=100.0, warning_threshold=0.8, hard_ceiling=0.8)
        error_str = str(exc_info.value)
        assert "hard_ceiling" in error_str or "warning_threshold" in error_str

    def test_total_spent_must_be_non_negative(self) -> None:
        """Test that total_spent rejects negative values."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCostLedger(
                budget_total=100.0, total_spent=-1.0, budget_remaining=101.0
            )

        assert "total_spent" in str(exc_info.value)

    def test_escalation_count_must_be_non_negative(self) -> None:
        """Test that escalation_count rejects negative values."""
        with pytest.raises(ValidationError) as exc_info:
            ModelCostLedger(budget_total=100.0, escalation_count=-1)

        assert "escalation_count" in str(exc_info.value)

    def test_budget_remaining_consistency(self) -> None:
        """Test budget_remaining must be consistent with budget_total - total_spent."""
        # This test validates that budget_remaining is properly computed
        ledger = ModelCostLedger(
            budget_total=100.0, total_spent=30.0, budget_remaining=70.0
        )
        assert ledger.budget_remaining == ledger.budget_total - ledger.total_spent

    def test_missing_required_field_budget_total(self) -> None:
        """Test that missing budget_total raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            # NOTE: Intentionally testing Pydantic validation - mypy correctly flags missing required arg
            ModelCostLedger()  # type: ignore[call-arg]

        assert "budget_total" in str(exc_info.value)


# ============================================================================
# Test: Entries Cumulative Total Validation
# ============================================================================


class TestModelCostLedgerEntriesValidation:
    """Tests for entries cumulative_total validation on creation.

    The validator checks that adjacent entries have consistent cumulative_total
    values: entry[i].cumulative_total == entry[i-1].cumulative_total + entry[i].cost.

    Single entries are always valid (no relative validation possible).
    The first entry's cumulative_total can be any value (may include prior
    spending not tracked as entries).
    """

    def test_create_with_consistent_entries(self) -> None:
        """Test that ledger can be created with consistent entries."""
        entry1 = ModelCostEntry(
            timestamp=datetime.now(UTC),
            operation="op1",
            model_used="gpt-4",
            tokens_in=100,
            tokens_out=50,
            cost=1.0,
            cumulative_total=1.0,
        )
        entry2 = ModelCostEntry(
            timestamp=datetime.now(UTC),
            operation="op2",
            model_used="gpt-4",
            tokens_in=100,
            tokens_out=50,
            cost=2.0,
            cumulative_total=3.0,  # 1.0 + 2.0
        )

        ledger = ModelCostLedger(
            budget_total=100.0,
            entries=(entry1, entry2),
            total_spent=3.0,
            budget_remaining=97.0,
        )

        assert len(ledger.entries) == 2
        assert ledger.total_spent == 3.0

    def test_create_with_inconsistent_entries_rejected(self) -> None:
        """Test that ledger rejects entries with inconsistent cumulative_total."""
        entry1 = ModelCostEntry(
            timestamp=datetime.now(UTC),
            operation="op1",
            model_used="gpt-4",
            tokens_in=100,
            tokens_out=50,
            cost=1.0,
            cumulative_total=1.0,
        )
        entry2 = ModelCostEntry(
            timestamp=datetime.now(UTC),
            operation="op2",
            model_used="gpt-4",
            tokens_in=100,
            tokens_out=50,
            cost=2.0,
            cumulative_total=999.0,  # WRONG! Should be 3.0
        )

        with pytest.raises(ValidationError) as exc_info:
            ModelCostLedger(
                budget_total=100.0,
                entries=(entry1, entry2),
                total_spent=3.0,
                budget_remaining=97.0,
            )

        assert "cumulative_total" in str(exc_info.value)

    def test_create_with_empty_entries_valid(self) -> None:
        """Test that ledger can be created with empty entries tuple."""
        ledger = ModelCostLedger(budget_total=100.0, entries=())

        assert ledger.entries == ()

    def test_create_with_single_entry_any_cumulative_valid(self) -> None:
        """Test single entry with any cumulative_total is valid.

        Single entries are not validated since there's no previous entry
        to compare against. The cumulative_total may include prior spending
        not tracked as entries.
        """
        # Entry with cumulative_total matching cost (common case)
        entry1 = ModelCostEntry(
            timestamp=datetime.now(UTC),
            operation="op1",
            model_used="gpt-4",
            tokens_in=100,
            tokens_out=50,
            cost=5.0,
            cumulative_total=5.0,
        )
        ledger1 = ModelCostLedger(
            budget_total=100.0,
            entries=(entry1,),
            total_spent=5.0,
            budget_remaining=95.0,
        )
        assert len(ledger1.entries) == 1

        # Entry with cumulative_total > cost (has prior untracked spending)
        entry2 = ModelCostEntry(
            timestamp=datetime.now(UTC),
            operation="op2",
            model_used="gpt-4",
            tokens_in=100,
            tokens_out=50,
            cost=5.0,
            cumulative_total=105.0,  # Prior spending of 100.0
        )
        ledger2 = ModelCostLedger(
            budget_total=200.0,
            entries=(entry2,),
            total_spent=105.0,
            budget_remaining=95.0,
        )
        assert len(ledger2.entries) == 1

    def test_create_with_entries_within_float_tolerance(self) -> None:
        """Test entries with cumulative_total within float tolerance are accepted."""
        entry1 = ModelCostEntry(
            timestamp=datetime.now(UTC),
            operation="op1",
            model_used="gpt-4",
            tokens_in=100,
            tokens_out=50,
            cost=5.0,
            cumulative_total=5.0,
        )
        entry2 = ModelCostEntry(
            timestamp=datetime.now(UTC),
            operation="op2",
            model_used="gpt-4",
            tokens_in=100,
            tokens_out=50,
            cost=3.0,
            cumulative_total=8.0 + 1e-10,  # Within 1e-9 tolerance
        )

        ledger = ModelCostLedger(
            budget_total=100.0,
            entries=(entry1, entry2),
            total_spent=8.0,
            budget_remaining=92.0,
        )

        assert len(ledger.entries) == 2

    def test_create_with_multiple_entries_validates_sequence(self) -> None:
        """Test that validation checks the entire sequence of entries."""
        entry1 = ModelCostEntry(
            timestamp=datetime.now(UTC),
            operation="op1",
            model_used="gpt-4",
            tokens_in=100,
            tokens_out=50,
            cost=1.0,
            cumulative_total=1.0,
        )
        entry2 = ModelCostEntry(
            timestamp=datetime.now(UTC),
            operation="op2",
            model_used="gpt-4",
            tokens_in=100,
            tokens_out=50,
            cost=2.0,
            cumulative_total=3.0,  # Correct: 1.0 + 2.0
        )
        entry3 = ModelCostEntry(
            timestamp=datetime.now(UTC),
            operation="op3",
            model_used="gpt-4",
            tokens_in=100,
            tokens_out=50,
            cost=3.0,
            cumulative_total=100.0,  # WRONG! Should be 6.0
        )

        with pytest.raises(ValidationError) as exc_info:
            ModelCostLedger(
                budget_total=200.0,
                entries=(entry1, entry2, entry3),
                total_spent=6.0,
                budget_remaining=194.0,
            )

        # Should report the error at entry 2 (0-indexed)
        assert "cumulative_total" in str(exc_info.value)
        assert "Entry 2" in str(exc_info.value)

    def test_create_with_prior_spending_entries_valid(self) -> None:
        """Test entries starting with prior spending are valid.

        The first entry can have a cumulative_total that includes prior
        spending not tracked as entries, as long as subsequent entries
        maintain relative consistency.
        """
        # First entry starts at 100.0 (prior spending)
        entry1 = ModelCostEntry(
            timestamp=datetime.now(UTC),
            operation="op1",
            model_used="gpt-4",
            tokens_in=100,
            tokens_out=50,
            cost=5.0,
            cumulative_total=105.0,  # 100.0 prior + 5.0 cost
        )
        entry2 = ModelCostEntry(
            timestamp=datetime.now(UTC),
            operation="op2",
            model_used="gpt-4",
            tokens_in=100,
            tokens_out=50,
            cost=10.0,
            cumulative_total=115.0,  # 105.0 + 10.0
        )

        ledger = ModelCostLedger(
            budget_total=200.0,
            entries=(entry1, entry2),
            total_spent=115.0,
            budget_remaining=85.0,
        )

        assert len(ledger.entries) == 2
        assert ledger.total_spent == 115.0


# ============================================================================
# Test: with_entry() Method
# ============================================================================


class TestModelCostLedgerWithEntry:
    """Tests for with_entry() immutable update method."""

    def test_with_entry_returns_new_instance(
        self, minimal_ledger_data: dict, sample_entry: ModelCostEntry
    ) -> None:
        """Test that with_entry returns a new ledger instance."""
        ledger = ModelCostLedger(**minimal_ledger_data)
        new_ledger = ledger.with_entry(sample_entry)

        assert new_ledger is not ledger
        assert isinstance(new_ledger, ModelCostLedger)

    def test_with_entry_preserves_original(
        self, minimal_ledger_data: dict, sample_entry: ModelCostEntry
    ) -> None:
        """Test that with_entry does not modify the original ledger."""
        ledger = ModelCostLedger(**minimal_ledger_data)
        original_total_spent = ledger.total_spent
        original_entries = ledger.entries

        _ = ledger.with_entry(sample_entry)

        assert ledger.total_spent == original_total_spent
        assert ledger.entries == original_entries

    def test_with_entry_updates_total_spent(
        self, minimal_ledger_data: dict, sample_entry: ModelCostEntry
    ) -> None:
        """Test that with_entry correctly updates total_spent."""
        ledger = ModelCostLedger(**minimal_ledger_data)
        new_ledger = ledger.with_entry(sample_entry)

        assert new_ledger.total_spent == ledger.total_spent + sample_entry.cost

    def test_with_entry_updates_budget_remaining(
        self, minimal_ledger_data: dict, sample_entry: ModelCostEntry
    ) -> None:
        """Test that with_entry correctly updates budget_remaining."""
        ledger = ModelCostLedger(**minimal_ledger_data)
        new_ledger = ledger.with_entry(sample_entry)

        expected_remaining = ledger.budget_total - new_ledger.total_spent
        assert new_ledger.budget_remaining == expected_remaining

    def test_with_entry_appends_to_entries_tuple(
        self, minimal_ledger_data: dict, sample_entry: ModelCostEntry
    ) -> None:
        """Test that with_entry appends the entry to the entries tuple."""
        ledger = ModelCostLedger(**minimal_ledger_data)
        new_ledger = ledger.with_entry(sample_entry)

        assert len(new_ledger.entries) == 1
        assert new_ledger.entries[-1] == sample_entry

    def test_multiple_entries_accumulate(self, minimal_ledger_data: dict) -> None:
        """Test that multiple entries accumulate correctly."""
        ledger = ModelCostLedger(**minimal_ledger_data)
        entry_cost = 0.0045

        # Add three entries with correct cumulative_total values
        for i in range(3):
            cumulative = (i + 1) * entry_cost
            entry = ModelCostEntry(
                timestamp=datetime.now(UTC),
                operation="chat_completion",
                model_used="gpt-4",
                tokens_in=100,
                tokens_out=50,
                cost=entry_cost,
                cumulative_total=cumulative,
            )
            ledger = ledger.with_entry(entry)

        assert len(ledger.entries) == 3
        assert ledger.total_spent == pytest.approx(entry_cost * 3)

    def test_with_entry_preserves_ledger_id(
        self, minimal_ledger_data: dict, sample_entry: ModelCostEntry
    ) -> None:
        """Test that with_entry preserves the ledger_id."""
        ledger = ModelCostLedger(**minimal_ledger_data)
        new_ledger = ledger.with_entry(sample_entry)

        assert new_ledger.ledger_id == ledger.ledger_id

    def test_with_entry_preserves_thresholds(
        self, sample_entry: ModelCostEntry
    ) -> None:
        """Test that with_entry preserves warning and hard thresholds."""
        ledger = ModelCostLedger(
            budget_total=100.0, warning_threshold=0.7, hard_ceiling=0.9
        )
        new_ledger = ledger.with_entry(sample_entry)

        assert new_ledger.warning_threshold == 0.7
        assert new_ledger.hard_ceiling == 0.9

    def test_with_entry_rejects_inconsistent_cumulative_total(
        self, minimal_ledger_data: dict
    ) -> None:
        """Test that with_entry rejects entries with inconsistent cumulative_total."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        # Create entry with wrong cumulative_total (should be 5.0, not 999.0)
        bad_entry = ModelCostEntry(
            timestamp=datetime.now(UTC),
            operation="test",
            model_used="gpt-4",
            tokens_in=100,
            tokens_out=50,
            cost=5.0,
            cumulative_total=999.0,  # Wrong! Should be 5.0
        )

        with pytest.raises(OnexError) as exc_info:
            ledger.with_entry(bad_entry)

        assert "cumulative_total" in str(exc_info.value)
        assert "999.0" in str(exc_info.value)
        assert "5.0" in str(exc_info.value)

    def test_with_entry_rejects_inconsistent_cumulative_total_with_prior_entries(
        self, minimal_ledger_data: dict, sample_entry: ModelCostEntry
    ) -> None:
        """Test validation works correctly after prior entries have been added."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        # Add first entry correctly
        ledger = ledger.with_entry(sample_entry)

        # sample_entry has cost=0.0045, so total_spent is now 0.0045
        # Next entry with cost=1.0 should have cumulative_total = 0.0045 + 1.0 = 1.0045
        bad_entry = ModelCostEntry(
            timestamp=datetime.now(UTC),
            operation="test",
            model_used="gpt-4",
            tokens_in=100,
            tokens_out=50,
            cost=1.0,
            cumulative_total=1.0,  # Wrong! Should be 1.0045
        )

        with pytest.raises(OnexError) as exc_info:
            ledger.with_entry(bad_entry)

        assert "cumulative_total" in str(exc_info.value)

    def test_with_entry_accepts_correct_cumulative_total_within_tolerance(
        self, minimal_ledger_data: dict
    ) -> None:
        """Test that with_entry accepts cumulative_total within float tolerance."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        # Create entry with cumulative_total that differs by less than 1e-9
        entry = ModelCostEntry(
            timestamp=datetime.now(UTC),
            operation="test",
            model_used="gpt-4",
            tokens_in=100,
            tokens_out=50,
            cost=5.0,
            cumulative_total=5.0 + 1e-10,  # Within tolerance
        )

        # Should not raise
        new_ledger = ledger.with_entry(entry)
        assert new_ledger.total_spent == 5.0


# ============================================================================
# Test: Threshold Methods
# ============================================================================


class TestModelCostLedgerThresholds:
    """Tests for is_warning() and is_exceeded() threshold methods."""

    def test_is_warning_false_below_threshold(self) -> None:
        """Test is_warning returns False when below threshold."""
        # 79% spent, warning at 80%
        ledger = ModelCostLedger(
            budget_total=100.0,
            total_spent=79.0,
            budget_remaining=21.0,
            warning_threshold=0.8,
        )
        assert ledger.is_warning() is False

    def test_is_warning_true_at_threshold(self) -> None:
        """Test is_warning returns True when at exactly threshold."""
        # 80% spent, warning at 80%
        ledger = ModelCostLedger(
            budget_total=100.0,
            total_spent=80.0,
            budget_remaining=20.0,
            warning_threshold=0.8,
        )
        assert ledger.is_warning() is True

    def test_is_warning_true_above_threshold(self) -> None:
        """Test is_warning returns True when above threshold."""
        # 85% spent, warning at 80%
        ledger = ModelCostLedger(
            budget_total=100.0,
            total_spent=85.0,
            budget_remaining=15.0,
            warning_threshold=0.8,
        )
        assert ledger.is_warning() is True

    def test_is_exceeded_false_below_ceiling(self) -> None:
        """Test is_exceeded returns False when below ceiling."""
        # 99% spent, ceiling at 100%
        ledger = ModelCostLedger(
            budget_total=100.0,
            total_spent=99.0,
            budget_remaining=1.0,
            hard_ceiling=1.0,
        )
        assert ledger.is_exceeded() is False

    def test_is_exceeded_true_at_ceiling(self) -> None:
        """Test is_exceeded returns True when at exactly ceiling."""
        # 100% spent, ceiling at 100%
        ledger = ModelCostLedger(
            budget_total=100.0,
            total_spent=100.0,
            budget_remaining=0.0,
            hard_ceiling=1.0,
        )
        assert ledger.is_exceeded() is True

    def test_is_exceeded_true_above_ceiling(self) -> None:
        """Test is_exceeded returns True when above ceiling via with_entry."""
        # Start with budget that will be exceeded by adding an entry
        ledger = ModelCostLedger(
            budget_total=100.0,
            total_spent=95.0,
            budget_remaining=5.0,
            hard_ceiling=1.0,
        )
        # Create entry with correct cumulative_total (95.0 + 50.0 = 145.0)
        large_entry = ModelCostEntry(
            timestamp=datetime.now(UTC),
            operation="chat_completion",
            model_used="gpt-4-turbo",
            tokens_in=5000,
            tokens_out=2000,
            cost=50.0,
            cumulative_total=145.0,  # 95.0 prior + 50.0 cost
        )
        # Adding large entry (cost=50.0) should push us well over ceiling
        ledger_exceeded = ledger.with_entry(large_entry)
        assert ledger_exceeded.is_exceeded() is True
        assert ledger_exceeded.total_spent == 145.0  # 95 + 50

    def test_thresholds_with_custom_values(self) -> None:
        """Test thresholds work correctly with custom values."""
        # 70% spent, warning at 75%, ceiling at 90%
        ledger = ModelCostLedger(
            budget_total=100.0,
            total_spent=70.0,
            budget_remaining=30.0,
            warning_threshold=0.75,
            hard_ceiling=0.9,
        )
        assert ledger.is_warning() is False
        assert ledger.is_exceeded() is False

        # 75% spent
        ledger = ModelCostLedger(
            budget_total=100.0,
            total_spent=75.0,
            budget_remaining=25.0,
            warning_threshold=0.75,
            hard_ceiling=0.9,
        )
        assert ledger.is_warning() is True
        assert ledger.is_exceeded() is False

        # 90% spent
        ledger = ModelCostLedger(
            budget_total=100.0,
            total_spent=90.0,
            budget_remaining=10.0,
            warning_threshold=0.75,
            hard_ceiling=0.9,
        )
        assert ledger.is_warning() is True
        assert ledger.is_exceeded() is True

    def test_thresholds_with_zero_total_spent(self, minimal_ledger_data: dict) -> None:
        """Test thresholds return False when nothing spent."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        assert ledger.is_warning() is False
        assert ledger.is_exceeded() is False


# ============================================================================
# Test: Utility Properties
# ============================================================================


class TestModelCostLedgerUtilityProperties:
    """Tests for utility properties like budget_utilization_pct."""

    def test_budget_utilization_pct(self) -> None:
        """Test budget_utilization_pct returns percentage value."""
        ledger = ModelCostLedger(
            budget_total=100.0,
            total_spent=75.0,
            budget_remaining=25.0,
        )
        assert ledger.budget_utilization_pct == 75.0

    def test_budget_utilization_pct_zero_spent(self) -> None:
        """Test budget_utilization_pct with zero spending."""
        ledger = ModelCostLedger(budget_total=100.0)
        assert ledger.budget_utilization_pct == 0.0

    def test_budget_utilization_pct_overspent(self) -> None:
        """Test budget_utilization_pct can exceed 100 when overspent."""
        ledger = ModelCostLedger(
            budget_total=100.0,
            total_spent=150.0,
            budget_remaining=-50.0,
        )
        assert ledger.budget_utilization_pct == 150.0

    def test_budget_utilization_pct_matches_fraction(self) -> None:
        """Test budget_utilization_pct is exactly 100x budget_utilization."""
        ledger = ModelCostLedger(
            budget_total=100.0,
            total_spent=33.33,
            budget_remaining=66.67,
        )
        assert ledger.budget_utilization_pct == ledger.budget_utilization * 100


# ============================================================================
# Test: Escalation Methods
# ============================================================================


class TestModelCostLedgerEscalation:
    """Tests for with_escalation() budget increase method."""

    def test_with_escalation_returns_new_instance(
        self, minimal_ledger_data: dict
    ) -> None:
        """Test that with_escalation returns a new ledger instance."""
        ledger = ModelCostLedger(**minimal_ledger_data)
        new_ledger = ledger.with_escalation(50.0, "Need more budget")

        assert new_ledger is not ledger
        assert isinstance(new_ledger, ModelCostLedger)

    def test_with_escalation_increases_budget(self, minimal_ledger_data: dict) -> None:
        """Test that with_escalation increases budget_total."""
        ledger = ModelCostLedger(**minimal_ledger_data)  # budget_total=100.0
        new_ledger = ledger.with_escalation(50.0, "Need more budget")

        assert new_ledger.budget_total == 150.0

    def test_with_escalation_updates_remaining(self, minimal_ledger_data: dict) -> None:
        """Test that with_escalation updates budget_remaining."""
        ledger = ModelCostLedger(
            budget_total=100.0, total_spent=80.0, budget_remaining=20.0
        )
        new_ledger = ledger.with_escalation(50.0, "Need more budget")

        # budget_remaining should be new budget_total - total_spent
        assert new_ledger.budget_remaining == 150.0 - 80.0
        assert new_ledger.budget_remaining == 70.0

    def test_with_escalation_tracks_count(self, minimal_ledger_data: dict) -> None:
        """Test that with_escalation increments escalation_count."""
        ledger = ModelCostLedger(**minimal_ledger_data)
        assert ledger.escalation_count == 0

        new_ledger = ledger.with_escalation(50.0, "First escalation")
        assert new_ledger.escalation_count == 1

    def test_with_escalation_stores_reason(self, minimal_ledger_data: dict) -> None:
        """Test that with_escalation stores the reason."""
        ledger = ModelCostLedger(**minimal_ledger_data)
        new_ledger = ledger.with_escalation(50.0, "High priority task")

        assert new_ledger.last_escalation_reason == "High priority task"

    def test_multiple_escalations_accumulate(self, minimal_ledger_data: dict) -> None:
        """Test that multiple escalations accumulate correctly."""
        ledger = ModelCostLedger(**minimal_ledger_data)  # budget_total=100.0

        ledger = ledger.with_escalation(25.0, "First escalation")
        assert ledger.budget_total == 125.0
        assert ledger.escalation_count == 1

        ledger = ledger.with_escalation(25.0, "Second escalation")
        assert ledger.budget_total == 150.0
        assert ledger.escalation_count == 2

        ledger = ledger.with_escalation(50.0, "Third escalation")
        assert ledger.budget_total == 200.0
        assert ledger.escalation_count == 3
        assert ledger.last_escalation_reason == "Third escalation"

    def test_with_escalation_preserves_ledger_id(
        self, minimal_ledger_data: dict
    ) -> None:
        """Test that with_escalation preserves the ledger_id."""
        ledger = ModelCostLedger(**minimal_ledger_data)
        new_ledger = ledger.with_escalation(50.0, "Test")

        assert new_ledger.ledger_id == ledger.ledger_id

    def test_with_escalation_preserves_entries(
        self, minimal_ledger_data: dict, sample_entry: ModelCostEntry
    ) -> None:
        """Test that with_escalation preserves existing entries."""
        ledger = ModelCostLedger(**minimal_ledger_data)
        ledger = ledger.with_entry(sample_entry)

        new_ledger = ledger.with_escalation(50.0, "Test")

        assert new_ledger.entries == ledger.entries
        assert len(new_ledger.entries) == 1

    def test_with_escalation_preserves_total_spent(
        self, minimal_ledger_data: dict, sample_entry: ModelCostEntry
    ) -> None:
        """Test that with_escalation preserves total_spent."""
        ledger = ModelCostLedger(**minimal_ledger_data)
        ledger = ledger.with_entry(sample_entry)
        original_spent = ledger.total_spent

        new_ledger = ledger.with_escalation(50.0, "Test")

        assert new_ledger.total_spent == original_spent

    def test_with_escalation_rejects_zero_budget(
        self, minimal_ledger_data: dict
    ) -> None:
        """Test that with_escalation rejects zero additional_budget."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        with pytest.raises(OnexError) as exc_info:
            ledger.with_escalation(0.0, "Valid reason")

        assert "additional_budget must be positive" in str(exc_info.value)

    def test_with_escalation_rejects_negative_budget(
        self, minimal_ledger_data: dict
    ) -> None:
        """Test that with_escalation rejects negative additional_budget."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        with pytest.raises(OnexError) as exc_info:
            ledger.with_escalation(-50.0, "Valid reason")

        assert "additional_budget must be positive" in str(exc_info.value)

    def test_with_escalation_rejects_empty_reason(
        self, minimal_ledger_data: dict
    ) -> None:
        """Test that with_escalation rejects empty reason string."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        with pytest.raises(OnexError) as exc_info:
            ledger.with_escalation(50.0, "")

        assert "reason cannot be empty" in str(exc_info.value)

    def test_with_escalation_rejects_whitespace_reason(
        self, minimal_ledger_data: dict
    ) -> None:
        """Test that with_escalation rejects whitespace-only reason."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        with pytest.raises(OnexError) as exc_info:
            ledger.with_escalation(50.0, "   ")

        assert "reason cannot be empty" in str(exc_info.value)

    def test_with_escalation_rejects_very_small_negative_budget(
        self, minimal_ledger_data: dict
    ) -> None:
        """Test that with_escalation rejects small negative additional_budget."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        with pytest.raises(OnexError) as exc_info:
            ledger.with_escalation(-0.0001, "Valid reason")

        assert "additional_budget must be positive" in str(exc_info.value)

    def test_with_escalation_accepts_very_small_positive_budget(
        self, minimal_ledger_data: dict
    ) -> None:
        """Test that with_escalation accepts very small positive additional_budget."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        new_ledger = ledger.with_escalation(0.0001, "Small increase")

        assert new_ledger.budget_total == pytest.approx(100.0001)
        assert new_ledger.escalation_count == 1

    def test_with_escalation_rejects_tabs_only_reason(
        self, minimal_ledger_data: dict
    ) -> None:
        """Test that with_escalation rejects tab-only reason string."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        with pytest.raises(OnexError) as exc_info:
            ledger.with_escalation(50.0, "\t\t\t")

        assert "reason cannot be empty" in str(exc_info.value)

    def test_with_escalation_rejects_newlines_only_reason(
        self, minimal_ledger_data: dict
    ) -> None:
        """Test that with_escalation rejects newline-only reason string."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        with pytest.raises(OnexError) as exc_info:
            ledger.with_escalation(50.0, "\n\n")

        assert "reason cannot be empty" in str(exc_info.value)

    def test_with_escalation_accepts_reason_with_leading_trailing_whitespace(
        self, minimal_ledger_data: dict
    ) -> None:
        """Test that with_escalation accepts reason with leading/trailing whitespace."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        # Note: The reason has content, just with whitespace around it
        new_ledger = ledger.with_escalation(50.0, "  Valid reason with spaces  ")

        assert new_ledger.escalation_count == 1
        assert new_ledger.last_escalation_reason == "  Valid reason with spaces  "

    def test_with_escalation_accepts_very_large_budget(
        self, minimal_ledger_data: dict
    ) -> None:
        """Test that with_escalation accepts very large additional_budget."""
        ledger = ModelCostLedger(**minimal_ledger_data)

        new_ledger = ledger.with_escalation(999999999.99, "Large budget increase")

        assert new_ledger.budget_total == pytest.approx(1000000099.99)
        assert new_ledger.escalation_count == 1


# ============================================================================
# Test: Serialization
# ============================================================================


class TestModelCostLedgerSerialization:
    """Tests for serialization and deserialization."""

    def test_model_dump(self, minimal_ledger_data: dict) -> None:
        """Test serialization to dictionary."""
        ledger = ModelCostLedger(**minimal_ledger_data)
        data = ledger.model_dump()

        assert "ledger_id" in data
        assert "budget_total" in data
        assert "budget_remaining" in data
        assert "entries" in data
        assert "total_spent" in data
        assert data["budget_total"] == 100.0

    def test_model_dump_json(self, minimal_ledger_data: dict) -> None:
        """Test serialization to JSON string."""
        ledger = ModelCostLedger(**minimal_ledger_data)
        json_str = ledger.model_dump_json()

        assert isinstance(json_str, str)
        assert "budget_total" in json_str
        assert "100.0" in json_str or "100" in json_str

    def test_round_trip_serialization(self, full_ledger_data: dict) -> None:
        """Test that model survives serialization round-trip."""
        original = ModelCostLedger(**full_ledger_data)
        data = original.model_dump()
        restored = ModelCostLedger(**data)

        assert original.ledger_id == restored.ledger_id
        assert original.budget_total == restored.budget_total
        assert original.total_spent == restored.total_spent
        assert original.escalation_count == restored.escalation_count

    def test_json_round_trip_serialization(self, minimal_ledger_data: dict) -> None:
        """Test JSON serialization and deserialization roundtrip."""
        original = ModelCostLedger(**minimal_ledger_data)

        json_str = original.model_dump_json()
        restored = ModelCostLedger.model_validate_json(json_str)

        assert original.ledger_id == restored.ledger_id
        assert original.budget_total == restored.budget_total
        assert original.budget_remaining == restored.budget_remaining
        assert original.warning_threshold == restored.warning_threshold

    def test_model_dump_contains_all_fields(self, full_ledger_data: dict) -> None:
        """Test model_dump contains all expected fields."""
        ledger = ModelCostLedger(**full_ledger_data)
        data = ledger.model_dump()

        expected_fields = [
            "ledger_id",
            "budget_total",
            "budget_remaining",
            "entries",
            "total_spent",
            "escalation_count",
            "last_escalation_reason",
            "warning_threshold",
            "hard_ceiling",
        ]
        for field in expected_fields:
            assert field in data

    def test_model_validate_from_dict(self, minimal_ledger_data: dict) -> None:
        """Test model validation from dictionary."""
        ledger = ModelCostLedger.model_validate(minimal_ledger_data)

        assert ledger.budget_total == minimal_ledger_data["budget_total"]


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestModelCostLedgerEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_zero_budget_remaining(self) -> None:
        """Test ledger with fully spent budget."""
        ledger = ModelCostLedger(
            budget_total=100.0, total_spent=100.0, budget_remaining=0.0
        )

        assert ledger.budget_remaining == 0.0
        assert ledger.is_exceeded() is True

    def test_negative_budget_remaining_after_overspend(self) -> None:
        """Test ledger can have negative budget_remaining via with_entry (overspent)."""
        # Start with budget near limit
        ledger = ModelCostLedger(
            budget_total=100.0, total_spent=95.0, budget_remaining=5.0
        )

        # Create entry with correct cumulative_total (95.0 + 50.0 = 145.0)
        large_entry = ModelCostEntry(
            timestamp=datetime.now(UTC),
            operation="chat_completion",
            model_used="gpt-4-turbo",
            tokens_in=5000,
            tokens_out=2000,
            cost=50.0,
            cumulative_total=145.0,  # 95.0 prior + 50.0 cost
        )

        # Add an entry that costs more than remaining budget (cost=50.0)
        ledger_overspent = ledger.with_entry(large_entry)

        # budget_remaining becomes negative through with_entry (100 - 145 = -45)
        assert ledger_overspent.budget_remaining == -45.0
        assert ledger_overspent.is_exceeded() is True

    def test_hash_consistency(self, minimal_ledger_data: dict) -> None:
        """Test that frozen model is hashable and consistent."""
        ledger_id = uuid4()
        minimal_ledger_data["ledger_id"] = ledger_id

        ledger1 = ModelCostLedger(**minimal_ledger_data)
        ledger2 = ModelCostLedger(**minimal_ledger_data)

        # Frozen models should be hashable
        assert hash(ledger1) == hash(ledger2)

    def test_can_use_as_dict_key(self, minimal_ledger_data: dict) -> None:
        """Test that frozen model can be used as dictionary key."""
        ledger_id = uuid4()
        minimal_ledger_data["ledger_id"] = ledger_id

        ledger = ModelCostLedger(**minimal_ledger_data)

        # Should be usable as dict key
        test_dict = {ledger: "value"}
        assert test_dict[ledger] == "value"

    def test_str_representation(self, minimal_ledger_data: dict) -> None:
        """Test __str__ method returns string."""
        ledger = ModelCostLedger(**minimal_ledger_data)
        str_repr = str(ledger)

        assert isinstance(str_repr, str)
        # Should contain some meaningful info
        assert "100" in str_repr or "ModelCostLedger" in str_repr

    def test_repr_representation(self, minimal_ledger_data: dict) -> None:
        """Test __repr__ method returns string with class name."""
        ledger = ModelCostLedger(**minimal_ledger_data)
        repr_str = repr(ledger)

        assert isinstance(repr_str, str)
        assert "ModelCostLedger" in repr_str

    def test_can_add_to_set(self, minimal_ledger_data: dict) -> None:
        """Test that frozen model can be added to set."""
        ledger_id = uuid4()
        minimal_ledger_data["ledger_id"] = ledger_id

        ledger1 = ModelCostLedger(**minimal_ledger_data)
        ledger2 = ModelCostLedger(**minimal_ledger_data)

        # Should be usable in sets
        test_set = {ledger1, ledger2}
        assert len(test_set) == 1  # Same ledger_id, same hash

    def test_model_equality(self, minimal_ledger_data: dict) -> None:
        """Test model equality comparison with same ledger_id."""
        ledger_id = uuid4()
        minimal_ledger_data["ledger_id"] = ledger_id

        ledger1 = ModelCostLedger(**minimal_ledger_data)
        ledger2 = ModelCostLedger(**minimal_ledger_data)

        assert ledger1 == ledger2

    def test_model_inequality_different_ledger_id(
        self, minimal_ledger_data: dict
    ) -> None:
        """Test model inequality when ledger_ids differ."""
        ledger1 = ModelCostLedger(**minimal_ledger_data)
        ledger2 = ModelCostLedger(**minimal_ledger_data)

        # Different auto-generated ledger_ids
        assert ledger1 != ledger2

    def test_very_small_budget_value(self) -> None:
        """Test handling of very small budget values."""
        ledger = ModelCostLedger(budget_total=0.00001)

        assert ledger.budget_total == 0.00001

    def test_very_large_budget_value(self) -> None:
        """Test handling of very large budget values."""
        ledger = ModelCostLedger(budget_total=999999999.99)

        assert ledger.budget_total == 999999999.99

    def test_float_precision_budget_total(self) -> None:
        """Test float precision for budget_total field."""
        ledger = ModelCostLedger(budget_total=123.456789)

        assert ledger.budget_total == 123.456789

    def test_entries_tuple_immutability(
        self, minimal_ledger_data: dict, sample_entry: ModelCostEntry
    ) -> None:
        """Test that entries tuple is truly immutable."""
        ledger = ModelCostLedger(**minimal_ledger_data)
        ledger = ledger.with_entry(sample_entry)

        # Tuple should be immutable
        with pytest.raises((TypeError, AttributeError)):
            # NOTE: Intentionally testing tuple immutability - mypy correctly flags item assignment to immutable sequence
            ledger.entries[0] = sample_entry  # type: ignore[index]


# ============================================================================
# Test: Integration Scenarios
# ============================================================================


class TestModelCostLedgerIntegration:
    """Integration tests for realistic usage scenarios."""

    def test_full_budget_lifecycle(self, sample_entry: ModelCostEntry) -> None:
        """Test a complete budget lifecycle from creation to escalation."""
        # Create ledger
        ledger = ModelCostLedger(budget_total=1.0, warning_threshold=0.8)
        assert ledger.is_warning() is False
        assert ledger.is_exceeded() is False

        # Add entries until warning threshold
        for _ in range(50):
            entry = ModelCostEntry(
                timestamp=datetime.now(UTC),
                operation="completion",
                model_used="gpt-4",
                tokens_in=10,
                tokens_out=10,
                cost=0.015,  # Each entry costs 0.015
                cumulative_total=ledger.total_spent + 0.015,
            )
            ledger = ledger.with_entry(entry)

        # Should be at warning level (50 * 0.015 = 0.75, which is < 0.8)
        assert ledger.total_spent == pytest.approx(0.75)
        assert ledger.is_warning() is False

        # Add more to exceed warning
        for _ in range(5):
            entry = ModelCostEntry(
                timestamp=datetime.now(UTC),
                operation="completion",
                model_used="gpt-4",
                tokens_in=10,
                tokens_out=10,
                cost=0.015,
                cumulative_total=ledger.total_spent + 0.015,
            )
            ledger = ledger.with_entry(entry)

        # Now at warning (55 * 0.015 = 0.825 > 0.8)
        assert ledger.is_warning() is True
        assert ledger.is_exceeded() is False

        # Escalate budget
        ledger = ledger.with_escalation(1.0, "Need more budget for project")
        assert ledger.budget_total == 2.0
        assert ledger.escalation_count == 1
        assert ledger.is_warning() is False  # Now below 80% of new budget

    def test_budget_tracking_accuracy(self) -> None:
        """Test that budget tracking maintains accuracy across many entries."""
        ledger = ModelCostLedger(budget_total=100.0)

        total_cost = 0.0
        for i in range(100):
            cost = 0.1 + (i * 0.001)  # Varying costs
            total_cost += cost
            entry = ModelCostEntry(
                timestamp=datetime.now(UTC),
                operation=f"operation_{i}",
                model_used="gpt-4",
                tokens_in=100,
                tokens_out=50,
                cost=cost,
                cumulative_total=total_cost,
            )
            ledger = ledger.with_entry(entry)

        assert len(ledger.entries) == 100
        assert ledger.total_spent == pytest.approx(total_cost)
        assert ledger.budget_remaining == pytest.approx(100.0 - total_cost)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
