#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ContractDiffComputer.

This module provides comprehensive TDD-style tests for the contract diffing algorithm.
Tests validate core diffing logic including scalar, nested, and list comparisons.

Coverage Requirements:
- >95% line coverage for all methods
- 100% coverage for error handling paths
- Comprehensive edge case and boundary condition testing
- Deterministic output validation (same input = same output)
"""

import pytest
from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.contracts.contract_diff_computer import (
    ContractDiffComputer,
    compute_contract_diff,
    render_diff_table,
)
from omnibase_core.enums.enum_contract_diff_change_type import (
    EnumContractDiffChangeType,
)
from omnibase_core.models.contracts.diff.model_contract_diff import ModelContractDiff
from omnibase_core.models.contracts.diff.model_diff_configuration import (
    ModelDiffConfiguration,
)

# =================== TEST MODELS ===================


class SampleContract(BaseModel):
    """Simple contract for testing basic diffing."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str = ""
    version: int = 1
    tags: list[str] = Field(default_factory=list)
    dependencies: list[dict] = Field(default_factory=list)  # Each has 'name' key


class NestedConfig(BaseModel):
    """Nested configuration for testing recursive diffing."""

    model_config = ConfigDict(extra="forbid")

    timeout_ms: int = 1000
    retry_count: int = 3
    enabled: bool = True


class SampleContractWithNested(BaseModel):
    """Contract with nested objects for testing recursive diffing."""

    model_config = ConfigDict(extra="forbid")

    name: str
    config: NestedConfig = Field(default_factory=NestedConfig)
    metadata: dict = Field(default_factory=dict)


class SampleContractWithOptional(BaseModel):
    """Contract with optional fields for testing added/removed scenarios."""

    model_config = ConfigDict(extra="forbid")

    name: str
    optional_field: str | None = None
    optional_int: int | None = None
    optional_list: list[str] | None = None


# =================== CORE DIFF TESTS ===================


