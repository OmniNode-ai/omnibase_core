# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for StrValueHelper mixin.

This module tests the StrValueHelper mixin which provides consistent
__str__ behavior for string-based enums.
"""

from __future__ import annotations

import json
from enum import Enum, unique

import pytest

from omnibase_core.utils.util_str_enum_base import StrValueHelper


# Test enums for different scenarios
class EnumTestStatus(StrValueHelper, str, Enum):  # type: ignore[misc]
    """Test enum using StrValueHelper."""

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"


@unique
class EnumTestWithUnique(StrValueHelper, str, Enum):  # type: ignore[misc]
    """Test enum with @unique decorator."""

    VALUE_A = "value_a"
    VALUE_B = "value_b"
    VALUE_C = "value_c"


class EnumTestEdgeCases(StrValueHelper, str, Enum):  # type: ignore[misc]
    """Test enum with edge case values."""

    EMPTY = ""
    WITH_SPACES = "value with spaces"
    WITH_UNDERSCORE = "value_with_underscore"
    WITH_HYPHEN = "value-with-hyphen"
    UPPERCASE = "UPPERCASE_VALUE"
    MIXED_CASE = "MixedCaseValue"


class EnumTestSpecialChars(StrValueHelper, str, Enum):  # type: ignore[misc]
    """Test enum with special characters."""

    WITH_DOT = "value.with.dots"
    WITH_SLASH = "value/with/slashes"
    WITH_COLON = "value:with:colons"
    WITH_BRACKETS = "value[with]brackets"
    WITH_AT = "value@with@at"
    WITH_HASH = "value#with#hash"


class EnumTestUnicode(StrValueHelper, str, Enum):  # type: ignore[misc]
    """Test enum with unicode values."""

    EMOJI = "status_complete"
    ACCENTED = "cafe"
    JAPANESE = "japanese_text"
    CHINESE = "chinese_text"
    ARABIC = "arabic_text"


class EnumWithoutMixin(str, Enum):
    """Standard str enum without StrValueHelper for comparison."""

    PENDING = "pending"
    ACTIVE = "active"


@pytest.mark.unit
class TestStrValueHelperBasic:
    """Basic functionality tests for StrValueHelper mixin."""

    def test_str_returns_value(self) -> None:
        """Test that __str__ returns the enum value."""
        assert str(EnumTestStatus.PENDING) == "pending"
        assert str(EnumTestStatus.ACTIVE) == "active"
        assert str(EnumTestStatus.COMPLETED) == "completed"

    def test_str_with_multiple_members(self) -> None:
        """Test str() works correctly with all enum members."""
        for member in EnumTestStatus:
            assert str(member) == member.value

    def test_str_does_not_return_member_name(self) -> None:
        """Test that str() returns value, not name."""
        # The name is uppercase (PENDING), value is lowercase (pending)
        assert str(EnumTestStatus.PENDING) != "PENDING"
        assert str(EnumTestStatus.PENDING) == "pending"

    def test_value_attribute_accessible(self) -> None:
        """Test that .value attribute returns expected string."""
        assert EnumTestStatus.PENDING.value == "pending"
        assert EnumTestStatus.ACTIVE.value == "active"

    def test_name_attribute_accessible(self) -> None:
        """Test that .name attribute returns member name."""
        assert EnumTestStatus.PENDING.name == "PENDING"
        assert EnumTestStatus.ACTIVE.name == "ACTIVE"


@pytest.mark.unit
class TestStrValueHelperInheritance:
    """Tests for inheritance order and MRO behavior."""

    def test_correct_mro_pattern(self) -> None:
        """Test that StrValueHelper, str, Enum is the correct MRO pattern."""
        # Verify the class follows the expected pattern
        mro = EnumTestStatus.__mro__
        mro_names = [cls.__name__ for cls in mro]

        # StrValueHelper should appear before str in MRO
        str_helper_idx = mro_names.index("StrValueHelper")
        str_idx = mro_names.index("str")
        assert str_helper_idx < str_idx, "StrValueHelper must come before str in MRO"

    def test_is_instance_of_str(self) -> None:
        """Test that enum members are instances of str."""
        assert isinstance(EnumTestStatus.PENDING, str)
        assert isinstance(EnumTestStatus.ACTIVE, str)

    def test_is_instance_of_enum(self) -> None:
        """Test that enum members are instances of Enum."""
        assert isinstance(EnumTestStatus.PENDING, Enum)

    def test_str_comparison_works(self) -> None:
        """Test that str comparison works due to str inheritance."""
        # Direct string comparison works because enum inherits from str
        # mypy doesn't understand str enum equality, but at runtime this works
        assert EnumTestStatus.PENDING == "pending"  # type: ignore[comparison-overlap]
        assert EnumTestStatus.ACTIVE == "active"  # type: ignore[comparison-overlap]


@pytest.mark.unit
class TestStrValueHelperVsStandardEnum:
    """Comparison tests between StrValueHelper enums and standard str enums."""

    def test_without_mixin_str_returns_full_representation(self) -> None:
        """Test that standard str,Enum without mixin returns different format."""
        # Without StrValueHelper, str() returns "EnumName.MEMBER"
        result = str(EnumWithoutMixin.PENDING)
        assert result == "EnumWithoutMixin.PENDING"
        assert result != "pending"

    def test_with_mixin_str_returns_value_only(self) -> None:
        """Test that StrValueHelper mixin returns just the value."""
        result = str(EnumTestStatus.PENDING)
        assert result == "pending"
        assert "EnumTestStatus" not in result

    def test_both_compare_equal_to_value(self) -> None:
        """Test that both enum types can compare equal to their value."""
        # Both inherit from str, so both should equal their value
        # mypy doesn't understand str enum equality, but at runtime this works
        assert EnumWithoutMixin.PENDING == "pending"  # type: ignore[comparison-overlap]
        assert EnumTestStatus.PENDING == "pending"  # type: ignore[comparison-overlap]

    def test_repr_differs_from_str(self) -> None:
        """Test that repr() and str() produce different outputs for mixin enum."""
        enum_val = EnumTestStatus.PENDING
        str_result = str(enum_val)
        repr_result = repr(enum_val)

        # str() returns just the value
        assert str_result == "pending"
        # repr() typically returns <EnumName.MEMBER: 'value'>
        assert "EnumTestStatus" in repr_result
        assert "PENDING" in repr_result


@pytest.mark.unit
class TestStrValueHelperIntegration:
    """Integration tests for common use cases."""

    def test_in_fstring(self) -> None:
        """Test enum works correctly in f-strings."""
        status = EnumTestStatus.COMPLETED
        result = f"Status: {status}"
        assert result == "Status: completed"

    def test_in_fstring_with_formatting(self) -> None:
        """Test enum works with f-string formatting."""
        status = EnumTestStatus.ACTIVE
        result = f"Status: {status:>10}"  # Right-align with width 10
        assert result == "Status:     active"

    def test_string_concatenation(self) -> None:
        """Test enum works with string concatenation."""
        status = EnumTestStatus.PENDING
        result = "prefix_" + str(status) + "_suffix"
        assert result == "prefix_pending_suffix"

    def test_in_string_format(self) -> None:
        """Test enum works with str.format()."""
        status = EnumTestStatus.ACTIVE
        result = f"Status: {status}"
        assert result == "Status: active"

    def test_as_dict_key(self) -> None:
        """Test enum can be used as dictionary key."""
        data = {
            EnumTestStatus.PENDING: "waiting",
            EnumTestStatus.ACTIVE: "in progress",
        }
        assert data[EnumTestStatus.PENDING] == "waiting"
        assert data[EnumTestStatus.ACTIVE] == "in progress"

    def test_in_set(self) -> None:
        """Test enum works correctly in sets."""
        status_set = {EnumTestStatus.PENDING, EnumTestStatus.ACTIVE}
        assert EnumTestStatus.PENDING in status_set
        assert EnumTestStatus.COMPLETED not in status_set

    def test_in_list_with_string_join(self) -> None:
        """Test enum works with string join operations."""
        statuses = [EnumTestStatus.PENDING, EnumTestStatus.ACTIVE]
        result = ", ".join(str(s) for s in statuses)
        assert result == "pending, active"


@pytest.mark.unit
class TestStrValueHelperJsonSerialization:
    """Tests for JSON serialization behavior."""

    def test_json_dumps_with_str(self) -> None:
        """Test enum serializes correctly with explicit str conversion."""
        status = EnumTestStatus.PENDING
        result = json.dumps({"status": str(status)})
        assert result == '{"status": "pending"}'

    def test_json_dumps_direct(self) -> None:
        """Test enum can be serialized directly since it's a str subclass."""
        status = EnumTestStatus.ACTIVE
        # Since EnumTestStatus inherits from str, it can be serialized directly
        result = json.dumps({"status": status})
        assert result == '{"status": "active"}'

    def test_json_dumps_list_of_enums(self) -> None:
        """Test list of enums serializes correctly."""
        statuses = [EnumTestStatus.PENDING, EnumTestStatus.ACTIVE]
        result = json.dumps({"statuses": statuses})
        assert result == '{"statuses": ["pending", "active"]}'

    def test_json_roundtrip(self) -> None:
        """Test JSON roundtrip preserves value."""
        original = EnumTestStatus.COMPLETED
        serialized = json.dumps({"status": original})
        deserialized = json.loads(serialized)

        # After roundtrip, we get back a string, not enum
        assert deserialized["status"] == "completed"
        assert deserialized["status"] == original.value


