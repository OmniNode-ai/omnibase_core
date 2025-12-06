"""Tests for ModelOnexWarning."""

from datetime import datetime
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.models.common.model_onex_warning import ModelOnexWarning


class TestModelOnexWarning:
    """Tests for ModelOnexWarning model."""

    def test_initialization_minimal(self):
        """Test warning initialization with minimal fields."""
        warning = ModelOnexWarning(message="Test warning")

        assert warning.message == "Test warning"
        assert warning.warning_code is None
        assert warning.status == EnumOnexStatus.WARNING
        assert warning.correlation_id is None
        assert isinstance(warning.timestamp, datetime)
        assert warning.context == {}

    def test_initialization_full(self):
        """Test warning initialization with all fields."""
        corr_id = uuid4()
        timestamp = datetime.now()
        context = {"file": "test.txt", "line": 42}

        warning = ModelOnexWarning(
            message="File overwrite warning",
            warning_code="ONEX_CORE_W001_FILE_OVERWRITE",
            status=EnumOnexStatus.WARNING,
            correlation_id=corr_id,
            timestamp=timestamp,
            context=context,
        )

        assert warning.message == "File overwrite warning"
        assert warning.warning_code == "ONEX_CORE_W001_FILE_OVERWRITE"
        assert warning.status == EnumOnexStatus.WARNING
        assert warning.correlation_id == corr_id
        assert warning.timestamp == timestamp
        assert warning.context == context

    def test_default_status_is_warning(self):
        """Test default status is WARNING."""
        warning = ModelOnexWarning(message="Test")
        assert warning.status == EnumOnexStatus.WARNING

    def test_timestamp_auto_generated(self):
        """Test timestamp is auto-generated if not provided."""
        warning = ModelOnexWarning(message="Test")

        # Just verify timestamp exists and is a datetime
        assert isinstance(warning.timestamp, datetime)
        assert warning.timestamp is not None

    def test_context_dictionary(self):
        """Test context dictionary handling."""
        context = {
            "file_path": "/path/to/file.py",
            "line_number": 123,
            "function": "test_function",
            "severity": "medium",
        }

        warning = ModelOnexWarning(message="Test", context=context)

        assert warning.context == context
        assert warning.context["file_path"] == "/path/to/file.py"
        assert warning.context["line_number"] == 123

    def test_warning_codes(self):
        """Test various warning codes."""
        codes = [
            "ONEX_CORE_W001_FILE_OVERWRITE",
            "ONEX_CORE_W002_DEPRECATED_API",
            "ONEX_CORE_W003_PERFORMANCE_CONCERN",
        ]

        for code in codes:
            warning = ModelOnexWarning(message="Test", warning_code=code)
            assert warning.warning_code == code

    def test_correlation_id_tracking(self):
        """Test correlation ID for request tracking."""
        corr_id = uuid4()
        warning = ModelOnexWarning(message="Test", correlation_id=corr_id)

        assert warning.correlation_id == corr_id

    def test_serialization_to_dict(self):
        """Test serialization to dictionary."""
        warning = ModelOnexWarning(
            message="Test warning",
            warning_code="W001",
            context={"key": "value"},
        )

        data = warning.model_dump()

        assert data["message"] == "Test warning"
        assert data["warning_code"] == "W001"
        assert data["status"] == "warning"
        assert "timestamp" in data
        assert data["context"] == {"key": "value"}

    def test_serialization_to_json(self):
        """Test serialization to JSON."""
        warning = ModelOnexWarning(
            message="JSON test",
            warning_code="W001",
        )

        json_str = warning.model_dump_json()

        assert isinstance(json_str, str)
        assert "JSON test" in json_str
        assert "W001" in json_str

    def test_deserialization_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "message": "Restored warning",
            "warning_code": "W002",
            "status": "warning",
            "context": {"restored": True},
        }

        warning = ModelOnexWarning(**data)

        assert warning.message == "Restored warning"
        assert warning.warning_code == "W002"
        assert warning.context == {"restored": True}

    def test_empty_context_default(self):
        """Test empty context is default."""
        warning = ModelOnexWarning(message="Test")

        assert warning.context == {}
        assert isinstance(warning.context, dict)

    def test_warning_with_complex_context(self):
        """Test warning with complex nested context."""
        context = {
            "operation": "file_write",
            "details": {
                "path": "/tmp/output.txt",
                "size_bytes": 1024,
                "permissions": "0644",
            },
            "alternatives": ["use_temp_dir", "request_permission"],
        }

        warning = ModelOnexWarning(message="Complex context test", context=context)

        assert warning.context["operation"] == "file_write"
        assert warning.context["details"]["size_bytes"] == 1024
        assert len(warning.context["alternatives"]) == 2

    def test_warning_message_required(self):
        """Test message is required field."""
        with pytest.raises(Exception):  # ValidationError
            ModelOnexWarning()  # type: ignore[call-arg]

    def test_multiple_warnings_independent(self):
        """Test multiple warnings are independent."""
        warning1 = ModelOnexWarning(message="Warning 1", context={"id": 1})
        warning2 = ModelOnexWarning(message="Warning 2", context={"id": 2})

        assert warning1.message != warning2.message
        assert warning1.context != warning2.context
        assert warning1.timestamp != warning2.timestamp

    def test_schema_example_structure(self):
        """Test schema example matches expected structure."""
        schema = ModelOnexWarning.model_json_schema()

        assert "example" in schema
        example = schema["example"]
        assert "message" in example
        assert "warning_code" in example
        assert "status" in example

    def test_file_overwrite_warning_pattern(self):
        """Test common file overwrite warning pattern."""
        warning = ModelOnexWarning(
            message="File already exists and will be overwritten: config.yaml",
            warning_code="ONEX_CORE_W001_FILE_OVERWRITE",
            correlation_id=uuid4(),
            context={"file_path": "/path/to/config.yaml", "backup_created": True},
        )

        assert "overwritten" in warning.message
        assert warning.warning_code == "ONEX_CORE_W001_FILE_OVERWRITE"
        assert warning.context["backup_created"] is True