@pytest.mark.unit
class TestContractDiffComputer:
    """Tests for ContractDiffComputer core functionality."""

    def test_identical_contracts_no_changes(self) -> None:
        """Test that identical contracts produce no changes."""
        contract = SampleContract(name="test", description="desc")
        diff = compute_contract_diff(contract, contract)
        assert not diff.has_changes
        assert diff.total_changes == 0
        assert len(diff.field_diffs) == 0
        assert len(diff.list_diffs) == 0

    def test_identical_nested_contracts_no_changes(self) -> None:
        """Test that identical nested contracts produce no changes."""
        contract = SampleContractWithNested(
            name="test",
            config=NestedConfig(timeout_ms=2000, retry_count=5),
            metadata={"key": "value"},
        )
        diff = compute_contract_diff(contract, contract)
        assert not diff.has_changes
        assert diff.total_changes == 0

    def test_scalar_field_added(self) -> None:
        """Test detection of added scalar field (missing key in before dict).

        Note: Uses dict comparison directly since Pydantic models always include
        optional fields (with None value). True ADDED detection requires key absence.
        """
        before_dict = {"name": "test"}  # No 'extra_field' key
        after_dict = {"name": "test", "extra_field": "new_value"}

        # Create a minimal contract-like model for this test
        class MinimalContract(BaseModel):
            model_config = ConfigDict(extra="allow")
            name: str

        before = MinimalContract(**before_dict)
        after = MinimalContract(**after_dict)
        diff = compute_contract_diff(before, after)

        assert diff.has_changes
        field_diff = next(
            (d for d in diff.field_diffs if "extra_field" in d.field_path), None
        )
        assert field_diff is not None
        assert field_diff.change_type == EnumContractDiffChangeType.ADDED
        assert field_diff.old_value is None
        assert field_diff.new_value is not None
        assert field_diff.new_value.to_value() == "new_value"

    def test_scalar_field_removed(self) -> None:
        """Test detection of removed scalar field (key present -> key absent).

        Note: Uses dict comparison directly since Pydantic models always include
        optional fields (with None value). True REMOVED detection requires key absence.
        """
        before_dict = {"name": "test", "extra_field": "old_value"}
        after_dict = {"name": "test"}  # No 'extra_field' key

        # Create a minimal contract-like model for this test
        class MinimalContract(BaseModel):
            model_config = ConfigDict(extra="allow")
            name: str

        before = MinimalContract(**before_dict)
        after = MinimalContract(**after_dict)
        diff = compute_contract_diff(before, after)

        assert diff.has_changes
        field_diff = next(
            (d for d in diff.field_diffs if "extra_field" in d.field_path), None
        )
        assert field_diff is not None
        assert field_diff.change_type == EnumContractDiffChangeType.REMOVED
        assert field_diff.old_value is not None
        assert field_diff.old_value.to_value() == "old_value"
        assert field_diff.new_value is None

    def test_scalar_field_modified_string(self) -> None:
        """Test detection of modified string field."""
        before = SampleContract(name="test", description="old_description")
        after = SampleContract(name="test", description="new_description")
        diff = compute_contract_diff(before, after)

        assert diff.has_changes
        desc_diff = next(
            (d for d in diff.field_diffs if "description" in d.field_path), None
        )
        assert desc_diff is not None
        assert desc_diff.change_type == EnumContractDiffChangeType.MODIFIED
        # Values are wrapped in ModelSchemaValue, use to_value() to unwrap
        assert desc_diff.old_value is not None
        assert desc_diff.old_value.to_value() == "old_description"
        assert desc_diff.new_value is not None
        assert desc_diff.new_value.to_value() == "new_description"

    def test_scalar_field_modified_int(self) -> None:
        """Test detection of modified integer field."""
        before = SampleContract(name="test", version=1)
        after = SampleContract(name="test", version=2)
        diff = compute_contract_diff(before, after)

        assert diff.has_changes
        version_diff = next(
            (d for d in diff.field_diffs if "version" in d.field_path), None
        )
        assert version_diff is not None
        assert version_diff.change_type == EnumContractDiffChangeType.MODIFIED
        # Values are wrapped in ModelSchemaValue, use to_value() to unwrap
        assert version_diff.old_value is not None
        assert version_diff.old_value.to_value() == 1
        assert version_diff.new_value is not None
        assert version_diff.new_value.to_value() == 2

    def test_multiple_scalar_fields_modified(self) -> None:
        """Test detection of multiple modified scalar fields."""
        before = SampleContract(name="test", description="old", version=1)
        after = SampleContract(name="test", description="new", version=2)
        diff = compute_contract_diff(before, after)

        assert diff.has_changes
        assert diff.total_changes >= 2

        # Find specific changes
        desc_diff = next(
            (d for d in diff.field_diffs if "description" in d.field_path), None
        )
        version_diff = next(
            (d for d in diff.field_diffs if "version" in d.field_path), None
        )

        assert desc_diff is not None
        assert version_diff is not None


# =================== NESTED OBJECT TESTS ===================


@pytest.mark.unit
class TestNestedObjectDiff:
    """Tests for recursive diffing of nested objects."""

    def test_nested_object_diff_single_field(self) -> None:
        """Test recursive diffing of nested objects with single field change."""
        before = SampleContractWithNested(
            name="test",
            config=NestedConfig(timeout_ms=1000),
        )
        after = SampleContractWithNested(
            name="test",
            config=NestedConfig(timeout_ms=2000),
        )
        diff = compute_contract_diff(before, after)

        assert diff.has_changes
        timeout_diff = next(
            (d for d in diff.field_diffs if "timeout_ms" in d.field_path), None
        )
        assert timeout_diff is not None
        assert timeout_diff.change_type == EnumContractDiffChangeType.MODIFIED
        # Verify the path includes the nested path
        assert "config" in timeout_diff.field_path

    def test_nested_object_diff_multiple_fields(self) -> None:
        """Test recursive diffing with multiple nested field changes."""
        before = SampleContractWithNested(
            name="test",
            config=NestedConfig(timeout_ms=1000, retry_count=3, enabled=True),
        )
        after = SampleContractWithNested(
            name="test",
            config=NestedConfig(timeout_ms=2000, retry_count=5, enabled=False),
        )
        diff = compute_contract_diff(before, after)

        assert diff.has_changes
        assert diff.total_changes >= 3

    def test_nested_dict_field_added(self) -> None:
        """Test adding a key to nested dict."""
        before = SampleContractWithNested(
            name="test",
            metadata={"existing": "value"},
        )
        after = SampleContractWithNested(
            name="test",
            metadata={"existing": "value", "new_key": "new_value"},
        )
        diff = compute_contract_diff(before, after)

        assert diff.has_changes

    def test_nested_dict_field_removed(self) -> None:
        """Test removing a key from nested dict."""
        before = SampleContractWithNested(
            name="test",
            metadata={"keep": "value", "remove": "this"},
        )
        after = SampleContractWithNested(
            name="test",
            metadata={"keep": "value"},
        )
        diff = compute_contract_diff(before, after)

        assert diff.has_changes

    def test_nested_dict_field_modified(self) -> None:
        """Test modifying a value in nested dict."""
        before = SampleContractWithNested(
            name="test",
            metadata={"key": "old_value"},
        )
        after = SampleContractWithNested(
            name="test",
            metadata={"key": "new_value"},
        )
        diff = compute_contract_diff(before, after)

        assert diff.has_changes


