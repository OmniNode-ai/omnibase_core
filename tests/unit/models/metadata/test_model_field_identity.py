# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelFieldIdentity."""

from uuid import uuid4

import pytest

from omnibase_core.models.metadata.model_field_identity import ModelFieldIdentity


@pytest.mark.unit
class TestModelFieldIdentityInstantiation:
    """Tests for ModelFieldIdentity instantiation."""

    def test_create_with_required_fields(self):
        """Test creating field identity with required fields."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(identity_id=identity_id, field_id=field_id)
        assert identity.identity_id == identity_id
        assert identity.field_id == field_id
        assert identity.description == ""

    def test_create_with_display_names(self):
        """Test creating field identity with display names."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(
            identity_id=identity_id,
            field_id=field_id,
            identity_display_name="METADATA_VERSION",
            field_display_name="metadata_version",
        )
        assert identity.identity_display_name == "METADATA_VERSION"
        assert identity.field_display_name == "metadata_version"

    def test_create_with_description(self):
        """Test creating field identity with description."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(
            identity_id=identity_id,
            field_id=field_id,
            description="Test description",
        )
        assert identity.description == "Test description"

    def test_create_with_all_fields(self):
        """Test creating field identity with all fields."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(
            identity_id=identity_id,
            field_id=field_id,
            identity_display_name="TEST_FIELD",
            field_display_name="test_field",
            description="A test field",
        )
        assert identity.identity_id == identity_id
        assert identity.field_id == field_id
        assert identity.identity_display_name == "TEST_FIELD"
        assert identity.field_display_name == "test_field"
        assert identity.description == "A test field"


@pytest.mark.unit
class TestModelFieldIdentityValidation:
    """Tests for ModelFieldIdentity validation."""

    def test_identity_display_name_pattern_valid_uppercase(self):
        """Test valid uppercase identity display name."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(
            identity_id=identity_id,
            field_id=field_id,
            identity_display_name="VALID_NAME",
        )
        assert identity.identity_display_name == "VALID_NAME"

    def test_identity_display_name_pattern_valid_with_numbers(self):
        """Test valid identity display name with numbers."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(
            identity_id=identity_id,
            field_id=field_id,
            identity_display_name="FIELD_123",
        )
        assert identity.identity_display_name == "FIELD_123"

    def test_identity_display_name_pattern_invalid_lowercase_start(self):
        """Test invalid identity display name starting with lowercase."""
        identity_id = uuid4()
        field_id = uuid4()
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelFieldIdentity(
                identity_id=identity_id,
                field_id=field_id,
                identity_display_name="invalid_name",
            )

    def test_identity_display_name_pattern_invalid_special_chars(self):
        """Test invalid identity display name with special characters."""
        identity_id = uuid4()
        field_id = uuid4()
        with pytest.raises(Exception):  # Pydantic ValidationError
            ModelFieldIdentity(
                identity_id=identity_id,
                field_id=field_id,
                identity_display_name="INVALID-NAME",
            )


@pytest.mark.unit
class TestModelFieldIdentityGetDisplayName:
    """Tests for get_display_name method."""

    def test_get_display_name_with_identity_display_name(self):
        """Test get_display_name with identity_display_name set."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(
            identity_id=identity_id,
            field_id=field_id,
            identity_display_name="METADATA_VERSION",
        )
        display_name = identity.get_display_name()
        assert display_name == "Metadata Version"

    def test_get_display_name_without_identity_display_name(self):
        """Test get_display_name without identity_display_name."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(identity_id=identity_id, field_id=field_id)
        display_name = identity.get_display_name()
        # Should use identity_id when no display name
        assert "Identity" in display_name or str(identity_id)[:8] in display_name

    def test_get_display_name_with_underscores(self):
        """Test get_display_name converts underscores to spaces."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(
            identity_id=identity_id,
            field_id=field_id,
            identity_display_name="COMPLEX_FIELD_NAME",
        )
        display_name = identity.get_display_name()
        assert display_name == "Complex Field Name"

    def test_get_display_name_with_numbers(self):
        """Test get_display_name with numbers."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(
            identity_id=identity_id,
            field_id=field_id,
            identity_display_name="FIELD_123_NAME",
        )
        display_name = identity.get_display_name()
        assert display_name == "Field 123 Name"