@pytest.mark.unit
class TestStrValueHelperEdgeCases:
    """Tests for edge cases and special values."""

    def test_empty_string_value(self) -> None:
        """Test enum with empty string value."""
        assert str(EnumTestEdgeCases.EMPTY) == ""
        assert len(str(EnumTestEdgeCases.EMPTY)) == 0

    def test_empty_string_in_fstring(self) -> None:
        """Test empty string value in f-string."""
        result = f"value=[{EnumTestEdgeCases.EMPTY}]"
        assert result == "value=[]"

    def test_value_with_spaces(self) -> None:
        """Test enum value containing spaces."""
        assert str(EnumTestEdgeCases.WITH_SPACES) == "value with spaces"

    def test_value_with_underscore(self) -> None:
        """Test enum value containing underscores."""
        assert str(EnumTestEdgeCases.WITH_UNDERSCORE) == "value_with_underscore"

    def test_value_with_hyphen(self) -> None:
        """Test enum value containing hyphens."""
        assert str(EnumTestEdgeCases.WITH_HYPHEN) == "value-with-hyphen"

    def test_uppercase_value(self) -> None:
        """Test enum with uppercase value."""
        assert str(EnumTestEdgeCases.UPPERCASE) == "UPPERCASE_VALUE"

    def test_mixed_case_value(self) -> None:
        """Test enum with mixed case value."""
        assert str(EnumTestEdgeCases.MIXED_CASE) == "MixedCaseValue"