# =================== LIST DIFF TESTS ===================


@pytest.mark.unit
class TestListIdentityMatching:
    """Tests for identity-based list diffing."""

    def test_list_identity_matching_added(self) -> None:
        """Test identity-based list diff detects added items."""
        before = SampleContract(name="test", dependencies=[{"name": "dep_a"}])
        after = SampleContract(
            name="test",
            dependencies=[{"name": "dep_a"}, {"name": "dep_b"}],
        )
        diff = compute_contract_diff(before, after)

        assert diff.has_changes
        deps_diff = next(
            (d for d in diff.list_diffs if "dependencies" in d.field_path), None
        )
        assert deps_diff is not None
        assert len(deps_diff.added_items) == 1
        # Verify the added item contains dep_b
        assert any("dep_b" in str(item) for item in deps_diff.added_items)

    def test_list_identity_matching_removed(self) -> None:
        """Test identity-based list diff detects removed items."""
        before = SampleContract(
            name="test",
            dependencies=[{"name": "dep_a"}, {"name": "dep_b"}],
        )
        after = SampleContract(name="test", dependencies=[{"name": "dep_b"}])
        diff = compute_contract_diff(before, after)

        assert diff.has_changes
        deps_diff = next(
            (d for d in diff.list_diffs if "dependencies" in d.field_path), None
        )
        assert deps_diff is not None
        assert len(deps_diff.removed_items) == 1

    def test_list_identity_matching_modified(self) -> None:
        """Test identity-based list diff detects modified items."""
        before = SampleContract(
            name="test",
            dependencies=[{"name": "dep_a", "version": "1.0"}],
        )
        after = SampleContract(
            name="test",
            dependencies=[{"name": "dep_a", "version": "2.0"}],
        )
        diff = compute_contract_diff(before, after)

        assert diff.has_changes
        deps_diff = next(
            (d for d in diff.list_diffs if "dependencies" in d.field_path), None
        )
        assert deps_diff is not None
        # The item should be detected as modified (same identity, different content)
        assert len(deps_diff.modified_items) == 1

    def test_list_identity_matching_moved(self) -> None:
        """Test identity-based list diff detects moved items."""
        before = SampleContract(
            name="test",
            dependencies=[{"name": "dep_a"}, {"name": "dep_b"}],
        )
        after = SampleContract(
            name="test",
            dependencies=[{"name": "dep_b"}, {"name": "dep_a"}],
        )
        diff = compute_contract_diff(before, after)

        deps_diff = next(
            (d for d in diff.list_diffs if "dependencies" in d.field_path), None
        )
        assert deps_diff is not None
        # Both items moved positions
        assert len(deps_diff.moved_items) == 2

    def test_list_identity_matching_complex_changes(self) -> None:
        """Test list diff with multiple types of changes."""
        before = SampleContract(
            name="test",
            dependencies=[
                {"name": "dep_a", "version": "1.0"},
                {"name": "dep_b"},
                {"name": "dep_c"},
            ],
        )
        after = SampleContract(
            name="test",
            dependencies=[
                {"name": "dep_c"},  # moved
                {"name": "dep_a", "version": "2.0"},  # modified and moved
                {"name": "dep_d"},  # added
                # dep_b removed
            ],
        )
        diff = compute_contract_diff(before, after)

        assert diff.has_changes
        deps_diff = next(
            (d for d in diff.list_diffs if "dependencies" in d.field_path), None
        )
        assert deps_diff is not None


# =================== PRIMITIVE LIST TESTS ===================


