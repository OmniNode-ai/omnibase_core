# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for OMN-8421 enforcement-chain fields on ModelPlanContract.

Covers the 7 fields added for the OMN-8416 plan -> epic -> tickets -> PR
-> dogfood enforcement chain: epic_id, plan_phases, dependencies,
success_criteria, halt_conditions, supersedes, superseded_by.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_plan_structure_type import EnumPlanStructureType
from omnibase_core.models.plan import (
    ModelDoDItem,
    ModelPlanContract,
    ModelPlanDocument,
    ModelPlanEntry,
)


def _doc() -> ModelPlanDocument:
    return ModelPlanDocument(
        title="Enforcement Test Plan",
        structure_type=EnumPlanStructureType.TASK_SECTIONS,
        entries=[
            ModelPlanEntry(id="P1", title="Task 1: item", content="body"),
            ModelPlanEntry(id="P2", title="Task 2: item", content="body"),
        ],
    )


@pytest.mark.unit
class TestEnforcementFieldDefaults:
    def test_all_new_fields_default_empty(self) -> None:
        c = ModelPlanContract(plan_id="PLAN-TEST-DEFAULTS", document=_doc())
        assert c.epic_id is None
        assert c.plan_phases == []
        assert c.dependencies == []
        assert c.success_criteria == []
        assert c.halt_conditions == []
        assert c.supersedes == []
        assert c.superseded_by is None

    def test_backwards_compat_minimal_construction(self) -> None:
        """A pre-OMN-8421 contract constructor call must still work unchanged."""
        c = ModelPlanContract(plan_id="PLAN-BWC-1", document=_doc())
        # Roundtrip via YAML to simulate reading an old persisted contract
        restored = ModelPlanContract.from_yaml(c.to_yaml())
        assert restored.plan_id == c.plan_id
        assert restored.epic_id is None
        assert restored.plan_phases == []


@pytest.mark.unit
class TestEpicIdValidator:
    def test_valid_epic_id(self) -> None:
        c = ModelPlanContract(
            plan_id="PLAN-EPIC-1", document=_doc(), epic_id="OMN-8416"
        )
        assert c.epic_id == "OMN-8416"

    def test_none_allowed(self) -> None:
        c = ModelPlanContract(plan_id="PLAN-EPIC-2", document=_doc(), epic_id=None)
        assert c.epic_id is None

    @pytest.mark.parametrize(
        "bad",
        [
            "foo-123",
            "OMN-",
            "",
            "OMN-abc",
            "omn-123",
            " OMN-8416 ",
        ],
    )
    def test_invalid_epic_id_rejected(self, bad: str) -> None:
        with pytest.raises(ValidationError):
            ModelPlanContract(plan_id="PLAN-EPIC-X", document=_doc(), epic_id=bad)


@pytest.mark.unit
class TestSuccessCriteriaField:
    def test_with_dod_items(self) -> None:
        items = [
            ModelDoDItem(id="d1", description="Tests pass"),
            ModelDoDItem(
                id="d2",
                description="Rendered output verified",
                evidence_type="rendered_output",
            ),
        ]
        c = ModelPlanContract(
            plan_id="PLAN-DOD-1", document=_doc(), success_criteria=items
        )
        assert len(c.success_criteria) == 2
        assert c.success_criteria[0].id == "d1"
        assert c.success_criteria[1].evidence_type == "rendered_output"


@pytest.mark.unit
class TestYAMLRoundTrip:
    def test_all_fields_round_trip(self) -> None:
        original = ModelPlanContract(
            plan_id="PLAN-YAML-1",
            document=_doc(),
            epic_id="OMN-8416",
            plan_phases=["P0", "P1", "P2"],
            dependencies=["PLAN-YAML-0"],
            success_criteria=[
                ModelDoDItem(id="d1", description="Green CI", satisfied=True),
                ModelDoDItem(id="d2", description="Screenshot"),
            ],
            halt_conditions=["diagnosis_required", "two_strike"],
            supersedes=["PLAN-OLD-A", "PLAN-OLD-B"],
            superseded_by=None,
        )
        restored = ModelPlanContract.from_yaml(original.to_yaml())
        assert restored.epic_id == "OMN-8416"
        assert restored.plan_phases == ["P0", "P1", "P2"]
        assert restored.dependencies == ["PLAN-YAML-0"]
        assert len(restored.success_criteria) == 2
        assert restored.success_criteria[0].satisfied is True
        assert restored.halt_conditions == ["diagnosis_required", "two_strike"]
        assert restored.supersedes == ["PLAN-OLD-A", "PLAN-OLD-B"]
        assert restored.superseded_by is None


