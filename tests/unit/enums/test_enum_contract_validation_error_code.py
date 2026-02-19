# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Tests for EnumContractValidationErrorCode.

Tests all aspects of the contract validation error code enumeration including:
- Value validation and integrity
- String conversion and comparison
- Enum member existence for merge and expanded phases
- Serialization/deserialization
- Pydantic model compatibility
- Edge cases and error conditions

Related:
    - OMN-1128: Contract Validation Pipeline
"""

import copy
import json
import pickle
from enum import Enum

import pytest

from omnibase_core.enums.enum_contract_validation_error_code import (
    EnumContractValidationErrorCode,
)


@pytest.mark.unit
class TestEnumContractValidationErrorCode:
    """Test cases for EnumContractValidationErrorCode."""

    def test_enum_inherits_from_str_and_enum(self) -> None:
        """Test that EnumContractValidationErrorCode properly inherits from str and Enum."""
        assert issubclass(EnumContractValidationErrorCode, str)
        assert issubclass(EnumContractValidationErrorCode, Enum)

    def test_all_merge_error_codes_exist(self) -> None:
        """Test that all Phase 2 (merge) error codes exist."""
        merge_codes = [
            "CONTRACT_VALIDATION_MERGE_REQUIRED_OVERRIDE_MISSING",
            "CONTRACT_VALIDATION_MERGE_PLACEHOLDER_VALUE_REJECTED",
            "CONTRACT_VALIDATION_MERGE_DEPENDENCY_REFERENCE_UNRESOLVED",
            "CONTRACT_VALIDATION_MERGE_PROFILE_NOT_FOUND",
            "CONTRACT_VALIDATION_MERGE_BASE_CONTRACT_INVALID",
            "CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED",
        ]

        for code in merge_codes:
            assert hasattr(EnumContractValidationErrorCode, code), (
                f"Missing merge error code: {code}"
            )

    def test_all_expanded_error_codes_exist(self) -> None:
        """Test that all Phase 3 (expanded) error codes exist."""
        expanded_codes = [
            "CONTRACT_VALIDATION_EXPANDED_EXECUTION_GRAPH_CYCLE",
            "CONTRACT_VALIDATION_EXPANDED_EXECUTION_GRAPH_ORPHAN",
            "CONTRACT_VALIDATION_EXPANDED_EVENT_ROUTING_INVALID",
            "CONTRACT_VALIDATION_EXPANDED_EVENT_CONSUMER_MISSING",
            "CONTRACT_VALIDATION_EXPANDED_DEPENDENCY_TYPE_MISMATCH",
            "CONTRACT_VALIDATION_EXPANDED_CAPABILITY_UNRESOLVED",
            "CONTRACT_VALIDATION_EXPANDED_RUNTIME_INVARIANT_VIOLATED",
            "CONTRACT_VALIDATION_EXPANDED_HANDLER_ID_INVALID",
            "CONTRACT_VALIDATION_EXPANDED_MODEL_REFERENCE_INVALID",
        ]

        for code in expanded_codes:
            assert hasattr(EnumContractValidationErrorCode, code), (
                f"Missing expanded error code: {code}"
            )

    def test_enum_string_values_match_names(self) -> None:
        """Test that enum values match their names (self-documenting pattern)."""
        for member in EnumContractValidationErrorCode:
            # The value should equal the name for self-documenting error codes
            assert member.value == member.name, (
                f"Error code {member.name} has mismatched value {member.value}"
            )


@pytest.mark.unit
class TestEnumContractValidationErrorCodeMerge:
    """Test cases specifically for merge validation error codes."""

    def test_merge_required_override_missing_value(self) -> None:
        """Test CONTRACT_VALIDATION_MERGE_REQUIRED_OVERRIDE_MISSING value."""
        code = EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_REQUIRED_OVERRIDE_MISSING
        assert code.value == "CONTRACT_VALIDATION_MERGE_REQUIRED_OVERRIDE_MISSING"

    def test_merge_placeholder_value_rejected_value(self) -> None:
        """Test CONTRACT_VALIDATION_MERGE_PLACEHOLDER_VALUE_REJECTED value."""
        code = EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_PLACEHOLDER_VALUE_REJECTED
        assert code.value == "CONTRACT_VALIDATION_MERGE_PLACEHOLDER_VALUE_REJECTED"

    def test_merge_dependency_reference_unresolved_value(self) -> None:
        """Test CONTRACT_VALIDATION_MERGE_DEPENDENCY_REFERENCE_UNRESOLVED value."""
        code = EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_DEPENDENCY_REFERENCE_UNRESOLVED
        assert code.value == "CONTRACT_VALIDATION_MERGE_DEPENDENCY_REFERENCE_UNRESOLVED"

    def test_merge_conflict_detected_value(self) -> None:
        """Test CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED value."""
        code = (
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED
        )
        assert code.value == "CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED"

    def test_merge_codes_have_merge_prefix(self) -> None:
        """Test that all merge codes have the _MERGE_ prefix."""
        merge_codes = [
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_REQUIRED_OVERRIDE_MISSING,
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_PLACEHOLDER_VALUE_REJECTED,
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_DEPENDENCY_REFERENCE_UNRESOLVED,
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_PROFILE_NOT_FOUND,
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_BASE_CONTRACT_INVALID,
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED,
        ]

        for code in merge_codes:
            assert "_MERGE_" in code.value, (
                f"Merge code {code.name} missing _MERGE_ prefix"
            )


@pytest.mark.unit
class TestEnumContractValidationErrorCodeExpanded:
    """Test cases specifically for expanded validation error codes."""

    def test_expanded_execution_graph_cycle_value(self) -> None:
        """Test CONTRACT_VALIDATION_EXPANDED_EXECUTION_GRAPH_CYCLE value."""
        code = EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_EXECUTION_GRAPH_CYCLE
        assert code.value == "CONTRACT_VALIDATION_EXPANDED_EXECUTION_GRAPH_CYCLE"

    def test_expanded_handler_id_invalid_value(self) -> None:
        """Test CONTRACT_VALIDATION_EXPANDED_HANDLER_ID_INVALID value."""
        code = EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_HANDLER_ID_INVALID
        assert code.value == "CONTRACT_VALIDATION_EXPANDED_HANDLER_ID_INVALID"

    def test_expanded_model_reference_invalid_value(self) -> None:
        """Test CONTRACT_VALIDATION_EXPANDED_MODEL_REFERENCE_INVALID value."""
        code = EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_MODEL_REFERENCE_INVALID
        assert code.value == "CONTRACT_VALIDATION_EXPANDED_MODEL_REFERENCE_INVALID"

    def test_expanded_codes_have_expanded_prefix(self) -> None:
        """Test that all expanded codes have the _EXPANDED_ prefix."""
        expanded_codes = [
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_EXECUTION_GRAPH_CYCLE,
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_EXECUTION_GRAPH_ORPHAN,
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_EVENT_ROUTING_INVALID,
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_EVENT_CONSUMER_MISSING,
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_DEPENDENCY_TYPE_MISMATCH,
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_CAPABILITY_UNRESOLVED,
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_RUNTIME_INVARIANT_VIOLATED,
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_HANDLER_ID_INVALID,
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_MODEL_REFERENCE_INVALID,
        ]

        for code in expanded_codes:
            assert "_EXPANDED_" in code.value, (
                f"Expanded code {code.name} missing _EXPANDED_ prefix"
            )


@pytest.mark.unit
class TestEnumContractValidationErrorCodeSerialization:
    """Test cases for serialization and deserialization."""

    def test_enum_can_be_created_from_string(self) -> None:
        """Test that enum members can be created from string values."""
        code_str = "CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED"
        code = EnumContractValidationErrorCode(code_str)
        assert (
            code
            == EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED
        )

    def test_enum_string_comparison(self) -> None:
        """Test that enum members can be compared with strings."""
        assert (
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED
            == "CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED"
        )

    def test_enum_serialization_json_compatible(self) -> None:
        """Test that enum values are JSON serializable."""
        for member in EnumContractValidationErrorCode:
            # Should be able to serialize the value
            serialized = json.dumps(member.value)
            deserialized = json.loads(serialized)

            # Should be able to reconstruct the enum
            reconstructed = EnumContractValidationErrorCode(deserialized)
            assert reconstructed == member

    def test_enum_with_pydantic_compatibility(self) -> None:
        """Test that enum works with Pydantic models."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            error_code: EnumContractValidationErrorCode

        # Test enum initialization
        model = TestModel(
            error_code=EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED
        )
        assert (
            model.error_code
            == EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED
        )

        # Test string initialization
        model = TestModel(error_code="CONTRACT_VALIDATION_EXPANDED_HANDLER_ID_INVALID")
        assert (
            model.error_code
            == EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_HANDLER_ID_INVALID
        )

        # Test serialization
        data = model.model_dump()
        assert data["error_code"] == "CONTRACT_VALIDATION_EXPANDED_HANDLER_ID_INVALID"

        # Test deserialization
        new_model = TestModel.model_validate(data)
        assert (
            new_model.error_code
            == EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_HANDLER_ID_INVALID
        )