@pytest.mark.unit
class TestPrimitiveListDiff:
    """Tests for diffing of primitive value lists.

    Note: Primitive lists without identity keys use positional comparison,
    which produces field_diffs (not list_diffs). To get list_diffs with
    identity-based matching, the field must have an identity key configured.
    """

    def test_primitive_list_diff_added(self) -> None:
        """Test detecting added items in primitive list.

        Without an identity key, positional comparison is used.
        The added item at index 2 produces a field_diff entry.
        """
        before = SampleContract(name="test", tags=["a", "b"])
        after = SampleContract(name="test", tags=["a", "b", "c"])
        diff = compute_contract_diff(before, after)

        assert diff.has_changes
        # Positional comparison puts results in field_diffs
        added_diffs = [
            d
            for d in diff.field_diffs
            if "tags" in d.field_path
            and d.change_type == EnumContractDiffChangeType.ADDED
        ]
        assert len(added_diffs) == 1

    def test_primitive_list_diff_removed(self) -> None:
        """Test detecting removed items in primitive list.

        With positional comparison, removing "b" at index 1 causes:
        - Position 1: "b" -> "c" (modified)
        - Position 2: "c" -> removed
        """
        before = SampleContract(name="test", tags=["a", "b", "c"])
        after = SampleContract(name="test", tags=["a", "c"])
        diff = compute_contract_diff(before, after)

        assert diff.has_changes
        # Positional comparison - check for changes in tags positions
        tags_diffs = [d for d in diff.field_diffs if "tags" in d.field_path]
        assert len(tags_diffs) >= 1  # At least one position changed

    def test_primitive_list_diff_mixed_changes(self) -> None:
        """Test primitive list with both additions and removals.

        With positional comparison:
        - Position 0: "a" -> "b" (modified)
        - Position 1: "b" -> "c" (modified)
        """
        before = SampleContract(name="test", tags=["a", "b"])
        after = SampleContract(name="test", tags=["b", "c"])
        diff = compute_contract_diff(before, after)

        assert diff.has_changes
        # Both positions modified in positional comparison
        tags_diffs = [
            d
            for d in diff.field_diffs
            if "tags" in d.field_path
            and d.change_type == EnumContractDiffChangeType.MODIFIED
        ]
        assert len(tags_diffs) == 2

    def test_primitive_list_empty_to_populated(self) -> None:
        """Test list going from empty to populated."""
        before = SampleContract(name="test", tags=[])
        after = SampleContract(name="test", tags=["a", "b"])
        diff = compute_contract_diff(before, after)

        assert diff.has_changes
        # Positional comparison - positions 0 and 1 are added
        added_diffs = [
            d
            for d in diff.field_diffs
            if "tags" in d.field_path
            and d.change_type == EnumContractDiffChangeType.ADDED
        ]
        assert len(added_diffs) == 2

    def test_primitive_list_populated_to_empty(self) -> None:
        """Test list going from populated to empty."""
        before = SampleContract(name="test", tags=["a", "b"])
        after = SampleContract(name="test", tags=[])
        diff = compute_contract_diff(before, after)

        assert diff.has_changes
        # Positional comparison - positions 0 and 1 are removed
        removed_diffs = [
            d
            for d in diff.field_diffs
            if "tags" in d.field_path
            and d.change_type == EnumContractDiffChangeType.REMOVED
        ]
        assert len(removed_diffs) == 2

    def test_nested_list_diffs_in_positional_mode(self) -> None:
        """Test that nested list diffs in positional mode are captured.

        This test verifies the fix for the list_diffs accumulator bug where
        nested lists inside positional list elements were not captured because
        a new empty list was passed instead of propagating the parent accumulator.

        Uses a list without an identity key (positional mode) containing dicts
        with nested lists that DO have identity keys (identity mode).
        """
        from pydantic import BaseModel, ConfigDict, Field

        class ContractWithNestedLists(BaseModel):
            """Contract with positional list containing nested identity lists."""

            model_config = ConfigDict(extra="forbid")
            name: str
            # items has no identity key configured - uses positional mode
            items: list[dict] = Field(default_factory=list)

        # Configure identity key for nested "dependencies" lists
        config = ModelDiffConfiguration(
            identity_keys={
                "dependencies": "name",  # Nested lists use identity mode
            }
        )

        before = ContractWithNestedLists(
            name="test",
            items=[
                {"id": 1, "dependencies": [{"name": "dep_a"}]},
            ],
        )
        after = ContractWithNestedLists(
            name="test",
            items=[
                {"id": 1, "dependencies": [{"name": "dep_a"}, {"name": "dep_b"}]},
            ],
        )

        diff = compute_contract_diff(before, after, config)

        # The nested list diff should be captured in list_diffs
        # Before the fix, this would be empty because list_diffs=[] was passed
        nested_list_diffs = [
            d for d in diff.list_diffs if "dependencies" in d.field_path
        ]
        assert len(nested_list_diffs) == 1
        deps_diff = nested_list_diffs[0]
        assert len(deps_diff.added_items) == 1
        assert "dep_b" in str(deps_diff.added_items[0])


