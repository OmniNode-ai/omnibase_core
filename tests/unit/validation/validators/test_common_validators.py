"""
Comprehensive tests for common validators.

This module tests the shared validators for common patterns:
- ISO 8601 duration strings
- BCP 47 locale tags
- UUID strings
- Semantic version strings (SemVer 2.0.0)

Ticket: OMN-1054
"""

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.validation.validators import (
    BCP47Locale,
    Duration,
    SemanticVersion,
    UUID,
    validate_bcp47_locale,
    validate_duration,
    validate_semantic_version,
    validate_uuid,
)


# =============================================================================
# Duration Validator Tests
# =============================================================================


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
            "P1WT1H",  # 1 week 1 hour
        ],
    )
    def test_valid_durations(self, duration: str) -> None:
        """Test that valid duration strings are accepted."""
        result = validate_duration(duration)
        assert result == duration

    @pytest.mark.parametrize(
        "duration,error_fragment",
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
        """Test that invalid duration strings raise ValueError."""
        with pytest.raises(ValueError, match=error_fragment):
            validate_duration(duration)



class TestDurationAnnotatedType:
    """Tests for Duration Annotated type with Pydantic."""

    def test_valid_duration_in_model(self) -> None:
        """Test that valid durations work in Pydantic models."""

        class Config(BaseModel):
            timeout: Duration

        config = Config(timeout="PT1H30M")
        assert config.timeout == "PT1H30M"

    def test_invalid_duration_in_model(self) -> None:
        """Test that invalid durations raise ValidationError."""

        class Config(BaseModel):
            timeout: Duration

        with pytest.raises(ValidationError):
            Config(timeout="invalid")


# =============================================================================
# BCP 47 Locale Validator Tests
# =============================================================================


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
        "locale,error_fragment",
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
        """Test that invalid locale strings raise ValueError."""
        with pytest.raises(ValueError, match=error_fragment):
            validate_bcp47_locale(locale)



class TestBCP47LocaleAnnotatedType:
    """Tests for BCP47Locale Annotated type with Pydantic."""

    def test_valid_locale_in_model(self) -> None:
        """Test that valid locales work in Pydantic models."""

        class UserPreferences(BaseModel):
            locale: BCP47Locale

        prefs = UserPreferences(locale="en-US")
        assert prefs.locale == "en-US"

    def test_invalid_locale_in_model(self) -> None:
        """Test that invalid locales raise ValidationError."""

        class UserPreferences(BaseModel):
            locale: BCP47Locale

        with pytest.raises(ValidationError):
            UserPreferences(locale="invalid_locale")


# =============================================================================
# UUID Validator Tests
# =============================================================================


class TestValidateUUID:
    """Tests for validate_uuid function."""

    @pytest.mark.parametrize(
        "uuid_str,expected",
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
        "uuid_str,error_fragment",
        [
            ("", "cannot be empty"),
            ("invalid-uuid", "Invalid UUID format"),
            ("550e8400-e29b-41d4-a716", "Invalid UUID format"),  # Too short
            (
                "550e8400-e29b-41d4-a716-4466554400000",
                "Invalid UUID format",
            ),  # Too long
            ("550e8400-e29b-41d4-a716-44665544000g", "Invalid UUID format"),  # Invalid char
            ("550e8400-e29b-41d4-a716-44665544000", "Invalid UUID format"),  # Missing digit
            ("550e8400_e29b_41d4_a716_446655440000", "Invalid UUID format"),  # Underscores
            ("550e8400e29b41d4a71644665544000", "Invalid UUID format"),  # One digit short
        ],
    )
    def test_invalid_uuids(self, uuid_str: str, error_fragment: str) -> None:
        """Test that invalid UUID strings raise ValueError."""
        with pytest.raises(ValueError, match=error_fragment):
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


class TestUUIDAnnotatedType:
    """Tests for UUID Annotated type with Pydantic."""

    def test_valid_uuid_in_model(self) -> None:
        """Test that valid UUIDs work in Pydantic models."""

        class Entity(BaseModel):
            id: UUID

        entity = Entity(id="550e8400-e29b-41d4-a716-446655440000")
        assert entity.id == "550e8400-e29b-41d4-a716-446655440000"

    def test_uuid_normalization_in_model(self) -> None:
        """Test that UUIDs are normalized in Pydantic models."""

        class Entity(BaseModel):
            id: UUID

        entity = Entity(id="550E8400E29B41D4A716446655440000")
        assert entity.id == "550e8400-e29b-41d4-a716-446655440000"

    def test_invalid_uuid_in_model(self) -> None:
        """Test that invalid UUIDs raise ValidationError."""

        class Entity(BaseModel):
            id: UUID

        with pytest.raises(ValidationError):
            Entity(id="invalid-uuid")


# =============================================================================
# Semantic Version Validator Tests
# =============================================================================


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
        "version,error_fragment",
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
            ("1.0.0-01", "Invalid semantic version format"),  # Leading zero in prerelease
            ("1.0.0-alpha..1", "Invalid semantic version format"),  # Double dot
            ("1.0.0+build..1", "Invalid semantic version format"),  # Double dot
            ("a.b.c", "Invalid semantic version format"),  # Non-numeric
            ("-1.0.0", "Invalid semantic version format"),  # Negative
            ("1.-1.0", "Invalid semantic version format"),  # Negative
            ("1.0.-1", "Invalid semantic version format"),  # Negative
        ],
    )
    def test_invalid_versions(self, version: str, error_fragment: str) -> None:
        """Test that invalid version strings raise ValueError."""
        with pytest.raises(ValueError, match=error_fragment):
            validate_semantic_version(version)



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
        """Test that invalid versions raise ValidationError."""

        class Package(BaseModel):
            version: SemanticVersion

        with pytest.raises(ValidationError):
            Package(version="1.0")


# =============================================================================
# Integration Tests
# =============================================================================


class TestMultipleValidatorsInModel:
    """Tests for using multiple validators in a single Pydantic model."""

    def test_all_validators_in_model(self) -> None:
        """Test that all validators work together in a single model."""

        class ComplexConfig(BaseModel):
            id: UUID
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
            id: UUID
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


class TestImports:
    """Tests for import paths."""

    def test_import_from_validators_package(self) -> None:
        """Test that validators can be imported from the validators package."""
        from omnibase_core.validation.validators import (
            BCP47Locale,
            Duration,
            SemanticVersion,
            UUID,
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

    def test_import_from_validation_package(self) -> None:
        """Test that validators can be imported from the main validation package."""
        from omnibase_core.validation import (
            BCP47Locale,
            Duration,
            SemanticVersion,
            UUID,
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
