"""
Comprehensive tests for common validators.

This module tests the shared validators for common patterns:
- ISO 8601 duration strings
- BCP 47 locale tags
- UUID strings
- Semantic version strings (SemVer 2.0.0)

Ticket: OMN-1054
"""

from collections.abc import Callable

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.errors import OnexError
from omnibase_core.validation.validators import (
    BCP47Locale,
    Duration,
    ErrorCode,
    SemanticVersion,
    UUIDString,
    validate_bcp47_locale,
    validate_duration,
    validate_error_code,
    validate_semantic_version,
    validate_uuid,
)

# =============================================================================
# Duration Validator Tests
# =============================================================================


@pytest.mark.unit
class TestValidateDuration:
    """Tests for validate_duration function."""

    @pytest.mark.parametrize(
        "duration",
        [
            # Time-only durations
            "PT1H",  # 1 hour
            "PT30M",  # 30 minutes
            "PT45S",  # 45 seconds
            "PT1H30M",  # 1 hour 30 minutes
            "PT1H30M45S",  # 1 hour 30 minutes 45 seconds
            "PT0.5S",  # 0.5 seconds (fractional)
            "PT1.234S",  # Multiple decimal places
            # Date-only durations
            "P1D",  # 1 day
            "P7D",  # 7 days
            "P1W",  # 1 week
            "P1M",  # 1 month
            "P1Y",  # 1 year
            "P1Y2M",  # 1 year 2 months
            "P1Y2M3D",  # 1 year 2 months 3 days
            # Combined date and time
            "P1DT1H",  # 1 day 1 hour
            "P1Y2M3DT4H5M6S",  # Full format
            # Weeks alone (valid - weeks cannot be combined with other components)
            "P52W",  # 52 weeks
            "P100W",  # 100 weeks
        ],
    )
    def test_valid_durations(self, duration: str) -> None:
        """Test that valid duration strings are accepted."""
        result = validate_duration(duration)
        assert result == duration

    @pytest.mark.parametrize(
        ("duration", "error_fragment"),
        [
            ("", "cannot be empty"),
            ("P", "must specify at least one time component"),
            ("PT", "must specify at least one time component"),
            ("1H", "Invalid ISO 8601 duration format"),
            ("T1H", "Invalid ISO 8601 duration format"),
            ("PT1H30", "Invalid ISO 8601 duration format"),
            ("invalid", "Invalid ISO 8601 duration format"),
            ("P-1D", "Invalid ISO 8601 duration format"),
            ("PT1.5.5S", "Invalid ISO 8601 duration format"),
        ],
    )
    def test_invalid_durations(self, duration: str, error_fragment: str) -> None:
        """Test that invalid duration strings raise OnexError."""
        with pytest.raises(OnexError, match=error_fragment):
            validate_duration(duration)

    @pytest.mark.parametrize(
        "duration",
        [
            "P1WT1H",  # weeks with hours
            "P1WT30M",  # weeks with minutes
            "P1WT45S",  # weeks with seconds
            "P1WT1H30M45S",  # weeks with full time
            "P1W1D",  # weeks with days
            "P1M1W",  # months with weeks
            "P1Y1W",  # years with weeks
            "P1Y2M1W",  # years, months with weeks
            "P1Y2M1W3D",  # years, months, weeks, days
            "P1W1DT1H",  # weeks, days with time
        ],
    )
    def test_weeks_cannot_be_combined(self, duration: str) -> None:
        """Test that weeks cannot be combined with other components per ISO 8601."""
        with pytest.raises(OnexError) as exc_info:
            validate_duration(duration)
        assert "weeks (W) cannot be combined" in str(exc_info.value)


@pytest.mark.unit
class TestDurationAnnotatedType:
    """Tests for Duration Annotated type with Pydantic."""

    def test_valid_duration_in_model(self) -> None:
        """Test that valid durations work in Pydantic models."""

        class Config(BaseModel):
            timeout: Duration

        config = Config(timeout="PT1H30M")
        assert config.timeout == "PT1H30M"

    def test_invalid_duration_in_model(self) -> None:
        """Test that invalid durations raise OnexError."""

        class Config(BaseModel):
            timeout: Duration

        with pytest.raises(OnexError):
            Config(timeout="invalid")


# =============================================================================
# BCP 47 Locale Validator Tests
# =============================================================================


@pytest.mark.unit
class TestValidateBCP47Locale:
    """Tests for validate_bcp47_locale function."""

    @pytest.mark.parametrize(
        "locale",
        [
            # Language only
            "en",
            "fr",
            "de",
            "zh",
            "ja",
            "ko",
            # Language + region
            "en-US",
            "en-GB",
            "fr-FR",
            "fr-CA",
            "pt-BR",
            "pt-PT",
            "zh-CN",
            "zh-TW",
            # Language + script
            "zh-Hans",
            "zh-Hant",
            "sr-Latn",
            "sr-Cyrl",
            # Language + script + region
            "zh-Hans-CN",
            "zh-Hant-TW",
            "sr-Latn-RS",
            # Language + region (numeric)
            "en-001",  # World
            "es-419",  # Latin America
            # 3-letter language codes
            "ast",  # Asturian
            "gsw",  # Swiss German
        ],
    )
    def test_valid_locales(self, locale: str) -> None:
        """Test that valid locale strings are accepted."""
        result = validate_bcp47_locale(locale)
        assert result == locale

    @pytest.mark.parametrize(
        ("locale", "error_fragment"),
        [
            ("", "cannot be empty"),
            ("e", "Invalid BCP 47 locale format"),  # Too short
            ("english", "Invalid BCP 47 locale format"),  # Too long
            ("en_US", "Invalid BCP 47 locale format"),  # Underscore not hyphen
            ("en-USA", "Invalid BCP 47 locale format"),  # Region too long
            ("12-US", "Invalid BCP 47 locale format"),  # Numeric language
            ("en-", "Invalid BCP 47 locale format"),  # Trailing hyphen
            ("-US", "Invalid BCP 47 locale format"),  # Leading hyphen
            ("en--US", "Invalid BCP 47 locale format"),  # Double hyphen
        ],
    )
    def test_invalid_locales(self, locale: str, error_fragment: str) -> None:
        """Test that invalid locale strings raise OnexError."""
        with pytest.raises(OnexError, match=error_fragment):
            validate_bcp47_locale(locale)