@pytest.mark.unit
class TestEnumContractValidationErrorCodeBehavior:
    """Test cases for general behavior."""

    def test_enum_member_count(self) -> None:
        """Test that the enum has the expected number of members."""
        # 6 merge codes + 9 expanded codes = 15 total
        expected_count = 15
        actual_count = len(list(EnumContractValidationErrorCode))
        assert actual_count == expected_count, (
            f"Expected {expected_count} members, got {actual_count}"
        )

    def test_enum_member_uniqueness(self) -> None:
        """Test that all enum members have unique values."""
        values = [member.value for member in EnumContractValidationErrorCode]
        unique_values = set(values)
        assert len(values) == len(unique_values), "Enum members must have unique values"

    def test_enum_iteration(self) -> None:
        """Test that enum can be iterated over."""
        members = list(EnumContractValidationErrorCode)
        # 6 merge codes + 9 expanded codes = 15 total
        assert len(members) == 15, f"Expected 15 enum members, got {len(members)}"
        assert all(isinstance(m, EnumContractValidationErrorCode) for m in members)

    def test_invalid_enum_value_raises_error(self) -> None:
        """Test that creating enum with invalid value raises ValueError."""
        with pytest.raises(ValueError):
            EnumContractValidationErrorCode("INVALID_ERROR_CODE")

    def test_enum_hash_consistency(self) -> None:
        """Test that enum members are hashable and consistent."""
        code_set = {
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED,
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_HANDLER_ID_INVALID,
        }
        assert len(code_set) == 2

        # Test that same enum members have same hash
        code = (
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED
        )
        assert hash(code) == hash(code)


