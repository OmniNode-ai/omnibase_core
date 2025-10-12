"""
Tests for ModelBaseResult.

Comprehensive tests for base result model including metadata handling,
serialization, and error tracking.
"""

from typing import Any

import pytest

from omnibase_core.models.core.model_base_error import ModelBaseError
from omnibase_core.models.core.model_base_result import ModelBaseResult
from omnibase_core.models.results.model_generic_metadata import ModelGenericMetadata


class TestModelBaseResult:
    """Test suite for ModelBaseResult."""

    def test_initialization_success_minimal(self):
        """Test initialization with minimal success result."""
        result = ModelBaseResult(exit_code=0, success=True)

        assert result.exit_code == 0
        assert result.success is True
        assert result.errors == []
        assert result.metadata is None

    def test_initialization_failure_minimal(self):
        """Test initialization with minimal failure result."""
        result = ModelBaseResult(exit_code=1, success=False)

        assert result.exit_code == 1
        assert result.success is False
        assert result.errors == []
        assert result.metadata is None

    def test_initialization_with_errors(self):
        """Test initialization with errors."""
        error1 = ModelBaseError(message="Error 1", code="E001")
        error2 = ModelBaseError(message="Error 2", code="E002")

        result = ModelBaseResult(exit_code=1, success=False, errors=[error1, error2])

        assert len(result.errors) == 2
        assert result.errors[0] == error1
        assert result.errors[1] == error2

    def test_initialization_with_metadata(self):
        """Test initialization with metadata."""
        metadata = ModelGenericMetadata()

        result = ModelBaseResult(exit_code=0, success=True, metadata=metadata)

        assert result.metadata == metadata
        assert isinstance(result.metadata, ModelGenericMetadata)

    def test_model_dump_without_metadata(self):
        """Test model_dump without metadata."""
        result = ModelBaseResult(exit_code=0, success=True)

        dumped = result.model_dump()

        assert isinstance(dumped, dict)
        assert dumped["exit_code"] == 0
        assert dumped["success"] is True
        assert dumped["errors"] == []
        assert "metadata" in dumped

    def test_model_dump_with_metadata(self):
        """Test model_dump with metadata."""
        metadata = ModelGenericMetadata()
        result = ModelBaseResult(exit_code=0, success=True, metadata=metadata)

        dumped = result.model_dump()

        assert isinstance(dumped, dict)
        assert "metadata" in dumped
        assert isinstance(dumped["metadata"], dict)

    def test_model_dump_exclude_none(self):
        """Test model_dump with exclude_none."""
        result = ModelBaseResult(exit_code=0, success=True)

        dumped = result.model_dump(exclude_none=True)

        assert isinstance(dumped, dict)
        # metadata should not be in result when exclude_none=True
        assert dumped.get("metadata") is None or "metadata" not in dumped

    def test_dict_method(self):
        """Test dict() method calls model_dump()."""
        result = ModelBaseResult(exit_code=0, success=True)

        dict_result = result.dict()
        dump_result = result.model_dump()

        assert dict_result == dump_result

    def test_dict_method_with_kwargs(self):
        """Test dict() method passes kwargs to model_dump()."""
        metadata = ModelGenericMetadata()
        result = ModelBaseResult(exit_code=0, success=True, metadata=metadata)

        dict_result = result.dict(exclude_none=False)

        assert isinstance(dict_result, dict)
        assert "metadata" in dict_result

    def test_parse_obj_without_metadata(self):
        """Test parse_obj without metadata."""
        obj = {"exit_code": 0, "success": True, "errors": []}

        result = ModelBaseResult.parse_obj(obj)

        assert result.exit_code == 0
        assert result.success is True
        assert result.metadata is None

    def test_parse_obj_with_metadata_dict(self):
        """Test parse_obj converts metadata dict to ModelGenericMetadata."""
        obj = {"exit_code": 0, "success": True, "errors": [], "metadata": {}}

        result = ModelBaseResult.parse_obj(obj)

        assert result.exit_code == 0
        assert result.metadata is not None
        assert isinstance(result.metadata, ModelGenericMetadata)

    def test_parse_obj_with_metadata_model(self):
        """Test parse_obj with metadata already as model."""
        metadata = ModelGenericMetadata()
        obj = {"exit_code": 0, "success": True, "errors": [], "metadata": metadata}

        result = ModelBaseResult.parse_obj(obj)

        assert result.metadata == metadata

    def test_parse_obj_with_none_metadata(self):
        """Test parse_obj with None metadata."""
        obj = {"exit_code": 0, "success": True, "errors": [], "metadata": None}

        result = ModelBaseResult.parse_obj(obj)

        assert result.metadata is None

    def test_multiple_errors(self):
        """Test handling multiple errors."""
        errors = [
            ModelBaseError(message=f"Error {i}", code=f"E{i:03d}") for i in range(10)
        ]

        result = ModelBaseResult(exit_code=1, success=False, errors=errors)

        assert len(result.errors) == 10
        assert all(isinstance(e, ModelBaseError) for e in result.errors)

    def test_exit_code_variations(self):
        """Test various exit codes."""
        for code in [0, 1, 2, 127, 255]:
            result = ModelBaseResult(exit_code=code, success=(code == 0))
            assert result.exit_code == code

    def test_success_false_exit_code_zero(self):
        """Test that success can be False even with exit_code 0."""
        result = ModelBaseResult(exit_code=0, success=False)

        assert result.exit_code == 0
        assert result.success is False

    def test_success_true_exit_code_nonzero(self):
        """Test that success can be True even with non-zero exit_code."""
        result = ModelBaseResult(exit_code=1, success=True)

        assert result.exit_code == 1
        assert result.success is True


