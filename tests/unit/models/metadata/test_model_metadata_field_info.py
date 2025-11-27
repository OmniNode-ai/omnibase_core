"""Tests for ModelMetadataFieldInfo."""

from uuid import uuid4

from omnibase_core.enums.enum_field_type import EnumFieldType
from omnibase_core.models.infrastructure.model_value import ModelValue
from omnibase_core.models.metadata.model_field_identity import ModelFieldIdentity
from omnibase_core.models.metadata.model_field_validation_rules import (
    ModelFieldValidationRules,
)
from omnibase_core.models.metadata.model_metadata_field_info import (
    ModelMetadataFieldInfo,
)


class TestModelMetadataFieldInfoInstantiation:
    """Tests for ModelMetadataFieldInfo instantiation."""

    def test_create_with_required_fields(self):
        """Test creating field info with required fields."""
        identity = ModelFieldIdentity(identity_id=uuid4(), field_id=uuid4())
        field_info = ModelMetadataFieldInfo(
            identity=identity,
            is_required=True,
            is_optional=False,
            is_volatile=False,
        )
        assert field_info.identity == identity
        assert field_info.is_required is True
        assert field_info.is_optional is False
        assert field_info.is_volatile is False

    def test_create_with_field_type(self):
        """Test creating field info with specific field type."""
        identity = ModelFieldIdentity(identity_id=uuid4(), field_id=uuid4())
        field_info = ModelMetadataFieldInfo(
            identity=identity,
            is_required=True,
            is_optional=False,
            is_volatile=False,
            field_type=EnumFieldType.INTEGER,
        )
        assert field_info.field_type == EnumFieldType.INTEGER

    def test_create_with_default_value(self):
        """Test creating field info with default value."""
        identity = ModelFieldIdentity(identity_id=uuid4(), field_id=uuid4())
        default_val = ModelValue.from_string("default")
        field_info = ModelMetadataFieldInfo(
            identity=identity,
            is_required=False,
            is_optional=True,
            is_volatile=False,
            default_value=default_val,
        )
        assert field_info.default_value == default_val

    def test_create_with_validation_rules(self):
        """Test creating field info with validation rules."""
        identity = ModelFieldIdentity(identity_id=uuid4(), field_id=uuid4())
        validation = ModelFieldValidationRules(min_length=5, max_length=10)
        field_info = ModelMetadataFieldInfo(
            identity=identity,
            is_required=True,
            is_optional=False,
            is_volatile=False,
            validation=validation,
        )
        assert field_info.validation == validation


class TestModelMetadataFieldInfoFactoryMetadataVersion:
    """Tests for metadata_version factory method."""

    def test_metadata_version_factory(self):
        """Test metadata_version factory method."""
        field_info = ModelMetadataFieldInfo.metadata_version()
        assert field_info.identity.identity_display_name == "METADATA_VERSION"
        assert field_info.identity.field_display_name == "metadata_version"
        assert field_info.is_required is False
        assert field_info.is_optional is True
        assert field_info.is_volatile is False
        assert field_info.field_type == EnumFieldType.STRING
        assert field_info.default_value is not None

    def test_metadata_version_default_value(self):
        """Test metadata_version has correct default value."""
        field_info = ModelMetadataFieldInfo.metadata_version()
        assert field_info.default_value is not None


class TestModelMetadataFieldInfoFactoryProtocolVersion:
    """Tests for protocol_version factory method."""

    def test_protocol_version_factory(self):
        """Test protocol_version factory method."""
        field_info = ModelMetadataFieldInfo.protocol_version()
        assert field_info.identity.identity_display_name == "PROTOCOL_VERSION"
        assert field_info.identity.field_display_name == "protocol_version"
        assert field_info.is_required is False
        assert field_info.is_optional is True
        assert field_info.is_volatile is False
        assert field_info.field_type == EnumFieldType.STRING

    def test_protocol_version_default_value(self):
        """Test protocol_version has correct default value."""
        field_info = ModelMetadataFieldInfo.protocol_version()
        assert field_info.default_value is not None