@pytest.mark.unit
class TestBCP47LocaleAnnotatedType:
    """Tests for BCP47Locale Annotated type with Pydantic."""

    def test_valid_locale_in_model(self) -> None:
        """Test that valid locales work in Pydantic models."""

        class UserPreferences(BaseModel):
            locale: BCP47Locale

        prefs = UserPreferences(locale="en-US")
        assert prefs.locale == "en-US"

    def test_invalid_locale_in_model(self) -> None:
        """Test that invalid locales raise OnexError."""

        class UserPreferences(BaseModel):
            locale: BCP47Locale

        with pytest.raises(OnexError):
            UserPreferences(locale="invalid_locale")


# =============================================================================
# UUID Validator Tests
# =============================================================================


@pytest.mark.unit
class TestValidateUUID:
    """Tests for validate_uuid function."""

    @pytest.mark.parametrize(
        ("uuid_str", "expected"),
        [
            # Standard format with hyphens
            (
                "550e8400-e29b-41d4-a716-446655440000",
                "550e8400-e29b-41d4-a716-446655440000",
            ),
            (
                "123e4567-e89b-12d3-a456-426614174000",
                "123e4567-e89b-12d3-a456-426614174000",
            ),
            # Without hyphens
            (
                "550e8400e29b41d4a716446655440000",
                "550e8400-e29b-41d4-a716-446655440000",
            ),
            # Uppercase (normalized to lowercase)
            (
                "550E8400-E29B-41D4-A716-446655440000",
                "550e8400-e29b-41d4-a716-446655440000",
            ),
            (
                "550E8400E29B41D4A716446655440000",
                "550e8400-e29b-41d4-a716-446655440000",
            ),
            # Mixed case
            (
                "550e8400-E29B-41d4-A716-446655440000",
                "550e8400-e29b-41d4-a716-446655440000",
            ),
            # Nil UUID
            (
                "00000000-0000-0000-0000-000000000000",
                "00000000-0000-0000-0000-000000000000",
            ),
            # Max UUID
            (
                "ffffffff-ffff-ffff-ffff-ffffffffffff",
                "ffffffff-ffff-ffff-ffff-ffffffffffff",
            ),
        ],
    )
    def test_valid_uuids(self, uuid_str: str, expected: str) -> None:
        """Test that valid UUID strings are accepted and normalized."""
        result = validate_uuid(uuid_str)
        assert result == expected

    @pytest.mark.parametrize(
        ("uuid_str", "error_fragment"),
        [
            ("", "cannot be empty"),
            ("invalid-uuid", "Invalid UUID format"),
            ("550e8400-e29b-41d4-a716", "Invalid UUID format"),  # Too short
            (
                "550e8400-e29b-41d4-a716-4466554400000",
                "Invalid UUID format",
            ),  # Too long
            (
                "550e8400-e29b-41d4-a716-44665544000g",
                "Invalid UUID format",
            ),  # Invalid char
            (
                "550e8400-e29b-41d4-a716-44665544000",
                "Invalid UUID format",
            ),  # Missing digit
            (
                "550e8400_e29b_41d4_a716_446655440000",
                "Invalid UUID format",
            ),  # Underscores
            (
                "550e8400e29b41d4a71644665544000",
                "Invalid UUID format",
            ),  # One digit short
        ],
    )
    def test_invalid_uuids(self, uuid_str: str, error_fragment: str) -> None:
        """Test that invalid UUID strings raise OnexError."""
        with pytest.raises(OnexError, match=error_fragment):
            validate_uuid(uuid_str)

    def test_uuid_normalization(self) -> None:
        """Test that UUIDs are normalized consistently."""
        # All these should normalize to the same value
        uuid_lower = "550e8400-e29b-41d4-a716-446655440000"
        uuid_upper = "550E8400-E29B-41D4-A716-446655440000"
        uuid_no_hyphens = "550e8400e29b41d4a716446655440000"

        result_lower = validate_uuid(uuid_lower)
        result_upper = validate_uuid(uuid_upper)
        result_no_hyphens = validate_uuid(uuid_no_hyphens)

        assert result_lower == result_upper == result_no_hyphens


@pytest.mark.unit
class TestUUIDStringAnnotatedType:
    """Tests for UUIDString Annotated type with Pydantic."""

    def test_valid_uuid_in_model(self) -> None:
        """Test that valid UUIDs work in Pydantic models."""

        class Entity(BaseModel):
            id: UUIDString

        entity = Entity(id="550e8400-e29b-41d4-a716-446655440000")
        assert entity.id == "550e8400-e29b-41d4-a716-446655440000"

    def test_uuid_normalization_in_model(self) -> None:
        """Test that UUIDs are normalized in Pydantic models."""

        class Entity(BaseModel):
            id: UUIDString

        entity = Entity(id="550E8400E29B41D4A716446655440000")
        assert entity.id == "550e8400-e29b-41d4-a716-446655440000"

    def test_invalid_uuid_in_model(self) -> None:
        """Test that invalid UUIDs raise OnexError."""

        class Entity(BaseModel):
            id: UUIDString

        with pytest.raises(OnexError):
            Entity(id="invalid-uuid")


# =============================================================================
# Semantic Version Validator Tests
# =============================================================================