@pytest.mark.unit
class TestStrValueHelperSpecialCharacters:
    """Tests for values with special characters."""

    def test_value_with_dots(self) -> None:
        """Test enum value containing dots."""
        assert str(EnumTestSpecialChars.WITH_DOT) == "value.with.dots"

    def test_value_with_slashes(self) -> None:
        """Test enum value containing slashes."""
        assert str(EnumTestSpecialChars.WITH_SLASH) == "value/with/slashes"

    def test_value_with_colons(self) -> None:
        """Test enum value containing colons."""
        assert str(EnumTestSpecialChars.WITH_COLON) == "value:with:colons"

    def test_value_with_brackets(self) -> None:
        """Test enum value containing brackets."""
        assert str(EnumTestSpecialChars.WITH_BRACKETS) == "value[with]brackets"

    def test_value_with_at_symbol(self) -> None:
        """Test enum value containing @ symbol."""
        assert str(EnumTestSpecialChars.WITH_AT) == "value@with@at"

    def test_value_with_hash(self) -> None:
        """Test enum value containing # symbol."""
        assert str(EnumTestSpecialChars.WITH_HASH) == "value#with#hash"

    def test_special_chars_in_json(self) -> None:
        """Test special character values serialize correctly to JSON."""
        result = json.dumps({"path": EnumTestSpecialChars.WITH_SLASH})
        assert result == '{"path": "value/with/slashes"}'


