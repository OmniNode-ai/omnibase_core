"""Tests for EnumProviderType."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_provider_type import EnumProviderType


class TestEnumProviderType:
    """Test suite for EnumProviderType."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumProviderType.LOCAL == "local"
        assert EnumProviderType.EXTERNAL_TRUSTED == "external_trusted"
        assert EnumProviderType.EXTERNAL_UNTRUSTED == "external_untrusted"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumProviderType, str)
        assert issubclass(EnumProviderType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        provider = EnumProviderType.LOCAL
        assert isinstance(provider, str)
        assert provider == "local"
        assert len(provider) == 5

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumProviderType)
        assert len(values) == 3
        assert EnumProviderType.LOCAL in values
        assert EnumProviderType.EXTERNAL_UNTRUSTED in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumProviderType.EXTERNAL_TRUSTED in EnumProviderType
        assert "external_trusted" in [e.value for e in EnumProviderType]

    def test_enum_comparison(self):
        """Test enum comparison."""
        provider1 = EnumProviderType.LOCAL
        provider2 = EnumProviderType.LOCAL
        provider3 = EnumProviderType.EXTERNAL_TRUSTED

        assert provider1 == provider2
        assert provider1 != provider3
        assert provider1 == "local"

    def test_enum_serialization(self):
        """Test enum serialization."""
        provider = EnumProviderType.EXTERNAL_TRUSTED
        serialized = provider.value
        assert serialized == "external_trusted"
        json_str = json.dumps(provider)
        assert json_str == '"external_trusted"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        provider = EnumProviderType("local")
        assert provider == EnumProviderType.LOCAL

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumProviderType("invalid_provider")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {"local", "external_trusted", "external_untrusted"}
        actual_values = {e.value for e in EnumProviderType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumProviderType.__doc__ is not None
        assert "provider" in EnumProviderType.__doc__.lower()

    def test_provider_trust_levels(self):
        """Test provider trust level categorization."""
        # Local is most trusted
        local_provider = {EnumProviderType.LOCAL}
        # External providers with different trust levels
        external_providers = {
            EnumProviderType.EXTERNAL_TRUSTED,
            EnumProviderType.EXTERNAL_UNTRUSTED,
        }
        assert all(p in EnumProviderType for p in local_provider)
        assert all(p in EnumProviderType for p in external_providers)

    def test_all_providers_categorized(self):
        """Test that all providers can be categorized."""
        # Local providers
        local = {EnumProviderType.LOCAL}
        # External providers
        external = {
            EnumProviderType.EXTERNAL_TRUSTED,
            EnumProviderType.EXTERNAL_UNTRUSTED,
        }
        all_providers = local | external
        assert all_providers == set(EnumProviderType)