@pytest.mark.unit
class TestValidateSemanticVersion:
    """Tests for validate_semantic_version function."""

    @pytest.mark.parametrize(
        "version",
        [
            # Basic versions
            "0.0.0",
            "0.0.1",
            "0.1.0",
            "1.0.0",
            "1.2.3",
            "10.20.30",
            "999.999.999",
            # With prerelease
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0-alpha.beta",
            "1.0.0-beta",
            "1.0.0-beta.2",
            "1.0.0-beta.11",
            "1.0.0-rc.1",
            "1.0.0-0.3.7",
            "1.0.0-x.7.z.92",
            # With build metadata
            "1.0.0+build",
            "1.0.0+build.123",
            "1.0.0+20230101",
            "1.0.0+exp.sha.5114f85",
            # With prerelease and build metadata
            "1.0.0-alpha+001",
            "1.0.0-alpha.1+build.123",
            "1.0.0-beta.1+exp.sha.5114f85",
            "2.1.3-beta.1+build.456",
        ],
    )
    def test_valid_versions(self, version: str) -> None:
        """Test that valid version strings are accepted."""
        result = validate_semantic_version(version)
        assert result == version

    @pytest.mark.parametrize(
        ("version", "error_fragment"),
        [
            ("", "cannot be empty"),
            ("1", "Invalid semantic version format"),
            ("1.0", "Invalid semantic version format"),
            ("1.0.0.0", "Invalid semantic version format"),  # Too many parts
            ("v1.0.0", "Invalid semantic version format"),  # Leading v
            ("1.0.0-", "Invalid semantic version format"),  # Trailing hyphen
            ("1.0.0+", "Invalid semantic version format"),  # Trailing plus
            ("01.0.0", "Invalid semantic version format"),  # Leading zero
            ("1.00.0", "Invalid semantic version format"),  # Leading zero
            ("1.0.00", "Invalid semantic version format"),  # Leading zero
            (
                "1.0.0-01",
                "Invalid semantic version format",
            ),  # Leading zero in prerelease
            ("1.0.0-alpha..1", "Invalid semantic version format"),  # Double dot
            ("1.0.0+build..1", "Invalid semantic version format"),  # Double dot
            ("a.b.c", "Invalid semantic version format"),  # Non-numeric
            ("-1.0.0", "Invalid semantic version format"),  # Negative
            ("1.-1.0", "Invalid semantic version format"),  # Negative
            ("1.0.-1", "Invalid semantic version format"),  # Negative
        ],
    )
    def test_invalid_versions(self, version: str, error_fragment: str) -> None:
        """Test that invalid version strings raise OnexError."""
        with pytest.raises(OnexError, match=error_fragment):
            validate_semantic_version(version)


@pytest.mark.unit
class TestSemanticVersionAnnotatedType:
    """Tests for SemanticVersion Annotated type with Pydantic."""

    def test_valid_version_in_model(self) -> None:
        """Test that valid versions work in Pydantic models."""

        class Package(BaseModel):
            version: SemanticVersion

        package = Package(version="1.0.0")
        assert package.version == "1.0.0"

    def test_version_with_prerelease_in_model(self) -> None:
        """Test that versions with prerelease work in Pydantic models."""

        class Package(BaseModel):
            version: SemanticVersion

        package = Package(version="2.1.3-beta.1+build.123")
        assert package.version == "2.1.3-beta.1+build.123"

    def test_invalid_version_in_model(self) -> None:
        """Test that invalid versions raise OnexError."""

        class Package(BaseModel):
            version: SemanticVersion

        with pytest.raises(OnexError):
            Package(version="1.0")


# =============================================================================
# Error Code Validator Tests
# =============================================================================


@pytest.mark.unit
class TestValidateErrorCode:
    """Tests for validate_error_code function."""

    @pytest.mark.parametrize(
        "error_code",
        [
            # Simple category codes
            "AUTH_001",
            "AUTH_1",
            "AUTH_1234",
            # Multi-word categories
            "VALIDATION_123",
            "NETWORK_TIMEOUT_001",
            "FILE_NOT_FOUND_42",
            # With numbers in category
            "ERROR2_001",
            "V2_AUTH_123",
            # Edge cases for digit count
            "X_1",  # Minimum: 1 digit
            "X_12",  # 2 digits
            "X_123",  # 3 digits
            "X_1234",  # Maximum: 4 digits
            # Various valid patterns
            "SYSTEM_01",
            "DB_CONNECTION_999",
            "API_RATE_LIMIT_0001",
        ],
    )
    def test_valid_error_codes(self, error_code: str) -> None:
        """Test that valid error code strings are accepted."""
        result = validate_error_code(error_code)
        assert result == error_code

    @pytest.mark.parametrize(
        ("error_code", "error_fragment"),
        [
            ("", "cannot be empty"),
            # Lint-style short codes (not supported)
            ("E001", "Invalid error code format"),
            ("W001", "Invalid error code format"),
            ("I001", "Invalid error code format"),
            # Missing underscore
            ("AUTH001", "Invalid error code format"),
            # Lowercase not allowed
            ("auth_001", "Invalid error code format"),
            ("Auth_001", "Invalid error code format"),
            # Missing numeric suffix
            ("AUTH_", "Invalid error code format"),
            ("AUTH", "Invalid error code format"),
            # Starting with number
            ("1AUTH_001", "Invalid error code format"),
            ("123_001", "Invalid error code format"),
            # Too many digits (>4)
            ("AUTH_12345", "Invalid error code format"),
            # Invalid characters
            ("AUTH-001", "Invalid error code format"),  # Hyphen instead of underscore
            ("AUTH.001", "Invalid error code format"),  # Dot separator
            ("AUTH 001", "Invalid error code format"),  # Space
            # Only numbers
            ("123_456", "Invalid error code format"),
            # Unicode/special characters
            ("AUTH_\u00e9001", "Invalid error code format"),  # Unicode in code
        ],
    )
    def test_invalid_error_codes(self, error_code: str, error_fragment: str) -> None:
        """Test that invalid error code strings raise OnexError."""
        with pytest.raises(OnexError, match=error_fragment):
            validate_error_code(error_code)


@pytest.mark.unit
class TestErrorCodeAnnotatedType:
    """Tests for ErrorCode Annotated type with Pydantic."""

    def test_valid_error_code_in_model(self) -> None:
        """Test that valid error codes work in Pydantic models."""

        class ErrorReport(BaseModel):
            code: ErrorCode

        report = ErrorReport(code="AUTH_001")
        assert report.code == "AUTH_001"

    def test_complex_error_code_in_model(self) -> None:
        """Test that complex error codes work in Pydantic models."""

        class ErrorReport(BaseModel):
            code: ErrorCode

        report = ErrorReport(code="NETWORK_TIMEOUT_001")
        assert report.code == "NETWORK_TIMEOUT_001"

    def test_invalid_error_code_in_model(self) -> None:
        """Test that invalid error codes raise OnexError."""

        class ErrorReport(BaseModel):
            code: ErrorCode

        with pytest.raises(OnexError):
            ErrorReport(code="invalid")

    def test_lint_style_code_rejected_in_model(self) -> None:
        """Test that lint-style short codes are rejected in Pydantic models."""

        class ErrorReport(BaseModel):
            code: ErrorCode

        with pytest.raises(OnexError):
            ErrorReport(code="E001")

    def test_optional_error_code_in_model(self) -> None:
        """Test that optional ErrorCode fields accept None."""

        class ErrorReport(BaseModel):
            code: ErrorCode | None = None

        report = ErrorReport(code=None)
        assert report.code is None

        report2 = ErrorReport()
        assert report2.code is None


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.unit
class TestMultipleValidatorsInModel:
    """Tests for using multiple validators in a single Pydantic model."""

    def test_all_validators_in_model(self) -> None:
        """Test that all validators work together in a single model."""

        class ComplexConfig(BaseModel):
            id: UUIDString
            version: SemanticVersion
            locale: BCP47Locale
            timeout: Duration

        config = ComplexConfig(
            id="550e8400-e29b-41d4-a716-446655440000",
            version="1.0.0-beta.1",
            locale="en-US",
            timeout="PT30M",
        )

        assert config.id == "550e8400-e29b-41d4-a716-446655440000"
        assert config.version == "1.0.0-beta.1"
        assert config.locale == "en-US"
        assert config.timeout == "PT30M"

    def test_optional_validators_in_model(self) -> None:
        """Test that validators work with optional fields."""

        class OptionalConfig(BaseModel):
            id: UUIDString
            version: SemanticVersion | None = None
            locale: BCP47Locale | None = None
            timeout: Duration | None = None

        # With only required field
        config1 = OptionalConfig(id="550e8400-e29b-41d4-a716-446655440000")
        assert config1.id == "550e8400-e29b-41d4-a716-446655440000"
        assert config1.version is None

        # With all fields
        config2 = OptionalConfig(
            id="550e8400-e29b-41d4-a716-446655440000",
            version="1.0.0",
            locale="en-US",
            timeout="PT1H",
        )
        assert config2.version == "1.0.0"


