"""Tests for enum_llm_provider.py"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_llm_provider import EnumLlmProvider


class TestEnumLLMProvider:
    """Test cases for EnumLlmProvider"""

    def test_enum_values(self):
        """Test that all enum values are correct"""
        assert EnumLlmProvider.CLAUDE == "claude"
        assert EnumLlmProvider.OLLAMA == "ollama"
        assert EnumLlmProvider.OPENAI == "openai"
        assert EnumLlmProvider.GEMINI == "gemini"
        assert EnumLlmProvider.ANTHROPIC == "anthropic"
        assert EnumLlmProvider.LOCAL == "local"
        assert EnumLlmProvider.LITELLM == "litellm"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum"""
        assert issubclass(EnumLlmProvider, str)
        assert issubclass(EnumLlmProvider, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values"""
        assert EnumLlmProvider.CLAUDE == "claude"
        assert EnumLlmProvider.OPENAI == "openai"
        assert EnumLlmProvider.GEMINI == "gemini"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values"""
        values = list(EnumLlmProvider)
        assert len(values) == 7
        assert EnumLlmProvider.CLAUDE in values
        assert EnumLlmProvider.LITELLM in values

    def test_enum_membership(self):
        """Test membership testing"""
        assert EnumLlmProvider.CLAUDE in EnumLlmProvider
        assert "claude" in EnumLlmProvider
        assert "invalid_value" not in EnumLlmProvider

    def test_enum_comparison(self):
        """Test enum comparison"""
        assert EnumLlmProvider.CLAUDE == EnumLlmProvider.CLAUDE
        assert EnumLlmProvider.OPENAI != EnumLlmProvider.CLAUDE
        assert EnumLlmProvider.CLAUDE == "claude"

    def test_enum_serialization(self):
        """Test enum serialization"""
        assert EnumLlmProvider.CLAUDE.value == "claude"
        assert EnumLlmProvider.OPENAI.value == "openai"

    def test_enum_deserialization(self):
        """Test enum deserialization"""
        assert EnumLlmProvider("claude") == EnumLlmProvider.CLAUDE
        assert EnumLlmProvider("openai") == EnumLlmProvider.OPENAI

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError"""
        with pytest.raises(ValueError):
            EnumLlmProvider("invalid_value")

        with pytest.raises(ValueError):
            EnumLlmProvider("")

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
        actual_values = {member.value for member in EnumLlmProvider}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring"""
        assert "Supported LLM providers" in EnumLlmProvider.__doc__

    def test_enum_provider_categories(self):
        """Test specific provider categories"""
        # Commercial providers
        assert EnumLlmProvider.CLAUDE.value == "claude"
        assert EnumLlmProvider.OPENAI.value == "openai"
        assert EnumLlmProvider.GEMINI.value == "gemini"
        assert EnumLlmProvider.ANTHROPIC.value == "anthropic"

        # Local providers
        assert EnumLlmProvider.OLLAMA.value == "ollama"
        assert EnumLlmProvider.LOCAL.value == "local"
        assert EnumLlmProvider.LITELLM.value == "litellm"

    def test_is_local_method(self):
        """Test the is_local method"""
        # Local providers
        assert EnumLlmProvider.OLLAMA.is_local() is True
        assert EnumLlmProvider.LOCAL.is_local() is True
        assert EnumLlmProvider.LITELLM.is_local() is True

        # Non-local providers
        assert EnumLlmProvider.CLAUDE.is_local() is False
        assert EnumLlmProvider.OPENAI.is_local() is False
        assert EnumLlmProvider.GEMINI.is_local() is False
        assert EnumLlmProvider.ANTHROPIC.is_local() is False

    def test_requires_api_key_method(self):
        """Test the requires_api_key method"""
        # Providers that require API keys
        assert EnumLlmProvider.CLAUDE.requires_api_key() is True
        assert EnumLlmProvider.OPENAI.requires_api_key() is True
        assert EnumLlmProvider.GEMINI.requires_api_key() is True
        assert EnumLlmProvider.ANTHROPIC.requires_api_key() is True

        # Providers that don't require API keys
        assert EnumLlmProvider.OLLAMA.requires_api_key() is False
        assert EnumLlmProvider.LOCAL.requires_api_key() is False
        assert EnumLlmProvider.LITELLM.requires_api_key() is False

    def test_enum_provider_types(self):
        """Test provider type categorization"""
        # Commercial API providers
        commercial_providers = {
            EnumLlmProvider.CLAUDE,
            EnumLlmProvider.OPENAI,
            EnumLlmProvider.GEMINI,
            EnumLlmProvider.ANTHROPIC,
        }

        # Local/self-hosted providers
        local_providers = {
            EnumLlmProvider.OLLAMA,
            EnumLlmProvider.LOCAL,
            EnumLlmProvider.LITELLM,
        }

        all_providers = set(EnumLlmProvider)
        assert commercial_providers.union(local_providers) == all_providers

        # Verify all commercial providers require API keys
        for provider in commercial_providers:
            assert provider.requires_api_key() is True

        # Verify all local providers don't require API keys
        for provider in local_providers:
            assert provider.requires_api_key() is False
