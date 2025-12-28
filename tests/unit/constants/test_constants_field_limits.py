"""
Unit tests for constants_field_limits module.

Tests the field length limit constants for ONEX model validation.
These constants provide standardized limits for identifiers, names,
paths, URLs, content fields, and collection sizes.
"""

import pytest

# Module-level pytest marker for all tests in this file
pytestmark = pytest.mark.unit


class TestIdentifierLimitConstants:
    """Test cases for identifier limit constants."""

    def test_max_identifier_length_value(self) -> None:
        """Test MAX_IDENTIFIER_LENGTH has expected value."""
        from omnibase_core.constants.constants_field_limits import (
            MAX_IDENTIFIER_LENGTH,
        )

        assert MAX_IDENTIFIER_LENGTH == 100

    def test_max_identifier_length_type(self) -> None:
        """Test MAX_IDENTIFIER_LENGTH is an integer."""
        from omnibase_core.constants.constants_field_limits import (
            MAX_IDENTIFIER_LENGTH,
        )

        assert isinstance(MAX_IDENTIFIER_LENGTH, int)

    def test_max_name_length_value(self) -> None:
        """Test MAX_NAME_LENGTH has expected value."""
        from omnibase_core.constants.constants_field_limits import MAX_NAME_LENGTH

        assert MAX_NAME_LENGTH == 255

    def test_max_name_length_type(self) -> None:
        """Test MAX_NAME_LENGTH is an integer."""
        from omnibase_core.constants.constants_field_limits import MAX_NAME_LENGTH

        assert isinstance(MAX_NAME_LENGTH, int)

    def test_max_key_length_value(self) -> None:
        """Test MAX_KEY_LENGTH has expected value."""
        from omnibase_core.constants.constants_field_limits import MAX_KEY_LENGTH

        assert MAX_KEY_LENGTH == 100

    def test_max_key_length_type(self) -> None:
        """Test MAX_KEY_LENGTH is an integer."""
        from omnibase_core.constants.constants_field_limits import MAX_KEY_LENGTH

        assert isinstance(MAX_KEY_LENGTH, int)

    def test_identifier_constants_are_positive(self) -> None:
        """Test all identifier limit constants are positive."""
        from omnibase_core.constants.constants_field_limits import (
            MAX_IDENTIFIER_LENGTH,
            MAX_KEY_LENGTH,
            MAX_NAME_LENGTH,
        )

        assert MAX_IDENTIFIER_LENGTH > 0
        assert MAX_NAME_LENGTH > 0
        assert MAX_KEY_LENGTH > 0

    def test_name_length_greater_than_identifier_length(self) -> None:
        """Test MAX_NAME_LENGTH is greater than MAX_IDENTIFIER_LENGTH.

        Names typically allow more characters than short identifiers.
        """
        from omnibase_core.constants.constants_field_limits import (
            MAX_IDENTIFIER_LENGTH,
            MAX_NAME_LENGTH,
        )

        assert MAX_NAME_LENGTH > MAX_IDENTIFIER_LENGTH


class TestPathLimitConstants:
    """Test cases for path limit constants."""

    def test_max_path_length_value(self) -> None:
        """Test MAX_PATH_LENGTH has expected value."""
        from omnibase_core.constants.constants_field_limits import MAX_PATH_LENGTH

        assert MAX_PATH_LENGTH == 255

    def test_max_path_length_type(self) -> None:
        """Test MAX_PATH_LENGTH is an integer."""
        from omnibase_core.constants.constants_field_limits import MAX_PATH_LENGTH

        assert isinstance(MAX_PATH_LENGTH, int)

    def test_max_url_length_value(self) -> None:
        """Test MAX_URL_LENGTH has expected value."""
        from omnibase_core.constants.constants_field_limits import MAX_URL_LENGTH

        assert MAX_URL_LENGTH == 2048

    def test_max_url_length_type(self) -> None:
        """Test MAX_URL_LENGTH is an integer."""
        from omnibase_core.constants.constants_field_limits import MAX_URL_LENGTH

        assert isinstance(MAX_URL_LENGTH, int)

    def test_path_constants_are_positive(self) -> None:
        """Test all path limit constants are positive."""
        from omnibase_core.constants.constants_field_limits import (
            MAX_PATH_LENGTH,
            MAX_URL_LENGTH,
        )

        assert MAX_PATH_LENGTH > 0
        assert MAX_URL_LENGTH > 0

    def test_url_length_greater_than_path_length(self) -> None:
        """Test MAX_URL_LENGTH is greater than MAX_PATH_LENGTH.

        URLs can include scheme, host, port, path, query, and fragment,
        so they require more space than file paths.
        """
        from omnibase_core.constants.constants_field_limits import (
            MAX_PATH_LENGTH,
            MAX_URL_LENGTH,
        )

        assert MAX_URL_LENGTH > MAX_PATH_LENGTH