# =============================================================================
# Import Tests
# =============================================================================


@pytest.mark.unit
class TestImports:
    """Tests for import paths."""

    def test_import_from_validators_package(self) -> None:
        """Test that validators can be imported from the validators package."""
        from omnibase_core.validation.validators import (
            BCP47Locale,
            Duration,
            SemanticVersion,
            UUIDString,
            validate_bcp47_locale,
            validate_duration,
            validate_semantic_version,
            validate_uuid,
        )

        # Verify they are callable/usable
        assert callable(validate_duration)
        assert callable(validate_bcp47_locale)
        assert callable(validate_uuid)
        assert callable(validate_semantic_version)
        # Verify type aliases are importable (not callable, but usable as types)
        assert BCP47Locale is not None
        assert Duration is not None
        assert SemanticVersion is not None
        assert UUIDString is not None

    def test_import_from_validation_package(self) -> None:
        """Test that validators can be imported from the main validation package."""
        from omnibase_core.validation import (
            BCP47Locale,
            Duration,
            SemanticVersion,
            UUIDString,
            validate_bcp47_locale,
            validate_duration,
            validate_semantic_version,
            validate_uuid,
        )

        # Verify they are callable/usable
        assert callable(validate_duration)
        assert callable(validate_bcp47_locale)
        assert callable(validate_uuid)
        assert callable(validate_semantic_version)
        # Verify type aliases are importable (not callable, but usable as types)
        assert BCP47Locale is not None
        assert Duration is not None
        assert SemanticVersion is not None
        assert UUIDString is not None

    def test_import_create_enum_normalizer(self) -> None:
        """Test that create_enum_normalizer can be imported from multiple paths."""
        from omnibase_core.utils import create_enum_normalizer as factory1
        from omnibase_core.utils.util_enum_normalizer import (
            create_enum_normalizer as factory2,
        )
        from omnibase_core.validation import create_enum_normalizer as factory3
        from omnibase_core.validation.validators import (
            create_enum_normalizer as factory4,
        )

        # All imports should be callable
        assert callable(factory1)
        assert callable(factory2)
        assert callable(factory3)
        assert callable(factory4)

        # All should reference the same underlying function
        assert factory1 is factory2
        assert factory3 is factory4
        # Validation re-exports from utils
        assert factory3 is factory1


# =============================================================================
# Enum Normalizer Factory Tests
# =============================================================================


@pytest.mark.unit
class TestCreateEnumNormalizer:
    """Tests for create_enum_normalizer factory function."""

    def test_none_input_returns_none(self) -> None:
        """Test that None input returns None."""
        from enum import Enum

        from omnibase_core.validation.validators import create_enum_normalizer

        class Color(Enum):
            RED = "red"
            BLUE = "blue"

        normalizer = create_enum_normalizer(Color)
        assert normalizer(None) is None

    def test_enum_instance_returns_unchanged(self) -> None:
        """Test that enum instance is returned unchanged."""
        from enum import Enum

        from omnibase_core.validation.validators import create_enum_normalizer

        class Color(Enum):
            RED = "red"
            BLUE = "blue"

        normalizer = create_enum_normalizer(Color)
        result = normalizer(Color.RED)
        assert result is Color.RED
        assert isinstance(result, Color)

    def test_valid_string_converted_to_enum(self) -> None:
        """Test that valid string is converted to enum."""
        from enum import Enum

        from omnibase_core.validation.validators import create_enum_normalizer

        class Color(Enum):
            RED = "red"
            BLUE = "blue"

        normalizer = create_enum_normalizer(Color)
        result = normalizer("red")
        assert result == Color.RED
        assert isinstance(result, Color)

    def test_string_case_insensitive(self) -> None:
        """Test that string conversion is case-insensitive (via lowercase)."""
        from enum import Enum

        from omnibase_core.validation.validators import create_enum_normalizer

        class Color(Enum):
            RED = "red"
            BLUE = "blue"

        normalizer = create_enum_normalizer(Color)
        assert normalizer("RED") == Color.RED
        assert normalizer("Red") == Color.RED
        assert normalizer("rEd") == Color.RED

    def test_invalid_string_kept_for_backward_compat(self) -> None:
        """Test that invalid string is kept as-is for backward compatibility."""
        from enum import Enum

        from omnibase_core.validation.validators import create_enum_normalizer

        class Color(Enum):
            RED = "red"
            BLUE = "blue"

        normalizer = create_enum_normalizer(Color)
        result = normalizer("green")
        assert result == "green"
        assert isinstance(result, str)

    def test_with_pydantic_model(self) -> None:
        """Test that normalizer works correctly with Pydantic models."""
        from enum import Enum

        from pydantic import BaseModel, field_validator

        from omnibase_core.validation.validators import create_enum_normalizer

        class Status(Enum):
            ACTIVE = "active"
            INACTIVE = "inactive"
            PENDING = "pending"

        class MyModel(BaseModel):
            status: Status | str | None = None

            @field_validator("status", mode="before")
            @classmethod
            def normalize_status(cls, v: Status | str | None) -> Status | str | None:
                return create_enum_normalizer(Status)(v)

        # Test with enum value
        m1 = MyModel(status=Status.ACTIVE)
        assert m1.status == Status.ACTIVE

        # Test with valid string (lowercase)
        m2 = MyModel(status="active")
        assert m2.status == Status.ACTIVE

        # Test with valid string (uppercase)
        m3 = MyModel(status="ACTIVE")
        assert m3.status == Status.ACTIVE

        # Test with None
        m4 = MyModel(status=None)
        assert m4.status is None

        # Test with invalid string (backward compat)
        m5 = MyModel(status="unknown_status")
        assert m5.status == "unknown_status"

    def test_with_real_omnibase_enum(self) -> None:
        """Test with real EnumTokenType from omnibase_core."""
        from omnibase_core.enums import EnumTokenType
        from omnibase_core.validation.validators import create_enum_normalizer

        normalizer = create_enum_normalizer(EnumTokenType)

        # Test with enum value
        assert normalizer(EnumTokenType.BEARER) is EnumTokenType.BEARER

        # Test with valid string
        assert normalizer("bearer") == EnumTokenType.BEARER
        assert normalizer("BEARER") == EnumTokenType.BEARER

        # Test with None
        assert normalizer(None) is None

        # Test with unknown string (backward compat)
        assert normalizer("custom_token") == "custom_token"

    def test_normalizer_is_reusable(self) -> None:
        """Test that the same normalizer can be called multiple times."""
        from enum import Enum

        from omnibase_core.validation.validators import create_enum_normalizer

        class Priority(Enum):
            LOW = "low"
            MEDIUM = "medium"
            HIGH = "high"

        normalizer = create_enum_normalizer(Priority)

        # Multiple calls with same normalizer
        assert normalizer("low") == Priority.LOW
        assert normalizer("MEDIUM") == Priority.MEDIUM
        assert normalizer("high") == Priority.HIGH
        assert normalizer(None) is None
        assert normalizer("critical") == "critical"

    def test_different_enum_types(self) -> None:
        """Test that factory works with different enum types."""
        from enum import Enum

        from omnibase_core.validation.validators import create_enum_normalizer

        class Color(Enum):
            RED = "red"
            BLUE = "blue"

        class Size(Enum):
            SMALL = "small"
            LARGE = "large"

        color_normalizer = create_enum_normalizer(Color)
        size_normalizer = create_enum_normalizer(Size)

        # Each normalizer works with its own enum type
        assert color_normalizer("red") == Color.RED
        assert size_normalizer("small") == Size.SMALL

        # Cross-enum strings are kept as-is
        assert color_normalizer("small") == "small"
        assert size_normalizer("red") == "red"


