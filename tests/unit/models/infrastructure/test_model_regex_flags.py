"""Tests for ModelRegexFlags."""

import re

import pytest

from omnibase_core.enums.enum_regex_flag_type import EnumRegexFlagType
from omnibase_core.models.errors.model_onex_error import ModelOnexError as OnexError
from omnibase_core.models.infrastructure.model_regex_flags import ModelRegexFlags


@pytest.mark.unit
class TestModelRegexFlagsInstantiation:
    """Tests for ModelRegexFlags instantiation."""

    def test_create_dotall(self):
        """Test creating DOTALL flag."""
        flags = ModelRegexFlags.dotall()
        assert flags.flag_type == EnumRegexFlagType.DOTALL
        assert flags.flag_value == re.DOTALL

    def test_create_ignorecase(self):
        """Test creating IGNORECASE flag."""
        flags = ModelRegexFlags.ignorecase()
        assert flags.flag_type == EnumRegexFlagType.IGNORECASE
        assert flags.flag_value == re.IGNORECASE

    def test_create_multiline(self):
        """Test creating MULTILINE flag."""
        flags = ModelRegexFlags.multiline()
        assert flags.flag_type == EnumRegexFlagType.MULTILINE
        assert flags.flag_value == re.MULTILINE

    def test_direct_instantiation(self):
        """Test direct instantiation with flag_type and flag_value."""
        flags = ModelRegexFlags(
            flag_type=EnumRegexFlagType.DOTALL, flag_value=re.DOTALL
        )
        assert flags.flag_type == EnumRegexFlagType.DOTALL
        assert flags.flag_value == re.DOTALL


@pytest.mark.unit
class TestModelRegexFlagsCombined:
    """Tests for combined ModelRegexFlags."""

    def test_combined_two_flags(self):
        """Test combining two flags."""
        flags = ModelRegexFlags.combined(re.DOTALL, re.IGNORECASE)
        assert flags.flag_type == EnumRegexFlagType.COMBINED
        assert flags.flag_value == (re.DOTALL | re.IGNORECASE)

    def test_combined_three_flags(self):
        """Test combining three flags."""
        flags = ModelRegexFlags.combined(re.DOTALL, re.IGNORECASE, re.MULTILINE)
        assert flags.flag_type == EnumRegexFlagType.COMBINED
        assert flags.flag_value == (re.DOTALL | re.IGNORECASE | re.MULTILINE)

    def test_dotall_ignorecase_multiline(self):
        """Test common combination factory method."""
        flags = ModelRegexFlags.dotall_ignorecase_multiline()
        assert flags.flag_type == EnumRegexFlagType.COMBINED
        assert flags.flag_value == (re.DOTALL | re.IGNORECASE | re.MULTILINE)

    def test_ignorecase_multiline(self):
        """Test ignorecase_multiline factory method."""
        flags = ModelRegexFlags.ignorecase_multiline()
        assert flags.flag_type == EnumRegexFlagType.COMBINED
        assert flags.flag_value == (re.IGNORECASE | re.MULTILINE)

    def test_dotall_multiline(self):
        """Test dotall_multiline factory method."""
        flags = ModelRegexFlags.dotall_multiline()
        assert flags.flag_type == EnumRegexFlagType.COMBINED
        assert flags.flag_value == (re.DOTALL | re.MULTILINE)


@pytest.mark.unit
class TestModelRegexFlagsValidation:
    """Tests for ModelRegexFlags validation."""

    def test_invalid_flag_value_for_dotall(self):
        """Test that wrong flag value for DOTALL raises error."""
        with pytest.raises(OnexError) as exc_info:
            ModelRegexFlags(
                flag_type=EnumRegexFlagType.DOTALL, flag_value=re.IGNORECASE
            )
        assert "doesn't match type" in str(exc_info.value)

    def test_invalid_flag_value_for_ignorecase(self):
        """Test that wrong flag value for IGNORECASE raises error."""
        with pytest.raises(OnexError) as exc_info:
            ModelRegexFlags(
                flag_type=EnumRegexFlagType.IGNORECASE, flag_value=re.MULTILINE
            )
        assert "doesn't match type" in str(exc_info.value)

    def test_invalid_flag_value_for_multiline(self):
        """Test that wrong flag value for MULTILINE raises error."""
        with pytest.raises(OnexError) as exc_info:
            ModelRegexFlags(flag_type=EnumRegexFlagType.MULTILINE, flag_value=re.DOTALL)
        assert "doesn't match type" in str(exc_info.value)

    def test_invalid_combined_flag_value(self):
        """Test that invalid combined flag value raises error."""
        with pytest.raises(OnexError) as exc_info:
            ModelRegexFlags(flag_type=EnumRegexFlagType.COMBINED, flag_value=0)
        assert "Invalid combined flag value" in str(exc_info.value)

    def test_invalid_combined_flag_negative(self):
        """Test that negative combined flag value raises error."""
        with pytest.raises(OnexError) as exc_info:
            ModelRegexFlags(flag_type=EnumRegexFlagType.COMBINED, flag_value=-1)
        assert "Invalid combined flag value" in str(exc_info.value)