# =================== CONFIGURATION TESTS ===================


@pytest.mark.unit
class TestDiffConfiguration:
    """Tests for ModelDiffConfiguration options."""

    def test_field_exclusions_work(self) -> None:
        """Test that excluded fields are not in diff output."""
        config = ModelDiffConfiguration(exclude_fields=frozenset({"description"}))
        before = SampleContract(name="test", description="old")
        after = SampleContract(name="test", description="new")
        diff = compute_contract_diff(before, after, config)

        field_paths = [d.field_path for d in diff.field_diffs]
        assert not any("description" in path for path in field_paths)

    def test_multiple_field_exclusions(self) -> None:
        """Test excluding multiple fields."""
        config = ModelDiffConfiguration(
            exclude_fields=frozenset({"description", "version"})
        )
        before = SampleContract(name="test", description="old", version=1)
        after = SampleContract(name="test", description="new", version=2)
        diff = compute_contract_diff(before, after, config)

        # Should have no changes since both changed fields are excluded
        field_paths = [d.field_path for d in diff.field_diffs]
        assert not any("description" in path for path in field_paths)
        assert not any("version" in path for path in field_paths)

    def test_include_unchanged_option(self) -> None:
        """Test include_unchanged shows unchanged fields."""
        config = ModelDiffConfiguration(include_unchanged=True)
        contract = SampleContract(name="test", description="desc", version=1)
        diff = compute_contract_diff(contract, contract, config)

        # Should have UNCHANGED entries for fields
        unchanged = [
            d
            for d in diff.field_diffs
            if d.change_type == EnumContractDiffChangeType.UNCHANGED
        ]
        assert len(unchanged) > 0

    def test_include_unchanged_with_changes(self) -> None:
        """Test include_unchanged with some actual changes."""
        config = ModelDiffConfiguration(include_unchanged=True)
        before = SampleContract(name="test", description="old", version=1)
        after = SampleContract(name="test", description="new", version=1)
        diff = compute_contract_diff(before, after, config)

        # Should have both MODIFIED and UNCHANGED entries
        modified = [
            d
            for d in diff.field_diffs
            if d.change_type == EnumContractDiffChangeType.MODIFIED
        ]
        unchanged = [
            d
            for d in diff.field_diffs
            if d.change_type == EnumContractDiffChangeType.UNCHANGED
        ]
        assert len(modified) > 0
        assert len(unchanged) > 0

    def test_default_config_excludes_unchanged(self) -> None:
        """Test that default config excludes unchanged fields."""
        contract = SampleContract(name="test", description="desc")
        diff = compute_contract_diff(contract, contract)

        # Should have no entries since nothing changed and unchanged excluded by default
        assert len(diff.field_diffs) == 0


# =================== RENDER TABLE TESTS ===================


