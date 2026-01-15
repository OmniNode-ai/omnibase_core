# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Comprehensive tests for ModelEffectInputData.

This module tests the ModelEffectInputData model, which provides typed context
for effect operation data including target systems, resource paths, and
operational characteristics.

Test Categories:
    - Instantiation tests: Create with various field combinations
    - Validation tests: Type checking, extra fields, constraints
    - Edge cases: Empty strings, None, unicode, boundary values
    - Immutability tests: Verify frozen behavior
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumEffectType
from omnibase_core.models.context.model_effect_input_data import ModelEffectInputData

# Test configuration constants
UNIT_TEST_TIMEOUT_SECONDS: int = 60


# =============================================================================
# INSTANTIATION TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(UNIT_TEST_TIMEOUT_SECONDS)
class TestModelEffectInputDataInstantiation:
    """Tests for creating ModelEffectInputData instances."""

    def test_create_with_required_field_only(self) -> None:
        """Create with only the required effect_type field."""
        model = ModelEffectInputData(effect_type=EnumEffectType.API_CALL)
        assert model.effect_type == EnumEffectType.API_CALL
        assert model.resource_path is None
        assert model.target_system is None
        assert model.idempotency_key is None
        assert model.operation_name is None
        assert model.resource_id is None
        assert model.content_type is None
        assert model.encoding is None

    def test_create_with_all_fields(self) -> None:
        """Create with all fields populated."""
        resource_uuid = uuid4()
        model = ModelEffectInputData(
            effect_type=EnumEffectType.DATABASE_OPERATION,
            resource_path="/data/users",
            target_system="postgres",
            idempotency_key="op-12345",
            operation_name="insert_user",
            resource_id=resource_uuid,
            content_type="application/json",
            encoding="utf-8",
        )
        assert model.effect_type == EnumEffectType.DATABASE_OPERATION
        assert model.resource_path == "/data/users"
        assert model.target_system == "postgres"
        assert model.idempotency_key == "op-12345"
        assert model.operation_name == "insert_user"
        assert model.resource_id == resource_uuid
        assert model.content_type == "application/json"
        assert model.encoding == "utf-8"

    def test_create_api_call_operation(self) -> None:
        """Create an API call effect operation."""
        model = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="https://api.example.com/users",
            target_system="user-service",
            operation_name="fetch_users",
            content_type="application/json",
        )
        assert model.effect_type == EnumEffectType.API_CALL
        assert model.resource_path == "https://api.example.com/users"
        assert model.target_system == "user-service"

    def test_create_file_operation(self) -> None:
        """Create a file operation effect."""
        model = ModelEffectInputData(
            effect_type=EnumEffectType.FILE_OPERATION,
            resource_path="/data/exports/report.json",
            target_system="local-fs",
            operation_name="write_report",
            content_type="application/json",
            encoding="utf-8",
        )
        assert model.effect_type == EnumEffectType.FILE_OPERATION
        assert model.resource_path == "/data/exports/report.json"
        assert model.encoding == "utf-8"

    def test_create_database_operation(self) -> None:
        """Create a database operation effect."""
        model = ModelEffectInputData(
            effect_type=EnumEffectType.DATABASE_OPERATION,
            resource_path="users",
            target_system="postgres",
            operation_name="select_active_users",
        )
        assert model.effect_type == EnumEffectType.DATABASE_OPERATION
        assert model.resource_path == "users"
        assert model.target_system == "postgres"

    def test_create_event_emission_operation(self) -> None:
        """Create an event emission effect."""
        model = ModelEffectInputData(
            effect_type=EnumEffectType.EVENT_EMISSION,
            resource_path="user.created",
            target_system="kafka",
            operation_name="emit_user_event",
            idempotency_key="event-abc123",
        )
        assert model.effect_type == EnumEffectType.EVENT_EMISSION
        assert model.idempotency_key == "event-abc123"

    def test_create_directory_operation(self) -> None:
        """Create a directory operation effect."""
        model = ModelEffectInputData(
            effect_type=EnumEffectType.DIRECTORY_OPERATION,
            resource_path="/data/exports",
            target_system="local-fs",
            operation_name="create_export_dir",
        )
        assert model.effect_type == EnumEffectType.DIRECTORY_OPERATION

    def test_create_ticket_storage_operation(self) -> None:
        """Create a ticket storage effect."""
        model = ModelEffectInputData(
            effect_type=EnumEffectType.TICKET_STORAGE,
            resource_path="tickets/PROJ-123",
            target_system="jira",
            operation_name="create_ticket",
        )
        assert model.effect_type == EnumEffectType.TICKET_STORAGE

    def test_create_metrics_collection_operation(self) -> None:
        """Create a metrics collection effect."""
        model = ModelEffectInputData(
            effect_type=EnumEffectType.METRICS_COLLECTION,
            resource_path="app.requests.count",
            target_system="prometheus",
            operation_name="increment_counter",
        )
        assert model.effect_type == EnumEffectType.METRICS_COLLECTION


