# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Enum for LLM provider types.

Defines supported LLM providers for agent system.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumLlmProvider(StrValueHelper, str, Enum):
    """Supported LLM providers for agents."""

    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    LITELLM = "litellm"

    def is_local(self) -> bool:
        """Check if this is a local provider."""
        return self in {self.LOCAL, self.LITELLM}

    def requires_api_key(self) -> bool:
        """Check if this provider requires an API key.

        Per OMN-7467/OMN-7835, all frontier providers use SSO/OAuth.
        Only GLM (Zhipu AI) requires an explicit API key, but GLM is
        not represented in this enum. All members here use SSO/OAuth.
        """
        return False


__all__ = ["EnumLlmProvider"]