@pytest.mark.unit
class TestRenderDiffTable:
    """Tests for render_diff_table function."""

    def test_empty_diff_has_header(self) -> None:
        """Test empty diff shows no changes message.

        When there are no changes, the table renders a summary section
        with a 'No changes detected' message instead of showing empty table headers.
        """
        contract = SampleContract(name="test")
        diff = compute_contract_diff(contract, contract)
        table = render_diff_table(diff)

        # Empty diff shows summary and no-changes message
        assert "Summary" in table
        assert "No changes detected" in table

    def test_changes_appear_in_table(self) -> None:
        """Test that changes appear as table rows."""
        before = SampleContract(name="test", description="old")
        after = SampleContract(name="test", description="new")
        diff = compute_contract_diff(before, after)
        table = render_diff_table(diff)

        assert "description" in table.lower()
        assert "modified" in table.lower()

    def test_table_includes_old_and_new_values(self) -> None:
        """Test that table includes old and new values."""
        before = SampleContract(name="test", description="old_value")
        after = SampleContract(name="test", description="new_value")
        diff = compute_contract_diff(before, after)
        table = render_diff_table(diff)

        assert "old_value" in table
        assert "new_value" in table

    def test_table_format_is_markdown(self) -> None:
        """Test that table is in markdown format."""
        before = SampleContract(name="test", description="old")
        after = SampleContract(name="test", description="new")
        diff = compute_contract_diff(before, after)
        table = render_diff_table(diff)

        # Markdown tables use pipe characters
        assert "|" in table

    def test_table_handles_list_diffs(self) -> None:
        """Test that table includes list diff information."""
        before = SampleContract(name="test", tags=["a"])
        after = SampleContract(name="test", tags=["a", "b"])
        diff = compute_contract_diff(before, after)
        table = render_diff_table(diff)

        assert "tags" in table.lower()


# =================== CONVENIENCE FUNCTION TESTS ===================


@pytest.mark.unit
class TestComputeContractDiffConvenience:
    """Tests for compute_contract_diff convenience function."""

    def test_creates_computer_with_default_config(self) -> None:
        """Test function works without explicit config."""
        contract = SampleContract(name="test")
        diff = compute_contract_diff(contract, contract)
        assert diff is not None
        assert isinstance(diff, ModelContractDiff)

    def test_accepts_custom_config(self) -> None:
        """Test function accepts custom configuration."""
        config = ModelDiffConfiguration(include_unchanged=True)
        contract = SampleContract(name="test")
        diff = compute_contract_diff(contract, contract, config)
        assert diff is not None
        assert isinstance(diff, ModelContractDiff)

    def test_returns_consistent_results(self) -> None:
        """Test deterministic output - same input = same output."""
        before = SampleContract(name="test", description="old", version=1)
        after = SampleContract(name="test", description="new", version=2)

        diff1 = compute_contract_diff(before, after)
        diff2 = compute_contract_diff(before, after)

        assert diff1.total_changes == diff2.total_changes
        assert diff1.has_changes == diff2.has_changes
        assert len(diff1.field_diffs) == len(diff2.field_diffs)


# =================== CONTRACT DIFF COMPUTER CLASS TESTS ===================


@pytest.mark.unit
class TestContractDiffComputerClass:
    """Tests for ContractDiffComputer class directly."""

    def test_instantiation_with_default_config(self) -> None:
        """Test computer can be instantiated with default config."""
        computer = ContractDiffComputer()
        assert computer is not None

    def test_instantiation_with_custom_config(self) -> None:
        """Test computer can be instantiated with custom config."""
        config = ModelDiffConfiguration(include_unchanged=True)
        computer = ContractDiffComputer(config=config)
        assert computer is not None

    def test_compute_method_returns_diff_result(self) -> None:
        """Test compute method returns ModelContractDiff."""
        computer = ContractDiffComputer()
        before = SampleContract(name="test")
        after = SampleContract(name="test", description="new")
        diff = computer.compute_diff(before, after)

        assert isinstance(diff, ModelContractDiff)

    def test_computer_is_reusable(self) -> None:
        """Test same computer can be used for multiple diffs."""
        computer = ContractDiffComputer()

        contract1_before = SampleContract(name="test1")
        contract1_after = SampleContract(name="test1", description="new1")

        contract2_before = SampleContract(name="test2")
        contract2_after = SampleContract(name="test2", version=2)

        diff1 = computer.compute_diff(contract1_before, contract1_after)
        diff2 = computer.compute_diff(contract2_before, contract2_after)

        assert diff1.has_changes
        assert diff2.has_changes