class TestContentLimitConstants:
    """Test cases for content limit constants."""

    def test_max_reason_length_value(self) -> None:
        """Test MAX_REASON_LENGTH has expected value."""
        from omnibase_core.constants.constants_field_limits import MAX_REASON_LENGTH

        assert MAX_REASON_LENGTH == 500

    def test_max_reason_length_type(self) -> None:
        """Test MAX_REASON_LENGTH is an integer."""
        from omnibase_core.constants.constants_field_limits import MAX_REASON_LENGTH

        assert isinstance(MAX_REASON_LENGTH, int)

    def test_max_message_length_value(self) -> None:
        """Test MAX_MESSAGE_LENGTH has expected value."""
        from omnibase_core.constants.constants_field_limits import MAX_MESSAGE_LENGTH

        assert MAX_MESSAGE_LENGTH == 1500

    def test_max_message_length_type(self) -> None:
        """Test MAX_MESSAGE_LENGTH is an integer."""
        from omnibase_core.constants.constants_field_limits import MAX_MESSAGE_LENGTH

        assert isinstance(MAX_MESSAGE_LENGTH, int)

    def test_max_description_length_value(self) -> None:
        """Test MAX_DESCRIPTION_LENGTH has expected value."""
        from omnibase_core.constants.constants_field_limits import (
            MAX_DESCRIPTION_LENGTH,
        )

        assert MAX_DESCRIPTION_LENGTH == 1000

    def test_max_description_length_type(self) -> None:
        """Test MAX_DESCRIPTION_LENGTH is an integer."""
        from omnibase_core.constants.constants_field_limits import (
            MAX_DESCRIPTION_LENGTH,
        )

        assert isinstance(MAX_DESCRIPTION_LENGTH, int)

    def test_max_error_message_length_value(self) -> None:
        """Test MAX_ERROR_MESSAGE_LENGTH has expected value."""
        from omnibase_core.constants.constants_field_limits import (
            MAX_ERROR_MESSAGE_LENGTH,
        )

        assert MAX_ERROR_MESSAGE_LENGTH == 2000

    def test_max_error_message_length_type(self) -> None:
        """Test MAX_ERROR_MESSAGE_LENGTH is an integer."""
        from omnibase_core.constants.constants_field_limits import (
            MAX_ERROR_MESSAGE_LENGTH,
        )

        assert isinstance(MAX_ERROR_MESSAGE_LENGTH, int)

    def test_max_log_message_length_value(self) -> None:
        """Test MAX_LOG_MESSAGE_LENGTH has expected value."""
        from omnibase_core.constants.constants_field_limits import (
            MAX_LOG_MESSAGE_LENGTH,
        )

        assert MAX_LOG_MESSAGE_LENGTH == 4000

    def test_max_log_message_length_type(self) -> None:
        """Test MAX_LOG_MESSAGE_LENGTH is an integer."""
        from omnibase_core.constants.constants_field_limits import (
            MAX_LOG_MESSAGE_LENGTH,
        )

        assert isinstance(MAX_LOG_MESSAGE_LENGTH, int)

    def test_content_constants_are_positive(self) -> None:
        """Test all content limit constants are positive."""
        from omnibase_core.constants.constants_field_limits import (
            MAX_DESCRIPTION_LENGTH,
            MAX_ERROR_MESSAGE_LENGTH,
            MAX_LOG_MESSAGE_LENGTH,
            MAX_MESSAGE_LENGTH,
            MAX_REASON_LENGTH,
        )

        assert MAX_REASON_LENGTH > 0
        assert MAX_MESSAGE_LENGTH > 0
        assert MAX_DESCRIPTION_LENGTH > 0
        assert MAX_ERROR_MESSAGE_LENGTH > 0
        assert MAX_LOG_MESSAGE_LENGTH > 0

    def test_content_limits_hierarchy(self) -> None:
        """Test content limits follow expected hierarchy.

        Reason (500) < Description (1000) < Message (1500) < ErrorMessage (2000) < LogMessage (4000).
        This allows for increasingly detailed content.
        """
        from omnibase_core.constants.constants_field_limits import (
            MAX_DESCRIPTION_LENGTH,
            MAX_ERROR_MESSAGE_LENGTH,
            MAX_LOG_MESSAGE_LENGTH,
            MAX_MESSAGE_LENGTH,
            MAX_REASON_LENGTH,
        )

        assert MAX_REASON_LENGTH < MAX_DESCRIPTION_LENGTH
        assert MAX_DESCRIPTION_LENGTH < MAX_MESSAGE_LENGTH
        assert MAX_MESSAGE_LENGTH < MAX_ERROR_MESSAGE_LENGTH
        assert MAX_ERROR_MESSAGE_LENGTH < MAX_LOG_MESSAGE_LENGTH