@pytest.mark.unit
class TestModelFieldIdentityMatchesName:
    """Tests for matches_name method."""

    def test_matches_name_identity_display_name_uppercase(self):
        """Test matches_name with identity_display_name in uppercase."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(
            identity_id=identity_id,
            field_id=field_id,
            identity_display_name="TEST_FIELD",
        )
        assert identity.matches_name("TEST_FIELD") is True
        assert identity.matches_name("test_field") is True
        assert identity.matches_name("Test_Field") is True

    def test_matches_name_field_display_name_lowercase(self):
        """Test matches_name with field_display_name in lowercase."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(
            identity_id=identity_id,
            field_id=field_id,
            identity_display_name="TEST_FIELD",
            field_display_name="test_field",
        )
        assert identity.matches_name("test_field") is True
        assert identity.matches_name("TEST_FIELD") is True

    def test_matches_name_no_match(self):
        """Test matches_name with non-matching name."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(
            identity_id=identity_id,
            field_id=field_id,
            identity_display_name="FIELD_ONE",
            field_display_name="field_one",
        )
        assert identity.matches_name("FIELD_TWO") is False
        assert identity.matches_name("other_field") is False

    def test_matches_name_without_display_names(self):
        """Test matches_name without display names."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(identity_id=identity_id, field_id=field_id)
        # Should use identity_id and field_id
        id_str = f"identity_{str(identity_id)[:8]}"
        field_str = f"field_{str(field_id)[:8]}"
        # The method generates names from IDs
        assert (
            identity.matches_name(id_str) is True
            or identity.matches_name(field_str) is True
        )


@pytest.mark.unit
class TestModelFieldIdentityProtocols:
    """Tests for ModelFieldIdentity protocol implementations."""

    def test_get_metadata(self):
        """Test get_metadata method."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(
            identity_id=identity_id,
            field_id=field_id,
            description="Test description",
        )
        metadata = identity.get_metadata()
        assert isinstance(metadata, dict)
        # Check that common metadata fields are included
        assert "description" in metadata

    def test_set_metadata(self):
        """Test set_metadata method."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(identity_id=identity_id, field_id=field_id)
        result = identity.set_metadata({"description": "New description"})
        assert result is True
        assert identity.description == "New description"

    def test_serialize(self):
        """Test serialize method."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(
            identity_id=identity_id,
            field_id=field_id,
            identity_display_name="TEST_FIELD",
        )
        data = identity.serialize()
        assert isinstance(data, dict)
        assert "identity_id" in data
        assert "field_id" in data

    def test_validate_instance(self):
        """Test validate_instance method."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(identity_id=identity_id, field_id=field_id)
        assert identity.validate_instance() is True


@pytest.mark.unit
class TestModelFieldIdentitySerialization:
    """Tests for ModelFieldIdentity serialization."""

    def test_model_dump(self):
        """Test model_dump method."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(
            identity_id=identity_id,
            field_id=field_id,
            identity_display_name="TEST_FIELD",
            field_display_name="test_field",
            description="Test field",
        )
        data = identity.model_dump()
        assert data["identity_id"] == identity_id
        assert data["field_id"] == field_id
        assert data["identity_display_name"] == "TEST_FIELD"
        assert data["field_display_name"] == "test_field"
        assert data["description"] == "Test field"

    def test_model_dump_exclude_none(self):
        """Test model_dump with exclude_none."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(identity_id=identity_id, field_id=field_id)
        data = identity.model_dump(exclude_none=True)
        assert "identity_display_name" not in data
        assert "field_display_name" not in data