class TestModelMetadataFieldInfoFactoryName:
    """Tests for name_field factory method."""

    def test_name_field_factory(self):
        """Test name_field factory method."""
        field_info = ModelMetadataFieldInfo.name_field()
        assert field_info.identity.identity_display_name == "NAME"
        assert field_info.identity.field_display_name == "name"
        assert field_info.is_required is True
        assert field_info.is_optional is False
        assert field_info.is_volatile is False
        assert field_info.field_type == EnumFieldType.STRING

    def test_name_field_no_default(self):
        """Test name_field has no default value."""
        field_info = ModelMetadataFieldInfo.name_field()
        assert field_info.default_value is None


class TestModelMetadataFieldInfoFactoryVersion:
    """Tests for version factory method."""

    def test_version_factory(self):
        """Test version factory method."""
        field_info = ModelMetadataFieldInfo.version()
        assert field_info.identity.identity_display_name == "VERSION"
        assert field_info.identity.field_display_name == "version"
        assert field_info.is_required is False
        assert field_info.is_optional is True
        assert field_info.is_volatile is False
        assert field_info.field_type == EnumFieldType.STRING

    def test_version_default_value(self):
        """Test version has correct default value."""
        field_info = ModelMetadataFieldInfo.version()
        assert field_info.default_value is not None


class TestModelMetadataFieldInfoFactoryUUID:
    """Tests for uuid factory method."""

    def test_uuid_factory(self):
        """Test uuid factory method."""
        field_info = ModelMetadataFieldInfo.uuid()
        assert field_info.identity.identity_display_name == "UUID"
        assert field_info.identity.field_display_name == "uuid"
        assert field_info.is_required is True
        assert field_info.is_optional is False
        assert field_info.is_volatile is False
        assert field_info.field_type == EnumFieldType.UUID

    def test_uuid_validation_pattern(self):
        """Test uuid has validation pattern."""
        field_info = ModelMetadataFieldInfo.uuid()
        assert field_info.validation.validation_pattern is not None
        assert "0-9a-f" in field_info.validation.validation_pattern


class TestModelMetadataFieldInfoFactoryAuthor:
    """Tests for author factory method."""

    def test_author_factory(self):
        """Test author factory method."""
        field_info = ModelMetadataFieldInfo.author()
        assert field_info.identity.identity_display_name == "AUTHOR"
        assert field_info.identity.field_display_name == "author"
        assert field_info.is_required is True
        assert field_info.is_optional is False
        assert field_info.is_volatile is False
        assert field_info.field_type == EnumFieldType.STRING


class TestModelMetadataFieldInfoFactoryCreatedAt:
    """Tests for created_at factory method."""

    def test_created_at_factory(self):
        """Test created_at factory method."""
        field_info = ModelMetadataFieldInfo.created_at()
        assert field_info.identity.identity_display_name == "CREATED_AT"
        assert field_info.identity.field_display_name == "created_at"
        assert field_info.is_required is True
        assert field_info.is_optional is False
        assert field_info.is_volatile is False
        assert field_info.field_type == EnumFieldType.DATETIME


class TestModelMetadataFieldInfoFactoryLastModifiedAt:
    """Tests for last_modified_at factory method."""

    def test_last_modified_at_factory(self):
        """Test last_modified_at factory method."""
        field_info = ModelMetadataFieldInfo.last_modified_at()
        assert field_info.identity.identity_display_name == "LAST_MODIFIED_AT"
        assert field_info.identity.field_display_name == "last_modified_at"
        assert field_info.is_required is True
        assert field_info.is_optional is False
        assert field_info.is_volatile is True  # Volatile field
        assert field_info.field_type == EnumFieldType.DATETIME


class TestModelMetadataFieldInfoFactoryHash:
    """Tests for hash factory method."""

    def test_hash_factory(self):
        """Test hash factory method."""
        field_info = ModelMetadataFieldInfo.hash()
        assert field_info.identity.identity_display_name == "HASH"
        assert field_info.identity.field_display_name == "hash"
        assert field_info.is_required is True
        assert field_info.is_optional is False
        assert field_info.is_volatile is True  # Volatile field
        assert field_info.field_type == EnumFieldType.STRING

    def test_hash_validation_pattern(self):
        """Test hash has validation pattern for 64 hex chars."""
        field_info = ModelMetadataFieldInfo.hash()
        assert field_info.validation.validation_pattern is not None
        assert "64" in field_info.validation.validation_pattern


