"""Tests for enum_kv_operation_type.py"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_kv_operation_type import EnumKVOperationType


class TestEnumKVOperationType:
    """Test cases for EnumKVOperationType"""

    def test_enum_values(self):
        """Test that all enum values are correct"""
        assert EnumKVOperationType.CREATE == "create"
        assert EnumKVOperationType.READ == "read"
        assert EnumKVOperationType.UPDATE == "update"
        assert EnumKVOperationType.DELETE == "delete"
        assert EnumKVOperationType.LIST == "list[Any]"
        assert EnumKVOperationType.WATCH == "watch"
        assert EnumKVOperationType.SYNC == "sync"
        assert EnumKVOperationType.BACKUP == "backup"
        assert EnumKVOperationType.RESTORE == "restore"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum"""
        assert issubclass(EnumKVOperationType, str)
        assert issubclass(EnumKVOperationType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values"""
        assert EnumKVOperationType.CREATE == "create"
        assert EnumKVOperationType.READ == "read"
        assert EnumKVOperationType.LIST == "list[Any]"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values"""
        values = list(EnumKVOperationType)
        assert len(values) == 9
        assert EnumKVOperationType.CREATE in values
        assert EnumKVOperationType.RESTORE in values

    def test_enum_membership(self):
        """Test membership testing"""
        assert EnumKVOperationType.CREATE in EnumKVOperationType
        assert "create" in EnumKVOperationType
        assert "invalid_value" not in EnumKVOperationType

    def test_enum_comparison(self):
        """Test enum comparison"""
        assert EnumKVOperationType.CREATE == EnumKVOperationType.CREATE
        assert EnumKVOperationType.READ != EnumKVOperationType.CREATE
        assert EnumKVOperationType.CREATE == "create"

    def test_enum_serialization(self):
        """Test enum serialization"""
        assert EnumKVOperationType.CREATE.value == "create"
        assert EnumKVOperationType.READ.value == "read"

    def test_enum_deserialization(self):
        """Test enum deserialization"""
        assert EnumKVOperationType("create") == EnumKVOperationType.CREATE
        assert EnumKVOperationType("read") == EnumKVOperationType.READ

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError"""
        with pytest.raises(ValueError):
            EnumKVOperationType("invalid_value")

        with pytest.raises(ValueError):
            EnumKVOperationType("")

    def test_enum_all_values(self):
        """Test that all expected values are present"""
        expected_values = {
            "create",
            "read",
            "update",
            "delete",
            "list[Any]",
            "watch",
            "sync",
            "backup",
            "restore",
        }
        actual_values = {member.value for member in EnumKVOperationType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring"""
        assert "Canonical KV operation types" in EnumKVOperationType.__doc__

    def test_enum_crud_operations(self):
        """Test CRUD operations"""
        crud_ops = {
            EnumKVOperationType.CREATE,
            EnumKVOperationType.READ,
            EnumKVOperationType.UPDATE,
            EnumKVOperationType.DELETE,
        }

        for op in crud_ops:
            assert op in EnumKVOperationType

    def test_enum_list_operations(self):
        """Test list operations"""
        assert EnumKVOperationType.LIST.value == "list[Any]"
        assert EnumKVOperationType.LIST in EnumKVOperationType

    def test_enum_watch_operations(self):
        """Test watch operations"""
        assert EnumKVOperationType.WATCH.value == "watch"
        assert EnumKVOperationType.WATCH in EnumKVOperationType

    def test_enum_sync_operations(self):
        """Test sync operations"""
        assert EnumKVOperationType.SYNC.value == "sync"
        assert EnumKVOperationType.SYNC in EnumKVOperationType

    def test_enum_backup_operations(self):
        """Test backup operations"""
        assert EnumKVOperationType.BACKUP.value == "backup"
        assert EnumKVOperationType.RESTORE.value == "restore"
        assert EnumKVOperationType.BACKUP in EnumKVOperationType
        assert EnumKVOperationType.RESTORE in EnumKVOperationType

    def test_enum_operation_categories(self):
        """Test operation categories"""
        # Basic CRUD operations
        basic_ops = {
            EnumKVOperationType.CREATE,
            EnumKVOperationType.READ,
            EnumKVOperationType.UPDATE,
            EnumKVOperationType.DELETE,
        }

        # Advanced operations
        advanced_ops = {
            EnumKVOperationType.LIST,
            EnumKVOperationType.WATCH,
            EnumKVOperationType.SYNC,
        }

        # Maintenance operations
        maintenance_ops = {EnumKVOperationType.BACKUP, EnumKVOperationType.RESTORE}

        all_ops = set(EnumKVOperationType)
        assert basic_ops.union(advanced_ops).union(maintenance_ops) == all_ops