@pytest.mark.unit
class TestModelFieldIdentityEdgeCases:
    """Tests for ModelFieldIdentity edge cases."""

    def test_empty_description(self):
        """Test field identity with empty description."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(
            identity_id=identity_id, field_id=field_id, description=""
        )
        assert identity.description == ""

    def test_long_description(self):
        """Test field identity with long description."""
        identity_id = uuid4()
        field_id = uuid4()
        long_desc = "A" * 1000
        identity = ModelFieldIdentity(
            identity_id=identity_id, field_id=field_id, description=long_desc
        )
        assert len(identity.description) == 1000

    def test_single_character_identity_display_name(self):
        """Test identity display name with single character."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(
            identity_id=identity_id, field_id=field_id, identity_display_name="X"
        )
        assert identity.identity_display_name == "X"

    def test_very_long_identity_display_name(self):
        """Test very long identity display name."""
        identity_id = uuid4()
        field_id = uuid4()
        long_name = "FIELD_" + "_".join(["NAME"] * 50)
        identity = ModelFieldIdentity(
            identity_id=identity_id, field_id=field_id, identity_display_name=long_name
        )
        assert identity.identity_display_name == long_name

    def test_multiple_underscores_in_display_name(self):
        """Test display name with multiple consecutive underscores."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(
            identity_id=identity_id,
            field_id=field_id,
            identity_display_name="FIELD___NAME",
        )
        display_name = identity.get_display_name()
        # Multiple underscores should create spaces
        assert "Field" in display_name and "Name" in display_name

    def test_special_uuid_values(self):
        """Test with specific UUID values."""
        # Using nil UUID
        from uuid import UUID

        nil_uuid = UUID("00000000-0000-0000-0000-000000000000")
        field_id = uuid4()
        identity = ModelFieldIdentity(identity_id=nil_uuid, field_id=field_id)
        assert identity.identity_id == nil_uuid

    def test_same_identity_and_field_id(self):
        """Test when identity_id and field_id are the same."""
        same_id = uuid4()
        identity = ModelFieldIdentity(identity_id=same_id, field_id=same_id)
        assert identity.identity_id == identity.field_id


@pytest.mark.unit
class TestModelFieldIdentityErrorBranches:
    """Tests for error handling branches in ModelFieldIdentity."""

    def test_get_metadata_with_none_values(self):
        """Test get_metadata when field values are None (line 91->88 branch)."""
        identity_id = uuid4()
        field_id = uuid4()
        # Create a model with optional fields as None
        identity = ModelFieldIdentity(
            identity_id=identity_id,
            field_id=field_id,
            identity_display_name=None,  # None value
            field_display_name=None,  # None value
        )
        metadata = identity.get_metadata()
        # Should not include None values in metadata
        assert (
            "identity_display_name" not in metadata
            or metadata.get("identity_display_name") is not None
        )
        assert isinstance(metadata, dict)

    def test_get_metadata_without_common_fields(self):
        """Test get_metadata when model doesn't have common fields."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(identity_id=identity_id, field_id=field_id)
        metadata = identity.get_metadata()
        # Should handle missing common fields gracefully
        assert isinstance(metadata, dict)
        # Only present fields should be included
        if "description" in metadata:
            assert metadata["description"] == ""

    def test_set_metadata_with_invalid_keys(self):
        """Test set_metadata with keys that don't exist (line 101->100 branch)."""
        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(identity_id=identity_id, field_id=field_id)
        # Try to set a field that doesn't exist
        result = identity.set_metadata(
            {
                "description": "Valid field",
                "non_existent_field": "Invalid field",  # Should be ignored
            }
        )
        assert result is True
        assert identity.description == "Valid field"
        # Non-existent field should not cause error, just be ignored

    def test_set_metadata_with_validation_error(self):
        """Test set_metadata exception handling (lines 104-105 branch)."""
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(identity_id=identity_id, field_id=field_id)

        # Try to set identity_display_name with invalid pattern (should fail validation)
        with pytest.raises(ModelOnexError) as exc_info:
            identity.set_metadata({"identity_display_name": "invalid_lowercase"})

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Operation failed" in str(exc_info.value.message)

    def test_set_metadata_with_type_error(self):
        """Test set_metadata with wrong type causing exception."""
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        identity_id = uuid4()
        field_id = uuid4()
        identity = ModelFieldIdentity(identity_id=identity_id, field_id=field_id)

        # Try to set field_id to an invalid type
        with pytest.raises(ModelOnexError) as exc_info:
            identity.set_metadata({"field_id": "not-a-uuid"})

        assert exc_info.value.error_code
        assert "Operation failed" in str(exc_info.value.message)
