"""
Comprehensive tests for ModelCliOutputData.

Tests cover:
- Field initialization and defaults
- Data management methods (add_result, add_metadata, add_file_created, add_file_modified)
- Value access methods (get_field_value, set_field_value)
- Factory methods (create_simple, create_with_results)
- Protocol implementations (serialize, get_name, set_name, validate_instance)
- Edge cases and error scenarios
"""

import pytest

from omnibase_core.enums.enum_cli_status import EnumCliStatus
from omnibase_core.enums.enum_output_format import EnumOutputFormat
from omnibase_core.enums.enum_output_type import EnumOutputType
from omnibase_core.models.cli.model_cli_output_data import ModelCliOutputData


@pytest.mark.unit
class TestModelCliOutputDataInitialization:
    """Test initialization and default values."""

    def test_initialization_with_defaults(self):
        """Test creating output data with default values."""
        data = ModelCliOutputData()

        assert data.output_type == EnumOutputType.CONSOLE
        assert data.format == EnumOutputFormat.JSON
        assert data.stdout == ""
        assert data.stderr == ""
        assert data.results == {}
        assert data.metadata == {}
        assert data.status == EnumCliStatus.SUCCESS
        assert data.is_valid is True
        assert data.execution_time_ms == 0.0
        assert data.memory_usage_mb == 0.0
        assert data.files_created == []
        assert data.files_modified == []

    def test_initialization_with_custom_values(self):
        """Test creating output data with custom values."""
        data = ModelCliOutputData(
            output_type=EnumOutputType.FILE,
            format=EnumOutputFormat.TEXT,
            stdout="Test output",
            stderr="Test error",
            status=EnumCliStatus.FAILED,
            is_valid=False,
            execution_time_ms=150.5,
            memory_usage_mb=25.3,
        )

        assert data.output_type == EnumOutputType.FILE
        assert data.format == EnumOutputFormat.TEXT
        assert data.stdout == "Test output"
        assert data.stderr == "Test error"
        assert data.status == EnumCliStatus.FAILED
        assert data.is_valid is False
        assert data.execution_time_ms == 150.5
        assert data.memory_usage_mb == 25.3


@pytest.mark.unit
class TestModelCliOutputDataResultsMethods:
    """Test methods for managing results."""

    def test_add_result_single(self):
        """Test adding a single result."""
        data = ModelCliOutputData()
        data.add_result("key1", "value1")

        assert "key1" in data.results
        assert str(data.results["key1"].to_python_value()) == "value1"

    def test_add_result_multiple(self):
        """Test adding multiple results."""
        data = ModelCliOutputData()
        data.add_result("key1", "value1")
        data.add_result("key2", "value2")
        data.add_result("key3", "value3")

        assert len(data.results) == 3
        assert "key1" in data.results
        assert "key2" in data.results
        assert "key3" in data.results

    def test_add_result_overwrite(self):
        """Test that adding result with same key overwrites."""
        data = ModelCliOutputData()
        data.add_result("key1", "value1")
        data.add_result("key1", "value2")

        assert len(data.results) == 1
        assert str(data.results["key1"].to_python_value()) == "value2"

    def test_add_metadata_single(self):
        """Test adding a single metadata entry."""
        data = ModelCliOutputData()
        data.add_metadata("meta_key", "meta_value")

        assert "meta_key" in data.metadata
        assert str(data.metadata["meta_key"].to_python_value()) == "meta_value"

    def test_add_metadata_multiple(self):
        """Test adding multiple metadata entries."""
        data = ModelCliOutputData()
        data.add_metadata("meta1", "value1")
        data.add_metadata("meta2", "value2")

        assert len(data.metadata) == 2
        assert "meta1" in data.metadata
        assert "meta2" in data.metadata

    def test_add_result_empty_string(self):
        """Test adding result with empty string value."""
        data = ModelCliOutputData()
        data.add_result("empty_key", "")

        assert "empty_key" in data.results
        assert str(data.results["empty_key"].to_python_value()) == ""

    def test_add_metadata_empty_string(self):
        """Test adding metadata with empty string value."""
        data = ModelCliOutputData()
        data.add_metadata("empty_meta", "")

        assert "empty_meta" in data.metadata
        assert str(data.metadata["empty_meta"].to_python_value()) == ""


