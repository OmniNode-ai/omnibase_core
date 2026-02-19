# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for EnumPermissionAction."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_permission_action import EnumPermissionAction


@pytest.mark.unit
class TestEnumPermissionAction:
    """Test suite for EnumPermissionAction."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumPermissionAction.CREATE == "create"
        assert EnumPermissionAction.READ == "read"
        assert EnumPermissionAction.UPDATE == "update"
        assert EnumPermissionAction.DELETE == "delete"
        assert EnumPermissionAction.EXECUTE == "execute"
        assert EnumPermissionAction.APPROVE == "approve"
        assert EnumPermissionAction.DENY == "deny"
        assert EnumPermissionAction.ADMIN == "admin"
        assert EnumPermissionAction.VIEW == "view"
        assert EnumPermissionAction.EDIT == "edit"
        assert EnumPermissionAction.SHARE == "share"
        assert EnumPermissionAction.EXPORT == "export"
        assert EnumPermissionAction.IMPORT == "import"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumPermissionAction, str)
        assert issubclass(EnumPermissionAction, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        action = EnumPermissionAction.CREATE
        assert isinstance(action, str)
        assert action == "create"
        assert len(action) == 6

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumPermissionAction)
        assert len(values) == 13
        assert EnumPermissionAction.CREATE in values
        assert EnumPermissionAction.ADMIN in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumPermissionAction.READ in EnumPermissionAction
        assert "read" in [e.value for e in EnumPermissionAction]

    def test_enum_comparison(self):
        """Test enum comparison."""
        action1 = EnumPermissionAction.UPDATE
        action2 = EnumPermissionAction.UPDATE
        action3 = EnumPermissionAction.DELETE

        assert action1 == action2
        assert action1 != action3
        assert action1 == "update"

    def test_enum_serialization(self):
        """Test enum serialization."""
        action = EnumPermissionAction.APPROVE
        serialized = action.value
        assert serialized == "approve"
        json_str = json.dumps(action)
        assert json_str == '"approve"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        action = EnumPermissionAction("execute")
        assert action == EnumPermissionAction.EXECUTE

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumPermissionAction("invalid_action")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "create",
            "read",
            "update",
            "delete",
            "execute",
            "approve",
            "deny",
            "admin",
            "view",
            "edit",
            "share",
            "export",
            "import",
        }
        actual_values = {e.value for e in EnumPermissionAction}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumPermissionAction.__doc__ is not None
        assert "permission" in EnumPermissionAction.__doc__.lower()

    def test_crud_operations(self):
        """Test CRUD operations grouping."""
        crud_actions = {
            EnumPermissionAction.CREATE,
            EnumPermissionAction.READ,
            EnumPermissionAction.UPDATE,
            EnumPermissionAction.DELETE,
        }
        assert all(action in EnumPermissionAction for action in crud_actions)

    def test_administrative_actions(self):
        """Test administrative actions."""
        admin_actions = {
            EnumPermissionAction.ADMIN,
            EnumPermissionAction.APPROVE,
            EnumPermissionAction.DENY,
        }
        assert all(action in EnumPermissionAction for action in admin_actions)

    def test_data_actions(self):
        """Test data manipulation actions."""
        data_actions = {
            EnumPermissionAction.EXPORT,
            EnumPermissionAction.IMPORT,
            EnumPermissionAction.SHARE,
        }
        assert all(action in EnumPermissionAction for action in data_actions)

    def test_viewing_actions(self):
        """Test viewing and editing actions."""
        view_actions = {
            EnumPermissionAction.VIEW,
            EnumPermissionAction.EDIT,
        }
        assert all(action in EnumPermissionAction for action in view_actions)

    def test_action_semantic_grouping(self):
        """Test semantic grouping of all actions."""
        # CRUD operations
        crud = {
            EnumPermissionAction.CREATE,
            EnumPermissionAction.READ,
            EnumPermissionAction.UPDATE,
            EnumPermissionAction.DELETE,
        }

        # Administrative
        admin = {
            EnumPermissionAction.ADMIN,
            EnumPermissionAction.APPROVE,
            EnumPermissionAction.DENY,
        }

        # Execution
        execution = {EnumPermissionAction.EXECUTE}

        # Data operations
        data_ops = {
            EnumPermissionAction.EXPORT,
            EnumPermissionAction.IMPORT,
            EnumPermissionAction.SHARE,
        }

        # View operations
        view_ops = {
            EnumPermissionAction.VIEW,
            EnumPermissionAction.EDIT,
        }

        all_grouped = crud | admin | execution | data_ops | view_ops
        assert all_grouped == set(EnumPermissionAction)
