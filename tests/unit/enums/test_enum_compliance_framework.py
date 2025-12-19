"""
Tests for EnumComplianceFramework enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_compliance_framework import EnumComplianceFramework


@pytest.mark.unit
class TestEnumComplianceFramework:
    """Test cases for EnumComplianceFramework enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert EnumComplianceFramework.SOX == "SOX"
        assert EnumComplianceFramework.HIPAA == "HIPAA"
        assert EnumComplianceFramework.GDPR == "GDPR"
        assert EnumComplianceFramework.PCI_DSS == "PCI_DSS"
        assert EnumComplianceFramework.FISMA == "FISMA"
        assert EnumComplianceFramework.ISO27001 == "ISO27001"
        assert EnumComplianceFramework.NIST == "NIST"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumComplianceFramework, str)
        assert issubclass(EnumComplianceFramework, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        framework = EnumComplianceFramework.SOX
        assert isinstance(framework, str)
        assert framework == "SOX"
        assert len(framework) == 3
        assert framework.startswith("SO")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumComplianceFramework)
        assert len(values) == 7
        assert EnumComplianceFramework.SOX in values
        assert EnumComplianceFramework.NIST in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "SOX" in EnumComplianceFramework
        assert "invalid_framework" not in EnumComplianceFramework

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        framework1 = EnumComplianceFramework.SOX
        framework2 = EnumComplianceFramework.HIPAA

        assert framework1 != framework2
        assert framework1 == "SOX"
        assert framework2 == "HIPAA"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        framework = EnumComplianceFramework.GDPR
        serialized = framework.value
        assert serialized == "GDPR"

        # Test JSON serialization
        import json

        json_str = json.dumps(framework)
        assert json_str == '"GDPR"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        framework = EnumComplianceFramework("PCI_DSS")
        assert framework == EnumComplianceFramework.PCI_DSS

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumComplianceFramework("invalid_framework")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "SOX",
            "HIPAA",
            "GDPR",
            "PCI_DSS",
            "FISMA",
            "ISO27001",
            "NIST",
        }

        actual_values = {member.value for member in EnumComplianceFramework}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert "Supported compliance frameworks" in EnumComplianceFramework.__doc__

    def test_enum_compliance_frameworks(self):
        """Test that enum covers typical compliance frameworks."""
        # Test financial compliance
        assert EnumComplianceFramework.SOX in EnumComplianceFramework

        # Test healthcare compliance
        assert EnumComplianceFramework.HIPAA in EnumComplianceFramework

        # Test data protection compliance
        assert EnumComplianceFramework.GDPR in EnumComplianceFramework

        # Test payment card compliance
        assert EnumComplianceFramework.PCI_DSS in EnumComplianceFramework

        # Test government compliance
        assert EnumComplianceFramework.FISMA in EnumComplianceFramework

        # Test international standards
        assert EnumComplianceFramework.ISO27001 in EnumComplianceFramework
        assert EnumComplianceFramework.NIST in EnumComplianceFramework
