# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from omnibase_core.enums.enum_plan_structure_type import EnumPlanStructureType
from omnibase_core.enums.plan import EnumPlanAction, EnumPlanPhase
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.plan import (
    ModelPlanContract,
    ModelPlanDocument,
    ModelPlanEntry,
    ModelPlanReviewResult,
    ModelPlanTicketLink,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entries(n: int) -> list[ModelPlanEntry]:
    return [
        ModelPlanEntry(
            id=f"P{i}",
            title=f"Task {i}: Item {i}",
            content=f"Content for task {i}.",
        )
        for i in range(1, n + 1)
    ]


def _make_document(n: int = 2) -> ModelPlanDocument:
    return ModelPlanDocument(
        title="Test Plan",
        structure_type=EnumPlanStructureType.TASK_SECTIONS,
        entries=_make_entries(n),
    )


def _make_review(
    contract: ModelPlanContract, *, passed: bool = True
) -> ModelPlanReviewResult:
    return ModelPlanReviewResult(
        reviewer="test-agent",
        passed=passed,
        findings=[] if passed else ["issue found"],
        document_fingerprint=contract.document_fingerprint(),
    )


def _make_link(entry_id: str, ticket_id: str = "OMN-100") -> ModelPlanTicketLink:
    return ModelPlanTicketLink(entry_id=entry_id, ticket_id=ticket_id)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def basic_document() -> ModelPlanDocument:
    """2-entry ModelPlanDocument (P1, P2) with TASK_SECTIONS structure."""
    return _make_document(2)


@pytest.fixture
def basic_contract(basic_document: ModelPlanDocument) -> ModelPlanContract:
    """ModelPlanContract wrapping basic_document in DRAFT phase."""
    return ModelPlanContract(plan_id="PLAN-TEST-1", document=basic_document)


@pytest.fixture
def reviewed_contract(basic_document: ModelPlanDocument) -> ModelPlanContract:
    """Contract with a passing review matching current document, in REVIEWED phase."""
    c = ModelPlanContract(plan_id="PLAN-TEST-2", document=basic_document)
    review = _make_review(c, passed=True)
    c.add_review(review)
    c.transition_to(EnumPlanPhase.REVIEWED)
    return c


@pytest.fixture
def fully_linked_contract(reviewed_contract: ModelPlanContract) -> ModelPlanContract:
    """All entries linked to tickets, in TICKETED phase."""
    c = reviewed_contract
    c.add_ticket_link(_make_link("P1", "OMN-100"))
    c.add_ticket_link(_make_link("P2", "OMN-101"))
    c.transition_to(EnumPlanPhase.TICKETED)
    return c


# ---------------------------------------------------------------------------
# Phase transitions (10 tests)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPhaseTransitions:
    def test_draft_to_reviewed_succeeds_with_passing_review(
        self, basic_contract: ModelPlanContract
    ) -> None:
        review = _make_review(basic_contract, passed=True)
        basic_contract.add_review(review)
        basic_contract.transition_to(EnumPlanPhase.REVIEWED)
        assert basic_contract.phase == EnumPlanPhase.REVIEWED

    def test_draft_to_reviewed_fails_without_review(
        self, basic_contract: ModelPlanContract
    ) -> None:
        with pytest.raises(ModelOnexError):
            basic_contract.transition_to(EnumPlanPhase.REVIEWED)

    def test_draft_to_reviewed_fails_with_stale_fingerprint(
        self, basic_contract: ModelPlanContract
    ) -> None:
        review = ModelPlanReviewResult(
            reviewer="test-agent",
            passed=True,
            findings=[],
            document_fingerprint="deadbeefdeadbeef",
        )
        # Force-append review bypassing add_review() fingerprint check
        basic_contract.reviews.append(review)
        with pytest.raises(ModelOnexError):
            basic_contract.transition_to(EnumPlanPhase.REVIEWED)

    def test_reviewed_to_draft_always_succeeds(
        self, reviewed_contract: ModelPlanContract
    ) -> None:
        reviewed_contract.transition_to(EnumPlanPhase.DRAFT)
        assert reviewed_contract.phase == EnumPlanPhase.DRAFT

    def test_reviewed_to_ticketed_fails_when_not_fully_ticketed(
        self, reviewed_contract: ModelPlanContract
    ) -> None:
        with pytest.raises(ModelOnexError):
            reviewed_contract.transition_to(EnumPlanPhase.TICKETED)

    def test_reviewed_to_ticketed_succeeds_when_fully_ticketed(
        self, reviewed_contract: ModelPlanContract
    ) -> None:
        reviewed_contract.add_ticket_link(_make_link("P1", "OMN-100"))
        reviewed_contract.add_ticket_link(_make_link("P2", "OMN-101"))
        reviewed_contract.transition_to(EnumPlanPhase.TICKETED)
        assert reviewed_contract.phase == EnumPlanPhase.TICKETED

    def test_executing_to_closed_succeeds_with_lifecycle_complete(
        self, fully_linked_contract: ModelPlanContract
    ) -> None:
        fully_linked_contract.transition_to(EnumPlanPhase.EXECUTING)
        fully_linked_contract.transition_to(EnumPlanPhase.CLOSED)
        assert fully_linked_contract.phase == EnumPlanPhase.CLOSED

    def test_executing_to_closed_fails_without_review_tickets(
        self, basic_document: ModelPlanDocument
    ) -> None:
        c = ModelPlanContract(plan_id="PLAN-X", document=basic_document)
        # Force phase to EXECUTING without going through normal transitions
        c.phase = EnumPlanPhase.EXECUTING
        with pytest.raises(ModelOnexError):
            c.transition_to(EnumPlanPhase.CLOSED)

    def test_transition_from_closed_raises(
        self, fully_linked_contract: ModelPlanContract
    ) -> None:
        fully_linked_contract.transition_to(EnumPlanPhase.EXECUTING)
        fully_linked_contract.transition_to(EnumPlanPhase.CLOSED)
        with pytest.raises(ModelOnexError):
            fully_linked_contract.transition_to(EnumPlanPhase.DRAFT)

    def test_invalid_transition_draft_to_ticketed(
        self, basic_contract: ModelPlanContract
    ) -> None:
        with pytest.raises(ModelOnexError):
            basic_contract.transition_to(EnumPlanPhase.TICKETED)


# ---------------------------------------------------------------------------
# Action enforcement (4 tests)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestActionEnforcement:
    def test_allowed_action_succeeds_disallowed_raises(
        self, basic_contract: ModelPlanContract
    ) -> None:
        # EDIT_PLAN is allowed in DRAFT
        basic_contract.assert_action_allowed(EnumPlanAction.EDIT_PLAN)
        # LINK_TICKET is NOT allowed in DRAFT
        with pytest.raises(ModelOnexError):
            basic_contract.assert_action_allowed(EnumPlanAction.LINK_TICKET)

    def test_string_input_normalized_to_enum(
        self, basic_contract: ModelPlanContract
    ) -> None:
        # String "edit_plan" should work in DRAFT
        basic_contract.assert_action_allowed("edit_plan")

    def test_invalid_string_raises(self, basic_contract: ModelPlanContract) -> None:
        with pytest.raises(ModelOnexError):
            basic_contract.assert_action_allowed("not_a_real_action")

    def test_wrong_type_raises(self, basic_contract: ModelPlanContract) -> None:
        with pytest.raises(ModelOnexError):
            basic_contract.assert_action_allowed(42)  # type: ignore[arg-type]
        with pytest.raises(ModelOnexError):
            basic_contract.assert_action_allowed(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Review governance (8 tests)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReviewGovernance:
    def test_is_review_complete_true_with_passing_current(
        self, basic_contract: ModelPlanContract
    ) -> None:
        review = _make_review(basic_contract, passed=True)
        basic_contract.add_review(review)
        assert basic_contract.is_review_complete() is True

    def test_is_review_complete_false_no_reviews(
        self, basic_contract: ModelPlanContract
    ) -> None:
        assert basic_contract.is_review_complete() is False

    def test_is_review_complete_false_only_failing(
        self, basic_contract: ModelPlanContract
    ) -> None:
        review = _make_review(basic_contract, passed=False)
        basic_contract.add_review(review)
        assert basic_contract.is_review_complete() is False

    def test_is_review_complete_false_stale_fingerprint(
        self, basic_contract: ModelPlanContract
    ) -> None:
        # Add passing review for current doc
        review = _make_review(basic_contract, passed=True)
        basic_contract.add_review(review)
        assert basic_contract.is_review_complete() is True
        # Replace document -- review becomes stale
        new_doc = ModelPlanDocument(
            title="Revised Plan",
            structure_type=EnumPlanStructureType.TASK_SECTIONS,
            entries=_make_entries(2),
            goal="New goal",
        )
        basic_contract.replace_document(new_doc)
        assert basic_contract.is_review_complete() is False

    def test_add_review_succeeds_in_draft(
        self, basic_contract: ModelPlanContract
    ) -> None:
        review = _make_review(basic_contract, passed=True)
        basic_contract.add_review(review)
        assert len(basic_contract.reviews) == 1

    def test_add_review_succeeds_in_reviewed(
        self, reviewed_contract: ModelPlanContract
    ) -> None:
        review = _make_review(reviewed_contract, passed=True)
        reviewed_contract.add_review(review)
        assert len(reviewed_contract.reviews) >= 2

    def test_add_review_rejected_in_ticketed(
        self, fully_linked_contract: ModelPlanContract
    ) -> None:
        review = _make_review(fully_linked_contract, passed=True)
        with pytest.raises(ModelOnexError):
            fully_linked_contract.add_review(review)

    def test_add_review_rejected_fingerprint_mismatch(
        self, basic_contract: ModelPlanContract
    ) -> None:
        bad_review = ModelPlanReviewResult(
            reviewer="test-agent",
            passed=True,
            findings=[],
            document_fingerprint="deadbeefdeadbeef",
        )
        with pytest.raises(ModelOnexError):
            basic_contract.add_review(bad_review)


# ---------------------------------------------------------------------------
# Ticket link governance (5 tests)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTicketLinkGovernance:
    def test_add_ticket_link_succeeds_for_valid_entry(
        self, reviewed_contract: ModelPlanContract
    ) -> None:
        reviewed_contract.add_ticket_link(_make_link("P1", "OMN-200"))
        assert len(reviewed_contract.ticket_links) == 1

    def test_add_ticket_link_rejected_orphan_entry(
        self, reviewed_contract: ModelPlanContract
    ) -> None:
        with pytest.raises(ModelOnexError):
            reviewed_contract.add_ticket_link(_make_link("P99", "OMN-200"))

    def test_add_ticket_link_rejected_duplicate_entry(
        self, reviewed_contract: ModelPlanContract
    ) -> None:
        reviewed_contract.add_ticket_link(_make_link("P1", "OMN-200"))
        with pytest.raises(ModelOnexError):
            reviewed_contract.add_ticket_link(_make_link("P1", "OMN-201"))

    def test_is_fully_ticketed(self, reviewed_contract: ModelPlanContract) -> None:
        assert reviewed_contract.is_fully_ticketed() is False
        reviewed_contract.add_ticket_link(_make_link("P1", "OMN-200"))
        assert reviewed_contract.is_fully_ticketed() is False
        reviewed_contract.add_ticket_link(_make_link("P2", "OMN-201"))
        assert reviewed_contract.is_fully_ticketed() is True

    def test_link_for_entry_returns_correct_or_none(
        self, reviewed_contract: ModelPlanContract
    ) -> None:
        assert reviewed_contract.link_for_entry("P1") is None
        link = _make_link("P1", "OMN-300")
        reviewed_contract.add_ticket_link(link)
        result = reviewed_contract.link_for_entry("P1")
        assert result is not None
        assert result.ticket_id == "OMN-300"
        assert reviewed_contract.link_for_entry("P2") is None


# ---------------------------------------------------------------------------
# Document replacement (5 tests)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDocumentReplacement:
    def test_replace_document_succeeds_no_conflicting_links(
        self, basic_contract: ModelPlanContract
    ) -> None:
        new_doc = _make_document(3)
        basic_contract.replace_document(new_doc)
        assert len(basic_contract.document.entries) == 3

    def test_replace_document_fails_when_link_references_removed_entry(
        self, reviewed_contract: ModelPlanContract
    ) -> None:
        reviewed_contract.add_ticket_link(_make_link("P1", "OMN-100"))
        # New doc only has P3 -- P1 link is orphaned
        new_doc = ModelPlanDocument(
            title="New",
            structure_type=EnumPlanStructureType.TASK_SECTIONS,
            entries=[ModelPlanEntry(id="P3", title="Task 3", content="C.")],
        )
        with pytest.raises(ModelOnexError):
            reviewed_contract.replace_document(new_doc)

    def test_replace_document_from_reviewed_demotes_to_draft(
        self, reviewed_contract: ModelPlanContract
    ) -> None:
        assert reviewed_contract.phase == EnumPlanPhase.REVIEWED
        new_doc = _make_document(2)
        reviewed_contract.replace_document(new_doc)
        assert reviewed_contract.phase == EnumPlanPhase.DRAFT

    def test_replace_document_from_draft_preserves_draft(
        self, basic_contract: ModelPlanContract
    ) -> None:
        assert basic_contract.phase == EnumPlanPhase.DRAFT
        new_doc = _make_document(2)
        basic_contract.replace_document(new_doc)
        assert basic_contract.phase == EnumPlanPhase.DRAFT

    def test_replace_document_rejected_in_closed(
        self, fully_linked_contract: ModelPlanContract
    ) -> None:
        fully_linked_contract.transition_to(EnumPlanPhase.EXECUTING)
        fully_linked_contract.transition_to(EnumPlanPhase.CLOSED)
        with pytest.raises(ModelOnexError):
            fully_linked_contract.replace_document(_make_document(2))


# ---------------------------------------------------------------------------
# Fingerprinting (5 tests)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFingerprinting:
    def test_compute_fingerprint_returns_16_char_hex(
        self, basic_contract: ModelPlanContract
    ) -> None:
        fp = basic_contract.compute_fingerprint()
        assert len(fp) == 16
        assert all(c in "0123456789abcdef" for c in fp)

    def test_fingerprint_changes_on_phase_mutation(
        self, basic_contract: ModelPlanContract
    ) -> None:
        fp_draft = basic_contract.compute_fingerprint()
        review = _make_review(basic_contract, passed=True)
        basic_contract.add_review(review)
        basic_contract.transition_to(EnumPlanPhase.REVIEWED)
        fp_reviewed = basic_contract.compute_fingerprint()
        assert fp_draft != fp_reviewed

    def test_fingerprint_excludes_timestamps_and_self(
        self, basic_document: ModelPlanDocument
    ) -> None:
        t1 = datetime(2020, 1, 1, tzinfo=UTC)
        t2 = datetime(2025, 6, 15, tzinfo=UTC)
        c1 = ModelPlanContract(
            plan_id="PLAN-FP", document=basic_document, created_at=t1, updated_at=t1
        )
        c2 = ModelPlanContract(
            plan_id="PLAN-FP", document=basic_document, created_at=t2, updated_at=t2
        )
        assert c1.compute_fingerprint() == c2.compute_fingerprint()

    def test_fingerprint_is_deterministic(
        self, basic_document: ModelPlanDocument
    ) -> None:
        c = ModelPlanContract(plan_id="PLAN-DET", document=basic_document)
        assert c.compute_fingerprint() == c.compute_fingerprint()

    def test_document_fingerprint_returns_16_char_hex(
        self, basic_contract: ModelPlanContract
    ) -> None:
        fp = basic_contract.document_fingerprint()
        assert len(fp) == 16
        assert all(c in "0123456789abcdef" for c in fp)


# ---------------------------------------------------------------------------
# YAML round-trip (5 tests)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestYamlRoundTrip:
    def test_round_trip_preserves_all_fields(
        self, reviewed_contract: ModelPlanContract
    ) -> None:
        yaml_str = reviewed_contract.to_yaml()
        restored = ModelPlanContract.from_yaml(yaml_str)
        assert restored.plan_id == reviewed_contract.plan_id
        assert restored.phase == reviewed_contract.phase
        assert len(restored.reviews) == len(reviewed_contract.reviews)
        assert restored.document.title == reviewed_contract.document.title
        assert len(restored.document.entries) == len(reviewed_contract.document.entries)

    def test_extra_fields_survive_round_trip(
        self, basic_contract: ModelPlanContract
    ) -> None:
        # Set extra field via Pydantic's __pydantic_extra__ (extra="allow")
        if basic_contract.__pydantic_extra__ is None:
            basic_contract.__pydantic_extra__ = {}
        basic_contract.__pydantic_extra__["custom_plugin_field"] = "hello"
        yaml_str = basic_contract.to_yaml()
        assert "custom_plugin_field" in yaml_str
        restored = ModelPlanContract.from_yaml(yaml_str)
        # extra="allow" means extra fields are preserved
        assert getattr(restored, "custom_plugin_field", None) == "hello"

    def test_invalid_yaml_syntax_raises_parse_error(self) -> None:
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPlanContract.from_yaml(":\n  invalid: [yaml\n  broken")
        assert "CONFIGURATION_PARSE_ERROR" in str(exc_info.value.error_code)

    def test_valid_yaml_invalid_schema_raises_validation_error(self) -> None:
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPlanContract.from_yaml("plan_id: 123\nphase: invalid\n")
        assert "VALIDATION_ERROR" in str(exc_info.value.error_code)

    def test_valid_yaml_orphan_ticket_link_raises_validation_error(
        self, basic_contract: ModelPlanContract
    ) -> None:
        # Build valid YAML but with a ticket_link referencing non-existent entry
        yaml_str = basic_contract.to_yaml()
        # Inject an orphan ticket link
        import yaml as _yaml

        data = _yaml.safe_load(yaml_str)
        data["ticket_links"] = [
            {
                "entry_id": "P99",
                "ticket_id": "OMN-999",
                "created_at": "2026-01-01T00:00:00+00:00",
            }
        ]
        patched_yaml = _yaml.dump(data, default_flow_style=False)
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPlanContract.from_yaml(patched_yaml)
        assert "VALIDATION_ERROR" in str(exc_info.value.error_code)


# ---------------------------------------------------------------------------
# is_done() semantics (3 tests)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsDone:
    def test_true_when_closed_review_complete_fully_ticketed(
        self, fully_linked_contract: ModelPlanContract
    ) -> None:
        fully_linked_contract.transition_to(EnumPlanPhase.EXECUTING)
        fully_linked_contract.transition_to(EnumPlanPhase.CLOSED)
        assert fully_linked_contract.is_done() is True

    def test_false_when_closed_but_review_stale(
        self, fully_linked_contract: ModelPlanContract
    ) -> None:
        fully_linked_contract.transition_to(EnumPlanPhase.EXECUTING)
        fully_linked_contract.transition_to(EnumPlanPhase.CLOSED)
        # Directly mutate the document to make reviews stale
        # (simulates a bug or direct field mutation)
        new_doc = ModelPlanDocument(
            title="Sneaky Revision",
            structure_type=EnumPlanStructureType.TASK_SECTIONS,
            entries=_make_entries(2),
            goal="different goal to change fingerprint",
        )
        fully_linked_contract.document = new_doc
        assert fully_linked_contract.is_done() is False

    def test_false_when_not_closed_even_if_complete(
        self, fully_linked_contract: ModelPlanContract
    ) -> None:
        # TICKETED phase, review complete, fully ticketed, but not CLOSED
        assert fully_linked_contract.is_review_complete() is True
        assert fully_linked_contract.is_fully_ticketed() is True
        assert fully_linked_contract.phase != EnumPlanPhase.CLOSED
        assert fully_linked_contract.is_done() is False


# ---------------------------------------------------------------------------
# Cardinality edge cases (3 tests)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCardinalityEdgeCases:
    def test_two_entries_same_ticket_and_execution_complete(self) -> None:
        doc = _make_document(2)
        c = ModelPlanContract(plan_id="PLAN-CARD", document=doc)
        review = _make_review(c, passed=True)
        c.add_review(review)
        c.transition_to(EnumPlanPhase.REVIEWED)
        # Both entries linked to the SAME ticket
        c.add_ticket_link(_make_link("P1", "OMN-500"))
        c.add_ticket_link(_make_link("P2", "OMN-500"))
        assert c.is_fully_ticketed() is True
        # One status covers both entries
        assert c.is_execution_complete({"OMN-500": True}) is True
        assert c.is_execution_complete({"OMN-500": False}) is False

    def test_linked_ticket_ids_deduplicates(self) -> None:
        doc = _make_document(2)
        c = ModelPlanContract(plan_id="PLAN-DEDUP", document=doc)
        review = _make_review(c, passed=True)
        c.add_review(review)
        c.transition_to(EnumPlanPhase.REVIEWED)
        c.add_ticket_link(_make_link("P1", "OMN-500"))
        c.add_ticket_link(_make_link("P2", "OMN-500"))
        ids = c.linked_ticket_ids()
        assert ids == ["OMN-500"]

    def test_is_execution_complete_missing_key_returns_false(self) -> None:
        doc = _make_document(2)
        c = ModelPlanContract(plan_id="PLAN-MISS", document=doc)
        review = _make_review(c, passed=True)
        c.add_review(review)
        c.transition_to(EnumPlanPhase.REVIEWED)
        c.add_ticket_link(_make_link("P1", "OMN-600"))
        c.add_ticket_link(_make_link("P2", "OMN-601"))
        # Only OMN-600 present -- OMN-601 missing => fail-closed
        assert c.is_execution_complete({"OMN-600": True}) is False


# ---------------------------------------------------------------------------
# Grace period (4 tests)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGracePeriod:
    def test_before_cutoff_returns_false(self) -> None:
        old_date = datetime(2020, 1, 1, tzinfo=UTC)
        assert ModelPlanContract.is_contract_required(old_date) is False

    def test_after_cutoff_returns_true(self) -> None:
        future_date = datetime(2030, 1, 1, tzinfo=UTC)
        assert ModelPlanContract.is_contract_required(future_date) is True

    def test_string_input_accepted(self) -> None:
        assert (
            ModelPlanContract.is_contract_required("2020-01-01T00:00:00+00:00") is False
        )
        assert (
            ModelPlanContract.is_contract_required("2030-01-01T00:00:00+00:00") is True
        )

    def test_naive_datetime_treated_as_utc(self) -> None:
        # Naive datetime at exactly the cutoff should be treated as UTC
        cutoff = ModelPlanContract.PLAN_CONTRACT_REQUIRED_AFTER
        naive_at_cutoff = cutoff.replace(tzinfo=None)
        assert ModelPlanContract.is_contract_required(naive_at_cutoff) is True


# ---------------------------------------------------------------------------
# UTC enforcement (2 tests)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUtcEnforcement:
    def test_naive_datetime_gets_utc(self) -> None:
        naive = datetime(2026, 1, 1)
        c = ModelPlanContract(
            plan_id="PLAN-UTC",
            document=_make_document(1),
            created_at=naive,
            updated_at=naive,
        )
        assert c.created_at.tzinfo is not None
        assert c.created_at.tzinfo == UTC
        assert c.updated_at.tzinfo == UTC

    def test_non_utc_datetime_converted(self) -> None:
        est = timezone(timedelta(hours=-5))
        est_dt = datetime(2026, 1, 1, 12, 0, 0, tzinfo=est)
        c = ModelPlanContract(
            plan_id="PLAN-EST",
            document=_make_document(1),
            created_at=est_dt,
            updated_at=est_dt,
        )
        assert c.created_at.tzinfo == UTC
        assert c.created_at.hour == 17  # 12 EST = 17 UTC


# ---------------------------------------------------------------------------
# Convenience methods (3 tests)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConvenienceMethods:
    def test_unlinked_entries_returns_correct_subset(
        self, reviewed_contract: ModelPlanContract
    ) -> None:
        assert len(reviewed_contract.unlinked_entries()) == 2
        reviewed_contract.add_ticket_link(_make_link("P1", "OMN-100"))
        unlinked = reviewed_contract.unlinked_entries()
        assert len(unlinked) == 1
        assert unlinked[0].id == "P2"

    def test_linked_ticket_ids_returns_unique(
        self, reviewed_contract: ModelPlanContract
    ) -> None:
        reviewed_contract.add_ticket_link(_make_link("P1", "OMN-100"))
        reviewed_contract.add_ticket_link(_make_link("P2", "OMN-100"))
        assert reviewed_contract.linked_ticket_ids() == ["OMN-100"]

    def test_link_for_entry_unambiguous(
        self, reviewed_contract: ModelPlanContract
    ) -> None:
        link = _make_link("P1", "OMN-100")
        reviewed_contract.add_ticket_link(link)
        result = reviewed_contract.link_for_entry("P1")
        assert result is not None
        assert result.entry_id == "P1"
        assert result.ticket_id == "OMN-100"
