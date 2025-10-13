"""Tests for EnumPermissionScope."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_permission_scope import EnumPermissionScope


class TestEnumPermissionScope:
    """Test suite for EnumPermissionScope."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumPermissionScope.GLOBAL == "global"
        assert EnumPermissionScope.ORGANIZATION == "organization"
        assert EnumPermissionScope.PROJECT == "project"
        assert EnumPermissionScope.TEAM == "team"
        assert EnumPermissionScope.USER == "user"
        assert EnumPermissionScope.SERVICE == "service"
        assert EnumPermissionScope.RESOURCE == "resource"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumPermissionScope, str)
        assert issubclass(EnumPermissionScope, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        scope = EnumPermissionScope.PROJECT
        assert isinstance(scope, str)
        assert scope == "project"
        assert len(scope) == 7

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumPermissionScope)
        assert len(values) == 7
        assert EnumPermissionScope.GLOBAL in values
        assert EnumPermissionScope.RESOURCE in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumPermissionScope.TEAM in EnumPermissionScope
        assert "team" in [e.value for e in EnumPermissionScope]

    def test_enum_comparison(self):
        """Test enum comparison."""
        scope1 = EnumPermissionScope.ORGANIZATION
        scope2 = EnumPermissionScope.ORGANIZATION
        scope3 = EnumPermissionScope.USER

        assert scope1 == scope2
        assert scope1 != scope3
        assert scope1 == "organization"

    def test_enum_serialization(self):
        """Test enum serialization."""
        scope = EnumPermissionScope.SERVICE
        serialized = scope.value
        assert serialized == "service"
        json_str = json.dumps(scope)
        assert json_str == '"service"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        scope = EnumPermissionScope("project")
        assert scope == EnumPermissionScope.PROJECT

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumPermissionScope("invalid_scope")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "global",
            "organization",
            "project",
            "team",
            "user",
            "service",
            "resource",
        }
        actual_values = {e.value for e in EnumPermissionScope}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumPermissionScope.__doc__ is not None
        assert "permission" in EnumPermissionScope.__doc__.lower()

    def test_organizational_hierarchy(self):
        """Test organizational hierarchy scopes."""
        hierarchy_scopes = {
            EnumPermissionScope.GLOBAL,
            EnumPermissionScope.ORGANIZATION,
            EnumPermissionScope.PROJECT,
            EnumPermissionScope.TEAM,
        }
        assert all(scope in EnumPermissionScope for scope in hierarchy_scopes)

    def test_entity_scopes(self):
        """Test entity-level scopes."""
        entity_scopes = {
            EnumPermissionScope.USER,
            EnumPermissionScope.SERVICE,
            EnumPermissionScope.RESOURCE,
        }
        assert all(scope in EnumPermissionScope for scope in entity_scopes)

    def test_scope_hierarchy_ordering(self):
        """Test logical ordering from broadest to narrowest scope."""
        # From broadest to narrowest in organizational hierarchy
        hierarchy_order = [
            EnumPermissionScope.GLOBAL,
            EnumPermissionScope.ORGANIZATION,
            EnumPermissionScope.PROJECT,
            EnumPermissionScope.TEAM,
        ]
        # All should be valid enum values
        assert all(scope in EnumPermissionScope for scope in hierarchy_order)

    def test_all_scopes_categorized(self):
        """Test that all scopes are properly categorized."""
        # Organizational hierarchy
        org_hierarchy = {
            EnumPermissionScope.GLOBAL,
            EnumPermissionScope.ORGANIZATION,
            EnumPermissionScope.PROJECT,
            EnumPermissionScope.TEAM,
        }

        # Entity-level
        entities = {
            EnumPermissionScope.USER,
            EnumPermissionScope.SERVICE,
            EnumPermissionScope.RESOURCE,
        }

        # All scopes should be categorized
        all_scopes = org_hierarchy | entities
        assert all_scopes == set(EnumPermissionScope)
