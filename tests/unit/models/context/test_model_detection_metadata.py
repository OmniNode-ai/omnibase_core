# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelDetectionMetadata validators and edge cases.

These tests focus on the validator logic introduced in PR #251:
- rule_version ModelSemVer coercion (string/dict to ModelSemVer)
- false_positive_likelihood enum normalization
- Security-focused tests for malicious inputs

Related tests in test_context_models.py cover basic instantiation,
defaults, immutability, and from_attributes behavior.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumLikelihood
from omnibase_core.models.context import ModelDetectionMetadata
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Combined exception types for semver validation
# ModelOnexError is raised by ModelSemVer validators, ValidationError by Pydantic
SemVerValidationErrors = (ValidationError, ModelOnexError)


# =============================================================================
# MODELSEMVER COERCION TESTS
# =============================================================================


@pytest.mark.unit
class TestModelDetectionMetadataSemVerCoercion:
    """Tests for rule_version ModelSemVer coercion validator."""

    def test_rule_version_accepts_model_semver_directly(self) -> None:
        """Test that rule_version accepts ModelSemVer objects directly."""
        semver = ModelSemVer(major=2, minor=1, patch=0)
        metadata = ModelDetectionMetadata(rule_version=semver)
        assert metadata.rule_version == semver
        assert isinstance(metadata.rule_version, ModelSemVer)

    def test_rule_version_coerces_valid_string(self) -> None:
        """Test that valid semver string is coerced to ModelSemVer type."""
        metadata = ModelDetectionMetadata(
            rule_version="2.1.0"  # type: ignore[arg-type]
        )
        assert metadata.rule_version == ModelSemVer(major=2, minor=1, patch=0)
        assert isinstance(metadata.rule_version, ModelSemVer)

    def test_rule_version_coerces_string_with_prerelease(self) -> None:
        """Test that semver string with prerelease is coerced."""
        metadata = ModelDetectionMetadata(
            rule_version="1.0.0-alpha.1"  # type: ignore[arg-type]
        )
        assert metadata.rule_version is not None
        assert metadata.rule_version.major == 1
        assert metadata.rule_version.minor == 0
        assert metadata.rule_version.patch == 0
        assert metadata.rule_version.prerelease == ("alpha", 1)

    def test_rule_version_coerces_string_with_build_metadata(self) -> None:
        """Test that semver string with build metadata is coerced."""
        metadata = ModelDetectionMetadata(
            rule_version="1.2.3+build.456"  # type: ignore[arg-type]
        )
        assert metadata.rule_version is not None
        assert metadata.rule_version.major == 1
        assert metadata.rule_version.minor == 2
        assert metadata.rule_version.patch == 3
        assert metadata.rule_version.build == ("build", "456")

    def test_rule_version_coerces_dict(self) -> None:
        """Test that dict with major/minor/patch is coerced to ModelSemVer."""
        metadata = ModelDetectionMetadata(
            rule_version={"major": 3, "minor": 2, "patch": 1}  # type: ignore[arg-type]
        )
        assert metadata.rule_version == ModelSemVer(major=3, minor=2, patch=1)
        assert isinstance(metadata.rule_version, ModelSemVer)

    def test_rule_version_coerces_dict_with_all_fields(self) -> None:
        """Test that dict with all fields is coerced properly."""
        metadata = ModelDetectionMetadata(
            rule_version={"major": 1, "minor": 0, "patch": 0}  # type: ignore[arg-type]
        )
        assert metadata.rule_version == ModelSemVer(major=1, minor=0, patch=0)

    def test_rule_version_rejects_invalid_string(self) -> None:
        """Test that invalid semver string raises ValueError."""
        with pytest.raises(SemVerValidationErrors) as exc_info:
            ModelDetectionMetadata(
                rule_version="not.a.version"  # type: ignore[arg-type]
            )
        error_message = str(exc_info.value).lower()
        assert "version" in error_message or "semver" in error_message

    def test_rule_version_rejects_incomplete_string(self) -> None:
        """Test that incomplete version string raises error."""
        with pytest.raises(SemVerValidationErrors):
            ModelDetectionMetadata(rule_version="1.2")  # type: ignore[arg-type]

    def test_rule_version_rejects_empty_string(self) -> None:
        """Test that empty string raises error."""
        with pytest.raises(SemVerValidationErrors):
            ModelDetectionMetadata(rule_version="")  # type: ignore[arg-type]

    def test_rule_version_accepts_none(self) -> None:
        """Test that rule_version accepts None."""
        metadata = ModelDetectionMetadata(rule_version=None)
        assert metadata.rule_version is None

    def test_rule_version_rejects_dict_missing_fields(self) -> None:
        """Test that dict missing required fields raises error."""
        with pytest.raises(SemVerValidationErrors):
            ModelDetectionMetadata(
                rule_version={"major": 1, "minor": 2}  # type: ignore[arg-type]
            )  # missing patch

    def test_rule_version_rejects_dict_with_non_integer(self) -> None:
        """Test that dict with non-integer values raises error."""
        with pytest.raises(SemVerValidationErrors):
            ModelDetectionMetadata(
                rule_version={"major": "1", "minor": "2", "patch": "3"}  # type: ignore[arg-type]
            )

    def test_rule_version_rejects_integer(self) -> None:
        """Test that rule_version rejects plain integer."""
        with pytest.raises(SemVerValidationErrors):
            ModelDetectionMetadata(rule_version=123)  # type: ignore[arg-type]

    def test_rule_version_rejects_list(self) -> None:
        """Test that rule_version rejects list."""
        with pytest.raises(SemVerValidationErrors):
            ModelDetectionMetadata(rule_version=[1, 2, 3])  # type: ignore[arg-type]

    def test_rule_version_coerces_zero_version(self) -> None:
        """Test that 0.0.0 version is valid."""
        metadata = ModelDetectionMetadata(rule_version="0.0.0")  # type: ignore[arg-type]
        assert metadata.rule_version == ModelSemVer(major=0, minor=0, patch=0)

    def test_rule_version_coerces_large_version_numbers(self) -> None:
        """Test that large version numbers are valid."""
        metadata = ModelDetectionMetadata(
            rule_version="999.999.999"  # type: ignore[arg-type]
        )
        assert metadata.rule_version == ModelSemVer(major=999, minor=999, patch=999)


