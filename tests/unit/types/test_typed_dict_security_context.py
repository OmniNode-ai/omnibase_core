"""
Test suite for TypedDictSecurityContext.
"""

from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest

from omnibase_core.types.typed_dict_security_context import TypedDictSecurityContext


@pytest.mark.unit
class TestTypedDictSecurityContext:
    """Test TypedDictSecurityContext functionality."""

    def test_typed_dict_security_context_creation(self):
        """Test creating TypedDictSecurityContext with all required fields."""
        user_id = uuid4()
        session_id = uuid4()
        now = datetime.now()

        context: TypedDictSecurityContext = {
            "user_id": user_id,
            "session_id": session_id,
            "permissions": ["read", "write", "admin"],
            "roles": ["user", "admin"],
            "authenticated_at": now,
        }

        assert context["user_id"] == user_id
        assert context["session_id"] == session_id
        assert context["permissions"] == ["read", "write", "admin"]
        assert context["roles"] == ["user", "admin"]
        assert context["authenticated_at"] == now

    def test_typed_dict_security_context_with_expires_at(self):
        """Test TypedDictSecurityContext with optional expires_at field."""
        user_id = uuid4()
        session_id = uuid4()
        now = datetime.now()
        expires_at = now + timedelta(hours=1)

        context: TypedDictSecurityContext = {
            "user_id": user_id,
            "session_id": session_id,
            "permissions": ["read"],
            "roles": ["user"],
            "authenticated_at": now,
            "expires_at": expires_at,
        }

        assert context["user_id"] == user_id
        assert context["session_id"] == session_id
        assert context["expires_at"] == expires_at
        assert context["authenticated_at"] < context["expires_at"]

    def test_typed_dict_security_context_field_types(self):
        """Test that all fields have correct types."""
        user_id = uuid4()
        session_id = uuid4()
        now = datetime.now()

        context: TypedDictSecurityContext = {
            "user_id": user_id,
            "session_id": session_id,
            "permissions": ["read", "write"],
            "roles": ["user"],
            "authenticated_at": now,
        }

        assert isinstance(context["user_id"], UUID)
        assert isinstance(context["session_id"], UUID)
        assert isinstance(context["permissions"], list)
        assert isinstance(context["roles"], list)
        assert isinstance(context["authenticated_at"], datetime)

    def test_typed_dict_security_context_empty_permissions(self):
        """Test TypedDictSecurityContext with empty permissions."""
        user_id = uuid4()
        session_id = uuid4()
        now = datetime.now()

        context: TypedDictSecurityContext = {
            "user_id": user_id,
            "session_id": session_id,
            "permissions": [],
            "roles": ["guest"],
            "authenticated_at": now,
        }

        assert context["permissions"] == []
        assert len(context["permissions"]) == 0

    def test_typed_dict_security_context_empty_roles(self):
        """Test TypedDictSecurityContext with empty roles."""
        user_id = uuid4()
        session_id = uuid4()
        now = datetime.now()

        context: TypedDictSecurityContext = {
            "user_id": user_id,
            "session_id": session_id,
            "permissions": ["read"],
            "roles": [],
            "authenticated_at": now,
        }

        assert context["roles"] == []
        assert len(context["roles"]) == 0

    def test_typed_dict_security_context_multiple_permissions(self):
        """Test TypedDictSecurityContext with multiple permissions."""
        user_id = uuid4()
        session_id = uuid4()
        now = datetime.now()

        permissions = [
            "read",
            "write",
            "delete",
            "admin",
            "superuser",
            "api_access",
            "database_access",
            "file_access",
        ]

        context: TypedDictSecurityContext = {
            "user_id": user_id,
            "session_id": session_id,
            "permissions": permissions,
            "roles": ["admin", "superuser"],
            "authenticated_at": now,
        }

        assert len(context["permissions"]) == 8
        assert "read" in context["permissions"]
        assert "admin" in context["permissions"]
        assert "superuser" in context["permissions"]

    def test_typed_dict_security_context_multiple_roles(self):
        """Test TypedDictSecurityContext with multiple roles."""
        user_id = uuid4()
        session_id = uuid4()
        now = datetime.now()

        roles = ["user", "admin", "moderator", "developer", "tester"]

        context: TypedDictSecurityContext = {
            "user_id": user_id,
            "session_id": session_id,
            "permissions": ["read", "write"],
            "roles": roles,
            "authenticated_at": now,
        }

        assert len(context["roles"]) == 5
        assert "user" in context["roles"]
        assert "admin" in context["roles"]
        assert "developer" in context["roles"]

    def test_typed_dict_security_context_session_expiry(self):
        """Test TypedDictSecurityContext with session expiry scenarios."""
        user_id = uuid4()
        session_id = uuid4()
        now = datetime.now()

        # Short session (1 hour)
        short_expiry = now + timedelta(hours=1)
        context_short: TypedDictSecurityContext = {
            "user_id": user_id,
            "session_id": session_id,
            "permissions": ["read"],
            "roles": ["user"],
            "authenticated_at": now,
            "expires_at": short_expiry,
        }

        # Long session (24 hours)
        long_expiry = now + timedelta(hours=24)
        context_long: TypedDictSecurityContext = {
            "user_id": user_id,
            "session_id": session_id,
            "permissions": ["read", "write"],
            "roles": ["user", "admin"],
            "authenticated_at": now,
            "expires_at": long_expiry,
        }

        assert context_short["expires_at"] == short_expiry
        assert context_long["expires_at"] == long_expiry
        assert context_short["expires_at"] < context_long["expires_at"]

    def test_typed_dict_security_context_different_users(self):
        """Test TypedDictSecurityContext with different user scenarios."""
        user1_id = uuid4()
        user2_id = uuid4()
        session1_id = uuid4()
        session2_id = uuid4()
        now = datetime.now()

        # Admin user
        admin_context: TypedDictSecurityContext = {
            "user_id": user1_id,
            "session_id": session1_id,
            "permissions": ["read", "write", "delete", "admin"],
            "roles": ["admin", "superuser"],
            "authenticated_at": now,
        }

        # Regular user
        user_context: TypedDictSecurityContext = {
            "user_id": user2_id,
            "session_id": session2_id,
            "permissions": ["read"],
            "roles": ["user"],
            "authenticated_at": now,
        }

        assert admin_context["user_id"] != user_context["user_id"]
        assert admin_context["session_id"] != user_context["session_id"]
        assert len(admin_context["permissions"]) > len(user_context["permissions"])
        assert "admin" in admin_context["roles"]
        assert "admin" not in user_context["roles"]

    def test_typed_dict_security_context_authentication_timing(self):
        """Test TypedDictSecurityContext with different authentication times."""
        user_id = uuid4()
        session_id = uuid4()

        # Recent authentication
        recent_auth = datetime.now()
        recent_context: TypedDictSecurityContext = {
            "user_id": user_id,
            "session_id": session_id,
            "permissions": ["read"],
            "roles": ["user"],
            "authenticated_at": recent_auth,
        }

        # Historical authentication
        historical_auth = datetime(2024, 1, 1, 12, 0, 0)
        historical_context: TypedDictSecurityContext = {
            "user_id": user_id,
            "session_id": session_id,
            "permissions": ["read"],
            "roles": ["user"],
            "authenticated_at": historical_auth,
        }

        assert recent_context["authenticated_at"] == recent_auth
        assert historical_context["authenticated_at"] == historical_auth
        assert (
            recent_context["authenticated_at"] > historical_context["authenticated_at"]
        )

    def test_typed_dict_security_context_permission_combinations(self):
        """Test TypedDictSecurityContext with different permission combinations."""
        user_id = uuid4()
        session_id = uuid4()
        now = datetime.now()

        # Read-only user
        read_only_context: TypedDictSecurityContext = {
            "user_id": user_id,
            "session_id": session_id,
            "permissions": ["read"],
            "roles": ["viewer"],
            "authenticated_at": now,
        }

        # Read-write user
        read_write_context: TypedDictSecurityContext = {
            "user_id": user_id,
            "session_id": session_id,
            "permissions": ["read", "write"],
            "roles": ["editor"],
            "authenticated_at": now,
        }

        # Full access user
        full_access_context: TypedDictSecurityContext = {
            "user_id": user_id,
            "session_id": session_id,
            "permissions": ["read", "write", "delete", "admin"],
            "roles": ["admin", "owner"],
            "authenticated_at": now,
        }

        assert len(read_only_context["permissions"]) == 1
        assert len(read_write_context["permissions"]) == 2
        assert len(full_access_context["permissions"]) == 4
        assert "read" in read_only_context["permissions"]
        assert "write" in read_write_context["permissions"]
        assert "admin" in full_access_context["permissions"]
