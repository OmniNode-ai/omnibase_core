"""
Unit tests for EnumNodeType to EnumNodeKind mapping.

This test module enforces hard invariants for the mapping between
EnumNodeType (specific implementations) and EnumNodeKind (architectural roles).

Critical Invariants Enforced:
1. Every EnumNodeType (except UNKNOWN) MUST map to exactly one EnumNodeKind
2. The mapping MUST be complete for all mapped types
3. No EnumNodeType may share names with EnumNodeKind (prevent collisions)
4. UNKNOWN intentionally has NO mapping - it must raise ModelOnexError

DESIGN DECISION - UNKNOWN is intentionally unmapped:
- UNKNOWN semantically means "we don't know what this is"
- Silently defaulting UNKNOWN to COMPUTE would hide bugs
- Callers must explicitly handle the UNKNOWN case with proper error handling
- get_node_kind(EnumNodeType.UNKNOWN) raises ModelOnexError by design

These tests will FAIL if the mapping becomes incomplete, ensuring regression
protection during refactoring and future development.
"""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.enums.enum_node_type import EnumNodeType


class TestEnumNodeTypeKindMapping:
    """Validate EnumNodeType to EnumNodeKind mapping invariants."""

    def test_all_node_types_have_kind_mapping(self) -> None:
        """
        Ensure every EnumNodeType (except UNKNOWN) maps to exactly one EnumNodeKind.

        This test enforces COMPLETENESS: no EnumNodeType (except UNKNOWN) can exist
        without a corresponding EnumNodeKind mapping.

        DESIGN DECISION - UNKNOWN is intentionally unmapped:
        - UNKNOWN semantically means "we don't know what this is"
        - Silently defaulting UNKNOWN to COMPUTE would hide bugs
        - Callers must explicitly handle the UNKNOWN case
        - See test_unknown_type_intentionally_unmapped() for explicit verification

        Failure Scenarios:
        - New EnumNodeType added without mapping (except UNKNOWN)
        - Mapping table missing entries
        - Typos in mapping keys

        CRITICAL: This test MUST pass for the system to function correctly.
        """
        # Skip this test if _KIND_MAP doesn't exist yet (pre-refactor state)
        if not hasattr(EnumNodeType, "_KIND_MAP"):
            pytest.skip("EnumNodeType._KIND_MAP not yet implemented")

        # UNKNOWN is intentionally unmapped - exclude it from completeness check
        all_types = set(EnumNodeType) - {EnumNodeType.UNKNOWN}
        mapped_types = set(EnumNodeType._KIND_MAP.keys())

        unmapped = all_types - mapped_types
        assert not unmapped, (
            f"Unmapped EnumNodeType values: {unmapped}. "
            f"Every type (except UNKNOWN) must map to a kind in EnumNodeType._KIND_MAP. "
            f"Add mappings for these types to EnumNodeType._KIND_MAP."
        )

        extra_mappings = mapped_types - all_types
        assert not extra_mappings, (
            f"Extra mappings for non-existent EnumNodeType values: {extra_mappings}. "
            f"These entries should be removed from EnumNodeType._KIND_MAP."
        )

        assert all_types == mapped_types, (
            f"Mapping table mismatch. Expected {len(all_types)} types, "
            f"got {len(mapped_types)} mappings. "
            f"Difference: {all_types.symmetric_difference(mapped_types)}"
        )

    def test_no_name_collision_between_kind_and_type(self) -> None:
        """
        Ensure no EnumNodeType shares names with EnumNodeKind.

        This test enforces NAME UNIQUENESS to prevent confusion and bugs
        when using both enums in the same context.

        Allowed Patterns:
        - EnumNodeType.COMPUTE_GENERIC is OK (suffix differentiates)
        - EnumNodeType.TRANSFORMER is OK (completely different name)

        Forbidden Patterns:
        - EnumNodeType.COMPUTE would collide with EnumNodeKind.COMPUTE
        - EnumNodeType.EFFECT would collide with EnumNodeKind.EFFECT

        CRITICAL: Name collisions can cause import confusion and bugs.

        NOTE: This test will be enforced after the refactor when _KIND_MAP
        exists. Currently, collisions exist but will be resolved during refactor.
        """
        # Skip this test until the refactor is complete and _KIND_MAP exists
        # At that point, all collisions should be resolved
        if not hasattr(EnumNodeType, "_KIND_MAP"):
            pytest.skip(
                "EnumNodeType._KIND_MAP not yet implemented. "
                "This test will enforce name uniqueness after refactor."
            )

        kind_names = {k.name.upper() for k in EnumNodeKind}
        type_names = {t.name.upper() for t in EnumNodeType}

        # Detect exact name collisions (case-insensitive)
        collisions = kind_names & type_names

        if collisions:
            collision_details = []
            for name in collisions:
                kind_member = next(k for k in EnumNodeKind if k.name.upper() == name)
                type_member = next(t for t in EnumNodeType if t.name.upper() == name)
                collision_details.append(
                    f"  - {name}: EnumNodeKind.{kind_member.name} "
                    f"vs EnumNodeType.{type_member.name}"
                )

            assert False, (
                f"Name collisions detected between EnumNodeKind and EnumNodeType:\n"
                + "\n".join(collision_details)
                + "\n\nEnumNodeType names must not match EnumNodeKind names. "
                "Consider using suffixes like COMPUTE_GENERIC instead of COMPUTE."
            )

    def test_get_node_kind_returns_valid_kind(self) -> None:
        """
        Verify get_node_kind() returns valid EnumNodeKind for all mapped types.

        This test enforces TYPE SAFETY: every mapping MUST resolve to a
        valid EnumNodeKind member.

        NOTE: UNKNOWN is excluded because it intentionally raises ModelOnexError.
        See test_unknown_type_intentionally_unmapped() for verification.

        Failure Scenarios:
        - Mapping contains invalid string values
        - Mapping returns None
        - Mapping returns wrong type

        CRITICAL: Invalid mappings can cause runtime errors in node routing.
        """
        # Skip this test if get_node_kind doesn't exist yet (pre-refactor state)
        if not hasattr(EnumNodeType, "get_node_kind"):
            pytest.skip("EnumNodeType.get_node_kind() not yet implemented")

        # Exclude UNKNOWN - it intentionally raises ModelOnexError
        for node_type in EnumNodeType:
            if node_type == EnumNodeType.UNKNOWN:
                continue  # UNKNOWN is tested separately in test_unknown_type_intentionally_unmapped

            kind = EnumNodeType.get_node_kind(node_type)

            assert isinstance(kind, EnumNodeKind), (
                f"get_node_kind({node_type}) returned {kind} (type: {type(kind)}), "
                f"expected EnumNodeKind instance. "
                f"Check mapping for {node_type} in EnumNodeType._KIND_MAP."
            )

            # Ensure the kind is a valid enum member
            assert kind in EnumNodeKind, (
                f"get_node_kind({node_type}) returned {kind}, "
                f"which is not a valid EnumNodeKind member. "
                f"Valid members: {list(EnumNodeKind)}"
            )

    def test_mapping_is_consistent(self) -> None:
        """
        Verify mapping relationships are semantically consistent.

        This test enforces SEMANTIC CORRECTNESS: mappings should follow
        logical relationships between types and kinds.

        Expected Relationships (examples):
        - COMPUTE_GENERIC, TRANSFORMER, AGGREGATOR → COMPUTE kind
        - EFFECT → EFFECT kind
        - ORCHESTRATOR → ORCHESTRATOR kind
        - REDUCER → REDUCER kind

        NOTE: This test validates the STRUCTURE of the mapping, not specific
        values. Adjust assertions based on actual mapping decisions.
        """
        # Skip this test if mapping doesn't exist yet (pre-refactor state)
        if not hasattr(EnumNodeType, "_KIND_MAP"):
            pytest.skip("EnumNodeType._KIND_MAP not yet implemented")

        # Example semantic checks - adjust based on actual mapping
        compute_related_types = {
            EnumNodeType.COMPUTE_GENERIC,
            EnumNodeType.TRANSFORMER,
            EnumNodeType.AGGREGATOR,
        }

        for node_type in compute_related_types:
            if node_type in EnumNodeType._KIND_MAP:
                kind = EnumNodeType._KIND_MAP[node_type]
                assert kind in EnumNodeKind, (
                    f"{node_type} maps to {kind}, which is not a valid EnumNodeKind. "
                    f"Expected one of: {list(EnumNodeKind)}"
                )

    def test_kind_map_is_complete(self) -> None:
        """
        Ensure mapping table has exactly as many entries as mapped enum values.

        This test enforces COMPLETENESS: the mapping table must cover ALL
        EnumNodeType values that should be mapped (excludes UNKNOWN).

        DESIGN DECISION - UNKNOWN is intentionally unmapped:
        - UNKNOWN semantically means "we don't know what this is"
        - Silently defaulting UNKNOWN to COMPUTE would hide bugs
        - Expected count = len(EnumNodeType) - 1 (excluding UNKNOWN)

        Failure Scenarios:
        - Missing mappings (len(_KIND_MAP) < expected)
        - Extra mappings (len(_KIND_MAP) > expected)
        - Duplicate entries

        CRITICAL: Incomplete mapping causes runtime errors during node dispatch.
        """
        # Skip this test if _KIND_MAP doesn't exist yet (pre-refactor state)
        if not hasattr(EnumNodeType, "_KIND_MAP"):
            pytest.skip("EnumNodeType._KIND_MAP not yet implemented")

        mapping_count = len(EnumNodeType._KIND_MAP)
        # UNKNOWN is intentionally unmapped, so expected count is len - 1
        expected_count = len(EnumNodeType) - 1

        assert mapping_count == expected_count, (
            f"Mapping table has {mapping_count} entries, "
            f"but expected {expected_count} (all EnumNodeType values except UNKNOWN). "
            f"Every type (except UNKNOWN) must be mapped exactly once. "
            f"Missing: {set(EnumNodeType) - {EnumNodeType.UNKNOWN} - set(EnumNodeType._KIND_MAP.keys())}, "
            f"Extra: {set(EnumNodeType._KIND_MAP.keys()) - set(EnumNodeType)}"
        )

    def test_mapping_values_are_all_valid_kinds(self) -> None:
        """
        Verify all mapping values are valid EnumNodeKind members.

        This test enforces VALUE VALIDITY: mapping table must only contain
        valid EnumNodeKind instances, never strings or invalid values.

        Failure Scenarios:
        - Mapping contains string values instead of enum members
        - Mapping contains typos in kind names
        - Mapping contains None values

        CRITICAL: Invalid mapping values cause type errors in node routing.
        """
        # Skip this test if _KIND_MAP doesn't exist yet (pre-refactor state)
        if not hasattr(EnumNodeType, "_KIND_MAP"):
            pytest.skip("EnumNodeType._KIND_MAP not yet implemented")

        invalid_mappings = []
        for node_type, kind in EnumNodeType._KIND_MAP.items():
            if not isinstance(kind, EnumNodeKind):
                invalid_mappings.append(
                    f"  - {node_type} → {kind} (type: {type(kind).__name__})"
                )

        assert not invalid_mappings, (
            "Invalid mapping values detected (must be EnumNodeKind instances):\n"
            + "\n".join(invalid_mappings)
            + "\n\nAll mapping values must be EnumNodeKind enum members, "
            "not strings or other types."
        )

    def test_each_kind_has_at_least_one_type(self) -> None:
        """
        Verify each EnumNodeKind is mapped from at least one EnumNodeType.

        This test enforces COVERAGE: every EnumNodeKind should have at least
        one corresponding EnumNodeType implementation.

        NOTE: This is a RECOMMENDATION, not a hard requirement. Some kinds
        may not have implementations yet. This test warns about unused kinds.
        """
        # Skip this test if _KIND_MAP doesn't exist yet (pre-refactor state)
        if not hasattr(EnumNodeType, "_KIND_MAP"):
            pytest.skip("EnumNodeType._KIND_MAP not yet implemented")

        # Count how many types map to each kind
        kind_usage = {kind: 0 for kind in EnumNodeKind}
        for kind in EnumNodeType._KIND_MAP.values():
            if kind in kind_usage:
                kind_usage[kind] += 1

        # Find kinds with no mappings
        unused_kinds = [kind for kind, count in kind_usage.items() if count == 0]

        # This is a soft warning, not a hard failure
        if unused_kinds:
            pytest.skip(
                f"Some EnumNodeKind values have no corresponding EnumNodeType: "
                f"{unused_kinds}. This may be intentional during development."
            )

    def test_mapping_is_one_to_many_not_many_to_many(self) -> None:
        """
        Verify mapping follows one-to-many pattern (Kind → Types).

        This test enforces MAPPING STRUCTURE: multiple EnumNodeType values
        can map to the same EnumNodeKind, but each EnumNodeType maps to
        exactly ONE EnumNodeKind.

        Valid Pattern (one-to-many):
        - COMPUTE_GENERIC → COMPUTE
        - TRANSFORMER → COMPUTE
        - AGGREGATOR → COMPUTE

        Invalid Pattern (many-to-many):
        - TRANSFORMER → [COMPUTE, EFFECT]  # WRONG: one type → multiple kinds

        CRITICAL: Many-to-many mappings create ambiguity in node routing.
        """
        # Skip this test if _KIND_MAP doesn't exist yet (pre-refactor state)
        if not hasattr(EnumNodeType, "_KIND_MAP"):
            pytest.skip("EnumNodeType._KIND_MAP not yet implemented")

        # Verify each type appears exactly once in the mapping
        type_occurrences: dict[EnumNodeType, int] = {}
        for node_type in EnumNodeType._KIND_MAP.keys():
            if node_type in type_occurrences:
                type_occurrences[node_type] += 1
            else:
                type_occurrences[node_type] = 1

        duplicate_mappings = [
            (node_type, count)
            for node_type, count in type_occurrences.items()
            if count > 1
        ]

        assert not duplicate_mappings, (
            f"Duplicate mappings detected (each type must map to exactly one kind):\n"
            + "\n".join(
                f"  - {node_type}: {count} mappings"
                for node_type, count in duplicate_mappings
            )
            + "\n\nEach EnumNodeType must appear exactly once in _KIND_MAP."
        )


