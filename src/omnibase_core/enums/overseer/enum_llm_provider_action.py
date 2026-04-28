# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import StrEnum


class EnumLLMProviderAction(StrEnum):
    """Actions the overseer can request from an LLM provider.

    Used in protocol dispatch to model inference integrations
    (e.g. OpenAI, Anthropic, vLLM).
    """

    COMPLETE = "COMPLETE"
    """Generate a completion for a prompt."""

    CHAT = "CHAT"
    """Generate a response in a multi-turn chat context."""

    EMBED = "EMBED"
    """Produce an embedding vector for input text."""

    STREAM = "STREAM"
    """Stream a completion token-by-token."""

    COUNT_TOKENS = "COUNT_TOKENS"
    """Count the number of tokens in a given prompt."""

    LIST_MODELS = "LIST_MODELS"
    """List available models from the provider."""

    GET_MODEL_INFO = "GET_MODEL_INFO"
    """Retrieve metadata for a specific model."""

    CANCEL = "CANCEL"
    """Cancel an in-flight inference request."""


__all__: list[str] = ["EnumLLMProviderAction"]