class TestModelMetadataFieldInfoFactoryEntrypoint:
    """Tests for entrypoint factory method."""

    def test_entrypoint_factory(self):
        """Test entrypoint factory method."""
        field_info = ModelMetadataFieldInfo.entrypoint()
        assert field_info.identity.identity_display_name == "ENTRYPOINT"
        assert field_info.identity.field_display_name == "entrypoint"
        assert field_info.is_required is True
        assert field_info.is_optional is False
        assert field_info.is_volatile is False
        assert field_info.field_type == EnumFieldType.STRING


class TestModelMetadataFieldInfoFactoryNamespace:
    """Tests for namespace factory method."""

    def test_namespace_factory(self):
        """Test namespace factory method."""
        field_info = ModelMetadataFieldInfo.namespace()
        assert field_info.identity.identity_display_name == "NAMESPACE"
        assert field_info.identity.field_display_name == "namespace"
        assert field_info.is_required is True
        assert field_info.is_optional is False
        assert field_info.is_volatile is False
        assert field_info.field_type == EnumFieldType.STRING


class TestModelMetadataFieldInfoGetAllFields:
    """Tests for get_all_fields method."""

    def test_get_all_fields_returns_list(self):
        """Test get_all_fields returns list."""
        all_fields = ModelMetadataFieldInfo.get_all_fields()
        assert isinstance(all_fields, list)
        assert len(all_fields) > 0

    def test_get_all_fields_contains_standard_fields(self):
        """Test get_all_fields contains standard fields."""
        all_fields = ModelMetadataFieldInfo.get_all_fields()
        field_names = [f.identity.identity_display_name for f in all_fields]
        assert "METADATA_VERSION" in field_names
        assert "NAME" in field_names
        assert "VERSION" in field_names
        assert "UUID" in field_names

    def test_get_all_fields_returns_field_info_objects(self):
        """Test get_all_fields returns ModelMetadataFieldInfo objects."""
        all_fields = ModelMetadataFieldInfo.get_all_fields()
        for field in all_fields:
            assert isinstance(field, ModelMetadataFieldInfo)


class TestModelMetadataFieldInfoGetRequiredFields:
    """Tests for get_required_fields method."""

    def test_get_required_fields_returns_list(self):
        """Test get_required_fields returns list."""
        required_fields = ModelMetadataFieldInfo.get_required_fields()
        assert isinstance(required_fields, list)

    def test_get_required_fields_only_required(self):
        """Test get_required_fields only returns required fields."""
        required_fields = ModelMetadataFieldInfo.get_required_fields()
        for field in required_fields:
            assert field.is_required is True

    def test_get_required_fields_includes_name(self):
        """Test get_required_fields includes name field."""
        required_fields = ModelMetadataFieldInfo.get_required_fields()
        field_names = [f.identity.identity_display_name for f in required_fields]
        assert "NAME" in field_names

    def test_get_required_fields_excludes_optional(self):
        """Test get_required_fields excludes optional fields."""
        required_fields = ModelMetadataFieldInfo.get_required_fields()
        field_names = [f.identity.identity_display_name for f in required_fields]
        # METADATA_VERSION is optional
        assert "METADATA_VERSION" not in field_names


class TestModelMetadataFieldInfoGetOptionalFields:
    """Tests for get_optional_fields method."""

    def test_get_optional_fields_returns_list(self):
        """Test get_optional_fields returns list."""
        optional_fields = ModelMetadataFieldInfo.get_optional_fields()
        assert isinstance(optional_fields, list)

    def test_get_optional_fields_only_optional(self):
        """Test get_optional_fields only returns optional fields."""
        optional_fields = ModelMetadataFieldInfo.get_optional_fields()
        for field in optional_fields:
            assert field.is_optional is True

    def test_get_optional_fields_includes_metadata_version(self):
        """Test get_optional_fields includes metadata_version."""
        optional_fields = ModelMetadataFieldInfo.get_optional_fields()
        field_names = [f.identity.identity_display_name for f in optional_fields]
        assert "METADATA_VERSION" in field_names