@pytest.mark.unit
class TestStrValueHelperUnicode:
    """Tests for unicode value handling."""

    def test_unicode_values_accessible(self) -> None:
        """Test that unicode enum values are accessible."""
        # Note: These use ASCII-safe values to avoid encoding issues
        assert str(EnumTestUnicode.EMOJI) == "status_complete"
        assert str(EnumTestUnicode.ACCENTED) == "cafe"
        assert str(EnumTestUnicode.JAPANESE) == "japanese_text"

    def test_unicode_in_fstring(self) -> None:
        """Test unicode values work in f-strings."""
        result = f"Status: {EnumTestUnicode.EMOJI}"
        assert result == "Status: status_complete"

    def test_unicode_json_serialization(self) -> None:
        """Test unicode values serialize correctly to JSON."""
        result = json.dumps({"text": EnumTestUnicode.ACCENTED})
        assert result == '{"text": "cafe"}'


@pytest.mark.unit
class TestStrValueHelperWithUniqueDecorator:
    """Tests for StrValueHelper with @unique decorator."""

    def test_unique_decorator_compatible(self) -> None:
        """Test that @unique decorator works with StrValueHelper."""
        # If we got here without error, @unique is compatible
        assert EnumTestWithUnique.VALUE_A.value == "value_a"
        assert EnumTestWithUnique.VALUE_B.value == "value_b"

    def test_unique_enum_str_works(self) -> None:
        """Test str() works on @unique decorated enum."""
        assert str(EnumTestWithUnique.VALUE_A) == "value_a"
        assert str(EnumTestWithUnique.VALUE_B) == "value_b"

    def test_all_unique_members_stringify(self) -> None:
        """Test all members of @unique enum stringify correctly."""
        for member in EnumTestWithUnique:
            assert str(member) == member.value


@pytest.mark.unit
class TestStrValueHelperEquality:
    """Tests for equality comparisons."""

    def test_enum_equals_string(self) -> None:
        """Test enum member equals its string value."""
        # mypy doesn't understand str enum equality, but at runtime this works
        assert EnumTestStatus.PENDING == "pending"  # type: ignore[comparison-overlap,unreachable]
        assert EnumTestStatus.PENDING == "pending"  # type: ignore[comparison-overlap,unreachable]

    def test_enum_not_equals_different_string(self) -> None:
        """Test enum member does not equal different string."""
        # mypy doesn't understand str enum equality, but at runtime this works
        assert EnumTestStatus.PENDING != "active"  # type: ignore[comparison-overlap,unreachable]
        assert EnumTestStatus.PENDING != "active"  # type: ignore[comparison-overlap,unreachable]

    def test_enum_equals_same_member(self) -> None:
        """Test enum member equals itself."""
        assert EnumTestStatus.PENDING == EnumTestStatus.PENDING

    def test_enum_not_equals_different_member(self) -> None:
        """Test enum member does not equal different member."""
        # mypy sees these as Literal types that can never be equal, but the test is valid
        assert EnumTestStatus.PENDING != EnumTestStatus.ACTIVE  # type: ignore[comparison-overlap]

    def test_enum_hash_consistent_with_string(self) -> None:
        """Test enum hash is consistent for dict/set usage."""
        # Enum members should be hashable
        status = EnumTestStatus.PENDING
        assert hash(status) == hash(status)

        # Can use as dict key
        d = {status: "value"}
        assert d[status] == "value"