@pytest.mark.unit
class TestEnumNormalizerWithContextModels:
    """Integration tests with the actual context models using create_enum_normalizer."""

    def test_session_context_authentication_method(self) -> None:
        """Test that ModelSessionContext uses create_enum_normalizer correctly."""
        from omnibase_core.enums import EnumAuthenticationMethod
        from omnibase_core.models.context import ModelSessionContext

        # Test with enum value
        ctx1 = ModelSessionContext(
            authentication_method=EnumAuthenticationMethod.OAUTH2
        )
        assert ctx1.authentication_method == EnumAuthenticationMethod.OAUTH2

        # Test with string (lowercase)
        ctx2 = ModelSessionContext(authentication_method="oauth2")
        assert ctx2.authentication_method == EnumAuthenticationMethod.OAUTH2

        # Test with string (uppercase)
        ctx3 = ModelSessionContext(authentication_method="OAUTH2")
        assert ctx3.authentication_method == EnumAuthenticationMethod.OAUTH2

        # Test with None
        ctx4 = ModelSessionContext(authentication_method=None)
        assert ctx4.authentication_method is None

        # Test with unknown string (backward compat)
        ctx5 = ModelSessionContext(authentication_method="custom_auth")
        assert ctx5.authentication_method == "custom_auth"

    def test_authorization_context_token_type(self) -> None:
        """Test that ModelAuthorizationContext uses create_enum_normalizer correctly."""
        from omnibase_core.enums import EnumTokenType
        from omnibase_core.models.context import ModelAuthorizationContext

        # Test with enum value
        ctx1 = ModelAuthorizationContext(token_type=EnumTokenType.BEARER)
        assert ctx1.token_type == EnumTokenType.BEARER

        # Test with string
        ctx2 = ModelAuthorizationContext(token_type="bearer")
        assert ctx2.token_type == EnumTokenType.BEARER

        # Test backward compat
        ctx3 = ModelAuthorizationContext(token_type="custom_token")
        assert ctx3.token_type == "custom_token"

    def test_checkpoint_metadata_enums(self) -> None:
        """Test that ModelCheckpointMetadata uses create_enum_normalizer correctly."""
        from omnibase_core.enums import EnumCheckpointType, EnumTriggerEvent
        from omnibase_core.models.context import ModelCheckpointMetadata

        # Test checkpoint_type
        meta1 = ModelCheckpointMetadata(checkpoint_type="automatic")
        assert meta1.checkpoint_type == EnumCheckpointType.AUTOMATIC

        meta2 = ModelCheckpointMetadata(checkpoint_type=EnumCheckpointType.MANUAL)
        assert meta2.checkpoint_type == EnumCheckpointType.MANUAL

        # Test trigger_event
        meta3 = ModelCheckpointMetadata(trigger_event="error")
        assert meta3.trigger_event == EnumTriggerEvent.ERROR

        meta4 = ModelCheckpointMetadata(trigger_event=EnumTriggerEvent.TIMEOUT)
        assert meta4.trigger_event == EnumTriggerEvent.TIMEOUT

        # Test backward compat
        meta5 = ModelCheckpointMetadata(
            checkpoint_type="custom_type", trigger_event="custom_event"
        )
        assert meta5.checkpoint_type == "custom_type"
        assert meta5.trigger_event == "custom_event"

    def test_detection_metadata_likelihood(self) -> None:
        """Test that ModelDetectionMetadata uses create_enum_normalizer correctly."""
        from omnibase_core.enums import EnumLikelihood
        from omnibase_core.models.context import ModelDetectionMetadata

        # Test with enum value
        meta1 = ModelDetectionMetadata(false_positive_likelihood=EnumLikelihood.LOW)
        assert meta1.false_positive_likelihood == EnumLikelihood.LOW

        # Test with string
        meta2 = ModelDetectionMetadata(false_positive_likelihood="high")
        assert meta2.false_positive_likelihood == EnumLikelihood.HIGH

        # Test backward compat
        meta3 = ModelDetectionMetadata(false_positive_likelihood="uncertain")
        assert meta3.false_positive_likelihood == "uncertain"


