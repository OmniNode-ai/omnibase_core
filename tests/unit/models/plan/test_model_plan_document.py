# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_plan_structure_type import EnumPlanStructureType
from omnibase_core.models.plan.model_plan_document import ModelPlanDocument
from omnibase_core.models.plan.model_plan_entry import ModelPlanEntry


@pytest.mark.unit
class TestModelPlanDocument:
    def _make_entries(self, n: int) -> list[ModelPlanEntry]:
        return [
            ModelPlanEntry(
                id=f"P{i}",
                title=f"Task {i}: Item {i}",
                content=f"Content for task {i}.",
            )
            for i in range(1, n + 1)
        ]

    def test_construction(self) -> None:
        entries = self._make_entries(3)
        doc = ModelPlanDocument(
            title="Autopilot Implementation Plan",
            structure_type=EnumPlanStructureType.TASK_SECTIONS,
            entries=entries,
            source_path="~/.claude/plans/binary-launching-badger.md",
        )
        assert doc.title == "Autopilot Implementation Plan"
        assert len(doc.entries) == 3
        assert doc.is_canonical_format

    def test_empty_entries_rejected(self) -> None:
        with pytest.raises((ValidationError, ValueError)):
            ModelPlanDocument(
                title="Empty Plan",
                structure_type=EnumPlanStructureType.TASK_SECTIONS,
                entries=[],
            )

    def test_duplicate_entry_ids_rejected(self) -> None:
        entries = [
            ModelPlanEntry(id="P1", title="Task 1: First", content="Content."),
            ModelPlanEntry(id="P1", title="Task 1: Duplicate", content="Content."),
        ]
        with pytest.raises((ValidationError, ValueError)):
            ModelPlanDocument(
                title="Dup Plan",
                structure_type=EnumPlanStructureType.TASK_SECTIONS,
                entries=entries,
            )

    def test_is_canonical_format(self) -> None:
        entries = self._make_entries(1)
        canonical = ModelPlanDocument(
            title="T",
            structure_type=EnumPlanStructureType.TASK_SECTIONS,
            entries=entries,
        )
        legacy = ModelPlanDocument(
            title="T",
            structure_type=EnumPlanStructureType.PHASE_SECTIONS,
            entries=entries,
        )
        assert canonical.is_canonical_format
        assert not legacy.is_canonical_format

    def test_entry_by_id_found(self) -> None:
        entries = self._make_entries(3)
        doc = ModelPlanDocument(
            title="T",
            structure_type=EnumPlanStructureType.TASK_SECTIONS,
            entries=entries,
        )
        result = doc.entry_by_id("P2")
        assert result is not None
        assert result.title == "Task 2: Item 2"

    def test_entry_by_id_not_found(self) -> None:
        entries = self._make_entries(3)
        doc = ModelPlanDocument(
            title="T",
            structure_type=EnumPlanStructureType.TASK_SECTIONS,
            entries=entries,
        )
        assert doc.entry_by_id("P99") is None

    def test_dependency_graph_no_cycles(self) -> None:
        entries = [
            ModelPlanEntry(id="P1", title="Task 1", content="C."),
            ModelPlanEntry(id="P2", title="Task 2", content="C.", dependencies=["P1"]),
            ModelPlanEntry(id="P3", title="Task 3", content="C.", dependencies=["P2"]),
        ]
        doc = ModelPlanDocument(
            title="T",
            structure_type=EnumPlanStructureType.TASK_SECTIONS,
            entries=entries,
        )
        assert doc.has_valid_dependency_graph

    def test_dependency_graph_with_cycle_rejected(self) -> None:
        entries = [
            ModelPlanEntry(id="P1", title="Task 1", content="C.", dependencies=["P3"]),
            ModelPlanEntry(id="P2", title="Task 2", content="C.", dependencies=["P1"]),
            ModelPlanEntry(id="P3", title="Task 3", content="C.", dependencies=["P2"]),
        ]
        with pytest.raises((ValidationError, ValueError)):
            ModelPlanDocument(
                title="T",
                structure_type=EnumPlanStructureType.TASK_SECTIONS,
                entries=entries,
            )

    def test_dangling_internal_dependency_rejected(self) -> None:
        """P99 does not exist in the document -- must be rejected."""
        entries = [
            ModelPlanEntry(id="P1", title="Task 1", content="C."),
            ModelPlanEntry(id="P2", title="Task 2", content="C.", dependencies=["P99"]),
            ModelPlanEntry(id="P3", title="Task 3", content="C."),
        ]
        with pytest.raises((ValidationError, ValueError)):
            ModelPlanDocument(
                title="T",
                structure_type=EnumPlanStructureType.TASK_SECTIONS,
                entries=entries,
            )

    def test_external_dependency_omn_allowed(self) -> None:
        """OMN-* external deps must be allowed (validated elsewhere)."""
        entries = [
            ModelPlanEntry(
                id="P1", title="Task 1", content="C.", dependencies=["OMN-1234"]
            ),
        ]
        doc = ModelPlanDocument(
            title="T",
            structure_type=EnumPlanStructureType.TASK_SECTIONS,
            entries=entries,
        )
        assert len(doc.entries) == 1
        assert doc.entries[0].dependencies == ["OMN-1234"]

    def test_frozen_model(self) -> None:
        """ModelPlanDocument is immutable after construction."""
        entries = self._make_entries(1)
        doc = ModelPlanDocument(
            title="T",
            structure_type=EnumPlanStructureType.TASK_SECTIONS,
            entries=entries,
        )
        with pytest.raises(Exception):
            doc.title = "Changed"  # type: ignore[misc]

    def test_optional_fields_defaults(self) -> None:
        entries = self._make_entries(1)
        doc = ModelPlanDocument(
            title="T",
            structure_type=EnumPlanStructureType.TASK_SECTIONS,
            entries=entries,
        )
        assert doc.source_path is None
        assert doc.goal is None
        assert doc.architecture is None

    def test_optional_fields_set(self) -> None:
        entries = self._make_entries(2)
        doc = ModelPlanDocument(
            title="Plan",
            structure_type=EnumPlanStructureType.TASK_SECTIONS,
            entries=entries,
            source_path="/tmp/plan.md",
            goal="Create shared Pydantic models.",
            architecture="Frozen BaseModel under models/plan/.",
        )
        assert doc.source_path == "/tmp/plan.md"
        assert doc.goal == "Create shared Pydantic models."
        assert doc.architecture == "Frozen BaseModel under models/plan/."

    def test_multiple_entries_with_valid_dependency_chain(self) -> None:
        entries = [
            ModelPlanEntry(id="P1", title="Task 1", content="Implement base."),
            ModelPlanEntry(
                id="P2", title="Task 2", content="Build on base.", dependencies=["P1"]
            ),
            ModelPlanEntry(
                id="P3",
                title="Task 3",
                content="Final integration.",
                dependencies=["P1", "P2"],
            ),
        ]
        doc = ModelPlanDocument(
            title="Chain Plan",
            structure_type=EnumPlanStructureType.TASK_SECTIONS,
            entries=entries,
        )
        assert len(doc.entries) == 3
        assert doc.has_valid_dependency_graph

    def test_self_referential_dependency_rejected(self) -> None:
        """P1 depending on itself is a trivial cycle."""
        entries = [
            ModelPlanEntry(id="P1", title="Task 1", content="C.", dependencies=["P1"]),
        ]
        with pytest.raises((ValidationError, ValueError)):
            ModelPlanDocument(
                title="T",
                structure_type=EnumPlanStructureType.TASK_SECTIONS,
                entries=entries,
            )

    def test_longer_cycle_rejected(self) -> None:
        """P1->P2->P3->P1 three-node cycle must be detected."""
        entries = [
            ModelPlanEntry(id="P1", title="Task 1", content="C.", dependencies=["P3"]),
            ModelPlanEntry(id="P2", title="Task 2", content="C.", dependencies=["P1"]),
            ModelPlanEntry(id="P3", title="Task 3", content="C.", dependencies=["P2"]),
        ]
        with pytest.raises((ValidationError, ValueError), match=r"[Cc]ircular"):
            ModelPlanDocument(
                title="T",
                structure_type=EnumPlanStructureType.TASK_SECTIONS,
                entries=entries,
            )

    def test_dangling_dep_error_message(self) -> None:
        """Error message must mention the missing ID."""
        entries = [
            ModelPlanEntry(id="P1", title="Task 1", content="C."),
            ModelPlanEntry(id="P2", title="Task 2", content="C.", dependencies=["P99"]),
        ]
        with pytest.raises((ValidationError, ValueError), match="P99"):
            ModelPlanDocument(
                title="T",
                structure_type=EnumPlanStructureType.TASK_SECTIONS,
                entries=entries,
            )