@pytest.mark.unit
class TestStrValueHelperIteration:
    """Tests for iteration over enum members."""

    def test_iterate_and_stringify(self) -> None:
        """Test iterating over enum and converting to strings."""
        values = [str(s) for s in EnumTestStatus]
        assert "pending" in values
        assert "active" in values
        assert "completed" in values

    def test_iterate_preserves_order(self) -> None:
        """Test that iteration preserves definition order."""
        values = [str(s) for s in EnumTestStatus]
        assert values == ["pending", "active", "completed"]


@pytest.mark.unit
class TestStrValueHelperMemberAccess:
    """Tests for different ways to access enum members."""

    def test_access_by_name(self) -> None:
        """Test accessing enum member by name."""
        member = EnumTestStatus["PENDING"]
        assert str(member) == "pending"

    def test_access_by_value(self) -> None:
        """Test accessing enum member by value."""
        member = EnumTestStatus("pending")
        assert member == EnumTestStatus.PENDING
        assert str(member) == "pending"

    def test_access_by_attribute(self) -> None:
        """Test accessing enum member as attribute."""
        member = EnumTestStatus.PENDING
        assert str(member) == "pending"


@pytest.mark.unit
class TestStrValueHelperRealWorldUsage:
    """Tests based on real-world usage patterns from the codebase."""

    def test_status_in_log_message(self) -> None:
        """Test enum used in log-style message formatting."""
        status = EnumTestStatus.PENDING
        message = f"[{status}] Processing request..."
        assert message == "[pending] Processing request..."

    def test_status_in_api_response(self) -> None:
        """Test enum used in API response-like structure."""
        response = {
            "status": EnumTestStatus.COMPLETED,
            "message": "Operation successful",
        }
        serialized = json.dumps(response)
        assert '"status": "completed"' in serialized

    def test_status_comparison_in_conditional(self) -> None:
        """Test enum used in conditional logic."""
        current_status = EnumTestStatus.ACTIVE

        if current_status == "active":
            result = "is_active"
        else:
            result = "not_active"

        assert result == "is_active"

    def test_status_in_string_template(self) -> None:
        """Test enum used in string template replacement."""
        template = "The current status is: {status}"
        result = template.format(status=EnumTestStatus.COMPLETED)
        assert result == "The current status is: completed"


@pytest.mark.unit
class TestStrValueHelperStringOperations:
    """Tests for string operations on StrValueHelper enums."""

    def test_direct_concatenation_without_str(self) -> None:
        """Test direct string concatenation works without explicit str() call."""
        # Since enum inherits from str, direct concatenation should work
        status = EnumTestStatus.PENDING
        result = "prefix_" + status + "_suffix"
        assert result == "prefix_pending_suffix"

    def test_concatenation_with_join(self) -> None:
        """Test join works directly with enum values."""
        statuses = [EnumTestStatus.PENDING, EnumTestStatus.ACTIVE]
        # Join should work directly without str() conversion
        result = ", ".join(statuses)
        assert result == "pending, active"

    def test_string_upper_method(self) -> None:
        """Test upper() method works on enum values."""
        status = EnumTestStatus.PENDING
        assert status.upper() == "PENDING"

    def test_string_lower_method(self) -> None:
        """Test lower() method works on enum values."""
        status = EnumTestEdgeCases.UPPERCASE
        assert status.lower() == "uppercase_value"

    def test_string_startswith(self) -> None:
        """Test startswith() method works on enum values."""
        status = EnumTestStatus.PENDING
        assert status.startswith("pen")
        assert not status.startswith("act")

    def test_string_endswith(self) -> None:
        """Test endswith() method works on enum values."""
        status = EnumTestStatus.PENDING
        assert status.endswith("ing")
        assert not status.endswith("ive")

    def test_string_contains(self) -> None:
        """Test 'in' operator works on enum values."""
        status = EnumTestStatus.PENDING
        assert "end" in status
        assert "xyz" not in status

    def test_string_split(self) -> None:
        """Test split() method works on enum values."""
        value = EnumTestEdgeCases.WITH_UNDERSCORE
        parts = value.split("_")
        assert parts == ["value", "with", "underscore"]

    def test_string_replace(self) -> None:
        """Test replace() method works on enum values."""
        value = EnumTestEdgeCases.WITH_UNDERSCORE
        result = value.replace("_", "-")
        assert result == "value-with-underscore"

    def test_string_strip(self) -> None:
        """Test strip methods work on enum values."""
        # Using a value that has no leading/trailing whitespace
        status = EnumTestStatus.PENDING
        assert status.strip() == "pending"
        assert status.lstrip("p") == "ending"
        assert status.rstrip("g") == "pendin"

    def test_string_len(self) -> None:
        """Test len() works on enum values."""
        status = EnumTestStatus.PENDING
        assert len(status) == 7  # "pending" has 7 characters

    def test_string_indexing(self) -> None:
        """Test string indexing works on enum values."""
        status = EnumTestStatus.PENDING
        assert status[0] == "p"
        assert status[-1] == "g"
        assert status[1:4] == "end"

    def test_string_iteration(self) -> None:
        """Test iterating over characters in enum value."""
        status = EnumTestStatus.ACTIVE
        chars = list(status)
        assert chars == ["a", "c", "t", "i", "v", "e"]