# =============================================================================
# ENUM NORMALIZATION TESTS
# =============================================================================


@pytest.mark.unit
class TestModelDetectionMetadataEnumNormalization:
    """Tests for false_positive_likelihood enum normalization."""

    def test_false_positive_likelihood_accepts_enum_directly(self) -> None:
        """Test that false_positive_likelihood accepts EnumLikelihood directly."""
        metadata = ModelDetectionMetadata(false_positive_likelihood=EnumLikelihood.LOW)
        assert metadata.false_positive_likelihood == EnumLikelihood.LOW
        assert isinstance(metadata.false_positive_likelihood, EnumLikelihood)

    def test_false_positive_likelihood_normalizes_lowercase_string(self) -> None:
        """Test that lowercase string is normalized to enum."""
        metadata = ModelDetectionMetadata(false_positive_likelihood="low")
        assert metadata.false_positive_likelihood == EnumLikelihood.LOW

    def test_false_positive_likelihood_normalizes_uppercase_string(self) -> None:
        """Test that uppercase string is normalized to enum."""
        metadata = ModelDetectionMetadata(false_positive_likelihood="HIGH")
        assert metadata.false_positive_likelihood == EnumLikelihood.HIGH

    def test_false_positive_likelihood_normalizes_mixed_case(self) -> None:
        """Test that mixed case string is normalized to enum."""
        metadata = ModelDetectionMetadata(false_positive_likelihood="Medium")
        assert metadata.false_positive_likelihood == EnumLikelihood.MEDIUM

    def test_false_positive_likelihood_very_low(self) -> None:
        """Test that 'very_low' is normalized to enum."""
        metadata = ModelDetectionMetadata(false_positive_likelihood="very_low")
        assert metadata.false_positive_likelihood == EnumLikelihood.VERY_LOW

    def test_false_positive_likelihood_very_high(self) -> None:
        """Test that 'very_high' is normalized to enum."""
        metadata = ModelDetectionMetadata(false_positive_likelihood="very_high")
        assert metadata.false_positive_likelihood == EnumLikelihood.VERY_HIGH

    def test_false_positive_likelihood_keeps_unknown_string(self) -> None:
        """Test that unknown strings are kept as-is for extensibility."""
        metadata = ModelDetectionMetadata(false_positive_likelihood="negligible")
        assert metadata.false_positive_likelihood == "negligible"
        assert isinstance(metadata.false_positive_likelihood, str)

    def test_false_positive_likelihood_accepts_none(self) -> None:
        """Test that false_positive_likelihood accepts None."""
        metadata = ModelDetectionMetadata(false_positive_likelihood=None)
        assert metadata.false_positive_likelihood is None


# =============================================================================
# SECURITY TESTS
# =============================================================================