class TestCollectionLimitConstants:
    """Test cases for collection limit constants."""

    def test_max_tags_count_value(self) -> None:
        """Test MAX_TAGS_COUNT has expected value."""
        from omnibase_core.constants.constants_field_limits import MAX_TAGS_COUNT

        assert MAX_TAGS_COUNT == 50

    def test_max_tags_count_type(self) -> None:
        """Test MAX_TAGS_COUNT is an integer."""
        from omnibase_core.constants.constants_field_limits import MAX_TAGS_COUNT

        assert isinstance(MAX_TAGS_COUNT, int)

    def test_max_labels_count_value(self) -> None:
        """Test MAX_LABELS_COUNT has expected value."""
        from omnibase_core.constants.constants_field_limits import MAX_LABELS_COUNT

        assert MAX_LABELS_COUNT == 100

    def test_max_labels_count_type(self) -> None:
        """Test MAX_LABELS_COUNT is an integer."""
        from omnibase_core.constants.constants_field_limits import MAX_LABELS_COUNT

        assert isinstance(MAX_LABELS_COUNT, int)

    def test_max_label_length_value(self) -> None:
        """Test MAX_LABEL_LENGTH has expected value."""
        from omnibase_core.constants.constants_field_limits import MAX_LABEL_LENGTH

        assert MAX_LABEL_LENGTH == 100

    def test_max_label_length_type(self) -> None:
        """Test MAX_LABEL_LENGTH is an integer."""
        from omnibase_core.constants.constants_field_limits import MAX_LABEL_LENGTH

        assert isinstance(MAX_LABEL_LENGTH, int)

    def test_collection_constants_are_positive(self) -> None:
        """Test all collection limit constants are positive."""
        from omnibase_core.constants.constants_field_limits import (
            MAX_LABEL_LENGTH,
            MAX_LABELS_COUNT,
            MAX_TAGS_COUNT,
        )

        assert MAX_TAGS_COUNT > 0
        assert MAX_LABELS_COUNT > 0
        assert MAX_LABEL_LENGTH > 0

    def test_labels_allow_more_than_tags(self) -> None:
        """Test MAX_LABELS_COUNT is greater than MAX_TAGS_COUNT.

        Labels are typically more granular than tags, so entities
        may have more labels than tags.
        """
        from omnibase_core.constants.constants_field_limits import (
            MAX_LABELS_COUNT,
            MAX_TAGS_COUNT,
        )

        assert MAX_LABELS_COUNT > MAX_TAGS_COUNT


