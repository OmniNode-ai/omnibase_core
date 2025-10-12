"""
Test suite for MixinCompletionData.
"""

import pytest

from omnibase_core.mixins.mixin_completion_data import MixinCompletionData


class TestMixinCompletionData:
    """Test MixinCompletionData functionality."""

    def test_mixin_completion_data_empty(self):
        """Test creating empty MixinCompletionData."""
        completion = MixinCompletionData()

        assert completion.message is None
        assert completion.success is None
        assert completion.code is None
        assert completion.tags is None

    def test_mixin_completion_data_with_all_fields(self):
        """Test MixinCompletionData with all fields."""
        completion = MixinCompletionData(
            message="Operation completed successfully",
            success=True,
            code=200,
            tags=["success", "operation", "api"],
        )

        assert completion.message == "Operation completed successfully"
        assert completion.success is True
        assert completion.code == 200
        assert completion.tags == ["success", "operation", "api"]

    def test_mixin_completion_data_partial_fields(self):
        """Test MixinCompletionData with partial fields."""
        completion = MixinCompletionData(message="Processing complete", success=True)

        assert completion.message == "Processing complete"
        assert completion.success is True
        assert completion.code is None
        assert completion.tags is None

    def test_mixin_completion_data_field_types(self):
        """Test that all fields have correct types."""
        completion = MixinCompletionData(
            message="Test message", success=False, code=404, tags=["error", "not_found"]
        )

        assert isinstance(completion.message, str)
        assert isinstance(completion.success, bool)
        assert isinstance(completion.code, int)
        assert isinstance(completion.tags, list)

    def test_mixin_completion_data_success_scenarios(self):
        """Test MixinCompletionData with success scenarios."""
        success_completion = MixinCompletionData(
            message="Task completed",
            success=True,
            code=200,
            tags=["success", "completed"],
        )

        assert success_completion.success is True
        assert success_completion.code == 200
        assert "success" in success_completion.tags

    def test_mixin_completion_data_failure_scenarios(self):
        """Test MixinCompletionData with failure scenarios."""
        failure_completion = MixinCompletionData(
            message="Operation failed",
            success=False,
            code=500,
            tags=["error", "failed"],
        )

        assert failure_completion.success is False
        assert failure_completion.code == 500
        assert "error" in failure_completion.tags

    def test_mixin_completion_data_different_codes(self):
        """Test MixinCompletionData with different status codes."""
        test_cases = [
            (200, "OK"),
            (201, "Created"),
            (400, "Bad Request"),
            (401, "Unauthorized"),
            (403, "Forbidden"),
            (404, "Not Found"),
            (500, "Internal Server Error"),
        ]

        for code, message in test_cases:
            completion = MixinCompletionData(
                message=message, success=code < 400, code=code, tags=[f"code_{code}"]
            )

            assert completion.code == code
            assert completion.message == message
            assert completion.success == (code < 400)

    def test_mixin_completion_data_empty_tags(self):
        """Test MixinCompletionData with empty tags list."""
        completion = MixinCompletionData(
            message="No tags", success=True, code=200, tags=[]
        )

        assert completion.tags == []
        assert len(completion.tags) == 0

    def test_mixin_completion_data_multiple_tags(self):
        """Test MixinCompletionData with multiple tags."""
        completion = MixinCompletionData(
            message="Multi-tagged operation",
            success=True,
            code=200,
            tags=["api", "v1", "user", "profile", "update"],
        )

        assert len(completion.tags) == 5
        assert "api" in completion.tags
        assert "v1" in completion.tags
        assert "user" in completion.tags

    def test_mixin_completion_data_to_event_kwargs(self):
        """Test to_event_kwargs method."""
        completion = MixinCompletionData(
            message="Test event", success=True, code=200, tags=["test"]
        )

        kwargs = completion.to_event_kwargs()

        assert isinstance(kwargs, dict)
        assert kwargs["message"] == "Test event"
        assert kwargs["success"] is True
        assert kwargs["code"] == 200
        assert kwargs["tags"] == ["test"]

    def test_mixin_completion_data_to_event_kwargs_excludes_none(self):
        """Test to_event_kwargs excludes None values."""
        completion = MixinCompletionData(
            message="Partial data",
            success=True,
            # code and tags are None
        )

        kwargs = completion.to_event_kwargs()

        assert "message" in kwargs
        assert "success" in kwargs
        assert "code" not in kwargs
        assert "tags" not in kwargs

    def test_mixin_completion_data_immutable(self):
        """Test that MixinCompletionData is immutable."""
        completion = MixinCompletionData(
            message="Test", success=True, code=200, tags=["test"]
        )

        # Should not be able to modify fields (Pydantic ValidationError for frozen models)
        with pytest.raises(Exception):  # ValidationError for frozen models
            completion.message = "Modified"

        with pytest.raises(Exception):  # ValidationError for frozen models
            completion.success = False

    def test_mixin_completion_data_strict_types(self):
        """Test that MixinCompletionData enforces strict types."""
        # These should work
        completion1 = MixinCompletionData(
            message="String message", success=True, code=200, tags=["string", "tags"]
        )

        assert completion1.message == "String message"
        assert completion1.success is True
        assert completion1.code == 200
        assert completion1.tags == ["string", "tags"]

    def test_mixin_completion_data_zero_code(self):
        """Test MixinCompletionData with zero code."""
        completion = MixinCompletionData(
            message="Zero code", success=True, code=0, tags=["zero"]
        )

        assert completion.code == 0

    def test_mixin_completion_data_negative_code(self):
        """Test MixinCompletionData with negative code."""
        completion = MixinCompletionData(
            message="Negative code", success=False, code=-1, tags=["negative"]
        )

        assert completion.code == -1

    def test_mixin_completion_data_long_message(self):
        """Test MixinCompletionData with long message."""
        long_message = "This is a very long message that contains multiple sentences and should be handled properly by the completion data structure."

        completion = MixinCompletionData(
            message=long_message, success=True, code=200, tags=["long", "message"]
        )

        assert completion.message == long_message
        assert len(completion.message) > 100