# =============================================================================
# Edge Case Tests for Validators
# =============================================================================


@pytest.mark.unit
class TestValidatorEdgeCases:
    """Edge case tests for all validators.

    These tests focus on boundary conditions, whitespace handling,
    and type edge cases that may cause unexpected behavior.
    """

    # =========================================================================
    # Whitespace Handling Tests
    # =========================================================================

    @pytest.mark.parametrize(
        ("validator_func", "valid_input"),
        [
            (validate_duration, "PT1H"),
            (validate_bcp47_locale, "en-US"),
            (validate_uuid, "550e8400-e29b-41d4-a716-446655440000"),
            (validate_semantic_version, "1.0.0"),
            (validate_error_code, "AUTH_001"),
        ],
    )
    def test_validators_reject_leading_whitespace(
        self, validator_func: Callable[[str], str], valid_input: str
    ) -> None:
        """Test that validators reject inputs with leading whitespace."""
        with pytest.raises(OnexError):
            validator_func(f" {valid_input}")

    @pytest.mark.parametrize(
        ("validator_func", "valid_input"),
        [
            (validate_duration, "PT1H"),
            (validate_bcp47_locale, "en-US"),
            (validate_uuid, "550e8400-e29b-41d4-a716-446655440000"),
            (validate_semantic_version, "1.0.0"),
            (validate_error_code, "AUTH_001"),
        ],
    )
    def test_validators_reject_trailing_whitespace(
        self, validator_func: Callable[[str], str], valid_input: str
    ) -> None:
        """Test that validators reject inputs with trailing whitespace."""
        with pytest.raises(OnexError):
            validator_func(f"{valid_input} ")

    @pytest.mark.parametrize(
        ("validator_func", "valid_input"),
        [
            (validate_duration, "PT1H"),
            (validate_bcp47_locale, "en-US"),
            (validate_uuid, "550e8400-e29b-41d4-a716-446655440000"),
            (validate_semantic_version, "1.0.0"),
            (validate_error_code, "AUTH_001"),
        ],
    )
    def test_validators_reject_surrounding_whitespace(
        self, validator_func: Callable[[str], str], valid_input: str
    ) -> None:
        """Test that validators reject inputs with surrounding whitespace."""
        with pytest.raises(OnexError):
            validator_func(f"  {valid_input}  ")

    @pytest.mark.parametrize(
        "validator_func",
        [
            validate_duration,
            validate_bcp47_locale,
            validate_uuid,
            validate_semantic_version,
            validate_error_code,
        ],
    )
    def test_validators_reject_whitespace_only(
        self, validator_func: Callable[[str], str]
    ) -> None:
        """Test that validators reject whitespace-only inputs."""
        with pytest.raises(OnexError):
            validator_func("   ")
        with pytest.raises(OnexError):
            validator_func("\t")
        with pytest.raises(OnexError):
            validator_func("\n")

    # =========================================================================
    # None and Empty String Edge Cases
    # =========================================================================

    @pytest.mark.parametrize(
        "validator_func",
        [
            validate_duration,
            validate_bcp47_locale,
            validate_uuid,
            validate_semantic_version,
            validate_error_code,
        ],
    )
    def test_validators_reject_empty_string(
        self, validator_func: Callable[[str], str]
    ) -> None:
        """Test that all validators reject empty strings with clear message."""
        with pytest.raises(OnexError, match="cannot be empty"):
            validator_func("")

    # =========================================================================
    # UUID Validator Edge Cases
    # =========================================================================

    def test_uuid_validator_handles_braces(self) -> None:
        """Test that UUID validator rejects Microsoft-style braced UUIDs."""
        # Some systems use braced UUIDs like {uuid}
        with pytest.raises(OnexError, match="Invalid UUID format"):
            validate_uuid("{550e8400-e29b-41d4-a716-446655440000}")

    def test_uuid_validator_handles_urn(self) -> None:
        """Test that UUID validator rejects URN-formatted UUIDs."""
        # URN format: urn:uuid:xxx
        with pytest.raises(OnexError, match="Invalid UUID format"):
            validate_uuid("urn:uuid:550e8400-e29b-41d4-a716-446655440000")

    def test_uuid_validator_all_zeros(self) -> None:
        """Test that nil UUID (all zeros) is valid."""
        result = validate_uuid("00000000-0000-0000-0000-000000000000")
        assert result == "00000000-0000-0000-0000-000000000000"

    def test_uuid_validator_all_ones(self) -> None:
        """Test that max UUID (all f's) is valid."""
        result = validate_uuid("ffffffff-ffff-ffff-ffff-ffffffffffff")
        assert result == "ffffffff-ffff-ffff-ffff-ffffffffffff"

    # =========================================================================
    # Duration Validator Edge Cases
    # =========================================================================

    def test_duration_validator_zero_duration(self) -> None:
        """Test that zero duration is valid."""
        result = validate_duration("PT0S")
        assert result == "PT0S"

    def test_duration_validator_large_values(self) -> None:
        """Test that large duration values are valid."""
        result = validate_duration("P999Y")
        assert result == "P999Y"
        result = validate_duration("PT999999999S")
        assert result == "PT999999999S"

    def test_duration_validator_decimal_precision(self) -> None:
        """Test that decimal seconds with various precisions are valid."""
        assert validate_duration("PT0.1S") == "PT0.1S"
        assert validate_duration("PT0.01S") == "PT0.01S"
        assert validate_duration("PT0.001S") == "PT0.001S"
        assert validate_duration("PT0.123456789S") == "PT0.123456789S"

    def test_duration_validator_case_sensitivity(self) -> None:
        """Test that duration validators are case-sensitive (uppercase only)."""
        # ISO 8601 durations use uppercase letters
        with pytest.raises(OnexError):
            validate_duration("pt1h")  # lowercase not valid
        with pytest.raises(OnexError):
            validate_duration("p1d")  # lowercase not valid

    # =========================================================================
    # Locale Validator Edge Cases
    # =========================================================================

    def test_locale_validator_case_sensitivity(self) -> None:
        """Test that locale validator handles case correctly.

        Language subtags are case-insensitive per BCP 47, but our validator
        may be strict. Test current behavior.
        """
        # Standard lowercase language
        assert validate_bcp47_locale("en") == "en"
        # Standard uppercase region
        assert validate_bcp47_locale("en-US") == "en-US"
        # Mixed case (depends on implementation)
        result = validate_bcp47_locale("EN-us")
        assert result is not None  # Just verify it doesn't crash

    def test_locale_validator_grandfathered_tags(self) -> None:
        """Test behavior with grandfathered language tags.

        Some grandfathered tags like 'i-default' exist in BCP 47.
        Our validator may or may not support them.
        """
        # These may fail or pass depending on implementation
        # Just ensure they don't crash unexpectedly
        try:
            validate_bcp47_locale("i-default")
        except OnexError:
            pass  # Expected if not supported

    def test_locale_validator_private_use(self) -> None:
        """Test behavior with private use subtags."""
        # Private use subtags start with 'x-'
        try:
            validate_bcp47_locale("x-custom")
        except OnexError:
            pass  # May not be supported

    # =========================================================================
    # Semantic Version Validator Edge Cases
    # =========================================================================

    def test_semver_validator_zero_version(self) -> None:
        """Test that 0.0.0 is a valid semantic version."""
        result = validate_semantic_version("0.0.0")
        assert result == "0.0.0"

    def test_semver_validator_very_large_numbers(self) -> None:
        """Test semantic versions with very large numbers."""
        result = validate_semantic_version("999999.999999.999999")
        assert result == "999999.999999.999999"

    def test_semver_validator_prerelease_with_hyphens(self) -> None:
        """Test prerelease identifiers containing hyphens."""
        result = validate_semantic_version("1.0.0-alpha-beta-gamma")
        assert result == "1.0.0-alpha-beta-gamma"

    def test_semver_validator_build_metadata_with_dots(self) -> None:
        """Test build metadata with multiple dot-separated parts."""
        result = validate_semantic_version("1.0.0+build.123.abc.def")
        assert result == "1.0.0+build.123.abc.def"

    def test_semver_validator_prerelease_numeric_only(self) -> None:
        """Test prerelease with numeric-only identifiers."""
        result = validate_semantic_version("1.0.0-1.2.3")
        assert result == "1.0.0-1.2.3"

    # =========================================================================
    # Error Code Validator Edge Cases
    # =========================================================================

    def test_error_code_single_letter_category(self) -> None:
        """Test error codes with single letter categories."""
        # Single letter followed by underscore and digits
        result = validate_error_code("A_1")
        assert result == "A_1"
        result = validate_error_code("X_999")
        assert result == "X_999"

    def test_error_code_boundary_digit_counts(self) -> None:
        """Test error codes at boundary digit counts (1-4 digits)."""
        # 1 digit (minimum)
        result = validate_error_code("ERR_1")
        assert result == "ERR_1"
        # 4 digits (maximum)
        result = validate_error_code("ERR_9999")
        assert result == "ERR_9999"
        # 5 digits should fail (tested elsewhere)

    def test_error_code_with_underscores_in_category(self) -> None:
        """Test error codes with underscores in category name."""
        result = validate_error_code("NETWORK_CONN_001")
        assert result == "NETWORK_CONN_001"
        result = validate_error_code("DB_SQL_SYNTAX_1")
        assert result == "DB_SQL_SYNTAX_1"

    def test_error_code_with_numbers_in_category(self) -> None:
        """Test error codes with numbers embedded in category."""
        result = validate_error_code("V2_AUTH_123")
        assert result == "V2_AUTH_123"
        result = validate_error_code("ERROR404_001")
        assert result == "ERROR404_001"

    def test_error_code_leading_zeros_in_suffix(self) -> None:
        """Test error codes with leading zeros in numeric suffix."""
        result = validate_error_code("AUTH_001")
        assert result == "AUTH_001"
        result = validate_error_code("AUTH_0001")
        assert result == "AUTH_0001"


