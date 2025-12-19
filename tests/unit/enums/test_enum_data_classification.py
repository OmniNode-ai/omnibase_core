"""
Unit tests for EnumDataClassification.

Tests all aspects of the data classification enum including:
- Enum value validation
- Helper methods for security level assessment
- String representation
- JSON serialization compatibility
- Pydantic integration
- Security and compliance features
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_data_classification import EnumDataClassification


@pytest.mark.unit
class TestEnumDataClassification:
    """Test cases for EnumDataClassification."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "PUBLIC": "public",
            "INTERNAL": "internal",
            "CONFIDENTIAL": "confidential",
            "RESTRICTED": "restricted",
            "SECRET": "secret",
            "TOP_SECRET": "top_secret",
            "OPEN": "open",
            "PRIVATE": "private",
            "SENSITIVE": "sensitive",
            "CLASSIFIED": "classified",
            "UNCLASSIFIED": "unclassified",
        }

        for name, value in expected_values.items():
            classification = getattr(EnumDataClassification, name)
            assert classification.value == value
            assert str(classification) == value

    def test_string_inheritance(self):
        """Test that enum inherits from str."""
        assert isinstance(EnumDataClassification.PUBLIC, str)
        assert EnumDataClassification.PUBLIC == "public"

    def test_string_representation(self):
        """Test string representation of enum values."""
        assert str(EnumDataClassification.PUBLIC) == "public"
        assert str(EnumDataClassification.CONFIDENTIAL) == "confidential"
        assert str(EnumDataClassification.SECRET) == "secret"

    def test_get_security_level(self):
        """Test the get_security_level class method."""
        # Test all security level mappings
        assert (
            EnumDataClassification.get_security_level(EnumDataClassification.PUBLIC)
            == 1
        )
        assert (
            EnumDataClassification.get_security_level(EnumDataClassification.OPEN) == 1
        )
        assert (
            EnumDataClassification.get_security_level(
                EnumDataClassification.UNCLASSIFIED
            )
            == 2
        )
        assert (
            EnumDataClassification.get_security_level(EnumDataClassification.INTERNAL)
            == 3
        )
        assert (
            EnumDataClassification.get_security_level(EnumDataClassification.PRIVATE)
            == 4
        )
        assert (
            EnumDataClassification.get_security_level(EnumDataClassification.SENSITIVE)
            == 5
        )
        assert (
            EnumDataClassification.get_security_level(
                EnumDataClassification.CONFIDENTIAL
            )
            == 6
        )
        assert (
            EnumDataClassification.get_security_level(EnumDataClassification.CLASSIFIED)
            == 7
        )
        assert (
            EnumDataClassification.get_security_level(EnumDataClassification.RESTRICTED)
            == 8
        )
        assert (
            EnumDataClassification.get_security_level(EnumDataClassification.SECRET)
            == 9
        )
        assert (
            EnumDataClassification.get_security_level(EnumDataClassification.TOP_SECRET)
            == 10
        )

    def test_is_public(self):
        """Test the is_public class method."""
        # Public classifications
        public_classifications = [
            EnumDataClassification.PUBLIC,
            EnumDataClassification.OPEN,
            EnumDataClassification.UNCLASSIFIED,
        ]
        for classification in public_classifications:
            assert EnumDataClassification.is_public(classification) is True

        # Non-public classifications
        non_public_classifications = [
            EnumDataClassification.INTERNAL,
            EnumDataClassification.CONFIDENTIAL,
            EnumDataClassification.SECRET,
        ]
        for classification in non_public_classifications:
            assert EnumDataClassification.is_public(classification) is False

    def test_requires_encryption(self):
        """Test the requires_encryption class method."""
        # Classifications requiring encryption
        encrypted_classifications = [
            EnumDataClassification.CONFIDENTIAL,
            EnumDataClassification.RESTRICTED,
            EnumDataClassification.SECRET,
            EnumDataClassification.TOP_SECRET,
            EnumDataClassification.CLASSIFIED,
        ]
        for classification in encrypted_classifications:
            assert EnumDataClassification.requires_encryption(classification) is True

        # Classifications not requiring encryption
        unencrypted_classifications = [
            EnumDataClassification.PUBLIC,
            EnumDataClassification.OPEN,
            EnumDataClassification.INTERNAL,
            EnumDataClassification.PRIVATE,
            EnumDataClassification.SENSITIVE,
        ]
        for classification in unencrypted_classifications:
            assert EnumDataClassification.requires_encryption(classification) is False

    def test_get_retention_policy(self):
        """Test the get_retention_policy class method."""
        # Test retention policies
        assert (
            EnumDataClassification.get_retention_policy(EnumDataClassification.PUBLIC)
            == "indefinite"
        )
        assert (
            EnumDataClassification.get_retention_policy(EnumDataClassification.OPEN)
            == "indefinite"
        )
        assert (
            EnumDataClassification.get_retention_policy(EnumDataClassification.INTERNAL)
            == "7_years"
        )
        assert (
            EnumDataClassification.get_retention_policy(EnumDataClassification.PRIVATE)
            == "7_years"
        )
        assert (
            EnumDataClassification.get_retention_policy(
                EnumDataClassification.CONFIDENTIAL
            )
            == "5_years"
        )
        assert (
            EnumDataClassification.get_retention_policy(
                EnumDataClassification.SENSITIVE
            )
            == "5_years"
        )
        assert (
            EnumDataClassification.get_retention_policy(
                EnumDataClassification.RESTRICTED
            )
            == "3_years"
        )
        assert (
            EnumDataClassification.get_retention_policy(
                EnumDataClassification.CLASSIFIED
            )
            == "3_years"
        )
        assert (
            EnumDataClassification.get_retention_policy(EnumDataClassification.SECRET)
            == "1_year"
        )
        assert (
            EnumDataClassification.get_retention_policy(
                EnumDataClassification.TOP_SECRET
            )
            == "1_year"
        )

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert EnumDataClassification.PUBLIC == EnumDataClassification.PUBLIC
        assert EnumDataClassification.SECRET != EnumDataClassification.PUBLIC

    def test_enum_membership(self):
        """Test enum membership checking."""
        all_classifications = list(EnumDataClassification)
        for classification in all_classifications:
            assert classification in EnumDataClassification

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        classifications = list(EnumDataClassification)
        assert len(classifications) == 11

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        # Test direct serialization
        classification = EnumDataClassification.CONFIDENTIAL
        json_str = json.dumps(classification, default=str)
        assert json_str == '"confidential"'

        # Test in dictionary
        data = {"classification": EnumDataClassification.SECRET}
        json_str = json.dumps(data, default=str)
        assert '"classification": "secret"' in json_str

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class DataConfig(BaseModel):
            classification: EnumDataClassification

        # Test valid enum assignment
        config = DataConfig(classification=EnumDataClassification.CONFIDENTIAL)
        assert config.classification == EnumDataClassification.CONFIDENTIAL

        # Test string assignment (should work due to str inheritance)
        config = DataConfig(classification="secret")
        assert config.classification == EnumDataClassification.SECRET

        # Test invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            DataConfig(classification="invalid_classification")

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""

        class DataConfig(BaseModel):
            classification: EnumDataClassification

        config = DataConfig(classification=EnumDataClassification.RESTRICTED)

        # Test dict serialization
        config_dict = config.model_dump()
        assert config_dict == {"classification": "restricted"}

        # Test JSON serialization
        json_str = config.model_dump_json()
        assert json_str == '{"classification":"restricted"}'

    def test_security_level_ordering(self):
        """Test that security levels are properly ordered."""
        # Lower security levels should have lower numbers
        public_level = EnumDataClassification.get_security_level(
            EnumDataClassification.PUBLIC
        )
        internal_level = EnumDataClassification.get_security_level(
            EnumDataClassification.INTERNAL
        )
        secret_level = EnumDataClassification.get_security_level(
            EnumDataClassification.SECRET
        )

        assert public_level < internal_level < secret_level

    def test_aliases(self):
        """Test that alias classifications have appropriate security levels."""
        # PUBLIC and OPEN should have same level
        public_level = EnumDataClassification.get_security_level(
            EnumDataClassification.PUBLIC
        )
        open_level = EnumDataClassification.get_security_level(
            EnumDataClassification.OPEN
        )
        assert public_level == open_level

        # All classifications should have valid security levels
        for classification in EnumDataClassification:
            security_level = EnumDataClassification.get_security_level(classification)
            assert 1 <= security_level <= 10

    def test_comprehensive_security_features(self):
        """Test comprehensive security features for each classification level."""
        # Public data: low security, no encryption, indefinite retention
        assert (
            EnumDataClassification.get_security_level(EnumDataClassification.PUBLIC)
            == 1
        )
        assert EnumDataClassification.is_public(EnumDataClassification.PUBLIC) is True
        assert (
            EnumDataClassification.requires_encryption(EnumDataClassification.PUBLIC)
            is False
        )
        assert (
            EnumDataClassification.get_retention_policy(EnumDataClassification.PUBLIC)
            == "indefinite"
        )

        # Confidential data: higher security, requires encryption, 5-year retention
        assert (
            EnumDataClassification.get_security_level(
                EnumDataClassification.CONFIDENTIAL
            )
            == 6
        )
        assert (
            EnumDataClassification.is_public(EnumDataClassification.CONFIDENTIAL)
            is False
        )
        assert (
            EnumDataClassification.requires_encryption(
                EnumDataClassification.CONFIDENTIAL
            )
            is True
        )
        assert (
            EnumDataClassification.get_retention_policy(
                EnumDataClassification.CONFIDENTIAL
            )
            == "5_years"
        )

        # Top Secret: highest security, requires encryption, 1-year retention
        assert (
            EnumDataClassification.get_security_level(EnumDataClassification.TOP_SECRET)
            == 10
        )
        assert (
            EnumDataClassification.is_public(EnumDataClassification.TOP_SECRET) is False
        )
        assert (
            EnumDataClassification.requires_encryption(
                EnumDataClassification.TOP_SECRET
            )
            is True
        )
        assert (
            EnumDataClassification.get_retention_policy(
                EnumDataClassification.TOP_SECRET
            )
            == "1_year"
        )

    def test_encryption_requirements(self):
        """Test encryption requirements across security levels."""
        # High security levels should require encryption
        high_security = [
            EnumDataClassification.CONFIDENTIAL,
            EnumDataClassification.RESTRICTED,
            EnumDataClassification.SECRET,
            EnumDataClassification.TOP_SECRET,
        ]
        for classification in high_security:
            assert EnumDataClassification.requires_encryption(classification) is True

        # Low security levels should not require encryption
        low_security = [
            EnumDataClassification.PUBLIC,
            EnumDataClassification.OPEN,
            EnumDataClassification.UNCLASSIFIED,
        ]
        for classification in low_security:
            assert EnumDataClassification.requires_encryption(classification) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
