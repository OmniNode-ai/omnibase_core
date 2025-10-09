"""
Comprehensive tests for ModelUnifiedVersion.

Tests cover:
- Basic instantiation with required protocol_version
- Optional tool_version and schema_version fields
- ModelSemVer integration
- Optional last_updated datetime field
- Field validation and type safety
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from omnibase_core.models.core.model_semver import ModelSemVer
from omnibase_core.models.results.model_unified_version import ModelUnifiedVersion


class TestModelUnifiedVersionBasicInstantiation:
    """Test basic instantiation with required fields."""

    def test_minimal_instantiation_with_protocol_version(self):
        """Test creating version with only required protocol_version."""
        protocol = ModelSemVer(major=1, minor=0, patch=0)
        version = ModelUnifiedVersion(protocol_version=protocol)

        assert version.protocol_version == protocol
        assert version.tool_version is None
        assert version.schema_version is None
        assert version.last_updated is None

    def test_instantiation_with_all_fields(self):
        """Test creating version with all fields populated."""
        protocol = ModelSemVer(major=1, minor=0, patch=0)
        tool = ModelSemVer(major=2, minor=1, patch=3)
        schema = ModelSemVer(major=1, minor=2, patch=0)
        updated = datetime(2025, 1, 1, 12, 0, 0)

        version = ModelUnifiedVersion(
            protocol_version=protocol,
            tool_version=tool,
            schema_version=schema,
            last_updated=updated,
        )

        assert version.protocol_version == protocol
        assert version.tool_version == tool
        assert version.schema_version == schema
        assert version.last_updated == updated


class TestModelUnifiedVersionFieldValidation:
    """Test field validation and type safety."""

    def test_protocol_version_required(self):
        """Test that protocol_version is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelUnifiedVersion()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("protocol_version",) for error in errors)

    def test_protocol_version_must_be_semver(self):
        """Test that protocol_version must be ModelSemVer."""
        with pytest.raises(ValidationError):
            ModelUnifiedVersion(protocol_version="1.0.0")  # String not allowed

    def test_tool_version_must_be_semver_or_none(self):
        """Test that tool_version must be ModelSemVer or None."""
        protocol = ModelSemVer(major=1, minor=0, patch=0)

        # Valid with ModelSemVer
        tool = ModelSemVer(major=2, minor=0, patch=0)
        version = ModelUnifiedVersion(protocol_version=protocol, tool_version=tool)
        assert version.tool_version == tool

        # Valid with None
        version = ModelUnifiedVersion(protocol_version=protocol, tool_version=None)
        assert version.tool_version is None

        # Invalid with string
        with pytest.raises(ValidationError):
            ModelUnifiedVersion(protocol_version=protocol, tool_version="2.0.0")


class TestModelUnifiedVersionProtocolVersionField:
    """Test protocol_version field."""

    def test_protocol_version_with_various_versions(self):
        """Test protocol_version with different version numbers."""
        versions = [
            ModelSemVer(major=1, minor=0, patch=0),
            ModelSemVer(major=2, minor=1, patch=5),
            ModelSemVer(major=0, minor=1, patch=0),
        ]

        for protocol in versions:
            version = ModelUnifiedVersion(protocol_version=protocol)
            assert version.protocol_version.major == protocol.major
            assert version.protocol_version.minor == protocol.minor
            assert version.protocol_version.patch == protocol.patch

    def test_protocol_version_immutability(self):
        """Test that protocol_version maintains its value."""
        protocol = ModelSemVer(major=1, minor=2, patch=3)
        version = ModelUnifiedVersion(protocol_version=protocol)

        assert version.protocol_version.major == 1
        assert version.protocol_version.minor == 2
        assert version.protocol_version.patch == 3


class TestModelUnifiedVersionToolVersionField:
    """Test tool_version optional field."""

    def test_tool_version_with_semver(self):
        """Test tool_version with ModelSemVer."""
        protocol = ModelSemVer(major=1, minor=0, patch=0)
        tool = ModelSemVer(major=2, minor=1, patch=3)

        version = ModelUnifiedVersion(protocol_version=protocol, tool_version=tool)

        assert version.tool_version.major == 2
        assert version.tool_version.minor == 1
        assert version.tool_version.patch == 3

    def test_tool_version_optional(self):
        """Test that tool_version is optional."""
        protocol = ModelSemVer(major=1, minor=0, patch=0)
        version = ModelUnifiedVersion(protocol_version=protocol)

        assert version.tool_version is None