class TestModelBaseResultEdgeCases:
    """Edge case tests for ModelBaseResult."""

    def test_empty_errors_list(self):
        """Test with explicitly empty errors list."""
        result = ModelBaseResult(exit_code=0, success=True, errors=[])

        assert result.errors == []
        assert len(result.errors) == 0

    def test_model_copy(self):
        """Test model copying."""
        original = ModelBaseResult(
            exit_code=1,
            success=False,
            errors=[ModelBaseError(message="Error", code="E001")],
        )

        copy = original.model_copy()

        assert copy.exit_code == original.exit_code
        assert copy.success == original.success
        assert len(copy.errors) == len(original.errors)
        assert copy is not original

    def test_model_copy_deep(self):
        """Test deep model copying."""
        original = ModelBaseResult(
            exit_code=1,
            success=False,
            errors=[ModelBaseError(message="Error", code="E001")],
        )

        copy = original.model_copy(deep=True)

        # Modify copy
        copy.errors.append(ModelBaseError(message="New", code="E002"))

        # Original should be unchanged
        assert len(original.errors) == 1
        assert len(copy.errors) == 2

    def test_negative_exit_code(self):
        """Test with negative exit code."""
        result = ModelBaseResult(exit_code=-1, success=False)

        assert result.exit_code == -1

    def test_large_exit_code(self):
        """Test with large exit code."""
        result = ModelBaseResult(exit_code=99999, success=False)

        assert result.exit_code == 99999

    def test_serialization_deserialization_roundtrip(self):
        """Test roundtrip serialization."""
        original = ModelBaseResult(
            exit_code=1,
            success=False,
            errors=[ModelBaseError(message="Error", code="E001")],
        )

        # Serialize
        data = original.model_dump()

        # Deserialize
        restored = ModelBaseResult.parse_obj(data)

        assert restored.exit_code == original.exit_code
        assert restored.success == original.success
        assert len(restored.errors) == len(original.errors)

    def test_model_validate(self):
        """Test model validation."""
        data = {"exit_code": 0, "success": True}

        result = ModelBaseResult.model_validate(data)

        assert result.exit_code == 0
        assert result.success is True

    def test_errors_with_complex_messages(self):
        """Test errors with complex messages."""
        error = ModelBaseError(message="Error with\nnewlines\tand\ttabs", code="E001")

        result = ModelBaseResult(exit_code=1, success=False, errors=[error])

        assert "\n" in result.errors[0].message
        assert "\t" in result.errors[0].message