class TestModuleImports:
    """Test cases for module import functionality."""

    def test_direct_module_import(self) -> None:
        """Test constants can be imported directly from the module."""
        from omnibase_core.constants.constants_field_limits import (
            MAX_DESCRIPTION_LENGTH,
            MAX_ERROR_MESSAGE_LENGTH,
            MAX_IDENTIFIER_LENGTH,
            MAX_KEY_LENGTH,
            MAX_LABEL_LENGTH,
            MAX_LABELS_COUNT,
            MAX_LOG_MESSAGE_LENGTH,
            MAX_MESSAGE_LENGTH,
            MAX_NAME_LENGTH,
            MAX_PATH_LENGTH,
            MAX_REASON_LENGTH,
            MAX_TAGS_COUNT,
            MAX_URL_LENGTH,
        )

        # Verify all imports succeeded by checking they are integers
        assert isinstance(MAX_IDENTIFIER_LENGTH, int)
        assert isinstance(MAX_NAME_LENGTH, int)
        assert isinstance(MAX_KEY_LENGTH, int)
        assert isinstance(MAX_PATH_LENGTH, int)
        assert isinstance(MAX_URL_LENGTH, int)
        assert isinstance(MAX_REASON_LENGTH, int)
        assert isinstance(MAX_MESSAGE_LENGTH, int)
        assert isinstance(MAX_DESCRIPTION_LENGTH, int)
        assert isinstance(MAX_ERROR_MESSAGE_LENGTH, int)
        assert isinstance(MAX_LOG_MESSAGE_LENGTH, int)
        assert isinstance(MAX_TAGS_COUNT, int)
        assert isinstance(MAX_LABELS_COUNT, int)
        assert isinstance(MAX_LABEL_LENGTH, int)

    def test_all_constants_in_module_all(self) -> None:
        """Test that all constants are listed in __all__."""
        from omnibase_core.constants import constants_field_limits

        expected_exports = [
            "MAX_IDENTIFIER_LENGTH",
            "MAX_NAME_LENGTH",
            "MAX_KEY_LENGTH",
            "MAX_PATH_LENGTH",
            "MAX_URL_LENGTH",
            "MAX_REASON_LENGTH",
            "MAX_MESSAGE_LENGTH",
            "MAX_DESCRIPTION_LENGTH",
            "MAX_ERROR_MESSAGE_LENGTH",
            "MAX_LOG_MESSAGE_LENGTH",
            "MAX_TAGS_COUNT",
            "MAX_LABELS_COUNT",
            "MAX_LABEL_LENGTH",
            # Algorithm iteration limits
            "MAX_DFS_ITERATIONS",
            "MAX_BFS_ITERATIONS",
            "MAX_TIMEOUT_MS",
        ]

        for export in expected_exports:
            assert export in constants_field_limits.__all__, (
                f"Missing export in __all__: {export}"
            )

    def test_module_all_count(self) -> None:
        """Test __all__ contains exactly the expected number of exports."""
        from omnibase_core.constants import constants_field_limits

        # Should have exactly 16 constants (13 field limits + 3 algorithm limits)
        assert len(constants_field_limits.__all__) == 16


class TestModuleDocumentation:
    """Test cases for module documentation."""

    def test_module_has_docstring(self) -> None:
        """Test that the module has a docstring."""
        from omnibase_core.constants import constants_field_limits

        assert constants_field_limits.__doc__ is not None
        assert len(constants_field_limits.__doc__) > 0

    def test_module_docstring_describes_purpose(self) -> None:
        """Test that module docstring describes field limits."""
        from omnibase_core.constants import constants_field_limits

        docstring = constants_field_limits.__doc__.lower()
        assert "field" in docstring or "limit" in docstring


