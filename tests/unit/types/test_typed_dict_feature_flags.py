"""
Test suite for TypedDictFeatureFlags.
"""

from datetime import datetime

import pytest

from omnibase_core.types.typed_dict_feature_flags import TypedDictFeatureFlags


@pytest.mark.unit
class TestTypedDictFeatureFlags:
    """Test TypedDictFeatureFlags functionality."""

    def test_typed_dict_feature_flags_creation(self):
        """Test creating TypedDictFeatureFlags with required fields."""
        flags: TypedDictFeatureFlags = {
            "feature_name": "new_feature",
            "enabled": True,
            "environment": "production",
            "updated_at": datetime.now(),
            "updated_by": "admin",
        }

        assert flags["feature_name"] == "new_feature"
        assert flags["enabled"] is True
        assert flags["environment"] == "production"
        assert isinstance(flags["updated_at"], datetime)
        assert flags["updated_by"] == "admin"

    def test_typed_dict_feature_flags_with_description(self):
        """Test TypedDictFeatureFlags with optional description."""
        flags: TypedDictFeatureFlags = {
            "feature_name": "feature_with_description",
            "enabled": False,
            "environment": "staging",
            "updated_at": datetime(2024, 1, 15, 10, 30, 0),
            "updated_by": "developer",
            "description": "This is a test feature for demonstration",
        }

        assert flags["feature_name"] == "feature_with_description"
        assert flags["enabled"] is False
        assert flags["environment"] == "staging"
        assert flags["updated_at"] == datetime(2024, 1, 15, 10, 30, 0)
        assert flags["updated_by"] == "developer"
        assert flags["description"] == "This is a test feature for demonstration"

    def test_typed_dict_feature_flags_without_description(self):
        """Test TypedDictFeatureFlags without optional description."""
        flags: TypedDictFeatureFlags = {
            "feature_name": "feature_without_description",
            "enabled": True,
            "environment": "development",
            "updated_at": datetime.now(),
            "updated_by": "system",
        }

        assert flags["feature_name"] == "feature_without_description"
        assert flags["enabled"] is True
        assert "description" not in flags

    def test_typed_dict_feature_flags_boolean_states(self):
        """Test different boolean states for enabled field."""
        # Test enabled = True
        enabled_flags: TypedDictFeatureFlags = {
            "feature_name": "enabled_feature",
            "enabled": True,
            "environment": "production",
            "updated_at": datetime.now(),
            "updated_by": "admin",
        }
        assert enabled_flags["enabled"] is True

        # Test enabled = False
        disabled_flags: TypedDictFeatureFlags = {
            "feature_name": "disabled_feature",
            "enabled": False,
            "environment": "production",
            "updated_at": datetime.now(),
            "updated_by": "admin",
        }
        assert disabled_flags["enabled"] is False

    def test_typed_dict_feature_flags_environments(self):
        """Test different environment values."""
        environments = ["development", "staging", "production", "test", "local"]

        for env in environments:
            flags: TypedDictFeatureFlags = {
                "feature_name": f"feature_for_{env}",
                "enabled": True,
                "environment": env,
                "updated_at": datetime.now(),
                "updated_by": "admin",
            }
            assert flags["environment"] == env

    def test_typed_dict_feature_flags_updated_by_users(self):
        """Test different updated_by values."""
        users = ["admin", "developer", "system", "automation", "user123"]

        for user in users:
            flags: TypedDictFeatureFlags = {
                "feature_name": f"feature_updated_by_{user}",
                "enabled": True,
                "environment": "production",
                "updated_at": datetime.now(),
                "updated_by": user,
            }
            assert flags["updated_by"] == user

    def test_typed_dict_feature_flags_datetime_formats(self):
        """Test different datetime formats."""
        now = datetime.now()
        specific_time = datetime(2024, 12, 25, 15, 30, 45)
        iso_time = datetime.fromisoformat("2024-01-01T12:00:00")

        # Test with current time
        flags1: TypedDictFeatureFlags = {
            "feature_name": "current_time_feature",
            "enabled": True,
            "environment": "production",
            "updated_at": now,
            "updated_by": "admin",
        }
        assert flags1["updated_at"] == now

        # Test with specific time
        flags2: TypedDictFeatureFlags = {
            "feature_name": "specific_time_feature",
            "enabled": True,
            "environment": "production",
            "updated_at": specific_time,
            "updated_by": "admin",
        }
        assert flags2["updated_at"] == specific_time

        # Test with ISO time
        flags3: TypedDictFeatureFlags = {
            "feature_name": "iso_time_feature",
            "enabled": True,
            "environment": "production",
            "updated_at": iso_time,
            "updated_by": "admin",
        }
        assert flags3["updated_at"] == iso_time

    def test_typed_dict_feature_flags_long_strings(self):
        """Test with long string values."""
        long_name = "very_long_feature_name_" + "x" * 100
        long_environment = "very_long_environment_name_" + "y" * 50
        long_updated_by = "very_long_user_name_" + "z" * 30
        long_description = (
            "This is a very long description that contains a lot of text and should be handled properly by the system. "
            * 10
        )

        flags: TypedDictFeatureFlags = {
            "feature_name": long_name,
            "enabled": True,
            "environment": long_environment,
            "updated_at": datetime.now(),
            "updated_by": long_updated_by,
            "description": long_description,
        }

        assert flags["feature_name"] == long_name
        assert flags["environment"] == long_environment
        assert flags["updated_by"] == long_updated_by
        assert flags["description"] == long_description

    def test_typed_dict_feature_flags_special_characters(self):
        """Test with special characters in strings."""
        flags: TypedDictFeatureFlags = {
            "feature_name": "feature-with-special-chars_123",
            "enabled": True,
            "environment": "env@special#chars",
            "updated_at": datetime.now(),
            "updated_by": "user$with%special&chars",
            "description": "Description with special chars: !@#$%^&*()",
        }

        assert flags["feature_name"] == "feature-with-special-chars_123"
        assert flags["environment"] == "env@special#chars"
        assert flags["updated_by"] == "user$with%special&chars"
        assert flags["description"] == "Description with special chars: !@#$%^&*()"

    def test_typed_dict_feature_flags_unicode(self):
        """Test with unicode characters."""
        flags: TypedDictFeatureFlags = {
            "feature_name": "功能特性_测试",
            "enabled": True,
            "environment": "生产环境",
            "updated_at": datetime.now(),
            "updated_by": "管理员",
            "description": "这是一个测试功能的描述",
        }

        assert flags["feature_name"] == "功能特性_测试"
        assert flags["environment"] == "生产环境"
        assert flags["updated_by"] == "管理员"
        assert flags["description"] == "这是一个测试功能的描述"

    def test_typed_dict_feature_flags_type_annotations(self):
        """Test that all fields have correct type annotations."""
        flags: TypedDictFeatureFlags = {
            "feature_name": "type_test_feature",
            "enabled": True,
            "environment": "production",
            "updated_at": datetime.now(),
            "updated_by": "admin",
            "description": "Type testing feature",
        }

        assert isinstance(flags["feature_name"], str)
        assert isinstance(flags["enabled"], bool)
        assert isinstance(flags["environment"], str)
        assert isinstance(flags["updated_at"], datetime)
        assert isinstance(flags["updated_by"], str)
        assert isinstance(flags["description"], str)

    def test_typed_dict_feature_flags_mutability(self):
        """Test that TypedDictFeatureFlags behaves like a regular dict."""
        flags: TypedDictFeatureFlags = {
            "feature_name": "mutable_feature",
            "enabled": True,
            "environment": "production",
            "updated_at": datetime.now(),
            "updated_by": "admin",
        }

        # Should be able to modify like a regular dict
        flags["enabled"] = False
        flags["updated_by"] = "new_admin"
        flags["description"] = "Added description"

        assert flags["enabled"] is False
        assert flags["updated_by"] == "new_admin"
        assert flags["description"] == "Added description"

    def test_typed_dict_feature_flags_equality(self):
        """Test equality comparison between instances."""
        base_time = datetime(2024, 1, 1, 12, 0, 0)

        flags1: TypedDictFeatureFlags = {
            "feature_name": "equality_test",
            "enabled": True,
            "environment": "production",
            "updated_at": base_time,
            "updated_by": "admin",
        }

        flags2: TypedDictFeatureFlags = {
            "feature_name": "equality_test",
            "enabled": True,
            "environment": "production",
            "updated_at": base_time,
            "updated_by": "admin",
        }

        assert flags1 == flags2

        # Modify one field
        flags2["enabled"] = False
        assert flags1 != flags2

    def test_typed_dict_feature_flags_edge_cases(self):
        """Test edge cases for feature flags."""
        # Test with empty strings
        flags: TypedDictFeatureFlags = {
            "feature_name": "",
            "enabled": False,
            "environment": "",
            "updated_at": datetime.min,
            "updated_by": "",
        }

        assert flags["feature_name"] == ""
        assert flags["enabled"] is False
        assert flags["environment"] == ""
        assert flags["updated_at"] == datetime.min
        assert flags["updated_by"] == ""
