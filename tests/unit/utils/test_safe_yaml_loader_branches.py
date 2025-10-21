"""
Tests targeting conditional branch coverage in utils/safe_yaml_loader.py.

Focus on exception handling branches and edge cases.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.utils.safe_yaml_loader import (
    _dump_yaml_content,
    load_yaml_content_as_model,
    serialize_data_to_yaml,
    serialize_pydantic_model_to_yaml,
)


class SimpleModel(BaseModel):
    """Simple test model."""

    name: str
    value: int = 0


class TestLoadAndValidateYamlModelExceptionBranches:
    """Test exception handling branches in load_and_validate_yaml_model."""

    def test_load_yaml_file_not_found(self):
        """Test FileNotFoundError handling."""
        from omnibase_core.utils.safe_yaml_loader import load_and_validate_yaml_model

        # Non-existent path
        temp_path = Path(
            "/tmp/nonexistent_yaml_file_xyz.yaml"
        )  # noqa: S108 - Test data for FileNotFoundError, not actual temp file usage

        with pytest.raises(ModelOnexError) as exc_info:
            load_and_validate_yaml_model(temp_path, SimpleModel)

        assert exc_info.value.error_code == EnumCoreErrorCode.NOT_FOUND
        assert "not found" in str(exc_info.value).lower()

    def test_load_yaml_validation_error(self):
        """Test ValidationError from Pydantic."""
        from omnibase_core.utils.safe_yaml_loader import load_and_validate_yaml_model

        # Valid YAML but invalid model
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("name: test\nvalue: not_an_int\n")  # value should be int
            temp_path = Path(f.name)

        try:
            with pytest.raises(ModelOnexError) as exc_info:
                load_and_validate_yaml_model(temp_path, SimpleModel)

            assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        finally:
            temp_path.unlink()


class TestLoadYamlContentAsModelExceptionBranches:
    """Test exception handling branches in load_yaml_content_as_model."""

    def test_load_content_validation_error(self):
        """Test ValidationError from Pydantic."""
        # Valid YAML but invalid for model
        content = "name: test\nvalue: not_an_int"

        with pytest.raises(ModelOnexError) as exc_info:
            load_yaml_content_as_model(content, SimpleModel)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR


class TestSerializePydanticModelToYamlBranches:
    """Test conditional branches in serialize_pydantic_model_to_yaml."""

    def test_serialize_model_without_to_serializable_dict(self):
        """Test serialization without to_serializable_dict method."""

        model = SimpleModel(name="test", value=42)
        result = serialize_pydantic_model_to_yaml(model)

        assert "name" in result
        assert "test" in result

    def test_serialize_model_with_to_serializable_dict(self):
        """Test serialization with to_serializable_dict method."""

        class ModelWithSerializer(BaseModel):
            name: str
            value: int

            def to_serializable_dict(self):
                return {"custom_name": self.name, "custom_value": self.value}

        model = ModelWithSerializer(name="test", value=42)
        result = serialize_pydantic_model_to_yaml(model)

        assert "custom_name" in result or "custom_value" in result

    def test_serialize_model_with_comment_prefix(self):
        """Test serialization with comment prefix (lines 300-304)."""

        model = SimpleModel(name="test", value=42)
        result = serialize_pydantic_model_to_yaml(model, comment_prefix="# ")

        # Each line should have comment prefix
        for line in result.strip().split("\n"):
            if line.strip():
                assert line.startswith("# ") or line == ""

    def test_serialize_model_with_empty_comment_prefix(self):
        """Test serialization with empty comment prefix (no-op branch)."""

        model = SimpleModel(name="test", value=42)
        result = serialize_pydantic_model_to_yaml(model, comment_prefix="")

        # Should not have comment prefix
        assert not result.startswith("#")

    def test_serialize_model_with_yaml_options(self):
        """Test serialization with YAML options."""

        model = SimpleModel(name="test", value=42)
        result = serialize_pydantic_model_to_yaml(model, sort_keys=True)

        assert "name" in result
        assert "test" in result


class TestSerializeDataToYamlBranches:
    """Test conditional branches in serialize_data_to_yaml."""

    def test_serialize_data_with_comment_prefix(self):
        """Test serialization with comment prefix (lines 347-351)."""

        data = {"key": "value", "count": 42}
        result = serialize_data_to_yaml(data, comment_prefix="# ")

        # Each line should have comment prefix
        for line in result.strip().split("\n"):
            if line.strip():
                assert line.startswith("# ")

    def test_serialize_data_without_comment_prefix(self):
        """Test serialization without comment prefix."""

        data = {"key": "value"}
        result = serialize_data_to_yaml(data, comment_prefix="")

        assert not result.startswith("#")

    def test_serialize_data_with_various_types(self):
        """Test serialization with various data types."""

        data = {"string": "value", "number": 42, "list": [1, 2, 3]}
        result = serialize_data_to_yaml(data)

        assert "string" in result
        assert "value" in result


class TestDumpYamlContentValidationBranches:
    """Test validation branches in _dump_yaml_content."""

    def test_dump_yaml_content_utf8_validation_success(self):
        """Test UTF-8 encoding validation success branch."""

        # Valid UTF-8 content with unicode
        data = {"name": "test", "value": "unicode: \u00e9"}
        result = _dump_yaml_content(data)

        assert isinstance(result, str)
        # Should encode successfully as UTF-8
        result.encode("utf-8")

    def test_dump_yaml_content_basic_data(self):
        """Test _dump_yaml_content with basic data."""

        data = {"key": "value", "number": 42}
        result = _dump_yaml_content(data)

        assert isinstance(result, str)
        assert "key" in result


class TestYamlLoaderCommentPrefixEdgeCases:
    """Test comment prefix edge cases."""

    def test_serialize_model_comment_prefix_empty_lines(self):
        """Test comment prefix handling with empty lines."""

        model = SimpleModel(name="test", value=42)
        result = serialize_pydantic_model_to_yaml(model, comment_prefix="# ")

        # Empty lines should not have comment prefix (just empty string)
        lines = result.split("\n")
        for line in lines:
            # Either has comment prefix or is empty
            assert line.startswith("# ") or line.strip() == ""

    def test_serialize_data_comment_prefix_empty_lines(self):
        """Test comment prefix handling with empty lines in data serialization."""

        data = {"key1": "value1", "key2": "value2"}
        result = serialize_data_to_yaml(data, comment_prefix="## ")

        lines = result.split("\n")
        for line in lines:
            # Either has comment prefix or is empty
            assert line.startswith("## ") or line.strip() == ""


class TestYamlLoaderYamlOptionsHandling:
    """Test YAML options parameter handling."""

    def test_serialize_model_with_yaml_options(self):
        """Test serialize_pydantic_model_to_yaml with yaml_options."""

        model = SimpleModel(name="test", value=42)
        result = serialize_pydantic_model_to_yaml(
            model, sort_keys=True, default_flow_style=False
        )

        assert "name" in result
        assert "value" in result

    def test_serialize_data_with_yaml_options(self):
        """Test serialize_data_to_yaml with yaml_options."""

        data = {"zebra": 1, "apple": 2}
        result = serialize_data_to_yaml(data, sort_keys=True)

        assert "apple" in result or "zebra" in result


class TestGenericExceptionHandlers:
    """Test generic exception handlers in all functions."""

    def test_load_and_validate_yaml_model_generic_exception(self):
        """Test generic Exception handler in load_and_validate_yaml_model (lines 110-111)."""
        from omnibase_core.utils.safe_yaml_loader import load_and_validate_yaml_model

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("name: test\nvalue: 42\n")
            temp_path = Path(f.name)

        try:
            # Mock model_validate to raise unexpected exception
            with patch.object(
                SimpleModel,
                "model_validate",
                side_effect=RuntimeError("Unexpected error"),
            ):
                with pytest.raises(ModelOnexError) as exc_info:
                    load_and_validate_yaml_model(temp_path, SimpleModel)

                assert exc_info.value.error_code == EnumCoreErrorCode.INTERNAL_ERROR
                assert "Failed to load or validate YAML" in str(exc_info.value)
        finally:
            temp_path.unlink()

    def test_load_yaml_content_as_model_generic_exception(self):
        """Test generic Exception handler in load_yaml_content_as_model (lines 178-179)."""
        content = "name: test\nvalue: 42"

        # Mock model_validate to raise unexpected exception
        with patch.object(
            SimpleModel, "model_validate", side_effect=RuntimeError("Unexpected error")
        ):
            with pytest.raises(ModelOnexError) as exc_info:
                load_yaml_content_as_model(content, SimpleModel)

            assert exc_info.value.error_code == EnumCoreErrorCode.INTERNAL_ERROR
            assert "Failed to load or validate YAML content" in str(exc_info.value)

    def test_serialize_pydantic_model_to_yaml_generic_exception(self):
        """Test generic Exception handler in serialize_pydantic_model_to_yaml (lines 307-308)."""
        model = SimpleModel(name="test", value=42)

        # Mock ModelYamlValue.from_schema_value to raise unexpected exception
        with patch(
            "omnibase_core.utils.safe_yaml_loader.ModelYamlValue.from_schema_value",
            side_effect=RuntimeError("Unexpected error"),
        ):
            with pytest.raises(ModelOnexError) as exc_info:
                serialize_pydantic_model_to_yaml(model)

            assert exc_info.value.error_code == EnumCoreErrorCode.INTERNAL_ERROR
            assert "Failed to serialize model to YAML" in str(exc_info.value)

    def test_serialize_data_to_yaml_generic_exception(self):
        """Test generic Exception handler in serialize_data_to_yaml (lines 354-355)."""
        data = {"key": "value"}

        # Mock _dump_yaml_content to raise unexpected exception
        with patch(
            "omnibase_core.utils.safe_yaml_loader._dump_yaml_content",
            side_effect=RuntimeError("Unexpected error"),
        ):
            with pytest.raises(ModelOnexError) as exc_info:
                serialize_data_to_yaml(data)

            assert exc_info.value.error_code == EnumCoreErrorCode.INTERNAL_ERROR
            assert "Failed to serialize data to YAML" in str(exc_info.value)


class TestDumpYamlContentErrorHandling:
    """Test error handling in _dump_yaml_content."""

    def test_dump_yaml_content_carriage_return_error(self):
        """Test carriage return validation error (line 237)."""
        import yaml

        # Create a custom string class that keeps \r after replacements
        class PersistentCarriageReturnString(str):
            def replace(self, old, new, count=-1):
                # Always return a string that contains \r
                if old in ("\r\n", "\r"):
                    return PersistentCarriageReturnString("key: value\n\r")
                return PersistentCarriageReturnString(super().replace(old, new, count))

            def __contains__(self, item):
                if item == "\r":
                    return True
                return super().__contains__(item)

        data = {"key": "value"}
        mock_result = PersistentCarriageReturnString("key: value\r\n")

        with patch("yaml.dump", return_value=mock_result):
            with pytest.raises(ModelOnexError) as exc_info:
                _dump_yaml_content(data)

            assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
            assert "Carriage return found in YAML string" in str(exc_info.value)

    def test_dump_yaml_content_unicode_encode_error(self):
        """Test UnicodeEncodeError handling (lines 248-249)."""
        # Create a mock string that fails UTF-8 encoding and persists through replacements
        data = {"key": "value"}

        class BadString(str):
            def encode(self, encoding):
                if encoding == "utf-8":
                    # UnicodeEncodeError(encoding, object, start, end, reason)
                    # object must be str, not bytes
                    raise UnicodeEncodeError(
                        "utf-8", "test string", 0, 1, "invalid utf-8"
                    )
                return super().encode(encoding)

            def replace(self, old, new, count=-1):
                # Return another BadString to persist through replacements
                return BadString(super().replace(old, new, count))

        mock_result = BadString("key: value\n")

        with patch("yaml.dump", return_value=mock_result):
            with pytest.raises(ModelOnexError) as exc_info:
                _dump_yaml_content(data)

            assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
            assert "Invalid UTF-8 in YAML output" in str(exc_info.value)

    def test_dump_yaml_content_yaml_error(self):
        """Test yaml.YAMLError handling (lines 259-260)."""
        import yaml

        data = {"key": "value"}

        # Mock yaml.dump to raise YAMLError
        with patch(
            "yaml.dump", side_effect=yaml.YAMLError("YAML serialization failed")
        ):
            with pytest.raises(ModelOnexError) as exc_info:
                _dump_yaml_content(data)

            assert exc_info.value.error_code == EnumCoreErrorCode.CONVERSION_ERROR
            assert "YAML serialization error" in str(exc_info.value)
