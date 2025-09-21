"""
Test module for EnumInstanceType.

Tests the instance type enumeration for cloud and service instances.
"""

import pytest

from src.omnibase_core.enums.enum_instance_type import EnumInstanceType


class TestEnumInstanceType:
    """Test cases for EnumInstanceType."""

    def test_enum_values(self):
        """Test that enum values are correctly defined."""
        assert EnumInstanceType.T2_MICRO.value == "t2.micro"
        assert EnumInstanceType.T3_MEDIUM.value == "t3.medium"
        assert EnumInstanceType.M5_LARGE.value == "m5.large"
        assert EnumInstanceType.AZURE_B1S.value == "B1s"
        assert EnumInstanceType.GCP_F1_MICRO.value == "f1-micro"
        assert EnumInstanceType.SMALL.value == "small"

    def test_string_conversion(self):
        """Test string conversion of enum values."""
        assert str(EnumInstanceType.T3_LARGE) == "t3.large"
        assert str(EnumInstanceType.CONTAINER_MEDIUM) == "container.medium"
        assert str(EnumInstanceType.DB_T2_SMALL) == "db.t2.small"

    def test_is_aws_instance(self):
        """Test AWS instance detection."""
        assert EnumInstanceType.is_aws_instance(EnumInstanceType.T2_MICRO) is True
        assert EnumInstanceType.is_aws_instance(EnumInstanceType.T3_MEDIUM) is True
        assert EnumInstanceType.is_aws_instance(EnumInstanceType.M5_LARGE) is True
        assert EnumInstanceType.is_aws_instance(EnumInstanceType.C5_XLARGE) is True
        assert EnumInstanceType.is_aws_instance(EnumInstanceType.R5_2XLARGE) is True
        assert EnumInstanceType.is_aws_instance(EnumInstanceType.I3_LARGE) is True

        # Non-AWS instances
        assert EnumInstanceType.is_aws_instance(EnumInstanceType.AZURE_B1S) is False
        assert EnumInstanceType.is_aws_instance(EnumInstanceType.GCP_F1_MICRO) is False
        assert EnumInstanceType.is_aws_instance(EnumInstanceType.SMALL) is False

    def test_is_azure_instance(self):
        """Test Azure instance detection."""
        assert EnumInstanceType.is_azure_instance(EnumInstanceType.AZURE_B1S) is True
        assert EnumInstanceType.is_azure_instance(EnumInstanceType.AZURE_B2MS) is True
        assert EnumInstanceType.is_azure_instance(EnumInstanceType.AZURE_D2S_V3) is True

        # Non-Azure instances
        assert EnumInstanceType.is_azure_instance(EnumInstanceType.T2_MICRO) is False
        assert EnumInstanceType.is_azure_instance(EnumInstanceType.GCP_F1_MICRO) is False
        assert EnumInstanceType.is_azure_instance(EnumInstanceType.SMALL) is False

    def test_is_gcp_instance(self):
        """Test Google Cloud instance detection."""
        assert EnumInstanceType.is_gcp_instance(EnumInstanceType.GCP_F1_MICRO) is True
        assert EnumInstanceType.is_gcp_instance(EnumInstanceType.GCP_G1_SMALL) is True
        assert EnumInstanceType.is_gcp_instance(EnumInstanceType.GCP_N1_STANDARD_2) is True

        # Non-GCP instances
        assert EnumInstanceType.is_gcp_instance(EnumInstanceType.T2_MICRO) is False
        assert EnumInstanceType.is_gcp_instance(EnumInstanceType.AZURE_B1S) is False
        assert EnumInstanceType.is_gcp_instance(EnumInstanceType.SMALL) is False

    def test_is_database_instance(self):
        """Test database instance detection."""
        assert EnumInstanceType.is_database_instance(EnumInstanceType.DB_T2_MICRO) is True
        assert EnumInstanceType.is_database_instance(EnumInstanceType.DB_T3_MEDIUM) is True

        # Non-database instances
        assert EnumInstanceType.is_database_instance(EnumInstanceType.T2_MICRO) is False
        assert EnumInstanceType.is_database_instance(EnumInstanceType.CONTAINER_SMALL) is False

    def test_is_container_instance(self):
        """Test container instance detection."""
        assert EnumInstanceType.is_container_instance(EnumInstanceType.CONTAINER_SMALL) is True
        assert EnumInstanceType.is_container_instance(EnumInstanceType.CONTAINER_XLARGE) is True

        # Non-container instances
        assert EnumInstanceType.is_container_instance(EnumInstanceType.T2_MICRO) is False
        assert EnumInstanceType.is_container_instance(EnumInstanceType.DB_T2_MICRO) is False

    def test_get_size_category(self):
        """Test size category determination."""
        # Micro instances
        assert EnumInstanceType.get_size_category(EnumInstanceType.T2_NANO) == "micro"
        assert EnumInstanceType.get_size_category(EnumInstanceType.T2_MICRO) == "micro"
        assert EnumInstanceType.get_size_category(EnumInstanceType.GCP_F1_MICRO) == "micro"
        assert EnumInstanceType.get_size_category(EnumInstanceType.DB_T2_MICRO) == "micro"

        # Small instances
        assert EnumInstanceType.get_size_category(EnumInstanceType.T2_SMALL) == "small"
        assert EnumInstanceType.get_size_category(EnumInstanceType.SMALL) == "small"
        assert EnumInstanceType.get_size_category(EnumInstanceType.CONTAINER_SMALL) == "small"

        # Medium instances
        assert EnumInstanceType.get_size_category(EnumInstanceType.T2_MEDIUM) == "medium"
        assert EnumInstanceType.get_size_category(EnumInstanceType.MEDIUM) == "medium"
        assert EnumInstanceType.get_size_category(EnumInstanceType.M5_LARGE) == "medium"

        # Large instances
        assert EnumInstanceType.get_size_category(EnumInstanceType.T2_LARGE) == "large"
        assert EnumInstanceType.get_size_category(EnumInstanceType.LARGE) == "large"

        # XLarge instances
        assert EnumInstanceType.get_size_category(EnumInstanceType.T3_XLARGE) == "xlarge"
        assert EnumInstanceType.get_size_category(EnumInstanceType.M5_2XLARGE) == "xlarge"
        assert EnumInstanceType.get_size_category(EnumInstanceType.XLARGE) == "xlarge"

    def test_enum_creation_from_string(self):
        """Test creating enum from string values."""
        assert EnumInstanceType("t2.micro") == EnumInstanceType.T2_MICRO
        assert EnumInstanceType("m5.large") == EnumInstanceType.M5_LARGE
        assert EnumInstanceType("small") == EnumInstanceType.SMALL

    def test_enum_creation_invalid_string(self):
        """Test that invalid string raises ValueError."""
        with pytest.raises(ValueError):
            EnumInstanceType("invalid.instance.type")

    def test_enum_equality(self):
        """Test enum equality comparisons."""
        assert EnumInstanceType.T2_MICRO == EnumInstanceType.T2_MICRO
        assert EnumInstanceType.T2_MICRO != EnumInstanceType.T2_SMALL
        assert EnumInstanceType.T2_MICRO == "t2.micro"

    def test_enum_in_collections(self):
        """Test enum usage in collections."""
        aws_instances = {
            EnumInstanceType.T2_MICRO,
            EnumInstanceType.T3_MEDIUM,
            EnumInstanceType.M5_LARGE
        }

        assert EnumInstanceType.T2_MICRO in aws_instances
        assert EnumInstanceType.AZURE_B1S not in aws_instances

    def test_comprehensive_coverage(self):
        """Test that all major cloud providers are covered."""
        # AWS instances
        aws_count = sum(1 for instance in EnumInstanceType if instance.value.startswith(('t2.', 't3.', 'm5.', 'c5.', 'r5.', 'i3.')))
        assert aws_count >= 15  # Should have reasonable AWS coverage

        # Azure instances
        azure_instances = [instance for instance in EnumInstanceType if EnumInstanceType.is_azure_instance(instance)]
        assert len(azure_instances) >= 7  # Should have reasonable Azure coverage

        # GCP instances
        gcp_instances = [instance for instance in EnumInstanceType if EnumInstanceType.is_gcp_instance(instance)]
        assert len(gcp_instances) >= 6  # Should have reasonable GCP coverage

        # Database instances
        db_instances = [instance for instance in EnumInstanceType if EnumInstanceType.is_database_instance(instance)]
        assert len(db_instances) >= 6  # Should have reasonable DB coverage

        # Container instances
        container_instances = [instance for instance in EnumInstanceType if EnumInstanceType.is_container_instance(instance)]
        assert len(container_instances) >= 4  # Should have reasonable container coverage