class TestConstantsUsability:
    """Test cases for constant usability patterns."""

    def test_constants_can_be_used_as_max_length(self) -> None:
        """Test constants work for string length validation."""
        from omnibase_core.constants.constants_field_limits import (
            MAX_IDENTIFIER_LENGTH,
            MAX_NAME_LENGTH,
        )

        # Simulate max_length validation
        valid_id = "a" * MAX_IDENTIFIER_LENGTH
        valid_name = "b" * MAX_NAME_LENGTH

        assert len(valid_id) == MAX_IDENTIFIER_LENGTH
        assert len(valid_name) == MAX_NAME_LENGTH

    def test_constants_can_be_used_for_collection_validation(self) -> None:
        """Test constants work for collection size validation."""
        from omnibase_core.constants.constants_field_limits import (
            MAX_LABELS_COUNT,
            MAX_TAGS_COUNT,
        )

        # Simulate collection size validation
        valid_tags = ["tag"] * MAX_TAGS_COUNT
        valid_labels = ["label"] * MAX_LABELS_COUNT

        assert len(valid_tags) == MAX_TAGS_COUNT
        assert len(valid_labels) == MAX_LABELS_COUNT

    def test_constants_can_be_compared(self) -> None:
        """Test constants support numeric comparison."""
        from omnibase_core.constants.constants_field_limits import (
            MAX_DESCRIPTION_LENGTH,
            MAX_ERROR_MESSAGE_LENGTH,
            MAX_LOG_MESSAGE_LENGTH,
        )

        # Test comparison operations
        assert MAX_DESCRIPTION_LENGTH < MAX_ERROR_MESSAGE_LENGTH
        assert MAX_ERROR_MESSAGE_LENGTH < MAX_LOG_MESSAGE_LENGTH
        assert MAX_LOG_MESSAGE_LENGTH > MAX_DESCRIPTION_LENGTH

    def test_constants_can_be_used_in_arithmetic(self) -> None:
        """Test constants work in arithmetic operations."""
        from omnibase_core.constants.constants_field_limits import (
            MAX_DESCRIPTION_LENGTH,
            MAX_NAME_LENGTH,
        )

        # Common pattern: calculate total buffer size
        total = MAX_NAME_LENGTH + MAX_DESCRIPTION_LENGTH
        assert total == 1255

    def test_constants_can_be_used_as_dict_keys(self) -> None:
        """Test constants work as dictionary values for config."""
        from omnibase_core.constants.constants_field_limits import (
            MAX_DESCRIPTION_LENGTH,
            MAX_IDENTIFIER_LENGTH,
            MAX_NAME_LENGTH,
        )

        config = {
            "identifier_max": MAX_IDENTIFIER_LENGTH,
            "name_max": MAX_NAME_LENGTH,
            "description_max": MAX_DESCRIPTION_LENGTH,
        }

        assert config["identifier_max"] == 100
        assert config["name_max"] == 255
        assert config["description_max"] == 1000


class TestConstantImmutability:
    """Test cases verifying constants behave as expected."""

    def test_constants_are_not_none(self) -> None:
        """Test no constant is None."""
        from omnibase_core.constants.constants_field_limits import (
            MAX_DESCRIPTION_LENGTH,
            MAX_ERROR_MESSAGE_LENGTH,
            MAX_IDENTIFIER_LENGTH,
            MAX_KEY_LENGTH,
            MAX_LABEL_LENGTH,
            MAX_LABELS_COUNT,
            MAX_LOG_MESSAGE_LENGTH,
            MAX_MESSAGE_LENGTH,
            MAX_NAME_LENGTH,
            MAX_PATH_LENGTH,
            MAX_REASON_LENGTH,
            MAX_TAGS_COUNT,
            MAX_URL_LENGTH,
        )

        constants = [
            MAX_IDENTIFIER_LENGTH,
            MAX_NAME_LENGTH,
            MAX_KEY_LENGTH,
            MAX_PATH_LENGTH,
            MAX_URL_LENGTH,
            MAX_REASON_LENGTH,
            MAX_MESSAGE_LENGTH,
            MAX_DESCRIPTION_LENGTH,
            MAX_ERROR_MESSAGE_LENGTH,
            MAX_LOG_MESSAGE_LENGTH,
            MAX_TAGS_COUNT,
            MAX_LABELS_COUNT,
            MAX_LABEL_LENGTH,
        ]

        for constant in constants:
            assert constant is not None

    def test_all_constants_are_integers(self) -> None:
        """Test all constants are integers (not floats or other types)."""
        from omnibase_core.constants.constants_field_limits import (
            MAX_DESCRIPTION_LENGTH,
            MAX_ERROR_MESSAGE_LENGTH,
            MAX_IDENTIFIER_LENGTH,
            MAX_KEY_LENGTH,
            MAX_LABEL_LENGTH,
            MAX_LABELS_COUNT,
            MAX_LOG_MESSAGE_LENGTH,
            MAX_MESSAGE_LENGTH,
            MAX_NAME_LENGTH,
            MAX_PATH_LENGTH,
            MAX_REASON_LENGTH,
            MAX_TAGS_COUNT,
            MAX_URL_LENGTH,
        )

        constants = {
            "MAX_IDENTIFIER_LENGTH": MAX_IDENTIFIER_LENGTH,
            "MAX_NAME_LENGTH": MAX_NAME_LENGTH,
            "MAX_KEY_LENGTH": MAX_KEY_LENGTH,
            "MAX_PATH_LENGTH": MAX_PATH_LENGTH,
            "MAX_URL_LENGTH": MAX_URL_LENGTH,
            "MAX_REASON_LENGTH": MAX_REASON_LENGTH,
            "MAX_MESSAGE_LENGTH": MAX_MESSAGE_LENGTH,
            "MAX_DESCRIPTION_LENGTH": MAX_DESCRIPTION_LENGTH,
            "MAX_ERROR_MESSAGE_LENGTH": MAX_ERROR_MESSAGE_LENGTH,
            "MAX_LOG_MESSAGE_LENGTH": MAX_LOG_MESSAGE_LENGTH,
            "MAX_TAGS_COUNT": MAX_TAGS_COUNT,
            "MAX_LABELS_COUNT": MAX_LABELS_COUNT,
            "MAX_LABEL_LENGTH": MAX_LABEL_LENGTH,
        }

        for name, value in constants.items():
            assert isinstance(value, int), f"{name} should be int, got {type(value)}"
            # Ensure it's exactly int, not a subclass like bool
            assert type(value) is int, f"{name} should be exactly int type"