@pytest.mark.unit
class TestModelCliOutputDataFilesMethods:
    """Test methods for managing file operations."""

    def test_add_file_created_single(self):
        """Test adding a single created file."""
        data = ModelCliOutputData()
        data.add_file_created("/path/to/file.txt")

        assert len(data.files_created) == 1
        assert "/path/to/file.txt" in data.files_created

    def test_add_file_created_multiple(self):
        """Test adding multiple created files."""
        data = ModelCliOutputData()
        data.add_file_created("/path/to/file1.txt")
        data.add_file_created("/path/to/file2.txt")
        data.add_file_created("/path/to/file3.txt")

        assert len(data.files_created) == 3
        assert "/path/to/file1.txt" in data.files_created
        assert "/path/to/file2.txt" in data.files_created
        assert "/path/to/file3.txt" in data.files_created

    def test_add_file_created_duplicate(self):
        """Test that duplicate file paths are not added."""
        data = ModelCliOutputData()
        data.add_file_created("/path/to/file.txt")
        data.add_file_created("/path/to/file.txt")

        assert len(data.files_created) == 1

    def test_add_file_modified_single(self):
        """Test adding a single modified file."""
        data = ModelCliOutputData()
        data.add_file_modified("/path/to/modified.txt")

        assert len(data.files_modified) == 1
        assert "/path/to/modified.txt" in data.files_modified

    def test_add_file_modified_multiple(self):
        """Test adding multiple modified files."""
        data = ModelCliOutputData()
        data.add_file_modified("/path/to/modified1.txt")
        data.add_file_modified("/path/to/modified2.txt")

        assert len(data.files_modified) == 2

    def test_add_file_modified_duplicate(self):
        """Test that duplicate modified file paths are not added."""
        data = ModelCliOutputData()
        data.add_file_modified("/path/to/modified.txt")
        data.add_file_modified("/path/to/modified.txt")

        assert len(data.files_modified) == 1

    def test_mixed_files_operations(self):
        """Test mixing created and modified file operations."""
        data = ModelCliOutputData()
        data.add_file_created("/path/to/new.txt")
        data.add_file_modified("/path/to/existing.txt")
        data.add_file_created("/path/to/another.txt")
        data.add_file_modified("/path/to/existing.txt")  # Duplicate

        assert len(data.files_created) == 2
        assert len(data.files_modified) == 1


@pytest.mark.unit
class TestModelCliOutputDataValueAccessors:
    """Test value access methods."""

    def test_get_field_value_from_results(self):
        """Test getting field value from results."""
        data = ModelCliOutputData()
        data.add_result("test_key", "test_value")

        value = data.get_field_value("test_key")
        assert value == "test_value"

    def test_get_field_value_from_metadata(self):
        """Test getting field value from metadata."""
        data = ModelCliOutputData()
        data.add_metadata("meta_key", "meta_value")

        value = data.get_field_value("meta_key")
        assert value == "meta_value"

    def test_get_field_value_prioritizes_results(self):
        """Test that results are prioritized over metadata."""
        data = ModelCliOutputData()
        data.add_result("shared_key", "result_value")
        data.add_metadata("shared_key", "meta_value")

        value = data.get_field_value("shared_key")
        assert value == "result_value"

    def test_get_field_value_with_default(self):
        """Test getting field value with default for missing key."""
        data = ModelCliOutputData()

        value = data.get_field_value("nonexistent_key", "default_value")
        assert value == "default_value"

    def test_get_field_value_default_empty_string(self):
        """Test getting field value returns empty string by default."""
        data = ModelCliOutputData()

        value = data.get_field_value("nonexistent_key")
        assert value == ""

    def test_set_field_value(self):
        """Test setting field value in results."""
        data = ModelCliOutputData()
        data.set_field_value("new_key", "new_value")

        assert "new_key" in data.results
        value = data.get_field_value("new_key")
        assert value == "new_value"

    def test_set_field_value_overwrites(self):
        """Test that set_field_value overwrites existing values."""
        data = ModelCliOutputData()
        data.set_field_value("key1", "value1")
        data.set_field_value("key1", "value2")

        value = data.get_field_value("key1")
        assert value == "value2"