class TestModelMetadataFieldInfoGetVolatileFields:
    """Tests for get_volatile_fields method."""

    def test_get_volatile_fields_returns_list(self):
        """Test get_volatile_fields returns list."""
        volatile_fields = ModelMetadataFieldInfo.get_volatile_fields()
        assert isinstance(volatile_fields, list)

    def test_get_volatile_fields_only_volatile(self):
        """Test get_volatile_fields only returns volatile fields."""
        volatile_fields = ModelMetadataFieldInfo.get_volatile_fields()
        for field in volatile_fields:
            assert field.is_volatile is True

    def test_get_volatile_fields_includes_hash(self):
        """Test get_volatile_fields includes hash field."""
        volatile_fields = ModelMetadataFieldInfo.get_volatile_fields()
        field_names = [f.identity.identity_display_name for f in volatile_fields]
        assert "HASH" in field_names

    def test_get_volatile_fields_includes_last_modified_at(self):
        """Test get_volatile_fields includes last_modified_at."""
        volatile_fields = ModelMetadataFieldInfo.get_volatile_fields()
        field_names = [f.identity.identity_display_name for f in volatile_fields]
        assert "LAST_MODIFIED_AT" in field_names


class TestModelMetadataFieldInfoFromString:
    """Tests for from_string method."""

    def test_from_string_metadata_version(self):
        """Test from_string with METADATA_VERSION."""
        field_info = ModelMetadataFieldInfo.from_string("METADATA_VERSION")
        assert field_info.identity.identity_display_name == "METADATA_VERSION"

    def test_from_string_name(self):
        """Test from_string with NAME."""
        field_info = ModelMetadataFieldInfo.from_string("NAME")
        assert field_info.identity.identity_display_name == "NAME"

    def test_from_string_lowercase(self):
        """Test from_string with lowercase input."""
        field_info = ModelMetadataFieldInfo.from_string("name")
        assert field_info.identity.identity_display_name == "NAME"

    def test_from_string_unknown_field(self):
        """Test from_string with unknown field creates generic."""
        field_info = ModelMetadataFieldInfo.from_string("UNKNOWN_FIELD")
        assert field_info.identity.identity_display_name == "UNKNOWN_FIELD"
        assert field_info.is_optional is True
        assert field_info.field_type == EnumFieldType.STRING

    def test_from_string_all_standard_fields(self):
        """Test from_string works for all standard fields."""
        standard_fields = [
            "METADATA_VERSION",
            "PROTOCOL_VERSION",
            "NAME",
            "VERSION",
            "UUID",
            "AUTHOR",
            "CREATED_AT",
            "LAST_MODIFIED_AT",
            "HASH",
            "ENTRYPOINT",
            "NAMESPACE",
        ]
        for field_name in standard_fields:
            field_info = ModelMetadataFieldInfo.from_string(field_name)
            assert field_info.identity.identity_display_name == field_name


class TestModelMetadataFieldInfoStringRepresentation:
    """Tests for __str__ method."""

    def test_str_with_field_display_name(self):
        """Test __str__ uses field_display_name."""
        field_info = ModelMetadataFieldInfo.name_field()
        assert str(field_info) == "name"

    def test_str_with_version_field(self):
        """Test __str__ with version field."""
        field_info = ModelMetadataFieldInfo.version()
        assert str(field_info) == "version"

    def test_str_with_uuid_field(self):
        """Test __str__ with uuid field."""
        field_info = ModelMetadataFieldInfo.uuid()
        assert str(field_info) == "uuid"


class TestModelMetadataFieldInfoEquality:
    """Tests for __eq__ method."""

    def test_eq_with_string_field_display_name(self):
        """Test __eq__ with field_display_name string."""
        field_info = ModelMetadataFieldInfo.name_field()
        assert field_info == "name"

    def test_eq_with_string_identity_display_name(self):
        """Test __eq__ with identity_display_name string."""
        field_info = ModelMetadataFieldInfo.name_field()
        assert field_info == "NAME"

    def test_eq_with_another_field_info_same(self):
        """Test __eq__ with another ModelMetadataFieldInfo (same)."""
        field1 = ModelMetadataFieldInfo.name_field()
        field2 = ModelMetadataFieldInfo.name_field()
        assert field1 == field2

    def test_eq_with_another_field_info_different(self):
        """Test __eq__ with another ModelMetadataFieldInfo (different)."""
        field1 = ModelMetadataFieldInfo.name_field()
        field2 = ModelMetadataFieldInfo.version()
        assert field1 != field2

    def test_eq_with_non_string_non_field_info(self):
        """Test __eq__ with other types."""
        field_info = ModelMetadataFieldInfo.name_field()
        assert field_info != 123
        assert field_info != []