@pytest.mark.unit
class TestSupersededByChain:
    def test_no_successor_is_not_superseded(self) -> None:
        c = ModelPlanContract(plan_id="PLAN-A", document=_doc(), superseded_by=None)
        assert c.is_transitively_superseded({}) is False

    def test_direct_successor_present_in_resolver(self) -> None:
        b = ModelPlanContract(plan_id="PLAN-B", document=_doc(), superseded_by=None)
        a = ModelPlanContract(plan_id="PLAN-A", document=_doc(), superseded_by="PLAN-B")
        assert a.is_transitively_superseded({"PLAN-B": b}) is True

    def test_transitive_chain(self) -> None:
        c = ModelPlanContract(plan_id="PLAN-C", document=_doc(), superseded_by=None)
        b = ModelPlanContract(plan_id="PLAN-B", document=_doc(), superseded_by="PLAN-C")
        a = ModelPlanContract(plan_id="PLAN-A", document=_doc(), superseded_by="PLAN-B")
        resolver = {"PLAN-B": b, "PLAN-C": c}
        assert a.is_transitively_superseded(resolver) is True

    def test_cycle_treated_as_superseded(self) -> None:
        b = ModelPlanContract(plan_id="PLAN-B", document=_doc(), superseded_by="PLAN-A")
        a = ModelPlanContract(plan_id="PLAN-A", document=_doc(), superseded_by="PLAN-B")
        assert a.is_transitively_superseded({"PLAN-B": b}) is True

    def test_unresolvable_successor_not_falsely_superseded(self) -> None:
        """If the chain points to an unknown plan_id, supersession cannot be confirmed."""
        a = ModelPlanContract(
            plan_id="PLAN-A", document=_doc(), superseded_by="PLAN-UNKNOWN"
        )
        assert a.is_transitively_superseded({}) is False

    def test_is_transitively_superseded_returns_false_for_terminal_plan(self) -> None:
        """Chain that resolves to a terminal (live) plan: PLAN-A → PLAN-B (live).

        PLAN-A IS superseded — its chain leads to a live plan. Confirmed True.
        PLAN-B is terminal (superseded_by=None) — it is NOT superseded. Must be False.

        This is the TDD-first guard for the W0.6 bug: the method's final
        ``return True`` after the while loop must NOT fire for the terminal
        plan itself.
        """
        terminal = ModelPlanContract(
            plan_id="PLAN-TERMINAL", document=_doc(), superseded_by=None
        )
        # The terminal plan has no successor — must be False.
        assert terminal.is_transitively_superseded({}) is False
        # A plan that claims to be superseded by a known-live terminal → True.
        predecessor = ModelPlanContract(
            plan_id="PLAN-PRED", document=_doc(), superseded_by="PLAN-TERMINAL"
        )
        assert (
            predecessor.is_transitively_superseded({"PLAN-TERMINAL": terminal}) is True
        )

    def test_chain_terminates_at_unresolvable_does_not_falsely_supersede(self) -> None:
        """False-positive guard (W0.6 core bug): unknown successor must NOT claim supersession.

        When a plan's superseded_by points to a plan_id not present in the
        resolver, the chain cannot be confirmed. The method must return False
        rather than claiming supersession with no evidence of a live successor.
        """
        a = ModelPlanContract(
            plan_id="PLAN-A", document=_doc(), superseded_by="PLAN-GHOST"
        )
        # PLAN-GHOST is not in the resolver — no live successor confirmed.
        # Currently returns True (false positive). Must return False after fix.
        assert a.is_transitively_superseded({}) is False


@pytest.mark.unit
class TestFingerprintIncludesNewFields:
    def test_epic_id_change_changes_fingerprint(self) -> None:
        a = ModelPlanContract(plan_id="PLAN-FP-1", document=_doc(), epic_id="OMN-1")
        b = ModelPlanContract(plan_id="PLAN-FP-1", document=_doc(), epic_id="OMN-2")
        assert a.compute_fingerprint() != b.compute_fingerprint()

    def test_plan_phases_change_changes_fingerprint(self) -> None:
        a = ModelPlanContract(plan_id="PLAN-FP-2", document=_doc(), plan_phases=["P0"])
        b = ModelPlanContract(
            plan_id="PLAN-FP-2", document=_doc(), plan_phases=["P0", "P1"]
        )
        assert a.compute_fingerprint() != b.compute_fingerprint()