@pytest.mark.unit
class TestModelCliOutputDataFactoryMethods:
    """Test factory methods."""

    def test_create_simple_minimal(self):
        """Test creating simple output data with minimal parameters."""
        data = ModelCliOutputData.create_simple()

        assert data.stdout == ""
        assert data.stderr == ""
        assert data.status == EnumCliStatus.SUCCESS

    def test_create_simple_with_stdout(self):
        """Test creating simple output data with stdout."""
        data = ModelCliOutputData.create_simple(stdout="Test output")

        assert data.stdout == "Test output"
        assert data.stderr == ""
        assert data.status == EnumCliStatus.SUCCESS

    def test_create_simple_with_stderr(self):
        """Test creating simple output data with stderr."""
        data = ModelCliOutputData.create_simple(stderr="Error output")

        assert data.stdout == ""
        assert data.stderr == "Error output"
        assert data.status == EnumCliStatus.SUCCESS

    def test_create_simple_with_error_status(self):
        """Test creating simple output data with error status."""
        data = ModelCliOutputData.create_simple(
            stdout="Output",
            stderr="Error",
            status=EnumCliStatus.FAILED,
        )

        assert data.status == EnumCliStatus.FAILED

    def test_create_with_results_empty(self):
        """Test creating output data with empty results."""
        data = ModelCliOutputData.create_with_results({})

        assert len(data.results) == 0
        assert data.status == EnumCliStatus.SUCCESS

    def test_create_with_results_single(self):
        """Test creating output data with single result."""
        results = {"key1": "value1"}
        data = ModelCliOutputData.create_with_results(results)

        assert len(data.results) == 1
        assert data.get_field_value("key1") == "value1"

    def test_create_with_results_multiple(self):
        """Test creating output data with multiple results."""
        results = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3",
        }
        data = ModelCliOutputData.create_with_results(results)

        assert len(data.results) == 3
        assert data.get_field_value("key1") == "value1"
        assert data.get_field_value("key2") == "value2"
        assert data.get_field_value("key3") == "value3"

    def test_create_with_results_and_error_status(self):
        """Test creating output data with results and error status."""
        results = {"error_code": "ERR_001"}
        data = ModelCliOutputData.create_with_results(
            results,
            status=EnumCliStatus.FAILED,
        )

        assert data.status == EnumCliStatus.FAILED
        assert data.get_field_value("error_code") == "ERR_001"


@pytest.mark.unit
class TestModelCliOutputDataProtocols:
    """Test protocol method implementations."""

    def test_serialize(self):
        """Test serializing to dictionary."""
        data = ModelCliOutputData(
            stdout="Test output",
            stderr="Test error",
            status=EnumCliStatus.SUCCESS,
        )
        serialized = data.serialize()

        assert isinstance(serialized, dict)
        assert "stdout" in serialized
        assert "stderr" in serialized
        assert "status" in serialized

    def test_serialize_with_results(self):
        """Test serializing with results."""
        data = ModelCliOutputData()
        data.add_result("key1", "value1")
        data.add_metadata("meta1", "metavalue1")

        serialized = data.serialize()

        assert "results" in serialized
        assert "metadata" in serialized

    def test_get_name_default(self):
        """Test getting name returns default."""
        data = ModelCliOutputData()
        name = data.get_name()

        assert "ModelCliOutputData" in name

    def test_validate_instance(self):
        """Test validating instance."""
        data = ModelCliOutputData()
        is_valid = data.validate_instance()

        assert is_valid is True