class TestModelMetadataFieldInfoProtocols:
    """Tests for protocol implementations."""

    def test_get_metadata(self):
        """Test get_metadata method."""
        field_info = ModelMetadataFieldInfo.name_field()
        metadata = field_info.get_metadata()
        assert isinstance(metadata, dict)

    def test_set_metadata(self):
        """Test set_metadata method."""
        identity = ModelFieldIdentity(identity_id=uuid4(), field_id=uuid4())
        field_info = ModelMetadataFieldInfo(
            identity=identity,
            is_required=True,
            is_optional=False,
            is_volatile=False,
        )
        result = field_info.set_metadata({})
        assert result is True

    def test_serialize(self):
        """Test serialize method."""
        field_info = ModelMetadataFieldInfo.name_field()
        data = field_info.serialize()
        assert isinstance(data, dict)
        assert "identity" in data
        assert "is_required" in data

    def test_validate_instance(self):
        """Test validate_instance method."""
        field_info = ModelMetadataFieldInfo.name_field()
        assert field_info.validate_instance() is True


class TestModelMetadataFieldInfoEdgeCases:
    """Tests for edge cases."""

    def test_field_with_all_flags_false(self):
        """Test field with all boolean flags False."""
        identity = ModelFieldIdentity(identity_id=uuid4(), field_id=uuid4())
        field_info = ModelMetadataFieldInfo(
            identity=identity,
            is_required=False,
            is_optional=False,
            is_volatile=False,
        )
        assert field_info.is_required is False
        assert field_info.is_optional is False
        assert field_info.is_volatile is False

    def test_field_with_all_flags_true(self):
        """Test field with all boolean flags True."""
        identity = ModelFieldIdentity(identity_id=uuid4(), field_id=uuid4())
        field_info = ModelMetadataFieldInfo(
            identity=identity,
            is_required=True,
            is_optional=True,
            is_volatile=True,
        )
        assert field_info.is_required is True
        assert field_info.is_optional is True
        assert field_info.is_volatile is True

    def test_field_type_variations(self):
        """Test different field types."""
        identity = ModelFieldIdentity(identity_id=uuid4(), field_id=uuid4())
        field_types = [
            EnumFieldType.STRING,
            EnumFieldType.INTEGER,
            EnumFieldType.FLOAT,
            EnumFieldType.BOOLEAN,
            EnumFieldType.UUID,
            EnumFieldType.DATETIME,
        ]
        for field_type in field_types:
            field_info = ModelMetadataFieldInfo(
                identity=identity,
                is_required=True,
                is_optional=False,
                is_volatile=False,
                field_type=field_type,
            )
            assert field_info.field_type == field_type


class TestModelMetadataFieldInfoSerialization:
    """Tests for serialization."""

    def test_model_dump_with_all_fields(self):
        """Test model_dump with all fields populated."""
        identity = ModelFieldIdentity(
            identity_id=uuid4(),
            field_id=uuid4(),
            identity_display_name="TEST",
            field_display_name="test",
        )
        validation = ModelFieldValidationRules(min_length=5)
        default_val = ModelValue.from_string("default")
        field_info = ModelMetadataFieldInfo(
            identity=identity,
            is_required=True,
            is_optional=False,
            is_volatile=False,
            field_type=EnumFieldType.STRING,
            default_value=default_val,
            validation=validation,
        )
        data = field_info.model_dump()
        assert data["is_required"] is True
        assert data["is_optional"] is False
        assert data["is_volatile"] is False

    def test_model_dump_exclude_none(self):
        """Test model_dump with exclude_none."""
        identity = ModelFieldIdentity(identity_id=uuid4(), field_id=uuid4())
        field_info = ModelMetadataFieldInfo(
            identity=identity,
            is_required=True,
            is_optional=False,
            is_volatile=False,
        )
        data = field_info.model_dump(exclude_none=True)
        assert "default_value" not in data