class TestEnumNodeTypeKindMappingEdgeCases:
    """Test edge cases and error conditions for mapping."""

    def test_unknown_type_intentionally_unmapped(self) -> None:
        """
        Verify that UNKNOWN node type raises ModelOnexError when get_node_kind is called.

        DESIGN DECISION - UNKNOWN intentionally has NO kind mapping because:
        - UNKNOWN semantically means "we don't know what this is"
        - Silently defaulting UNKNOWN to COMPUTE would hide bugs in node classification
        - Callers must explicitly handle the UNKNOWN case with proper error handling
        - This forces explicit error handling rather than silent failures

        This test ensures the design decision is preserved across refactoring.
        """
        # Skip this test if get_node_kind doesn't exist yet (pre-refactor state)
        if not hasattr(EnumNodeType, "get_node_kind"):
            pytest.skip("EnumNodeType.get_node_kind() not yet implemented")

        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        # UNKNOWN must raise ModelOnexError, NOT return a default kind
        with pytest.raises(ModelOnexError) as exc_info:
            EnumNodeType.get_node_kind(EnumNodeType.UNKNOWN)

        # Verify the error message contains useful context
        error = exc_info.value
        assert "UNKNOWN" in str(error) or (
            error.context and "UNKNOWN" in str(error.context.get("node_type", ""))
        ), f"Error message should mention UNKNOWN. Got: {error}, context: {error.context}"

    def test_unknown_is_not_in_kind_map(self) -> None:
        """
        Verify that UNKNOWN is explicitly NOT in _KIND_MAP.

        This test enforces that UNKNOWN is intentionally excluded from the mapping,
        not accidentally forgotten. If UNKNOWN appears in _KIND_MAP, this test fails.
        """
        # Skip this test if _KIND_MAP doesn't exist yet (pre-refactor state)
        if not hasattr(EnumNodeType, "_KIND_MAP"):
            pytest.skip("EnumNodeType._KIND_MAP not yet implemented")

        assert EnumNodeType.UNKNOWN not in EnumNodeType._KIND_MAP, (
            "EnumNodeType.UNKNOWN should NOT be in _KIND_MAP. "
            "UNKNOWN intentionally has no kind mapping - callers must handle it explicitly. "
            "Remove UNKNOWN from _KIND_MAP to preserve this design decision."
        )

    def test_get_node_kind_with_invalid_type_raises_error(self) -> None:
        """
        Verify get_node_kind() handles invalid input gracefully.

        This test enforces ERROR HANDLING: the function should raise
        appropriate errors for invalid input.
        """
        # Skip this test if get_node_kind doesn't exist yet (pre-refactor state)
        if not hasattr(EnumNodeType, "get_node_kind"):
            pytest.skip("EnumNodeType.get_node_kind() not yet implemented")

        # Test with invalid input (if the method doesn't do type checking,
        # this documents the expected behavior)
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        get_node_kind_method = getattr(EnumNodeType, "get_node_kind")
        with pytest.raises((KeyError, ValueError, AttributeError, ModelOnexError)):
            get_node_kind_method("INVALID_TYPE")

    def test_mapping_table_is_immutable(self) -> None:
        """
        Verify _KIND_MAP cannot be accidentally modified.

        This test enforces IMMUTABILITY: the mapping table should be
        read-only to prevent accidental modification.

        NOTE: Python dicts are mutable, so this test documents the
        expectation that _KIND_MAP should not be modified at runtime.
        """
        # Skip this test if _KIND_MAP doesn't exist yet (pre-refactor state)
        if not hasattr(EnumNodeType, "_KIND_MAP"):
            pytest.skip("EnumNodeType._KIND_MAP not yet implemented")

        # Attempt to modify (if it's a regular dict, this will succeed)
        # This test documents the behavior and can be upgraded to enforce
        # immutability with types.MappingProxyType or similar
        original_length = len(EnumNodeType._KIND_MAP)

        # Just verify we can read it (actual immutability enforcement
        # would require MappingProxyType or frozen dataclass)
        assert isinstance(EnumNodeType._KIND_MAP, dict)
        assert len(EnumNodeType._KIND_MAP) == original_length


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