@pytest.mark.unit
class TestModelRegexFlagsUsage:
    """Tests for using ModelRegexFlags in regex operations."""

    def test_get_flag(self):
        """Test get_flag method."""
        flags = ModelRegexFlags.dotall()
        assert flags.get_flag() == re.DOTALL

    def test_as_int(self):
        """Test as_int method."""
        flags = ModelRegexFlags.ignorecase()
        assert flags.as_int() == re.IGNORECASE

    def test_use_in_regex_dotall(self):
        """Test using flag in actual regex operation."""
        flags = ModelRegexFlags.dotall()
        pattern = re.compile(r"a.b", flags.get_flag())
        match = pattern.match("a\nb")
        assert match is not None
        assert match.group(0) == "a\nb"

    def test_use_in_regex_ignorecase(self):
        """Test using IGNORECASE flag in regex."""
        flags = ModelRegexFlags.ignorecase()
        pattern = re.compile(r"hello", flags.get_flag())
        match = pattern.match("HELLO")
        assert match is not None
        assert match.group(0) == "HELLO"

    def test_use_in_regex_multiline(self):
        """Test using MULTILINE flag in regex."""
        flags = ModelRegexFlags.multiline()
        text = "line1\nline2"
        pattern = re.compile(r"^line2", flags.get_flag())
        match = pattern.search(text)
        assert match is not None
        assert match.group(0) == "line2"

    def test_use_combined_flags(self):
        """Test using combined flags in regex."""
        flags = ModelRegexFlags.combined(re.IGNORECASE, re.MULTILINE)
        text = "Line1\nLINE2"
        pattern = re.compile(r"^line2", flags.get_flag())
        match = pattern.search(text)
        assert match is not None
        assert match.group(0) == "LINE2"


@pytest.mark.unit
class TestModelRegexFlagsSerialization:
    """Tests for ModelRegexFlags serialization."""

    def test_model_dump(self):
        """Test model_dump serialization."""
        flags = ModelRegexFlags.dotall()
        data = flags.model_dump()
        assert "flag_type" in data
        assert "flag_value" in data
        assert data["flag_value"] == re.DOTALL

    def test_serialize_protocol(self):
        """Test serialize method from protocol."""
        flags = ModelRegexFlags.ignorecase()
        data = flags.serialize()
        assert "flag_type" in data
        assert "flag_value" in data


@pytest.mark.unit
class TestModelRegexFlagsProtocols:
    """Tests for ModelRegexFlags protocol implementations."""

    def test_execute_protocol(self):
        """Test execute method."""
        flags = ModelRegexFlags.dotall()
        result = flags.execute()
        assert result is True

    def test_configure_protocol(self):
        """Test configure method."""
        flags = ModelRegexFlags.multiline()
        result = flags.configure()
        assert result is True


@pytest.mark.unit
class TestModelRegexFlagsEdgeCases:
    """Tests for ModelRegexFlags edge cases."""

    def test_combined_with_single_flag(self):
        """Test combined method with single flag."""
        flags = ModelRegexFlags.combined(re.DOTALL)
        assert flags.flag_type == EnumRegexFlagType.COMBINED
        assert flags.flag_value == re.DOTALL

    def test_combined_with_no_flags(self):
        """Test combined method with no flags raises validation error."""
        with pytest.raises(OnexError) as exc_info:
            ModelRegexFlags.combined()
        assert "Invalid combined flag value" in str(exc_info.value)

    def test_flag_value_preservation(self):
        """Test that flag values are preserved correctly."""
        original_dotall = re.DOTALL
        flags = ModelRegexFlags.dotall()
        assert flags.flag_value == original_dotall

    def test_all_factory_methods_produce_valid_flags(self):
        """Test that all factory methods produce valid flags."""
        factory_methods = [
            ModelRegexFlags.dotall,
            ModelRegexFlags.ignorecase,
            ModelRegexFlags.multiline,
            ModelRegexFlags.dotall_ignorecase_multiline,
            ModelRegexFlags.ignorecase_multiline,
            ModelRegexFlags.dotall_multiline,
        ]

        for method in factory_methods:
            flags = method()
            assert isinstance(flags, ModelRegexFlags)
            assert flags.flag_value > 0 or flags.flag_type == EnumRegexFlagType.COMBINED