# =============================================================================
# VALIDATION TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(UNIT_TEST_TIMEOUT_SECONDS)
class TestModelEffectInputDataValidation:
    """Tests for validation behavior of ModelEffectInputData."""

    def test_missing_required_field_raises_error(self) -> None:
        """Missing effect_type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectInputData()
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("effect_type",)
        assert errors[0]["type"] == "missing"

    def test_invalid_effect_type_rejected(self) -> None:
        """Invalid effect_type value raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectInputData(effect_type="invalid_type")
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("effect_type",)

    def test_invalid_resource_path_type_rejected(self) -> None:
        """Non-string resource_path raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectInputData(
                effect_type=EnumEffectType.API_CALL,
                resource_path=12345,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("resource_path",) for e in errors)

    def test_invalid_resource_id_type_rejected(self) -> None:
        """Non-UUID resource_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectInputData(
                effect_type=EnumEffectType.API_CALL,
                resource_id="not-a-uuid",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("resource_id",) for e in errors)

    def test_extra_field_rejected(self) -> None:
        """Extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectInputData(
                effect_type=EnumEffectType.API_CALL,
                unknown_field="value",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "extra_forbidden"

    def test_resource_path_max_length_enforced(self) -> None:
        """resource_path exceeding 4096 chars raises ValidationError."""
        long_path = "a" * 4097
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectInputData(
                effect_type=EnumEffectType.API_CALL,
                resource_path=long_path,
            )
        errors = exc_info.value.errors()
        assert any(
            e["loc"] == ("resource_path",) and "string_too_long" in e["type"]
            for e in errors
        )

    def test_target_system_max_length_enforced(self) -> None:
        """target_system exceeding 256 chars raises ValidationError."""
        long_system = "s" * 257
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectInputData(
                effect_type=EnumEffectType.API_CALL,
                target_system=long_system,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("target_system",) for e in errors)

    def test_idempotency_key_max_length_enforced(self) -> None:
        """idempotency_key exceeding 512 chars raises ValidationError."""
        long_key = "k" * 513
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectInputData(
                effect_type=EnumEffectType.API_CALL,
                idempotency_key=long_key,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("idempotency_key",) for e in errors)

    def test_operation_name_max_length_enforced(self) -> None:
        """operation_name exceeding 256 chars raises ValidationError."""
        long_name = "n" * 257
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectInputData(
                effect_type=EnumEffectType.API_CALL,
                operation_name=long_name,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("operation_name",) for e in errors)

    def test_content_type_max_length_enforced(self) -> None:
        """content_type exceeding 256 chars raises ValidationError."""
        long_type = "t" * 257
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectInputData(
                effect_type=EnumEffectType.API_CALL,
                content_type=long_type,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("content_type",) for e in errors)

    def test_encoding_max_length_enforced(self) -> None:
        """encoding exceeding 64 chars raises ValidationError."""
        long_encoding = "e" * 65
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectInputData(
                effect_type=EnumEffectType.API_CALL,
                encoding=long_encoding,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("encoding",) for e in errors)

    def test_all_enum_values_accepted(self) -> None:
        """All EnumEffectType values are accepted."""
        for effect_type in EnumEffectType:
            model = ModelEffectInputData(effect_type=effect_type)
            assert model.effect_type == effect_type


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(UNIT_TEST_TIMEOUT_SECONDS)
class TestModelEffectInputDataEdgeCases:
    """Tests for edge cases in ModelEffectInputData."""

    def test_empty_string_resource_path_allowed(self) -> None:
        """Empty string is allowed for resource_path."""
        model = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="",
        )
        assert model.resource_path == ""

    def test_empty_string_target_system_allowed(self) -> None:
        """Empty string is allowed for target_system."""
        model = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            target_system="",
        )
        assert model.target_system == ""

    def test_empty_string_operation_name_allowed(self) -> None:
        """Empty string is allowed for operation_name."""
        model = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            operation_name="",
        )
        assert model.operation_name == ""

    def test_none_values_for_optional_fields(self) -> None:
        """None values work for all optional fields."""
        model = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path=None,
            target_system=None,
            idempotency_key=None,
            operation_name=None,
            resource_id=None,
            content_type=None,
            encoding=None,
        )
        assert model.resource_path is None
        assert model.target_system is None
        assert model.idempotency_key is None
        assert model.operation_name is None
        assert model.resource_id is None
        assert model.content_type is None
        assert model.encoding is None

    def test_boundary_resource_path_at_max_length(self) -> None:
        """resource_path at exactly 4096 chars is accepted."""
        max_path = "p" * 4096
        model = ModelEffectInputData(
            effect_type=EnumEffectType.FILE_OPERATION,
            resource_path=max_path,
        )
        assert len(model.resource_path) == 4096

    def test_boundary_target_system_at_max_length(self) -> None:
        """target_system at exactly 256 chars is accepted."""
        max_system = "s" * 256
        model = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            target_system=max_system,
        )
        assert len(model.target_system) == 256

    def test_boundary_idempotency_key_at_max_length(self) -> None:
        """idempotency_key at exactly 512 chars is accepted."""
        max_key = "k" * 512
        model = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            idempotency_key=max_key,
        )
        assert len(model.idempotency_key) == 512

    def test_boundary_encoding_at_max_length(self) -> None:
        """encoding at exactly 64 chars is accepted."""
        max_encoding = "e" * 64
        model = ModelEffectInputData(
            effect_type=EnumEffectType.FILE_OPERATION,
            encoding=max_encoding,
        )
        assert len(model.encoding) == 64

    def test_unicode_resource_path(self) -> None:
        """Unicode characters in resource_path are accepted."""
        # Test with actual unicode: accented Latin characters (cafe, naive)
        unicode_path = "/data/users/caf\u00e9_na\u00efve/customers"
        model = ModelEffectInputData(
            effect_type=EnumEffectType.FILE_OPERATION,
            resource_path=unicode_path,
        )
        assert model.resource_path == unicode_path

    def test_unicode_resource_path_japanese(self) -> None:
        """Japanese unicode characters in resource_path are accepted."""
        # Japanese: nihongo (Japanese language)
        unicode_path = "/data/users/\u65e5\u672c\u8a9e/user_id"
        model = ModelEffectInputData(
            effect_type=EnumEffectType.FILE_OPERATION,
            resource_path=unicode_path,
        )
        assert model.resource_path == unicode_path

    def test_unicode_resource_path_chinese(self) -> None:
        """Chinese unicode characters in resource_path are accepted."""
        # Chinese: zhongwen (Chinese language)
        unicode_path = "/data/users/\u4e2d\u6587/files"
        model = ModelEffectInputData(
            effect_type=EnumEffectType.FILE_OPERATION,
            resource_path=unicode_path,
        )
        assert model.resource_path == unicode_path

    def test_unicode_resource_path_arabic(self) -> None:
        """Arabic unicode characters in resource_path are accepted."""
        # Arabic: al-arabiya (Arabic)
        unicode_path = "/data/users/\u0627\u0644\u0639\u0631\u0628\u064a\u0629/docs"
        model = ModelEffectInputData(
            effect_type=EnumEffectType.FILE_OPERATION,
            resource_path=unicode_path,
        )
        assert model.resource_path == unicode_path

    def test_unicode_resource_path_emoji(self) -> None:
        """Emoji unicode characters in resource_path are accepted."""
        # Rocket emoji
        unicode_path = "/data/users/\U0001f680/launch"
        model = ModelEffectInputData(
            effect_type=EnumEffectType.FILE_OPERATION,
            resource_path=unicode_path,
        )
        assert model.resource_path == unicode_path

    def test_unicode_operation_name(self) -> None:
        """Unicode characters in operation_name are accepted."""
        # Test with actual unicode: accented Latin characters (cafe)
        unicode_name = "create_user_caf\u00e9"
        model = ModelEffectInputData(
            effect_type=EnumEffectType.DATABASE_OPERATION,
            operation_name=unicode_name,
        )
        assert model.operation_name == unicode_name

    def test_unicode_operation_name_multilingual(self) -> None:
        """Multilingual unicode in operation_name is accepted."""
        # Japanese characters: data processing
        unicode_name = "\u30c7\u30fc\u30bf\u51e6\u7406"
        model = ModelEffectInputData(
            effect_type=EnumEffectType.DATABASE_OPERATION,
            operation_name=unicode_name,
        )
        assert model.operation_name == unicode_name

    def test_unicode_target_system(self) -> None:
        """Unicode characters in target_system are accepted."""
        # Chinese characters: system
        unicode_system = "\u7cfb\u7edf"
        model = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            target_system=unicode_system,
        )
        assert model.target_system == unicode_system

    def test_special_characters_in_resource_path(self) -> None:
        """Special characters in resource_path are accepted."""
        special_path = "/data/users?filter=active&sort=name#section"
        model = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path=special_path,
        )
        assert model.resource_path == special_path

    def test_whitespace_in_strings(self) -> None:
        """Whitespace in string fields is preserved."""
        model = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="  /path/with/spaces  ",
            target_system=" system ",
            operation_name="  operation  ",
        )
        assert model.resource_path == "  /path/with/spaces  "
        assert model.target_system == " system "
        assert model.operation_name == "  operation  "

    def test_valid_uuid_resource_id(self) -> None:
        """Valid UUID is accepted for resource_id."""
        test_uuid = UUID("12345678-1234-5678-1234-567812345678")
        model = ModelEffectInputData(
            effect_type=EnumEffectType.DATABASE_OPERATION,
            resource_id=test_uuid,
        )
        assert model.resource_id == test_uuid

    def test_uuid_string_coerced_to_uuid(self) -> None:
        """UUID string is coerced to UUID object."""
        uuid_str = "12345678-1234-5678-1234-567812345678"
        model = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_id=uuid_str,
        )
        assert isinstance(model.resource_id, UUID)
        assert str(model.resource_id) == uuid_str


# =============================================================================
# IMMUTABILITY TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(UNIT_TEST_TIMEOUT_SECONDS)
class TestModelEffectInputDataImmutability:
    """Tests for immutability (frozen=True) behavior."""

    def test_effect_type_cannot_be_modified(self) -> None:
        """effect_type cannot be changed after creation."""
        model = ModelEffectInputData(effect_type=EnumEffectType.API_CALL)
        with pytest.raises(ValidationError):
            model.effect_type = EnumEffectType.DATABASE_OPERATION

    def test_resource_path_cannot_be_modified(self) -> None:
        """resource_path cannot be changed after creation."""
        model = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="/original/path",
        )
        with pytest.raises(ValidationError):
            model.resource_path = "/new/path"

    def test_target_system_cannot_be_modified(self) -> None:
        """target_system cannot be changed after creation."""
        model = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            target_system="original-system",
        )
        with pytest.raises(ValidationError):
            model.target_system = "new-system"

    def test_resource_id_cannot_be_modified(self) -> None:
        """resource_id cannot be changed after creation."""
        original_uuid = uuid4()
        model = ModelEffectInputData(
            effect_type=EnumEffectType.DATABASE_OPERATION,
            resource_id=original_uuid,
        )
        with pytest.raises(ValidationError):
            model.resource_id = uuid4()


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(UNIT_TEST_TIMEOUT_SECONDS)
class TestModelEffectInputDataSerialization:
    """Tests for serialization/deserialization behavior."""

    def test_model_dump_includes_all_fields(self) -> None:
        """model_dump() includes all fields."""
        resource_uuid = uuid4()
        model = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="/api/users",
            target_system="user-service",
            idempotency_key="key-123",
            operation_name="get_users",
            resource_id=resource_uuid,
            content_type="application/json",
            encoding="utf-8",
        )
        data = model.model_dump()
        assert data["effect_type"] == EnumEffectType.API_CALL
        assert data["resource_path"] == "/api/users"
        assert data["target_system"] == "user-service"
        assert data["idempotency_key"] == "key-123"
        assert data["operation_name"] == "get_users"
        assert data["resource_id"] == resource_uuid
        assert data["content_type"] == "application/json"
        assert data["encoding"] == "utf-8"

    def test_model_dump_mode_json(self) -> None:
        """model_dump(mode='json') produces JSON-serializable output."""
        resource_uuid = uuid4()
        model = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_id=resource_uuid,
        )
        data = model.model_dump(mode="json")
        assert data["effect_type"] == "api_call"
        assert data["resource_id"] == str(resource_uuid)

    def test_model_validate_roundtrip(self) -> None:
        """Model can be recreated from model_dump() output."""
        original = ModelEffectInputData(
            effect_type=EnumEffectType.FILE_OPERATION,
            resource_path="/data/file.txt",
            target_system="s3",
            resource_id=uuid4(),
        )
        data = original.model_dump()
        recreated = ModelEffectInputData.model_validate(data)
        assert recreated.effect_type == original.effect_type
        assert recreated.resource_path == original.resource_path
        assert recreated.target_system == original.target_system
        assert recreated.resource_id == original.resource_id

    def test_from_attributes_enabled(self) -> None:
        """from_attributes=True allows creation from object attributes."""

        class MockObject:
            effect_type = EnumEffectType.API_CALL
            resource_path = "/api/test"
            target_system = "test-system"
            idempotency_key = None
            operation_name = None
            resource_id = None
            content_type = None
            encoding = None

        mock = MockObject()
        model = ModelEffectInputData.model_validate(mock)
        assert model.effect_type == EnumEffectType.API_CALL
        assert model.resource_path == "/api/test"
        assert model.target_system == "test-system"


# =============================================================================
# HASH AND EQUALITY TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.timeout(UNIT_TEST_TIMEOUT_SECONDS)
class TestModelEffectInputDataHashEquality:
    """Tests for hash and equality behavior."""

    def test_equal_models_are_equal(self) -> None:
        """Two models with same values are equal."""
        resource_uuid = uuid4()
        model1 = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="/api/test",
            resource_id=resource_uuid,
        )
        model2 = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="/api/test",
            resource_id=resource_uuid,
        )
        assert model1 == model2

    def test_different_models_are_not_equal(self) -> None:
        """Two models with different values are not equal."""
        model1 = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="/api/test1",
        )
        model2 = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="/api/test2",
        )
        assert model1 != model2

    def test_frozen_model_is_hashable(self) -> None:
        """Frozen model is hashable."""
        model = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="/api/test",
        )
        # Should not raise
        hash_value = hash(model)
        assert isinstance(hash_value, int)

    def test_equal_models_have_same_hash(self) -> None:
        """Equal models have the same hash."""
        resource_uuid = uuid4()
        model1 = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="/api/test",
            resource_id=resource_uuid,
        )
        model2 = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="/api/test",
            resource_id=resource_uuid,
        )
        assert hash(model1) == hash(model2)

    def test_model_can_be_used_in_set(self) -> None:
        """Model can be used as set element."""
        model1 = ModelEffectInputData(effect_type=EnumEffectType.API_CALL)
        model2 = ModelEffectInputData(effect_type=EnumEffectType.DATABASE_OPERATION)
        model_set = {model1, model2}
        assert len(model_set) == 2

    def test_model_can_be_used_as_dict_key(self) -> None:
        """Model can be used as dictionary key."""
        model = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            operation_name="test_op",
        )
        test_dict = {model: "value"}
        assert test_dict[model] == "value"