@pytest.mark.unit
class TestEnumContractValidationErrorCodeEdgeCases:
    """Test edge cases and error conditions."""

    def test_enum_with_none_value(self) -> None:
        """Test behavior when None is passed."""
        with pytest.raises((ValueError, TypeError)):
            EnumContractValidationErrorCode(None)  # type: ignore[arg-type]

    def test_enum_with_empty_string(self) -> None:
        """Test behavior with empty string."""
        with pytest.raises(ValueError):
            EnumContractValidationErrorCode("")

    def test_enum_pickling(self) -> None:
        """Test that enum members can be pickled and unpickled."""
        for member in EnumContractValidationErrorCode:
            pickled = pickle.dumps(member)
            unpickled = pickle.loads(pickled)
            assert unpickled == member
            assert unpickled is member  # Should be the same object

    def test_enum_copy_behavior(self) -> None:
        """Test enum behavior with copy operations."""
        code = (
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED
        )

        # Shallow copy should return the same object
        shallow_copy = copy.copy(code)
        assert shallow_copy is code

        # Deep copy should also return the same object
        deep_copy = copy.deepcopy(code)
        assert deep_copy is code

    def test_enum_equality_and_identity(self) -> None:
        """Test enum equality and identity behavior."""
        code1 = (
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED
        )
        code2 = (
            EnumContractValidationErrorCode.CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED
        )

        # Same enum members should be identical
        assert code1 is code2

        # Equality with strings should work
        assert code1 == "CONTRACT_VALIDATION_MERGE_CONFLICT_DETECTED"
        assert code1 != "CONTRACT_VALIDATION_EXPANDED_HANDLER_ID_INVALID"

    def test_error_codes_categorization(self) -> None:
        """Test that error codes can be categorized by prefix."""
        merge_codes: list[EnumContractValidationErrorCode] = []
        expanded_codes: list[EnumContractValidationErrorCode] = []

        for code in EnumContractValidationErrorCode:
            if "_MERGE_" in code.value:
                merge_codes.append(code)
            elif "_EXPANDED_" in code.value:
                expanded_codes.append(code)

        assert len(merge_codes) == 6, "Expected 6 merge error codes"
        assert len(expanded_codes) == 9, "Expected 9 expanded error codes"
        assert len(merge_codes) + len(expanded_codes) == len(
            list(EnumContractValidationErrorCode)
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