class TestConstantsSummary:
    """Summary test cases for all constants."""

    def test_all_constants_summary(self) -> None:
        """Test all constants have expected values in a single test."""
        from omnibase_core.constants.constants_field_limits import (
            MAX_DESCRIPTION_LENGTH,
            MAX_ERROR_MESSAGE_LENGTH,
            MAX_IDENTIFIER_LENGTH,
            MAX_KEY_LENGTH,
            MAX_LABEL_LENGTH,
            MAX_LABELS_COUNT,
            MAX_LOG_MESSAGE_LENGTH,
            MAX_MESSAGE_LENGTH,
            MAX_NAME_LENGTH,
            MAX_PATH_LENGTH,
            MAX_REASON_LENGTH,
            MAX_TAGS_COUNT,
            MAX_URL_LENGTH,
        )

        expected = {
            "MAX_IDENTIFIER_LENGTH": 100,
            "MAX_NAME_LENGTH": 255,
            "MAX_KEY_LENGTH": 100,
            "MAX_PATH_LENGTH": 255,
            "MAX_URL_LENGTH": 2048,
            "MAX_REASON_LENGTH": 500,
            "MAX_MESSAGE_LENGTH": 1500,
            "MAX_DESCRIPTION_LENGTH": 1000,
            "MAX_ERROR_MESSAGE_LENGTH": 2000,
            "MAX_LOG_MESSAGE_LENGTH": 4000,
            "MAX_TAGS_COUNT": 50,
            "MAX_LABELS_COUNT": 100,
            "MAX_LABEL_LENGTH": 100,
        }

        actual = {
            "MAX_IDENTIFIER_LENGTH": MAX_IDENTIFIER_LENGTH,
            "MAX_NAME_LENGTH": MAX_NAME_LENGTH,
            "MAX_KEY_LENGTH": MAX_KEY_LENGTH,
            "MAX_PATH_LENGTH": MAX_PATH_LENGTH,
            "MAX_URL_LENGTH": MAX_URL_LENGTH,
            "MAX_REASON_LENGTH": MAX_REASON_LENGTH,
            "MAX_MESSAGE_LENGTH": MAX_MESSAGE_LENGTH,
            "MAX_DESCRIPTION_LENGTH": MAX_DESCRIPTION_LENGTH,
            "MAX_ERROR_MESSAGE_LENGTH": MAX_ERROR_MESSAGE_LENGTH,
            "MAX_LOG_MESSAGE_LENGTH": MAX_LOG_MESSAGE_LENGTH,
            "MAX_TAGS_COUNT": MAX_TAGS_COUNT,
            "MAX_LABELS_COUNT": MAX_LABELS_COUNT,
            "MAX_LABEL_LENGTH": MAX_LABEL_LENGTH,
        }

        for name, expected_value in expected.items():
            assert actual[name] == expected_value, (
                f"{name}: expected {expected_value}, got {actual[name]}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