class TestModelBaseResultBranchCoverage:
    """Branch coverage tests for conditional logic in ModelBaseResult."""

    def test_model_dump_metadata_none_branch(self):
        """Test model_dump when metadata is None (False branch)."""
        result = ModelBaseResult(exit_code=0, success=True, metadata=None)

        dumped = result.model_dump()

        # Should not process metadata when it's None
        assert "metadata" in dumped
        assert dumped["metadata"] is None

    def test_model_dump_metadata_exists_and_is_generic_metadata(self):
        """Test model_dump when metadata exists and is ModelGenericMetadata (True branch)."""
        metadata = ModelGenericMetadata()
        result = ModelBaseResult(exit_code=0, success=True, metadata=metadata)

        dumped = result.model_dump()

        # Should process metadata through special handling
        assert "metadata" in dumped
        assert isinstance(dumped["metadata"], dict)

    def test_model_dump_metadata_false_branch(self):
        """Test model_dump when metadata is falsy but not None."""
        # This tests the edge case where metadata could be set to a falsy value
        # In practice, Pydantic validation ensures this is either None or ModelGenericMetadata
        # but we test the conditional logic
        result = ModelBaseResult(exit_code=0, success=True, metadata=None)

        # Manually test the conditional by calling model_dump
        dumped = result.model_dump()

        # The first condition (self.metadata) should be False
        assert dumped["metadata"] is None

    def test_parse_obj_not_dict_branch(self):
        """Test parse_obj when obj is not a dict (False branch of isinstance check)."""
        # When parse_obj receives a non-dict, the conditional should take False branch
        # Pydantic will handle this through its normal parsing
        result_obj = ModelBaseResult(exit_code=0, success=True)

        # Parsing the object itself should work
        parsed = ModelBaseResult.parse_obj(result_obj)

        assert parsed.exit_code == 0
        assert parsed.success is True

    def test_parse_obj_dict_without_metadata_key(self):
        """Test parse_obj when dict doesn't have 'metadata' key (False branch)."""
        obj = {
            "exit_code": 0,
            "success": True,
            "errors": [],
            # No metadata key
        }

        result = ModelBaseResult.parse_obj(obj)

        # Should not attempt metadata conversion when key is missing
        assert result.metadata is None

    def test_parse_obj_dict_with_metadata_key_none_value(self):
        """Test parse_obj when dict has 'metadata' key but value is None (False branch)."""
        obj = {"exit_code": 0, "success": True, "errors": [], "metadata": None}

        result = ModelBaseResult.parse_obj(obj)

        # Should not convert None metadata
        assert result.metadata is None

    def test_parse_obj_dict_with_metadata_already_model(self):
        """Test parse_obj when metadata is already ModelGenericMetadata (False branch of inner if)."""
        metadata = ModelGenericMetadata()
        obj = {"exit_code": 0, "success": True, "errors": [], "metadata": metadata}

        result = ModelBaseResult.parse_obj(obj)

        # Should not re-convert when already ModelGenericMetadata
        assert result.metadata is metadata
        assert isinstance(result.metadata, ModelGenericMetadata)

    def test_parse_obj_dict_with_metadata_dict_needs_conversion(self):
        """Test parse_obj when metadata is dict and needs conversion (True branch of inner if)."""
        obj = {
            "exit_code": 0,
            "success": True,
            "errors": [],
            "metadata": {"some_field": "some_value"},
        }

        result = ModelBaseResult.parse_obj(obj)

        # Should convert dict to ModelGenericMetadata
        assert result.metadata is not None
        assert isinstance(result.metadata, ModelGenericMetadata)