# =================== EDGE CASE TESTS ===================


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_strings_comparison(self) -> None:
        """Test comparison with empty strings."""
        before = SampleContract(name="test", description="")
        after = SampleContract(name="test", description="content")
        diff = compute_contract_diff(before, after)

        assert diff.has_changes

    def test_empty_string_to_value_is_change(self) -> None:
        """Test that empty string to value is detected as change.

        Note: None -> value transitions in optional fields may cause validation
        issues since the field exists in both models. This test verifies that
        empty string to non-empty string is properly detected as a change.
        """
        before = SampleContractWithOptional(name="test", optional_field="")
        after = SampleContractWithOptional(name="test", optional_field="new_value")
        diff = compute_contract_diff(before, after)

        # "" vs "new_value" should be detected as a change
        assert diff.has_changes
        field_diff = next(
            (d for d in diff.field_diffs if "optional_field" in d.field_path), None
        )
        assert field_diff is not None
        assert field_diff.change_type == EnumContractDiffChangeType.MODIFIED

    def test_empty_list_vs_populated_list(self) -> None:
        """Test comparing empty list to populated list."""
        before = SampleContract(name="test", tags=[])
        after = SampleContract(name="test", tags=["single"])
        diff = compute_contract_diff(before, after)

        assert diff.has_changes
        assert diff.total_changes >= 1

    def test_deeply_nested_changes(self) -> None:
        """Test changes in deeply nested structures."""
        before = SampleContractWithNested(
            name="test",
            metadata={"level1": {"level2": {"level3": "old_value"}}},
        )
        after = SampleContractWithNested(
            name="test",
            metadata={"level1": {"level2": {"level3": "new_value"}}},
        )
        diff = compute_contract_diff(before, after)

        assert diff.has_changes

    def test_unicode_values_comparison(self) -> None:
        """Test comparison with unicode characters."""
        before = SampleContract(name="test", description="Hello World")
        after = SampleContract(name="test", description="Hello World!")
        diff = compute_contract_diff(before, after)

        assert diff.has_changes

    def test_numeric_string_vs_int(self) -> None:
        """Test that string '1' and int 1 are handled correctly."""
        # Using dict-based comparison since our model has typed fields
        before = SampleContractWithNested(
            name="test",
            metadata={"value": "1"},
        )
        after = SampleContractWithNested(
            name="test",
            metadata={"value": 1},
        )
        diff = compute_contract_diff(before, after)

        # Should detect as a change since types are different
        assert diff.has_changes

    def test_boolean_field_changes(self) -> None:
        """Test detection of boolean field changes."""
        before = SampleContractWithNested(
            name="test",
            config=NestedConfig(enabled=True),
        )
        after = SampleContractWithNested(
            name="test",
            config=NestedConfig(enabled=False),
        )
        diff = compute_contract_diff(before, after)

        assert diff.has_changes

    def test_large_list_comparison(self) -> None:
        """Test comparison of large lists for performance."""
        large_tags_before = [f"tag_{i}" for i in range(100)]
        large_tags_after = [f"tag_{i}" for i in range(100)]
        large_tags_after[50] = "modified_tag"

        before = SampleContract(name="test", tags=large_tags_before)
        after = SampleContract(name="test", tags=large_tags_after)
        diff = compute_contract_diff(before, after)

        assert diff.has_changes

    def test_list_with_duplicate_items(self) -> None:
        """Test list comparison with duplicate items."""
        before = SampleContract(name="test", tags=["a", "a", "b"])
        after = SampleContract(name="test", tags=["a", "b", "b"])
        diff = compute_contract_diff(before, after)

        # Depends on implementation - should detect the change
        # One 'a' removed, one 'b' added
        assert diff.has_changes


# =================== TYPE SAFETY TESTS ===================


@pytest.mark.unit
class TestTypeSafety:
    """Tests for type safety and validation."""

    def test_diff_result_is_immutable(self) -> None:
        """Test that diff result is immutable (frozen).

        Pydantic frozen models raise ValidationError when attempting
        to modify attributes.
        """
        from pydantic import ValidationError

        contract = SampleContract(name="test")
        diff = compute_contract_diff(contract, contract)

        # Attempting to modify a frozen Pydantic model raises ValidationError
        with pytest.raises(ValidationError):
            diff.has_changes = True  # type: ignore[misc]

    def test_field_diff_contains_required_fields(self) -> None:
        """Test that field diffs contain all required information."""
        before = SampleContract(name="test", description="old")
        after = SampleContract(name="test", description="new")
        diff = compute_contract_diff(before, after)

        assert len(diff.field_diffs) > 0
        field_diff = diff.field_diffs[0]

        # All field diffs should have these attributes
        assert hasattr(field_diff, "field_path")
        assert hasattr(field_diff, "change_type")
        assert hasattr(field_diff, "old_value")
        assert hasattr(field_diff, "new_value")

    def test_list_diff_contains_required_fields(self) -> None:
        """Test that list diffs contain all required information.

        Uses dependencies field which has an identity key configured,
        enabling identity-based list diffing that produces list_diffs.
        """
        before = SampleContract(name="test", dependencies=[{"name": "dep_a"}])
        after = SampleContract(
            name="test", dependencies=[{"name": "dep_a"}, {"name": "dep_b"}]
        )
        diff = compute_contract_diff(before, after)

        assert len(diff.list_diffs) > 0
        list_diff = diff.list_diffs[0]

        # All list diffs should have these attributes
        assert hasattr(list_diff, "field_path")
        assert hasattr(list_diff, "added_items")
        assert hasattr(list_diff, "removed_items")
        assert hasattr(list_diff, "modified_items")
        assert hasattr(list_diff, "moved_items")