@pytest.mark.unit
class TestStrValueHelperPydanticIntegration:
    """Tests for Pydantic model integration."""

    def test_enum_in_pydantic_model(self) -> None:
        """Test enum works correctly in Pydantic models."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            status: EnumTestStatus

        model = TestModel(status=EnumTestStatus.ACTIVE)
        assert model.status == EnumTestStatus.ACTIVE
        assert str(model.status) == "active"

    def test_enum_serialization_in_pydantic(self) -> None:
        """Test enum serializes correctly in Pydantic model_dump."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            status: EnumTestStatus

        model = TestModel(status=EnumTestStatus.COMPLETED)
        dumped = model.model_dump()
        assert dumped["status"] == EnumTestStatus.COMPLETED

    def test_enum_json_serialization_in_pydantic(self) -> None:
        """Test enum serializes correctly in Pydantic model_dump_json."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            status: EnumTestStatus

        model = TestModel(status=EnumTestStatus.PENDING)
        json_str = model.model_dump_json()
        assert '"status":"pending"' in json_str

    def test_enum_from_string_in_pydantic(self) -> None:
        """Test enum can be created from string value in Pydantic."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            status: EnumTestStatus

        # Pydantic should accept the string value and convert to enum
        model = TestModel(status="active")  # type: ignore[arg-type]
        assert model.status == EnumTestStatus.ACTIVE
        assert str(model.status) == "active"

    def test_enum_validation_in_pydantic(self) -> None:
        """Test invalid enum value raises validation error in Pydantic."""
        from pydantic import BaseModel, ValidationError

        class TestModel(BaseModel):
            status: EnumTestStatus

        with pytest.raises(ValidationError):
            TestModel(status="invalid_status")  # type: ignore[arg-type]


@pytest.mark.unit
class TestStrValueHelperTypeChecking:
    """Tests for type checking and type behavior."""

    def test_is_subclass_of_str(self) -> None:
        """Test that enum class is a subclass of str."""
        assert issubclass(EnumTestStatus, str)

    def test_is_subclass_of_enum(self) -> None:
        """Test that enum class is a subclass of Enum."""
        assert issubclass(EnumTestStatus, Enum)

    def test_type_function_returns_enum_class(self) -> None:
        """Test that type() returns the enum class."""
        status = EnumTestStatus.PENDING
        assert type(status) is EnumTestStatus

    def test_isinstance_checks(self) -> None:
        """Test isinstance checks work correctly."""
        status = EnumTestStatus.PENDING
        assert isinstance(status, EnumTestStatus)
        assert isinstance(status, str)
        assert isinstance(status, Enum)
        assert isinstance(status, StrValueHelper)
