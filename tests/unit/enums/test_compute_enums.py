"""Unit tests for Contract-Driven NodeCompute v1.0 enums."""

import pytest

from omnibase_core.enums.enum_case_mode import EnumCaseMode
from omnibase_core.enums.enum_compute_step_type import EnumComputeStepType
from omnibase_core.enums.enum_regex_flag import EnumRegexFlag
from omnibase_core.enums.enum_transformation_type import EnumTransformationType
from omnibase_core.enums.enum_trim_mode import EnumTrimMode
from omnibase_core.enums.enum_unicode_form import EnumUnicodeForm


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestEnumComputeStepType:
    """Tests for EnumComputeStepType."""

    def test_values_exist(self) -> None:
        """Test all expected values exist."""
        assert EnumComputeStepType.VALIDATION == "validation"
        assert EnumComputeStepType.TRANSFORMATION == "transformation"
        assert EnumComputeStepType.MAPPING == "mapping"

    def test_is_str_enum(self) -> None:
        """Test enum values are strings for JSON serialization."""
        for member in EnumComputeStepType:
            assert isinstance(member.value, str)

    def test_member_count(self) -> None:
        """Test only v1.0 members exist (no CONDITIONAL/PARALLEL)."""
        assert len(EnumComputeStepType) == 3


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestEnumTransformationType:
    """Tests for EnumTransformationType."""

    def test_values_exist(self) -> None:
        """Test all v1.0 values exist."""
        assert EnumTransformationType.IDENTITY == "identity"
        assert EnumTransformationType.REGEX == "regex"
        assert EnumTransformationType.CASE_CONVERSION == "case_conversion"
        assert EnumTransformationType.TRIM == "trim"
        assert EnumTransformationType.NORMALIZE_UNICODE == "normalize_unicode"
        assert EnumTransformationType.JSON_PATH == "json_path"

    def test_is_str_enum(self) -> None:
        """Test enum values are strings for JSON serialization."""
        for member in EnumTransformationType:
            assert isinstance(member.value, str)

    def test_member_count(self) -> None:
        """Test only v1.0 members exist (6 transformations)."""
        assert len(EnumTransformationType) == 6


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestEnumCaseMode:
    """Tests for EnumCaseMode."""

    def test_values_exist(self) -> None:
        """Test all values exist."""
        assert EnumCaseMode.UPPER == "uppercase"
        assert EnumCaseMode.LOWER == "lowercase"
        assert EnumCaseMode.TITLE == "titlecase"

    def test_is_str_enum(self) -> None:
        """Test enum values are strings."""
        for member in EnumCaseMode:
            assert isinstance(member.value, str)

    def test_member_count(self) -> None:
        """Test expected number of members (3 case modes)."""
        assert len(EnumCaseMode) == 3


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestEnumRegexFlag:
    """Tests for EnumRegexFlag."""

    def test_values_exist(self) -> None:
        """Test all values exist."""
        assert EnumRegexFlag.IGNORECASE == "IGNORECASE"
        assert EnumRegexFlag.MULTILINE == "MULTILINE"
        assert EnumRegexFlag.DOTALL == "DOTALL"

    def test_is_str_enum(self) -> None:
        """Test enum values are strings."""
        for member in EnumRegexFlag:
            assert isinstance(member.value, str)

    def test_member_count(self) -> None:
        """Test expected number of members (3 regex flags)."""
        assert len(EnumRegexFlag) == 3


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestEnumUnicodeForm:
    """Tests for EnumUnicodeForm."""

    def test_values_exist(self) -> None:
        """Test all Unicode normalization forms exist."""
        assert EnumUnicodeForm.NFC == "NFC"
        assert EnumUnicodeForm.NFD == "NFD"
        assert EnumUnicodeForm.NFKC == "NFKC"
        assert EnumUnicodeForm.NFKD == "NFKD"

    def test_is_str_enum(self) -> None:
        """Test enum values are strings."""
        for member in EnumUnicodeForm:
            assert isinstance(member.value, str)

    def test_member_count(self) -> None:
        """Test expected number of members (4 Unicode forms)."""
        assert len(EnumUnicodeForm) == 4


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestEnumTrimMode:
    """Tests for EnumTrimMode."""

    def test_values_exist(self) -> None:
        """Test all values exist."""
        assert EnumTrimMode.BOTH == "both"
        assert EnumTrimMode.LEFT == "left"
        assert EnumTrimMode.RIGHT == "right"

    def test_is_str_enum(self) -> None:
        """Test enum values are strings."""
        for member in EnumTrimMode:
            assert isinstance(member.value, str)

    def test_member_count(self) -> None:
        """Test expected number of members (3 trim modes)."""
        assert len(EnumTrimMode) == 3