@pytest.mark.unit
class TestModelCliOutputDataEdgeCases:
    """Test edge cases and error scenarios."""

    def test_result_with_special_characters(self):
        """Test result value with special characters."""
        data = ModelCliOutputData()
        special_value = "test!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
        data.add_result("special_key", special_value)

        assert data.get_field_value("special_key") == special_value

    def test_result_with_unicode(self):
        """Test result value with unicode characters."""
        data = ModelCliOutputData()
        unicode_value = "Hello 世界 🌍"
        data.add_result("unicode_key", unicode_value)

        assert data.get_field_value("unicode_key") == unicode_value

    def test_large_stdout(self):
        """Test with large stdout content."""
        large_output = "x" * 10000
        data = ModelCliOutputData(stdout=large_output)

        assert len(data.stdout) == 10000
        assert data.stdout == large_output

    def test_negative_execution_time(self):
        """Test with negative execution time (edge case)."""
        data = ModelCliOutputData(execution_time_ms=-1.0)
        assert data.execution_time_ms == -1.0

    def test_zero_execution_time(self):
        """Test with zero execution time."""
        data = ModelCliOutputData(execution_time_ms=0.0)
        assert data.execution_time_ms == 0.0

    def test_large_execution_time(self):
        """Test with large execution time."""
        data = ModelCliOutputData(execution_time_ms=999999.999)
        assert data.execution_time_ms == 999999.999

    def test_multiple_file_operations_same_file(self):
        """Test that same file can be in both created and modified lists."""
        data = ModelCliOutputData()
        data.add_file_created("/path/to/file.txt")
        data.add_file_modified("/path/to/file.txt")

        # File can be in both lists (created then modified in same execution)
        assert "/path/to/file.txt" in data.files_created
        assert "/path/to/file.txt" in data.files_modified

    def test_all_status_values(self):
        """Test with different status enum values."""
        for status in [
            EnumCliStatus.SUCCESS,
            EnumCliStatus.FAILED,
            EnumCliStatus.WARNING,
            EnumCliStatus.RUNNING,
            EnumCliStatus.CANCELLED,
            EnumCliStatus.TIMEOUT,
        ]:
            data = ModelCliOutputData(status=status)
            assert data.status == status

    def test_all_output_types(self):
        """Test with different output type enum values."""
        for output_type in [
            EnumOutputType.CONSOLE,
            EnumOutputType.FILE,
            EnumOutputType.STREAM,
            EnumOutputType.API,
        ]:
            data = ModelCliOutputData(output_type=output_type)
            assert data.output_type == output_type

    def test_all_output_formats(self):
        """Test with different output format enum values."""
        for format_type in [
            EnumOutputFormat.JSON,
            EnumOutputFormat.TEXT,
            EnumOutputFormat.YAML,
            EnumOutputFormat.MARKDOWN,
            EnumOutputFormat.TABLE,
            EnumOutputFormat.CSV,
        ]:
            data = ModelCliOutputData(format=format_type)
            assert data.format == format_type

    def test_is_valid_flag_manipulation(self):
        """Test is_valid flag can be set and read."""
        data = ModelCliOutputData(is_valid=True)
        assert data.is_valid is True

        data.is_valid = False
        assert data.is_valid is False

    def test_empty_results_and_metadata(self):
        """Test behavior with empty results and metadata dictionaries."""
        data = ModelCliOutputData()

        value = data.get_field_value("any_key", "default")
        assert value == "default"

    def test_model_config_extra_ignore(self):
        """Test that extra fields are ignored."""
        data = ModelCliOutputData(
            stdout="Test",
            extra_field="should_be_ignored",
        )

        assert data.stdout == "Test"
        assert not hasattr(data, "extra_field")

    def test_combined_operations(self):
        """Test combining multiple operations."""
        data = ModelCliOutputData()
        data.add_result("result1", "value1")
        data.add_result("result2", "value2")
        data.add_metadata("meta1", "metavalue1")
        data.add_file_created("/file1.txt")
        data.add_file_modified("/file2.txt")
        data.set_field_value("result3", "value3")

        assert len(data.results) == 3
        assert len(data.metadata) == 1
        assert len(data.files_created) == 1
        assert len(data.files_modified) == 1

        assert data.get_field_value("result1") == "value1"
        assert data.get_field_value("result3") == "value3"
        assert data.get_field_value("meta1") == "metavalue1"