@pytest.mark.unit
class TestValidatorNoneHandlingInModels:
    """Test None handling when validators are used in Pydantic models."""

    def test_optional_duration_accepts_none(self) -> None:
        """Test that optional Duration fields accept None."""

        class Config(BaseModel):
            timeout: Duration | None = None

        config = Config(timeout=None)
        assert config.timeout is None

        config2 = Config()
        assert config2.timeout is None

    def test_optional_locale_accepts_none(self) -> None:
        """Test that optional BCP47Locale fields accept None."""

        class Config(BaseModel):
            locale: BCP47Locale | None = None

        config = Config(locale=None)
        assert config.locale is None

    def test_optional_uuid_accepts_none(self) -> None:
        """Test that optional UUIDString fields accept None."""

        class Entity(BaseModel):
            parent_id: UUIDString | None = None

        entity = Entity(parent_id=None)
        assert entity.parent_id is None

    def test_optional_version_accepts_none(self) -> None:
        """Test that optional SemanticVersion fields accept None."""

        class Package(BaseModel):
            version: SemanticVersion | None = None

        package = Package(version=None)
        assert package.version is None

    def test_optional_error_code_accepts_none(self) -> None:
        """Test that optional ErrorCode fields accept None."""

        class ErrorReport(BaseModel):
            code: ErrorCode | None = None

        report = ErrorReport(code=None)
        assert report.code is None

        report2 = ErrorReport()
        assert report2.code is None

    def test_required_fields_reject_none(self) -> None:
        """Test that required validated fields reject None properly.

        Note: Pydantic catches None at the type level (since Duration is
        Annotated[str, ...] which doesn't accept None) before our custom
        validator runs, so this raises ValidationError not OnexError.
        """

        class Config(BaseModel):
            timeout: Duration
            locale: BCP47Locale
            id: UUIDString
            version: SemanticVersion

        with pytest.raises(ValidationError):
            Config(
                timeout=None,
                locale="en-US",
                id="550e8400-e29b-41d4-a716-446655440000",
                version="1.0.0",
            )


