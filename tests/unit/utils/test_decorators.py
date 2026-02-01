"""Tests for utility decorators."""

import pytest
from pydantic import BaseModel

from omnibase_core.utils.util_decorators import allow_any_type


@pytest.mark.unit
class TestDecorators:
    """Test utility decorators."""

    def test_allow_any_type_decorator(self):
        """Test allow_any_type decorator."""
        reason = "Testing any type allowance"

        @allow_any_type(reason)
        class TestModel(BaseModel):
            field: str

        # Check that the decorator was applied
        assert hasattr(TestModel, "_allow_any_reasons")
        assert reason in TestModel._allow_any_reasons

    def test_allow_any_type_multiple_reasons(self):
        """Test allow_any_type decorator with multiple reasons."""
        reason1 = "First reason"
        reason2 = "Second reason"

        @allow_any_type(reason1)
        @allow_any_type(reason2)
        class TestModel(BaseModel):
            field: str

        assert hasattr(TestModel, "_allow_any_reasons")
        assert reason1 in TestModel._allow_any_reasons
        assert reason2 in TestModel._allow_any_reasons
        assert len(TestModel._allow_any_reasons) == 2

    def test_decorator_preserves_class_functionality(self):
        """Test that decorators don't break normal class functionality."""
        reason = "Testing functionality preservation"

        @allow_any_type(reason)
        class TestModel(BaseModel):
            name: str
            value: int

        # Test normal model functionality
        instance = TestModel(name="test", value=42)
        assert instance.name == "test"
        assert instance.value == 42

        # Test serialization
        data = instance.model_dump()
        assert data == {"name": "test", "value": 42}

    def test_decorator_with_inheritance(self):
        """Test decorators work with inheritance."""
        reason = "Testing inheritance"

        @allow_any_type(reason)
        class BaseTestModel(BaseModel):
            base_field: str

        class ChildTestModel(BaseTestModel):
            child_field: int

        # Check that decorator metadata is inherited
        assert hasattr(ChildTestModel, "_allow_any_reasons")
        assert reason in ChildTestModel._allow_any_reasons

    def test_decorator_reason_types(self):
        """Test decorators with different reason types."""

        # Test with empty string
        @allow_any_type("")
        class EmptyReasonModel(BaseModel):
            field: str

        assert "" in EmptyReasonModel._allow_any_reasons

        # Test with long string
        long_reason = "This is a very long reason that explains why we need to allow any types in this model for various compatibility and interoperability reasons"

        @allow_any_type(long_reason)
        class LongReasonModel(BaseModel):
            field: str

        assert long_reason in LongReasonModel._allow_any_reasons

    def test_decorator_without_reason(self):
        """Test decorators still work without explicit reason."""

        @allow_any_type("")
        class NoReasonModel(BaseModel):
            field: str

        assert hasattr(NoReasonModel, "_allow_any_reasons")

    def test_decorator_metadata_persistence(self):
        """Test that decorator metadata persists across model operations."""
        reason = "Testing metadata persistence"

        @allow_any_type(reason)
        class TestModel(BaseModel):
            field: str

        # Create instance
        instance = TestModel(field="test")

        # Check metadata is still there
        assert hasattr(TestModel, "_allow_any_reasons")
        assert reason in TestModel._allow_any_reasons

        # Check after model operations
        data = instance.model_dump()
        new_instance = TestModel.model_validate(data)

        # Metadata should still be there
        assert hasattr(TestModel, "_allow_any_reasons")
        assert reason in TestModel._allow_any_reasons
