# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import pytest

from omnibase_core.enums.enum_plan_structure_type import EnumPlanStructureType
from omnibase_core.models.plan.model_plan_entry import ModelPlanEntry


@pytest.mark.unit
class TestEnumPlanStructureType:
    def test_canonical_values(self) -> None:
        assert EnumPlanStructureType.TASK_SECTIONS.value == "task_sections"
        assert EnumPlanStructureType.PHASE_SECTIONS.value == "phase_sections"
        assert EnumPlanStructureType.MILESTONE_TABLE.value == "milestone_table"
        assert EnumPlanStructureType.PRIORITY_LABELS.value == "priority_labels"
        assert EnumPlanStructureType.NUMBERED_LIST.value == "numbered_list"

    def test_is_canonical(self) -> None:
        assert EnumPlanStructureType.TASK_SECTIONS.is_canonical
        assert not EnumPlanStructureType.PHASE_SECTIONS.is_canonical
        assert not EnumPlanStructureType.MILESTONE_TABLE.is_canonical
        assert not EnumPlanStructureType.PRIORITY_LABELS.is_canonical
        assert not EnumPlanStructureType.NUMBERED_LIST.is_canonical

    def test_all_values_count(self) -> None:
        assert len(EnumPlanStructureType) == 5


@pytest.mark.unit
class TestModelPlanEntry:
    def test_minimal_construction(self) -> None:
        entry = ModelPlanEntry(
            id="P1",
            title="Task 1: Create skill specification",
            content="Create the SKILL.md file with full specification.",
        )
        assert entry.id == "P1"
        assert entry.dependencies == []

    def test_with_dependencies(self) -> None:
        entry = ModelPlanEntry(
            id="P3",
            title="Task 3: Implement circuit breaker",
            content="Implement circuit breaker logic.",
            dependencies=["P1", "P2"],
        )
        assert entry.dependencies == ["P1", "P2"]

    def test_with_external_dependencies(self) -> None:
        entry = ModelPlanEntry(
            id="P5",
            title="Task 5: Integration test",
            content="Write integration tests.",
            dependencies=["P4", "OMN-3795"],
        )
        assert "OMN-3795" in entry.dependencies

    def test_frozen(self) -> None:
        entry = ModelPlanEntry(id="P1", title="t", content="c")
        with pytest.raises(Exception):
            entry.title = "changed"  # type: ignore[misc]

    def test_empty_content_rejected(self) -> None:
        with pytest.raises(ValueError, match="empty or whitespace-only"):
            ModelPlanEntry(id="P1", title="t", content="")

    def test_whitespace_only_content_rejected(self) -> None:
        with pytest.raises(ValueError, match="empty or whitespace-only"):
            ModelPlanEntry(id="P1", title="t", content="   \n  ")

    # --- ID normalization and validation ---

    def test_id_normalization_lowercase_p(self) -> None:
        entry = ModelPlanEntry(id="p3", title="t", content="c")
        assert entry.id == "P3"

    def test_id_normalization_strip_whitespace(self) -> None:
        entry = ModelPlanEntry(id="  P5  ", title="t", content="c")
        assert entry.id == "P5"

    def test_id_with_subindex(self) -> None:
        entry = ModelPlanEntry(id="P3_1", title="t", content="c")
        assert entry.id == "P3_1"

    def test_id_invalid_pattern_alpha(self) -> None:
        with pytest.raises(ValueError, match="does not match pattern"):
            ModelPlanEntry(id="Pfoo", title="t", content="c")

    def test_id_invalid_pattern_leading_zero(self) -> None:
        with pytest.raises(ValueError, match="does not match pattern"):
            ModelPlanEntry(id="P01", title="t", content="c")

    def test_id_invalid_pattern_alpha_suffix(self) -> None:
        with pytest.raises(ValueError, match="does not match pattern"):
            ModelPlanEntry(id="P1A", title="t", content="c")

    def test_id_invalid_pattern_nested_subindex(self) -> None:
        with pytest.raises(ValueError, match="does not match pattern"):
            ModelPlanEntry(id="P1_1_2", title="t", content="c")

    # --- Dependency normalization and validation ---

    def test_dependency_normalization_lowercase_p(self) -> None:
        entry = ModelPlanEntry(id="P2", title="t", content="c", dependencies=["p1"])
        assert entry.dependencies == ["P1"]

    def test_dependency_normalization_lowercase_omn(self) -> None:
        entry = ModelPlanEntry(id="P2", title="t", content="c", dependencies=["omn-123"])
        assert entry.dependencies == ["OMN-123"]

    def test_dependency_normalization_strip_whitespace(self) -> None:
        entry = ModelPlanEntry(id="P2", title="t", content="c", dependencies=["  P1  "])
        assert entry.dependencies == ["P1"]

    def test_dependency_invalid_pattern(self) -> None:
        with pytest.raises(ValueError, match="does not match"):
            ModelPlanEntry(id="P2", title="t", content="c", dependencies=["JIRA-123"])

    def test_dependency_invalid_internal_pattern(self) -> None:
        with pytest.raises(ValueError, match="does not match"):
            ModelPlanEntry(id="P2", title="t", content="c", dependencies=["P1A"])

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(Exception):
            ModelPlanEntry(id="P1", title="t", content="c", unknown_field="bad")  # type: ignore[call-arg]