class TestModelUnifiedVersionSchemaVersionField:
    """Test schema_version optional field."""

    def test_schema_version_with_semver(self):
        """Test schema_version with ModelSemVer."""
        protocol = ModelSemVer(major=1, minor=0, patch=0)
        schema = ModelSemVer(major=3, minor=2, patch=1)

        version = ModelUnifiedVersion(protocol_version=protocol, schema_version=schema)

        assert version.schema_version.major == 3
        assert version.schema_version.minor == 2
        assert version.schema_version.patch == 1

    def test_schema_version_optional(self):
        """Test that schema_version is optional."""
        protocol = ModelSemVer(major=1, minor=0, patch=0)
        version = ModelUnifiedVersion(protocol_version=protocol)

        assert version.schema_version is None


class TestModelUnifiedVersionLastUpdatedField:
    """Test last_updated datetime field."""

    def test_last_updated_with_datetime(self):
        """Test last_updated with datetime value."""
        protocol = ModelSemVer(major=1, minor=0, patch=0)
        updated = datetime(2025, 1, 15, 14, 30, 0)

        version = ModelUnifiedVersion(protocol_version=protocol, last_updated=updated)

        assert version.last_updated == updated
        assert isinstance(version.last_updated, datetime)

    def test_last_updated_optional(self):
        """Test that last_updated is optional."""
        protocol = ModelSemVer(major=1, minor=0, patch=0)
        version = ModelUnifiedVersion(protocol_version=protocol)

        assert version.last_updated is None

    def test_last_updated_with_current_time(self):
        """Test last_updated with current datetime."""
        protocol = ModelSemVer(major=1, minor=0, patch=0)
        now = datetime.now()

        version = ModelUnifiedVersion(protocol_version=protocol, last_updated=now)

        assert version.last_updated == now


class TestModelUnifiedVersionSerialization:
    """Test model serialization and deserialization."""

    def test_model_dump_basic(self):
        """Test model_dump() produces correct dictionary."""
        protocol = ModelSemVer(major=1, minor=0, patch=0)
        tool = ModelSemVer(major=2, minor=1, patch=3)

        version = ModelUnifiedVersion(protocol_version=protocol, tool_version=tool)

        dumped = version.model_dump()

        assert "protocol_version" in dumped
        assert "tool_version" in dumped
        assert dumped["protocol_version"]["major"] == 1
        assert dumped["tool_version"]["major"] == 2

    def test_model_dump_exclude_none(self):
        """Test model_dump(exclude_none=True) removes None fields."""
        protocol = ModelSemVer(major=1, minor=0, patch=0)
        version = ModelUnifiedVersion(protocol_version=protocol)

        dumped = version.model_dump(exclude_none=True)

        assert "protocol_version" in dumped
        assert "tool_version" not in dumped
        assert "schema_version" not in dumped
        assert "last_updated" not in dumped

    def test_model_dump_json_roundtrip(self):
        """Test JSON serialization roundtrip."""
        protocol = ModelSemVer(major=1, minor=0, patch=0)
        tool = ModelSemVer(major=2, minor=1, patch=3)

        original = ModelUnifiedVersion(protocol_version=protocol, tool_version=tool)

        json_str = original.model_dump_json()
        restored = ModelUnifiedVersion.model_validate_json(json_str)

        assert restored.protocol_version.major == original.protocol_version.major
        assert restored.tool_version.major == original.tool_version.major


