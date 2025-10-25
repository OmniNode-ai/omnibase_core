"""Unit tests for EnumAuthenticationMethod."""

import pytest

from omnibase_core.enums.enum_authentication_method import EnumAuthenticationMethod


class TestEnumAuthenticationMethod:
    """Test suite for EnumAuthenticationMethod enumeration."""

    def test_enum_values(self) -> None:
        """Test that all authentication methods are defined."""
        assert EnumAuthenticationMethod.NONE.value == "none"
        assert EnumAuthenticationMethod.BASIC.value == "basic"
        assert EnumAuthenticationMethod.TOKEN.value == "token"
        assert EnumAuthenticationMethod.CERTIFICATE.value == "certificate"
        assert EnumAuthenticationMethod.MULTI_FACTOR.value == "multi_factor"

    def test_enum_count(self) -> None:
        """Test that enum has exactly 5 members."""
        members = list(EnumAuthenticationMethod)
        assert len(members) == 5

    def test_string_enum_behavior(self) -> None:
        """Test that enum inherits from str."""
        assert isinstance(EnumAuthenticationMethod.BASIC, str)
        assert EnumAuthenticationMethod.TOKEN == "token"

    def test_enum_comparison(self) -> None:
        """Test enum member equality."""
        method1 = EnumAuthenticationMethod.BASIC
        method2 = EnumAuthenticationMethod.BASIC
        method3 = EnumAuthenticationMethod.TOKEN

        assert method1 == method2
        assert method1 != method3
        assert method1 is method2

    def test_enum_in_collection(self) -> None:
        """Test enum usage in collections."""
        methods = {EnumAuthenticationMethod.BASIC, EnumAuthenticationMethod.TOKEN}
        assert EnumAuthenticationMethod.BASIC in methods
        assert EnumAuthenticationMethod.CERTIFICATE not in methods

    def test_enum_iteration(self) -> None:
        """Test iterating over enum members."""
        methods = list(EnumAuthenticationMethod)
        assert EnumAuthenticationMethod.NONE in methods
        assert EnumAuthenticationMethod.MULTI_FACTOR in methods
        assert len(methods) == 5

    def test_enum_membership_check(self) -> None:
        """Test membership checks."""
        assert "basic" in [e.value for e in EnumAuthenticationMethod]
        assert "invalid" not in [e.value for e in EnumAuthenticationMethod]

    def test_enum_string_representation(self) -> None:
        """Test string representation."""
        # str() returns the enum name, not value (even though it inherits from str)
        assert str(EnumAuthenticationMethod.TOKEN) == "EnumAuthenticationMethod.TOKEN"
        assert (
            repr(EnumAuthenticationMethod.BASIC)
            == "<EnumAuthenticationMethod.BASIC: 'basic'>"
        )
        # The value itself equals the string
        assert EnumAuthenticationMethod.TOKEN == "token"

    def test_enum_value_uniqueness(self) -> None:
        """Test that all enum values are unique."""
        values = [e.value for e in EnumAuthenticationMethod]
        assert len(values) == len(set(values))