@pytest.mark.unit
class TestValidatorsNoneHandlingDirect:
    """Test handling of None values passed directly to validator functions.

    These tests verify what happens when None is passed directly to validators
    (not via Pydantic model optional fields). The validators use `if not value:`
    checks which treat None similarly to empty strings.
    """

    def test_validate_duration_none_raises_onex_error(self) -> None:
        """Test that None raises OnexError (treated as empty)."""
        # None triggers the `if not value:` check
        with pytest.raises(OnexError, match="cannot be empty"):
            validate_duration(None)  # type: ignore[arg-type]

    def test_validate_bcp47_locale_none_raises_onex_error(self) -> None:
        """Test that None raises OnexError (treated as empty)."""
        with pytest.raises(OnexError, match="cannot be empty"):
            validate_bcp47_locale(None)  # type: ignore[arg-type]

    def test_validate_uuid_none_raises_onex_error(self) -> None:
        """Test that None raises OnexError (treated as empty)."""
        with pytest.raises(OnexError, match="cannot be empty"):
            validate_uuid(None)  # type: ignore[arg-type]

    def test_validate_semantic_version_none_raises_onex_error(self) -> None:
        """Test that None raises OnexError (treated as empty)."""
        with pytest.raises(OnexError, match="cannot be empty"):
            validate_semantic_version(None)  # type: ignore[arg-type]

    def test_validate_error_code_none_raises_onex_error(self) -> None:
        """Test that None raises OnexError (treated as empty)."""
        with pytest.raises(OnexError, match="cannot be empty"):
            validate_error_code(None)  # type: ignore[arg-type]


@pytest.mark.unit
class TestValidatorsTypeEdgeCases:
    """Test handling of non-string types passed to validators."""

    @pytest.mark.parametrize(
        ("validator_func", "valid_input"),
        [
            (validate_duration, "PT1H"),
            (validate_bcp47_locale, "en-US"),
            (validate_uuid, "550e8400-e29b-41d4-a716-446655440000"),
            (validate_semantic_version, "1.0.0"),
            (validate_error_code, "AUTH_001"),
        ],
    )
    def test_validators_with_integer_input(
        self, validator_func: Callable[[str], str], valid_input: str
    ) -> None:
        """Test that validators reject integer inputs."""
        with pytest.raises((ValueError, TypeError, AttributeError)):
            validator_func(123)  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        ("validator_func", "valid_input"),
        [
            (validate_duration, "PT1H"),
            (validate_bcp47_locale, "en-US"),
            (validate_uuid, "550e8400-e29b-41d4-a716-446655440000"),
            (validate_semantic_version, "1.0.0"),
            (validate_error_code, "AUTH_001"),
        ],
    )
    def test_validators_with_list_input(
        self, validator_func: Callable[[str], str], valid_input: str
    ) -> None:
        """Test that validators reject list inputs."""
        with pytest.raises((ValueError, TypeError, AttributeError)):
            validator_func([valid_input])  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        ("validator_func", "valid_input"),
        [
            (validate_duration, "PT1H"),
            (validate_bcp47_locale, "en-US"),
            (validate_uuid, "550e8400-e29b-41d4-a716-446655440000"),
            (validate_semantic_version, "1.0.0"),
            (validate_error_code, "AUTH_001"),
        ],
    )
    def test_validators_with_dict_input(
        self, validator_func: Callable[[str], str], valid_input: str
    ) -> None:
        """Test that validators reject dict inputs."""
        with pytest.raises((ValueError, TypeError, AttributeError)):
            validator_func({"value": valid_input})  # type: ignore[arg-type]


@pytest.mark.unit
class TestEnumNormalizerEdgeCases:
    """Edge case tests for create_enum_normalizer factory."""

    def test_normalizer_with_empty_string(self) -> None:
        """Test that empty string is kept as-is (backward compat)."""
        from enum import Enum

        from omnibase_core.validation.validators import create_enum_normalizer

        class Status(Enum):
            ACTIVE = "active"

        normalizer = create_enum_normalizer(Status)
        result = normalizer("")
        assert result == ""

    def test_normalizer_with_whitespace_string(self) -> None:
        """Test that whitespace-only string is kept as-is."""
        from enum import Enum

        from omnibase_core.validation.validators import create_enum_normalizer

        class Status(Enum):
            ACTIVE = "active"

        normalizer = create_enum_normalizer(Status)
        result = normalizer("   ")
        assert result == "   "

    def test_normalizer_preserves_string_with_whitespace(self) -> None:
        """Test that strings with surrounding whitespace are kept as-is."""
        from enum import Enum

        from omnibase_core.validation.validators import create_enum_normalizer

        class Status(Enum):
            ACTIVE = "active"

        normalizer = create_enum_normalizer(Status)
        # Whitespace prevents matching, so kept as-is
        result = normalizer(" active ")
        assert result == " active "

    def test_normalizer_with_unicode_string(self) -> None:
        """Test normalizer with unicode strings."""
        from enum import Enum

        from omnibase_core.validation.validators import create_enum_normalizer

        class Status(Enum):
            ACTIVE = "active"
            PENDING = "pending"

        normalizer = create_enum_normalizer(Status)
        # Unicode string that doesn't match any enum value
        result = normalizer("\u0041CTIVE")  # 'A' as unicode + 'CTIVE'
        # This should normalize to 'active' via lowercase
        assert result == Status.ACTIVE

    def test_normalizer_with_mixed_case_enum_values(self) -> None:
        """Test normalizer with enums that have mixed case values.

        The normalizer lowercases the input and looks for exact match.
        Enums with mixed-case values like "InProgress" won't match
        lowercased input "inprogress" because the enum value is "InProgress".
        This is expected - normalizer works best with lowercase enum values.
        """
        from enum import Enum

        from omnibase_core.validation.validators import create_enum_normalizer

        class CamelStatus(Enum):
            InProgress = "InProgress"
            Completed = "Completed"

        normalizer = create_enum_normalizer(CamelStatus)
        # Lowercase input won't match mixed-case enum value "InProgress"
        # because normalizer does enum_class(input.lower())
        result = normalizer("inprogress")
        # Kept as string since no exact match found
        assert result == "inprogress"

        # Original case preserved when no match found
        result2 = normalizer("InProgress")
        # "InProgress".lower() = "inprogress", no match, so original kept
        assert result2 == "InProgress"

        # Enum instance passes through unchanged
        result3 = normalizer(CamelStatus.InProgress)
        assert result3 is CamelStatus.InProgress

    def test_normalizer_with_numeric_enum_values(self) -> None:
        """Test normalizer behavior with enums that have non-string values."""
        from enum import Enum

        from omnibase_core.validation.validators import create_enum_normalizer

        class Priority(Enum):
            LOW = 1
            MEDIUM = 2
            HIGH = 3

        normalizer = create_enum_normalizer(Priority)
        # String input won't match integer values
        result = normalizer("1")
        assert result == "1"  # Kept as-is

        # Enum value should pass through
        result = normalizer(Priority.LOW)
        assert result is Priority.LOW