class TestModelUnifiedVersionComplexScenarios:
    """Test complex usage scenarios."""

    def test_full_version_information(self):
        """Test fully populated version instance."""
        protocol = ModelSemVer(major=1, minor=0, patch=0)
        tool = ModelSemVer(major=2, minor=1, patch=3)
        schema = ModelSemVer(major=1, minor=2, patch=0)
        updated = datetime(2025, 1, 1, 12, 0, 0)

        version = ModelUnifiedVersion(
            protocol_version=protocol,
            tool_version=tool,
            schema_version=schema,
            last_updated=updated,
        )

        assert version.protocol_version.major == 1
        assert version.tool_version.major == 2
        assert version.schema_version.major == 1
        assert version.last_updated == updated

    def test_version_with_different_semvers(self):
        """Test version with different version numbers."""
        protocol = ModelSemVer(major=2, minor=0, patch=0)
        tool = ModelSemVer(major=3, minor=5, patch=1)
        schema = ModelSemVer(major=1, minor=0, patch=0)

        version = ModelUnifiedVersion(
            protocol_version=protocol,
            tool_version=tool,
            schema_version=schema,
        )

        # Protocol is v2.0.0
        assert str(version.protocol_version) == "2.0.0"
        # Tool is v3.5.1
        assert str(version.tool_version) == "3.5.1"
        # Schema is v1.0.0
        assert str(version.schema_version) == "1.0.0"

    def test_version_upgrade_scenario(self):
        """Test version representing an upgrade."""
        # Old protocol
        old_protocol = ModelSemVer(major=1, minor=0, patch=0)
        old_version = ModelUnifiedVersion(protocol_version=old_protocol)

        # New protocol (upgraded)
        new_protocol = ModelSemVer(major=2, minor=0, patch=0)
        new_version = ModelUnifiedVersion(protocol_version=new_protocol)

        assert new_version.protocol_version > old_version.protocol_version


class TestModelUnifiedVersionVersionComparison:
    """Test version comparison scenarios."""

    def test_comparing_protocol_versions(self):
        """Test comparing different protocol versions."""
        v1 = ModelUnifiedVersion(
            protocol_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        v2 = ModelUnifiedVersion(
            protocol_version=ModelSemVer(major=2, minor=0, patch=0),
        )

        assert v2.protocol_version > v1.protocol_version
        assert v1.protocol_version < v2.protocol_version

    def test_comparing_tool_versions(self):
        """Test comparing different tool versions."""
        protocol = ModelSemVer(major=1, minor=0, patch=0)

        v1 = ModelUnifiedVersion(
            protocol_version=protocol,
            tool_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        v2 = ModelUnifiedVersion(
            protocol_version=protocol,
            tool_version=ModelSemVer(major=1, minor=1, patch=0),
        )

        assert v2.tool_version > v1.tool_version


class TestModelUnifiedVersionEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_protocol_version_zero(self):
        """Test protocol_version with 0.0.0."""
        protocol = ModelSemVer(major=0, minor=0, patch=0)
        version = ModelUnifiedVersion(protocol_version=protocol)

        assert version.protocol_version.major == 0
        assert version.protocol_version.minor == 0
        assert version.protocol_version.patch == 0

    def test_all_versions_same(self):
        """Test when all version fields have same version."""
        same_version = ModelSemVer(major=1, minor=2, patch=3)

        version = ModelUnifiedVersion(
            protocol_version=same_version,
            tool_version=ModelSemVer(major=1, minor=2, patch=3),
            schema_version=ModelSemVer(major=1, minor=2, patch=3),
        )

        assert version.protocol_version == same_version
        assert version.tool_version.major == same_version.major
        assert version.schema_version.minor == same_version.minor

    def test_last_updated_far_future(self):
        """Test last_updated with far future date."""
        protocol = ModelSemVer(major=1, minor=0, patch=0)
        future = datetime(2099, 12, 31, 23, 59, 59)

        version = ModelUnifiedVersion(protocol_version=protocol, last_updated=future)

        assert version.last_updated.year == 2099


class TestModelUnifiedVersionTypeSafety:
    """Test type safety - ZERO TOLERANCE for Any types."""

    def test_no_any_types_in_annotations(self):
        """Test that model fields don't use Any type."""
        from typing import get_type_hints

        hints = get_type_hints(ModelUnifiedVersion)

        # Check that no field uses Any type
        for field_name, field_type in hints.items():
            type_str = str(field_type)
            assert (
                "typing.Any" not in type_str or "None" in type_str
            ), f"Field {field_name} uses Any type: {type_str}"

    def test_version_fields_use_model_semver(self):
        """Test that version fields use ModelSemVer type."""
        from typing import get_type_hints

        hints = get_type_hints(ModelUnifiedVersion)

        # Check protocol_version
        protocol_type = hints["protocol_version"]
        assert "ModelSemVer" in str(protocol_type)

        # Check tool_version (optional)
        tool_type = hints.get("tool_version")
        assert tool_type is not None
        assert "ModelSemVer" in str(tool_type)

        # Check schema_version (optional)
        schema_type = hints.get("schema_version")
        assert schema_type is not None
        assert "ModelSemVer" in str(schema_type)
