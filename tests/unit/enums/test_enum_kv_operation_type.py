"""Tests for enum_kv_operation_type.py"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_kv_operation_type import EnumKvOperationType


class TestEnumKVOperationType:
    """Test cases for EnumKvOperationType"""

    def test_enum_values(self):
        """Test that all enum values are correct"""
        assert EnumKvOperationType.CREATE == "create"
        assert EnumKvOperationType.READ == "read"
        assert EnumKvOperationType.UPDATE == "update"
        assert EnumKvOperationType.DELETE == "delete"
        assert EnumKvOperationType.LIST == "list[Any]"
        assert EnumKvOperationType.WATCH == "watch"
        assert EnumKvOperationType.SYNC == "sync"
        assert EnumKvOperationType.BACKUP == "backup"
        assert EnumKvOperationType.RESTORE == "restore"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum"""
        assert issubclass(EnumKvOperationType, str)
        assert issubclass(EnumKvOperationType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values"""
        assert EnumKvOperationType.CREATE == "create"
        assert EnumKvOperationType.READ == "read"
        assert EnumKvOperationType.LIST == "list[Any]"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values"""
        values = list(EnumKvOperationType)
        assert len(values) == 9
        assert EnumKvOperationType.CREATE in values
        assert EnumKvOperationType.RESTORE in values

    def test_enum_membership(self):
        """Test membership testing"""
        assert EnumKvOperationType.CREATE in EnumKvOperationType
        assert "create" in EnumKvOperationType
        assert "invalid_value" not in EnumKvOperationType

    def test_enum_comparison(self):
        """Test enum comparison"""
        assert EnumKvOperationType.CREATE == EnumKvOperationType.CREATE
        assert EnumKvOperationType.READ != EnumKvOperationType.CREATE
        assert EnumKvOperationType.CREATE == "create"

    def test_enum_serialization(self):
        """Test enum serialization"""
        assert EnumKvOperationType.CREATE.value == "create"
        assert EnumKvOperationType.READ.value == "read"

    def test_enum_deserialization(self):
        """Test enum deserialization"""
        assert EnumKvOperationType("create") == EnumKvOperationType.CREATE
        assert EnumKvOperationType("read") == EnumKvOperationType.READ

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError"""
        with pytest.raises(ValueError):
            EnumKvOperationType("invalid_value")

        with pytest.raises(ValueError):
            EnumKvOperationType("")

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
        actual_values = {member.value for member in EnumKvOperationType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring"""
        assert "Canonical KV operation types" in EnumKvOperationType.__doc__

    def test_enum_crud_operations(self):
        """Test CRUD operations"""
        crud_ops = {
            EnumKvOperationType.CREATE,
            EnumKvOperationType.READ,
            EnumKvOperationType.UPDATE,
            EnumKvOperationType.DELETE,
        }

        for op in crud_ops:
            assert op in EnumKvOperationType

    def test_enum_list_operations(self):
        """Test list operations"""
        assert EnumKvOperationType.LIST.value == "list[Any]"
        assert EnumKvOperationType.LIST in EnumKvOperationType

    def test_enum_watch_operations(self):
        """Test watch operations"""
        assert EnumKvOperationType.WATCH.value == "watch"
        assert EnumKvOperationType.WATCH in EnumKvOperationType

    def test_enum_sync_operations(self):
        """Test sync operations"""
        assert EnumKvOperationType.SYNC.value == "sync"
        assert EnumKvOperationType.SYNC in EnumKvOperationType

    def test_enum_backup_operations(self):
        """Test backup operations"""
        assert EnumKvOperationType.BACKUP.value == "backup"
        assert EnumKvOperationType.RESTORE.value == "restore"
        assert EnumKvOperationType.BACKUP in EnumKvOperationType
        assert EnumKvOperationType.RESTORE in EnumKvOperationType

    def test_enum_operation_categories(self):
        """Test operation categories"""
        # Basic CRUD operations
        basic_ops = {
            EnumKvOperationType.CREATE,
            EnumKvOperationType.READ,
            EnumKvOperationType.UPDATE,
            EnumKvOperationType.DELETE,
        }

        # Advanced operations
        advanced_ops = {
            EnumKvOperationType.LIST,
            EnumKvOperationType.WATCH,
            EnumKvOperationType.SYNC,
        }

        # Maintenance operations
        maintenance_ops = {EnumKvOperationType.BACKUP, EnumKvOperationType.RESTORE}

        all_ops = set(EnumKvOperationType)
        assert basic_ops.union(advanced_ops).union(maintenance_ops) == all_ops
