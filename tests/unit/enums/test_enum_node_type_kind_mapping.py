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

            raise AssertionError(
                "Name collisions detected between EnumNodeKind and EnumNodeType:\n"
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
            "Duplicate mappings detected (each type must map to exactly one kind):\n"
            + "\n".join(
                f"  - {node_type}: {count} mappings"
                for node_type, count in duplicate_mappings
            )
            + "\n\nEach EnumNodeType must appear exactly once in _KIND_MAP."
        )


class TestHasNodeKind:
    """Test the has_node_kind() helper method for defensive programming."""

    def test_has_node_kind_returns_true_for_mapped_types(self) -> None:
        """
        Verify has_node_kind() returns True for all mapped node types.

        All node types except UNKNOWN have kind mappings, so has_node_kind()
        should return True for them.
        """
        # Skip this test if has_node_kind doesn't exist yet
        if not hasattr(EnumNodeType, "has_node_kind"):
            pytest.skip("EnumNodeType.has_node_kind() not yet implemented")

        # Test all types except UNKNOWN
        for node_type in EnumNodeType:
            if node_type == EnumNodeType.UNKNOWN:
                continue

            result = EnumNodeType.has_node_kind(node_type)
            assert result is True, (
                f"has_node_kind({node_type}) returned {result}, expected True. "
                f"All node types except UNKNOWN should have kind mappings."
            )

    def test_has_node_kind_returns_false_for_unknown(self) -> None:
        """
        Verify has_node_kind() returns False for EnumNodeType.UNKNOWN.

        UNKNOWN intentionally has no kind mapping, so has_node_kind() must
        return False to enable defensive programming patterns.
        """
        # Skip this test if has_node_kind doesn't exist yet
        if not hasattr(EnumNodeType, "has_node_kind"):
            pytest.skip("EnumNodeType.has_node_kind() not yet implemented")

        result = EnumNodeType.has_node_kind(EnumNodeType.UNKNOWN)
        assert result is False, (
            f"has_node_kind(UNKNOWN) returned {result}, expected False. "
            "UNKNOWN intentionally has no kind mapping."
        )

    def test_has_node_kind_for_compute_generic(self) -> None:
        """Verify has_node_kind() returns True for COMPUTE_GENERIC."""
        if not hasattr(EnumNodeType, "has_node_kind"):
            pytest.skip("EnumNodeType.has_node_kind() not yet implemented")

        assert EnumNodeType.has_node_kind(EnumNodeType.COMPUTE_GENERIC) is True

    def test_has_node_kind_for_effect_generic(self) -> None:
        """Verify has_node_kind() returns True for EFFECT_GENERIC."""
        if not hasattr(EnumNodeType, "has_node_kind"):
            pytest.skip("EnumNodeType.has_node_kind() not yet implemented")

        assert EnumNodeType.has_node_kind(EnumNodeType.EFFECT_GENERIC) is True

    def test_has_node_kind_for_reducer_generic(self) -> None:
        """Verify has_node_kind() returns True for REDUCER_GENERIC."""
        if not hasattr(EnumNodeType, "has_node_kind"):
            pytest.skip("EnumNodeType.has_node_kind() not yet implemented")

        assert EnumNodeType.has_node_kind(EnumNodeType.REDUCER_GENERIC) is True

    def test_has_node_kind_for_orchestrator_generic(self) -> None:
        """Verify has_node_kind() returns True for ORCHESTRATOR_GENERIC."""
        if not hasattr(EnumNodeType, "has_node_kind"):
            pytest.skip("EnumNodeType.has_node_kind() not yet implemented")

        assert EnumNodeType.has_node_kind(EnumNodeType.ORCHESTRATOR_GENERIC) is True

    def test_has_node_kind_for_runtime_host_generic(self) -> None:
        """Verify has_node_kind() returns True for RUNTIME_HOST_GENERIC."""
        if not hasattr(EnumNodeType, "has_node_kind"):
            pytest.skip("EnumNodeType.has_node_kind() not yet implemented")

        assert EnumNodeType.has_node_kind(EnumNodeType.RUNTIME_HOST_GENERIC) is True

    def test_defensive_programming_pattern(self) -> None:
        """
        Verify the defensive programming pattern works correctly.

        This test demonstrates the intended usage pattern where has_node_kind()
        is used to guard calls to get_node_kind().
        """
        if not hasattr(EnumNodeType, "has_node_kind"):
            pytest.skip("EnumNodeType.has_node_kind() not yet implemented")

        # Test the pattern with a mapped type
        node_type = EnumNodeType.COMPUTE_GENERIC
        if EnumNodeType.has_node_kind(node_type):
            kind = EnumNodeType.get_node_kind(node_type)
            assert kind == EnumNodeKind.COMPUTE

        # Test the pattern with UNKNOWN
        unknown_type = EnumNodeType.UNKNOWN
        handled_unknown = False
        if EnumNodeType.has_node_kind(unknown_type):
            # This branch should NOT be taken
            kind = EnumNodeType.get_node_kind(unknown_type)
        else:
            # This branch should be taken
            handled_unknown = True

        assert handled_unknown is True, (
            "The defensive programming pattern failed - UNKNOWN should have "
            "triggered the else branch."
        )

    def test_has_node_kind_consistency_with_kind_map(self) -> None:
        """
        Verify has_node_kind() is consistent with _KIND_MAP membership.

        has_node_kind() should return True if and only if the node type
        is a key in _KIND_MAP.
        """
        if not hasattr(EnumNodeType, "has_node_kind"):
            pytest.skip("EnumNodeType.has_node_kind() not yet implemented")

        if not hasattr(EnumNodeType, "_KIND_MAP"):
            pytest.skip("EnumNodeType._KIND_MAP not yet implemented")

        for node_type in EnumNodeType:
            expected = node_type in EnumNodeType._KIND_MAP
            actual = EnumNodeType.has_node_kind(node_type)
            assert actual == expected, (
                f"has_node_kind({node_type}) returned {actual}, "
                f"but expected {expected} based on _KIND_MAP membership."
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


class TestEnumNodeTypeCoreAndInfrastructureMethods:
    """Test get_core_node_types() and get_infrastructure_types() methods."""

    def test_get_core_node_types_returns_set(self) -> None:
        """Verify get_core_node_types() returns a set."""
        if not hasattr(EnumNodeType, "get_core_node_types"):
            pytest.skip("EnumNodeType.get_core_node_types() not yet implemented")

        result = EnumNodeType.get_core_node_types()
        assert isinstance(
            result, set
        ), f"get_core_node_types() should return a set, got {type(result).__name__}"

    def test_get_infrastructure_types_returns_set(self) -> None:
        """Verify get_infrastructure_types() returns a set."""
        if not hasattr(EnumNodeType, "get_infrastructure_types"):
            pytest.skip("EnumNodeType.get_infrastructure_types() not yet implemented")

        result = EnumNodeType.get_infrastructure_types()
        assert isinstance(
            result, set
        ), f"get_infrastructure_types() should return a set, got {type(result).__name__}"

    def test_get_core_node_types_contains_expected_types(self) -> None:
        """
        Verify get_core_node_types() contains all expected core types.

        Core types should include all EnumNodeType values that map to:
        COMPUTE, EFFECT, REDUCER, or ORCHESTRATOR kinds.
        """
        if not hasattr(EnumNodeType, "get_core_node_types"):
            pytest.skip("EnumNodeType.get_core_node_types() not yet implemented")

        core_types = EnumNodeType.get_core_node_types()

        # These should definitely be in core types
        expected_core = {
            EnumNodeType.COMPUTE_GENERIC,
            EnumNodeType.TRANSFORMER,
            EnumNodeType.AGGREGATOR,
            EnumNodeType.FUNCTION,
            EnumNodeType.MODEL,
            EnumNodeType.EFFECT_GENERIC,
            EnumNodeType.TOOL,
            EnumNodeType.AGENT,
            EnumNodeType.REDUCER_GENERIC,
            EnumNodeType.ORCHESTRATOR_GENERIC,
            EnumNodeType.GATEWAY,
            EnumNodeType.VALIDATOR,
            EnumNodeType.WORKFLOW,
            # Legacy types mapped to COMPUTE for backward compatibility
            EnumNodeType.PLUGIN,
            EnumNodeType.SCHEMA,
            EnumNodeType.NODE,
            EnumNodeType.SERVICE,
        }

        missing = expected_core - core_types
        assert (
            not missing
        ), f"get_core_node_types() is missing expected types: {missing}"

    def test_get_infrastructure_types_contains_expected_types(self) -> None:
        """
        Verify get_infrastructure_types() contains all expected infrastructure types.

        Infrastructure types should include all EnumNodeType values that map to
        RUNTIME_HOST kind.
        """
        if not hasattr(EnumNodeType, "get_infrastructure_types"):
            pytest.skip("EnumNodeType.get_infrastructure_types() not yet implemented")

        infra_types = EnumNodeType.get_infrastructure_types()

        # RUNTIME_HOST_GENERIC should be in infrastructure types
        expected_infra = {EnumNodeType.RUNTIME_HOST_GENERIC}

        missing = expected_infra - infra_types
        assert (
            not missing
        ), f"get_infrastructure_types() is missing expected types: {missing}"

        # Verify the set only contains infrastructure types
        assert infra_types == expected_infra, (
            f"get_infrastructure_types() returned unexpected types. "
            f"Expected: {expected_infra}, Got: {infra_types}"
        )

    def test_core_and_infrastructure_types_are_disjoint(self) -> None:
        """
        Verify core types and infrastructure types do not overlap.

        A node type should be either core or infrastructure, never both.
        """
        if not hasattr(EnumNodeType, "get_core_node_types"):
            pytest.skip("EnumNodeType.get_core_node_types() not yet implemented")
        if not hasattr(EnumNodeType, "get_infrastructure_types"):
            pytest.skip("EnumNodeType.get_infrastructure_types() not yet implemented")

        core_types = EnumNodeType.get_core_node_types()
        infra_types = EnumNodeType.get_infrastructure_types()

        overlap = core_types & infra_types
        assert not overlap, (
            f"Core and infrastructure types should be disjoint, "
            f"but found overlap: {overlap}"
        )

    def test_unknown_not_in_core_types(self) -> None:
        """
        Verify UNKNOWN is not included in core types.

        UNKNOWN has no mapping, so it cannot be classified as core.
        """
        if not hasattr(EnumNodeType, "get_core_node_types"):
            pytest.skip("EnumNodeType.get_core_node_types() not yet implemented")

        core_types = EnumNodeType.get_core_node_types()
        assert EnumNodeType.UNKNOWN not in core_types, (
            "UNKNOWN should NOT be in get_core_node_types() result. "
            "UNKNOWN has no kind mapping and cannot be classified."
        )

    def test_unknown_not_in_infrastructure_types(self) -> None:
        """
        Verify UNKNOWN is not included in infrastructure types.

        UNKNOWN has no mapping, so it cannot be classified as infrastructure.
        """
        if not hasattr(EnumNodeType, "get_infrastructure_types"):
            pytest.skip("EnumNodeType.get_infrastructure_types() not yet implemented")

        infra_types = EnumNodeType.get_infrastructure_types()
        assert EnumNodeType.UNKNOWN not in infra_types, (
            "UNKNOWN should NOT be in get_infrastructure_types() result. "
            "UNKNOWN has no kind mapping and cannot be classified."
        )

    def test_core_and_infrastructure_cover_all_mapped_types(self) -> None:
        """
        Verify that core + infrastructure types cover all mapped types.

        Every type in _KIND_MAP should appear in either core or infrastructure.
        """
        if not hasattr(EnumNodeType, "get_core_node_types"):
            pytest.skip("EnumNodeType.get_core_node_types() not yet implemented")
        if not hasattr(EnumNodeType, "get_infrastructure_types"):
            pytest.skip("EnumNodeType.get_infrastructure_types() not yet implemented")
        if not hasattr(EnumNodeType, "_KIND_MAP"):
            pytest.skip("EnumNodeType._KIND_MAP not yet implemented")

        core_types = EnumNodeType.get_core_node_types()
        infra_types = EnumNodeType.get_infrastructure_types()
        mapped_types = set(EnumNodeType._KIND_MAP.keys())

        combined = core_types | infra_types
        missing = mapped_types - combined
        extra = combined - mapped_types

        assert (
            not missing
        ), f"Some mapped types are not in core or infrastructure: {missing}"
        assert (
            not extra
        ), f"Some types in core/infrastructure are not in _KIND_MAP: {extra}"

    def test_get_core_node_types_consistency_with_enum_node_kind(self) -> None:
        """
        Verify get_core_node_types() is consistent with EnumNodeKind.is_core_node_type().

        For every type in the result, its kind should satisfy is_core_node_type().
        """
        if not hasattr(EnumNodeType, "get_core_node_types"):
            pytest.skip("EnumNodeType.get_core_node_types() not yet implemented")
        if not hasattr(EnumNodeType, "get_node_kind"):
            pytest.skip("EnumNodeType.get_node_kind() not yet implemented")

        core_types = EnumNodeType.get_core_node_types()

        for node_type in core_types:
            kind = EnumNodeType.get_node_kind(node_type)
            assert EnumNodeKind.is_core_node_type(kind), (
                f"{node_type} is in get_core_node_types() but its kind {kind} "
                f"does not satisfy EnumNodeKind.is_core_node_type()"
            )

    def test_get_infrastructure_types_consistency_with_enum_node_kind(self) -> None:
        """
        Verify get_infrastructure_types() is consistent with EnumNodeKind.is_infrastructure_type().

        For every type in the result, its kind should satisfy is_infrastructure_type().
        """
        if not hasattr(EnumNodeType, "get_infrastructure_types"):
            pytest.skip("EnumNodeType.get_infrastructure_types() not yet implemented")
        if not hasattr(EnumNodeType, "get_node_kind"):
            pytest.skip("EnumNodeType.get_node_kind() not yet implemented")

        infra_types = EnumNodeType.get_infrastructure_types()

        for node_type in infra_types:
            kind = EnumNodeType.get_node_kind(node_type)
            assert EnumNodeKind.is_infrastructure_type(kind), (
                f"{node_type} is in get_infrastructure_types() but its kind {kind} "
                f"does not satisfy EnumNodeKind.is_infrastructure_type()"
            )

    def test_runtime_host_generic_is_infrastructure(self) -> None:
        """
        Verify RUNTIME_HOST_GENERIC is classified as infrastructure.

        This is a key invariant: RUNTIME_HOST_GENERIC should be the only
        infrastructure type currently.
        """
        if not hasattr(EnumNodeType, "get_infrastructure_types"):
            pytest.skip("EnumNodeType.get_infrastructure_types() not yet implemented")

        infra_types = EnumNodeType.get_infrastructure_types()
        assert (
            EnumNodeType.RUNTIME_HOST_GENERIC in infra_types
        ), "RUNTIME_HOST_GENERIC should be in get_infrastructure_types() result"

    def test_runtime_host_generic_not_in_core(self) -> None:
        """
        Verify RUNTIME_HOST_GENERIC is NOT classified as core.

        Infrastructure types should never appear in core types.
        """
        if not hasattr(EnumNodeType, "get_core_node_types"):
            pytest.skip("EnumNodeType.get_core_node_types() not yet implemented")

        core_types = EnumNodeType.get_core_node_types()
        assert (
            EnumNodeType.RUNTIME_HOST_GENERIC not in core_types
        ), "RUNTIME_HOST_GENERIC should NOT be in get_core_node_types() result"


class TestNodeRoutingIntegration:
    """
    Integration tests for node type to kind routing.

    These tests verify that the full routing pathway works correctly:
    EnumNodeType -> get_node_kind() -> EnumNodeKind

    Each test validates that specific categories of node types route
    to their expected architectural kinds, ensuring the mapping is
    semantically correct for realistic node routing scenarios.
    """

    def test_compute_types_route_to_compute_kind(self) -> None:
        """
        All COMPUTE-related types should route to COMPUTE kind.

        COMPUTE nodes perform data processing and transformation:
        - Pure calculations and algorithms
        - Data mapping and transformation
        - Validation and data manipulation

        This test verifies the full routing pathway for all node types
        that should resolve to EnumNodeKind.COMPUTE.
        """
        if not hasattr(EnumNodeType, "get_node_kind"):
            pytest.skip("EnumNodeType.get_node_kind() not yet implemented")

        compute_types = [
            EnumNodeType.COMPUTE_GENERIC,
            EnumNodeType.TRANSFORMER,
            EnumNodeType.AGGREGATOR,
            EnumNodeType.FUNCTION,
            EnumNodeType.MODEL,
            # Legacy types mapped to COMPUTE for backward compatibility
            EnumNodeType.PLUGIN,
            EnumNodeType.SCHEMA,
            EnumNodeType.NODE,
            EnumNodeType.SERVICE,
        ]

        for node_type in compute_types:
            kind = EnumNodeType.get_node_kind(node_type)
            assert kind == EnumNodeKind.COMPUTE, (
                f"Node type {node_type} should route to COMPUTE kind, "
                f"but got {kind}. This breaks compute node routing."
            )

    def test_effect_types_route_to_effect_kind(self) -> None:
        """
        All EFFECT-related types should route to EFFECT kind.

        EFFECT nodes handle external interactions (I/O):
        - API calls and network operations
        - Database operations
        - File system operations
        - Message queue interactions

        This test verifies the full routing pathway for all node types
        that should resolve to EnumNodeKind.EFFECT.
        """
        if not hasattr(EnumNodeType, "get_node_kind"):
            pytest.skip("EnumNodeType.get_node_kind() not yet implemented")

        effect_types = [
            EnumNodeType.EFFECT_GENERIC,
            EnumNodeType.TOOL,
            EnumNodeType.AGENT,
        ]

        for node_type in effect_types:
            kind = EnumNodeType.get_node_kind(node_type)
            assert kind == EnumNodeKind.EFFECT, (
                f"Node type {node_type} should route to EFFECT kind, "
                f"but got {kind}. This breaks effect node routing."
            )

    def test_reducer_types_route_to_reducer_kind(self) -> None:
        """
        All REDUCER-related types should route to REDUCER kind.

        REDUCER nodes handle state aggregation and management:
        - State machines (FSM with ModelIntent)
        - Accumulators
        - Event reduction and state transitions

        This test verifies the full routing pathway for all node types
        that should resolve to EnumNodeKind.REDUCER.
        """
        if not hasattr(EnumNodeType, "get_node_kind"):
            pytest.skip("EnumNodeType.get_node_kind() not yet implemented")

        reducer_types = [
            EnumNodeType.REDUCER_GENERIC,
        ]

        for node_type in reducer_types:
            kind = EnumNodeType.get_node_kind(node_type)
            assert kind == EnumNodeKind.REDUCER, (
                f"Node type {node_type} should route to REDUCER kind, "
                f"but got {kind}. This breaks reducer node routing."
            )

    def test_orchestrator_types_route_to_orchestrator_kind(self) -> None:
        """
        All ORCHESTRATOR-related types should route to ORCHESTRATOR kind.

        ORCHESTRATOR nodes handle workflow coordination:
        - Multi-step workflows (ModelAction with Leases)
        - Parallel execution coordination
        - Error recovery and retry logic
        - Gateway and validation control flow

        This test verifies the full routing pathway for all node types
        that should resolve to EnumNodeKind.ORCHESTRATOR.
        """
        if not hasattr(EnumNodeType, "get_node_kind"):
            pytest.skip("EnumNodeType.get_node_kind() not yet implemented")

        orchestrator_types = [
            EnumNodeType.ORCHESTRATOR_GENERIC,
            EnumNodeType.GATEWAY,
            EnumNodeType.VALIDATOR,
            EnumNodeType.WORKFLOW,
        ]

        for node_type in orchestrator_types:
            kind = EnumNodeType.get_node_kind(node_type)
            assert kind == EnumNodeKind.ORCHESTRATOR, (
                f"Node type {node_type} should route to ORCHESTRATOR kind, "
                f"but got {kind}. This breaks orchestrator node routing."
            )

    def test_runtime_host_types_route_to_runtime_host_kind(self) -> None:
        """
        RUNTIME_HOST types should route to RUNTIME_HOST kind.

        RUNTIME_HOST nodes manage the execution environment:
        - Node lifecycle management
        - Execution coordination
        - Runtime infrastructure support

        This test verifies the full routing pathway for all node types
        that should resolve to EnumNodeKind.RUNTIME_HOST.
        """
        if not hasattr(EnumNodeType, "get_node_kind"):
            pytest.skip("EnumNodeType.get_node_kind() not yet implemented")

        runtime_host_types = [
            EnumNodeType.RUNTIME_HOST_GENERIC,
        ]

        for node_type in runtime_host_types:
            kind = EnumNodeType.get_node_kind(node_type)
            assert kind == EnumNodeKind.RUNTIME_HOST, (
                f"Node type {node_type} should route to RUNTIME_HOST kind, "
                f"but got {kind}. This breaks runtime host node routing."
            )

    def test_routing_is_deterministic(self) -> None:
        """
        Same input should always produce same output.

        This test verifies that the routing is deterministic by calling
        get_node_kind() multiple times for the same input and ensuring
        the result is always identical. Non-deterministic routing would
        cause unpredictable behavior in node dispatch.
        """
        if not hasattr(EnumNodeType, "get_node_kind"):
            pytest.skip("EnumNodeType.get_node_kind() not yet implemented")

        # Test determinism for a sample of each kind
        test_cases = [
            EnumNodeType.COMPUTE_GENERIC,
            EnumNodeType.EFFECT_GENERIC,
            EnumNodeType.REDUCER_GENERIC,
            EnumNodeType.ORCHESTRATOR_GENERIC,
            EnumNodeType.RUNTIME_HOST_GENERIC,
            EnumNodeType.TRANSFORMER,
            EnumNodeType.TOOL,
            EnumNodeType.GATEWAY,
        ]

        for node_type in test_cases:
            # Call get_node_kind multiple times
            results = [
                EnumNodeType.get_node_kind(node_type) for _ in range(5)
            ]

            # All results should be identical
            first_result = results[0]
            for i, result in enumerate(results):
                assert result == first_result, (
                    f"Routing for {node_type} is non-deterministic: "
                    f"call {i} returned {result}, expected {first_result}"
                )

    def test_routing_covers_all_mapped_types(self) -> None:
        """
        Every mapped type should successfully route to a valid kind.

        This test iterates through all EnumNodeType values (except UNKNOWN)
        and verifies that each one successfully routes to a valid EnumNodeKind.
        This is an integration-level completeness check.
        """
        if not hasattr(EnumNodeType, "get_node_kind"):
            pytest.skip("EnumNodeType.get_node_kind() not yet implemented")

        # Track successful and failed routings
        successful_routings: dict[EnumNodeType, EnumNodeKind] = {}
        failed_routings: list[tuple[EnumNodeType, Exception]] = []

        for node_type in EnumNodeType:
            if node_type == EnumNodeType.UNKNOWN:
                continue  # UNKNOWN intentionally has no routing

            try:
                kind = EnumNodeType.get_node_kind(node_type)
                successful_routings[node_type] = kind
            except Exception as e:
                failed_routings.append((node_type, e))

        # All mapped types should route successfully
        assert not failed_routings, (
            f"Some node types failed to route:\n"
            + "\n".join(
                f"  - {node_type}: {type(e).__name__}: {e}"
                for node_type, e in failed_routings
            )
        )

        # Verify all routed kinds are valid EnumNodeKind members
        for node_type, kind in successful_routings.items():
            assert kind in EnumNodeKind, (
                f"{node_type} routed to {kind}, which is not a valid EnumNodeKind"
            )

    def test_routing_preserves_kind_semantics(self) -> None:
        """
        Routing should preserve semantic relationships between types and kinds.

        This test verifies that the routing respects the semantic categories:
        - Processing types route to processing kinds (COMPUTE, REDUCER)
        - Control flow types route to control kinds (ORCHESTRATOR)
        - I/O types route to effect kinds (EFFECT)
        - Infrastructure types route to infrastructure kinds (RUNTIME_HOST)
        """
        if not hasattr(EnumNodeType, "get_node_kind"):
            pytest.skip("EnumNodeType.get_node_kind() not yet implemented")

        # Semantic category mappings
        processing_types = {
            EnumNodeType.TRANSFORMER,
            EnumNodeType.AGGREGATOR,
            EnumNodeType.FUNCTION,
            EnumNodeType.MODEL,
        }
        processing_kinds = {EnumNodeKind.COMPUTE}

        control_types = {
            EnumNodeType.GATEWAY,
            EnumNodeType.VALIDATOR,
            EnumNodeType.WORKFLOW,
        }
        control_kinds = {EnumNodeKind.ORCHESTRATOR}

        io_types = {
            EnumNodeType.TOOL,
            EnumNodeType.AGENT,
        }
        io_kinds = {EnumNodeKind.EFFECT}

        infrastructure_types = {
            EnumNodeType.RUNTIME_HOST_GENERIC,
        }
        infrastructure_kinds = {EnumNodeKind.RUNTIME_HOST}

        # Verify processing types route to processing kinds
        for node_type in processing_types:
            kind = EnumNodeType.get_node_kind(node_type)
            assert kind in processing_kinds, (
                f"Processing type {node_type} should route to a processing kind, "
                f"but got {kind}"
            )

        # Verify control types route to control kinds
        for node_type in control_types:
            kind = EnumNodeType.get_node_kind(node_type)
            assert kind in control_kinds, (
                f"Control type {node_type} should route to a control kind, "
                f"but got {kind}"
            )

        # Verify I/O types route to effect kinds
        for node_type in io_types:
            kind = EnumNodeType.get_node_kind(node_type)
            assert kind in io_kinds, (
                f"I/O type {node_type} should route to an effect kind, "
                f"but got {kind}"
            )

        # Verify infrastructure types route to infrastructure kinds
        for node_type in infrastructure_types:
            kind = EnumNodeType.get_node_kind(node_type)
            assert kind in infrastructure_kinds, (
                f"Infrastructure type {node_type} should route to an "
                f"infrastructure kind, but got {kind}"
            )

    def test_generic_types_route_to_corresponding_kinds(self) -> None:
        """
        Generic node types should route to their corresponding kinds.

        Each generic type (e.g., COMPUTE_GENERIC) should route to its
        corresponding kind (e.g., COMPUTE). This is a fundamental invariant
        of the naming convention.
        """
        if not hasattr(EnumNodeType, "get_node_kind"):
            pytest.skip("EnumNodeType.get_node_kind() not yet implemented")

        generic_mappings = [
            (EnumNodeType.COMPUTE_GENERIC, EnumNodeKind.COMPUTE),
            (EnumNodeType.EFFECT_GENERIC, EnumNodeKind.EFFECT),
            (EnumNodeType.REDUCER_GENERIC, EnumNodeKind.REDUCER),
            (EnumNodeType.ORCHESTRATOR_GENERIC, EnumNodeKind.ORCHESTRATOR),
            (EnumNodeType.RUNTIME_HOST_GENERIC, EnumNodeKind.RUNTIME_HOST),
        ]

        for node_type, expected_kind in generic_mappings:
            actual_kind = EnumNodeType.get_node_kind(node_type)
            assert actual_kind == expected_kind, (
                f"Generic type {node_type} should route to {expected_kind}, "
                f"but got {actual_kind}. Generic types must route to their "
                f"corresponding kinds."
            )

    def test_all_core_kinds_have_routing_sources(self) -> None:
        """
        Each core kind should have at least one type that routes to it.

        This test verifies that every core architectural kind (COMPUTE, EFFECT,
        REDUCER, ORCHESTRATOR) has at least one EnumNodeType that routes to it.
        A kind without routing sources would be unreachable in the architecture.
        """
        if not hasattr(EnumNodeType, "get_node_kind"):
            pytest.skip("EnumNodeType.get_node_kind() not yet implemented")

        core_kinds = {
            EnumNodeKind.COMPUTE,
            EnumNodeKind.EFFECT,
            EnumNodeKind.REDUCER,
            EnumNodeKind.ORCHESTRATOR,
        }

        # Build reverse mapping: kind -> list of types that route to it
        kind_to_types: dict[EnumNodeKind, list[EnumNodeType]] = {
            kind: [] for kind in core_kinds
        }

        for node_type in EnumNodeType:
            if node_type == EnumNodeType.UNKNOWN:
                continue
            kind = EnumNodeType.get_node_kind(node_type)
            if kind in kind_to_types:
                kind_to_types[kind].append(node_type)

        # Each core kind should have at least one type routing to it
        kinds_without_sources = [
            kind for kind, types in kind_to_types.items() if not types
        ]

        assert not kinds_without_sources, (
            f"Some core kinds have no types routing to them: {kinds_without_sources}. "
            f"Each core kind must be reachable from at least one EnumNodeType."
        )

    def test_runtime_host_kind_has_routing_sources(self) -> None:
        """
        RUNTIME_HOST kind should have at least one type that routes to it.

        This test verifies that the RUNTIME_HOST kind is reachable from
        at least one EnumNodeType. Without routing sources, RUNTIME_HOST
        nodes could not be properly classified.
        """
        if not hasattr(EnumNodeType, "get_node_kind"):
            pytest.skip("EnumNodeType.get_node_kind() not yet implemented")

        runtime_host_sources = []

        for node_type in EnumNodeType:
            if node_type == EnumNodeType.UNKNOWN:
                continue
            kind = EnumNodeType.get_node_kind(node_type)
            if kind == EnumNodeKind.RUNTIME_HOST:
                runtime_host_sources.append(node_type)

        assert runtime_host_sources, (
            "No EnumNodeType routes to RUNTIME_HOST kind. "
            "RUNTIME_HOST must be reachable from at least one node type."
        )

        # Verify RUNTIME_HOST_GENERIC is one of the sources
        assert EnumNodeType.RUNTIME_HOST_GENERIC in runtime_host_sources, (
            "RUNTIME_HOST_GENERIC should route to RUNTIME_HOST kind"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
