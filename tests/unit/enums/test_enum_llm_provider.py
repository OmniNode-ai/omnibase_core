"""Tests for enum_llm_provider.py"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_llm_provider import EnumLLMProvider


class TestEnumLLMProvider:
    """Test cases for EnumLLMProvider"""

    def test_enum_values(self):
        """Test that all enum values are correct"""
        assert EnumLLMProvider.CLAUDE == "claude"
        assert EnumLLMProvider.OLLAMA == "ollama"
        assert EnumLLMProvider.OPENAI == "openai"
        assert EnumLLMProvider.GEMINI == "gemini"
        assert EnumLLMProvider.ANTHROPIC == "anthropic"
        assert EnumLLMProvider.LOCAL == "local"
        assert EnumLLMProvider.LITELLM == "litellm"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum"""
        assert issubclass(EnumLLMProvider, str)
        assert issubclass(EnumLLMProvider, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values"""
        assert EnumLLMProvider.CLAUDE == "claude"
        assert EnumLLMProvider.OPENAI == "openai"
        assert EnumLLMProvider.GEMINI == "gemini"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values"""
        values = list(EnumLLMProvider)
        assert len(values) == 7
        assert EnumLLMProvider.CLAUDE in values
        assert EnumLLMProvider.LITELLM in values

    def test_enum_membership(self):
        """Test membership testing"""
        assert EnumLLMProvider.CLAUDE in EnumLLMProvider
        assert "claude" in EnumLLMProvider
        assert "invalid_value" not in EnumLLMProvider

    def test_enum_comparison(self):
        """Test enum comparison"""
        assert EnumLLMProvider.CLAUDE == EnumLLMProvider.CLAUDE
        assert EnumLLMProvider.OPENAI != EnumLLMProvider.CLAUDE
        assert EnumLLMProvider.CLAUDE == "claude"

    def test_enum_serialization(self):
        """Test enum serialization"""
        assert EnumLLMProvider.CLAUDE.value == "claude"
        assert EnumLLMProvider.OPENAI.value == "openai"

    def test_enum_deserialization(self):
        """Test enum deserialization"""
        assert EnumLLMProvider("claude") == EnumLLMProvider.CLAUDE
        assert EnumLLMProvider("openai") == EnumLLMProvider.OPENAI

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError"""
        with pytest.raises(ValueError):
            EnumLLMProvider("invalid_value")

        with pytest.raises(ValueError):
            EnumLLMProvider("")

    def test_enum_all_values(self):
        """Test that all expected values are present"""
        expected_values = {
            "claude",
            "ollama",
            "openai",
            "gemini",
            "anthropic",
            "local",
            "litellm",
        }
        actual_values = {member.value for member in EnumLLMProvider}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring"""
        assert "Supported LLM providers" in EnumLLMProvider.__doc__

    def test_enum_provider_categories(self):
        """Test specific provider categories"""
        # Commercial providers
        assert EnumLLMProvider.CLAUDE.value == "claude"
        assert EnumLLMProvider.OPENAI.value == "openai"
        assert EnumLLMProvider.GEMINI.value == "gemini"
        assert EnumLLMProvider.ANTHROPIC.value == "anthropic"

        # Local providers
        assert EnumLLMProvider.OLLAMA.value == "ollama"
        assert EnumLLMProvider.LOCAL.value == "local"
        assert EnumLLMProvider.LITELLM.value == "litellm"

    def test_is_local_method(self):
        """Test the is_local method"""
        # Local providers
        assert EnumLLMProvider.OLLAMA.is_local() is True
        assert EnumLLMProvider.LOCAL.is_local() is True
        assert EnumLLMProvider.LITELLM.is_local() is True

        # Non-local providers
        assert EnumLLMProvider.CLAUDE.is_local() is False
        assert EnumLLMProvider.OPENAI.is_local() is False
        assert EnumLLMProvider.GEMINI.is_local() is False
        assert EnumLLMProvider.ANTHROPIC.is_local() is False

    def test_requires_api_key_method(self):
        """Test the requires_api_key method"""
        # Providers that require API keys
        assert EnumLLMProvider.CLAUDE.requires_api_key() is True
        assert EnumLLMProvider.OPENAI.requires_api_key() is True
        assert EnumLLMProvider.GEMINI.requires_api_key() is True
        assert EnumLLMProvider.ANTHROPIC.requires_api_key() is True

        # Providers that don't require API keys
        assert EnumLLMProvider.OLLAMA.requires_api_key() is False
        assert EnumLLMProvider.LOCAL.requires_api_key() is False
        assert EnumLLMProvider.LITELLM.requires_api_key() is False

    def test_enum_provider_types(self):
        """Test provider type categorization"""
        # Commercial API providers
        commercial_providers = {
            EnumLLMProvider.CLAUDE,
            EnumLLMProvider.OPENAI,
            EnumLLMProvider.GEMINI,
            EnumLLMProvider.ANTHROPIC,
        }

        # Local/self-hosted providers
        local_providers = {
            EnumLLMProvider.OLLAMA,
            EnumLLMProvider.LOCAL,
            EnumLLMProvider.LITELLM,
        }

        all_providers = set(EnumLLMProvider)
        assert commercial_providers.union(local_providers) == all_providers

        # Verify all commercial providers require API keys
        for provider in commercial_providers:
            assert provider.requires_api_key() is True

        # Verify all local providers don't require API keys
        for provider in local_providers:
            assert provider.requires_api_key() is False