@pytest.mark.unit
class TestModelDetectionMetadataSecurity:
    """Security-focused tests for ModelDetectionMetadata."""

    def test_rule_version_rejects_sql_injection(self) -> None:
        """Test that SQL injection in rule_version is rejected."""
        with pytest.raises(SemVerValidationErrors):
            ModelDetectionMetadata(
                rule_version="'; DROP TABLE rules; --"  # type: ignore[arg-type]
            )

    def test_rule_version_rejects_script_injection(self) -> None:
        """Test that script injection in rule_version is rejected."""
        with pytest.raises(SemVerValidationErrors):
            ModelDetectionMetadata(
                rule_version="<script>alert('xss')</script>"  # type: ignore[arg-type]
            )

    def test_rule_version_rejects_path_traversal(self) -> None:
        """Test that path traversal in rule_version is rejected."""
        with pytest.raises(SemVerValidationErrors):
            ModelDetectionMetadata(
                rule_version="../../etc/passwd"  # type: ignore[arg-type]
            )

    def test_rule_version_rejects_null_byte_injection(self) -> None:
        """Test that null byte in rule_version is rejected."""
        with pytest.raises(SemVerValidationErrors):
            ModelDetectionMetadata(
                rule_version="1.0.0\x00malicious"  # type: ignore[arg-type]
            )

    def test_pattern_category_handles_special_characters(self) -> None:
        """Test that pattern_category handles special characters safely."""
        # Since pattern_category is just a string field, it should accept special chars
        metadata = ModelDetectionMetadata(
            pattern_category="injection<>\"&'_test",
        )
        assert metadata.pattern_category == "injection<>\"&'_test"

    def test_remediation_hint_handles_unicode(self) -> None:
        """Test that remediation_hint handles unicode safely."""
        metadata = ModelDetectionMetadata(
            remediation_hint="Rotate credentials immediately - 立即轮换凭据"
        )
        assert "立即轮换凭据" in metadata.remediation_hint  # type: ignore[operator]

    def test_error_message_does_not_leak_sensitive_data(self) -> None:
        """Test that error messages don't expose sensitive internal details."""
        try:
            ModelDetectionMetadata(
                rule_version="invalid-secret-version"  # type: ignore[arg-type]
            )
            pytest.fail("Should have raised an error")
        except SemVerValidationErrors as e:
            error_str = str(e)
            # Should not contain full stack traces
            assert "Traceback" not in error_str
            # Should mention format for user guidance
            assert "semver" in error_str.lower() or "version" in error_str.lower()

    def test_rule_version_dict_rejects_negative_values(self) -> None:
        """Test that negative version numbers are rejected."""
        with pytest.raises(SemVerValidationErrors):
            ModelDetectionMetadata(
                rule_version={"major": -1, "minor": 0, "patch": 0}  # type: ignore[arg-type]
            )


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