# =================== DUPLICATE IDENTITY KEY TESTS ===================


@pytest.mark.unit
class TestDuplicateIdentityKeys:
    """Tests for handling duplicate identity keys in lists.

    When list items share the same identity value (e.g., two items with
    name="dep_a"), the algorithm uses composite keys to preserve all items
    and avoid silent data loss.
    """

    def test_duplicate_identity_uses_composite_key(self) -> None:
        """Test that duplicate identity keys use composite key disambiguation.

        When multiple items have the same identity value, later items get
        a composite key like 'value__index' to preserve them in the map.
        """
        before = SampleContract(
            name="test",
            dependencies=[
                {"name": "dep_a", "version": "1.0"},
                {"name": "dep_a", "version": "2.0"},  # Same name, different version
            ],
        )
        after = SampleContract(
            name="test",
            dependencies=[
                {"name": "dep_a", "version": "1.0"},
                {"name": "dep_a", "version": "3.0"},  # Modified the duplicate
            ],
        )
        diff = compute_contract_diff(before, after)

        # Both items should be tracked - the duplicate uses composite key
        deps_diff = next(
            (d for d in diff.list_diffs if "dependencies" in d.field_path), None
        )
        assert deps_diff is not None

        # The modification of the second item should be detected
        assert deps_diff.has_changes
        # Either modified (if composite key matched) or removed+added
        total_changes = (
            len(deps_diff.added_items)
            + len(deps_diff.removed_items)
            + len(deps_diff.modified_items)
        )
        assert total_changes >= 1

    def test_duplicate_identity_no_data_loss(self) -> None:
        """Test that duplicate identity keys don't cause silent data loss.

        Both items with the same identity should be preserved and compared.
        """
        before = SampleContract(
            name="test",
            dependencies=[
                {"name": "dup", "data": "first"},
                {"name": "dup", "data": "second"},
                {"name": "dup", "data": "third"},
            ],
        )
        after = SampleContract(
            name="test",
            dependencies=[
                {"name": "dup", "data": "first"},
                {"name": "dup", "data": "MODIFIED"},  # Changed
                {"name": "dup", "data": "third"},
            ],
        )
        diff = compute_contract_diff(before, after)

        deps_diff = next(
            (d for d in diff.list_diffs if "dependencies" in d.field_path), None
        )
        assert deps_diff is not None
        assert deps_diff.has_changes

    def test_duplicate_identity_all_removed(self) -> None:
        """Test removing all items with duplicate identity keys."""
        before = SampleContract(
            name="test",
            dependencies=[
                {"name": "dep_a"},
                {"name": "dep_a"},  # Duplicate
            ],
        )
        after = SampleContract(
            name="test",
            dependencies=[],
        )
        diff = compute_contract_diff(before, after)

        deps_diff = next(
            (d for d in diff.list_diffs if "dependencies" in d.field_path), None
        )
        assert deps_diff is not None
        # Both items should be detected as removed
        assert len(deps_diff.removed_items) == 2

    def test_duplicate_identity_all_added(self) -> None:
        """Test adding items that all have the same identity key."""
        before = SampleContract(
            name="test",
            dependencies=[],
        )
        after = SampleContract(
            name="test",
            dependencies=[
                {"name": "new_dep"},
                {"name": "new_dep"},  # Duplicate
                {"name": "new_dep"},  # Another duplicate
            ],
        )
        diff = compute_contract_diff(before, after)

        deps_diff = next(
            (d for d in diff.list_diffs if "dependencies" in d.field_path), None
        )
        assert deps_diff is not None
        # All three items should be detected as added
        assert len(deps_diff.added_items) == 3