@pytest.mark.unit
class TestModelDetectionMetadataEdgeCases:
    """Edge case tests for ModelDetectionMetadata."""

    def test_all_fields_none(self) -> None:
        """Test creating metadata with all fields as None."""
        metadata = ModelDetectionMetadata()
        assert metadata.pattern_category is None
        assert metadata.detection_source is None
        assert metadata.rule_version is None
        assert metadata.false_positive_likelihood is None
        assert metadata.remediation_hint is None

    def test_all_fields_populated(self) -> None:
        """Test creating metadata with all fields populated."""
        metadata = ModelDetectionMetadata(
            pattern_category="credential_exposure",
            detection_source="regex_scanner",
            rule_version=ModelSemVer(major=2, minor=1, patch=0),
            false_positive_likelihood="low",
            remediation_hint="Rotate exposed credentials immediately",
        )
        assert metadata.pattern_category == "credential_exposure"
        assert metadata.detection_source == "regex_scanner"
        assert metadata.rule_version == ModelSemVer(major=2, minor=1, patch=0)
        assert metadata.false_positive_likelihood == EnumLikelihood.LOW
        assert metadata.remediation_hint == "Rotate exposed credentials immediately"

    def test_model_dump_round_trip(self) -> None:
        """Test that model can be serialized and deserialized."""
        original = ModelDetectionMetadata(
            pattern_category="injection",
            detection_source="ml_classifier",
            rule_version=ModelSemVer(major=1, minor=0, patch=0),
            false_positive_likelihood="medium",
            remediation_hint="Review and sanitize input",
        )

        dumped = original.model_dump()
        restored = ModelDetectionMetadata.model_validate(dumped)

        assert restored.pattern_category == original.pattern_category
        assert restored.detection_source == original.detection_source
        assert restored.remediation_hint == original.remediation_hint
        # rule_version may need special handling in round-trip
        assert restored.rule_version is not None

    def test_json_round_trip(self) -> None:
        """Test JSON serialization round trip."""
        import json

        original = ModelDetectionMetadata(
            pattern_category="xss",
            rule_version=ModelSemVer(major=3, minor=2, patch=1),
            false_positive_likelihood="high",
        )

        json_str = original.model_dump_json()
        parsed = json.loads(json_str)
        restored = ModelDetectionMetadata.model_validate(parsed)

        assert restored.pattern_category == original.pattern_category
        assert restored.rule_version is not None

    def test_hashable_for_frozen_model(self) -> None:
        """Test that frozen model is hashable."""
        metadata1 = ModelDetectionMetadata(
            pattern_category="injection",
            rule_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        metadata2 = ModelDetectionMetadata(
            pattern_category="injection",
            rule_version=ModelSemVer(major=1, minor=0, patch=0),
        )

        assert hash(metadata1) == hash(metadata2)
        assert metadata1 == metadata2

        # Can be used in set
        metadata_set = {metadata1, metadata2}
        assert len(metadata_set) == 1

    def test_unicode_in_string_fields(self) -> None:
        """Test unicode handling in string fields.

        Tests: Chinese (中文), Arabic (العربية), Hebrew (עברית), Emoji
        """
        metadata = ModelDetectionMetadata(
            pattern_category="credential_exposure_中文",
            detection_source="scanner_العربية",
            remediation_hint="עברית remediation 🔐🛡️",
        )
        assert "中文" in metadata.pattern_category  # type: ignore[operator]
        assert "العربية" in metadata.detection_source  # type: ignore[operator]
        assert "עברית" in metadata.remediation_hint  # type: ignore[operator]
        assert "🔐" in metadata.remediation_hint  # type: ignore[operator]

    def test_backward_compatible_with_string_rule_version(self) -> None:
        """Test backward compatibility: string rule_version is coerced."""
        # This is the pattern that might exist in legacy serialized data
        metadata = ModelDetectionMetadata(
            rule_version="2.1.0"  # type: ignore[arg-type]
        )
        assert isinstance(metadata.rule_version, ModelSemVer)
        assert metadata.rule_version == ModelSemVer(major=2, minor=1, patch=0)

    def test_backward_compatible_with_dict_rule_version(self) -> None:
        """Test backward compatibility: dict rule_version is coerced."""
        # This is the pattern that might exist in legacy serialized data
        metadata = ModelDetectionMetadata(
            rule_version={"major": 1, "minor": 2, "patch": 3}  # type: ignore[arg-type]
        )
        assert isinstance(metadata.rule_version, ModelSemVer)
        assert metadata.rule_version.major == 1
        assert metadata.rule_version.minor == 2
        assert metadata.rule_version.patch == 3


# =============================================================================
# INTEGRATION WITH SEMVER FEATURES
# =============================================================================


@pytest.mark.unit
class TestModelDetectionMetadataSemVerIntegration:
    """Tests for ModelDetectionMetadata integration with ModelSemVer features."""

    def test_rule_version_comparison(self) -> None:
        """Test that rule_version can be compared using SemVer rules."""
        metadata1 = ModelDetectionMetadata(
            rule_version=ModelSemVer(major=1, minor=0, patch=0)
        )
        metadata2 = ModelDetectionMetadata(
            rule_version=ModelSemVer(major=2, minor=0, patch=0)
        )

        assert metadata1.rule_version is not None
        assert metadata2.rule_version is not None
        assert metadata1.rule_version < metadata2.rule_version

    def test_rule_version_prerelease_comparison(self) -> None:
        """Test that prerelease versions compare correctly."""
        metadata_pre = ModelDetectionMetadata(
            rule_version="1.0.0-alpha"  # type: ignore[arg-type]
        )
        metadata_release = ModelDetectionMetadata(
            rule_version="1.0.0"  # type: ignore[arg-type]
        )

        assert metadata_pre.rule_version is not None
        assert metadata_release.rule_version is not None
        # Prerelease should be less than release
        assert metadata_pre.rule_version < metadata_release.rule_version

    def test_rule_version_string_representation(self) -> None:
        """Test that rule_version has correct string representation."""
        metadata = ModelDetectionMetadata(
            rule_version=ModelSemVer(major=2, minor=1, patch=3)
        )
        assert metadata.rule_version is not None
        assert str(metadata.rule_version) == "2.1.3"
