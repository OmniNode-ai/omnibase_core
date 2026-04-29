# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import StrEnum


class EnumProvider(StrEnum):
    """Model provider identifiers for overseer routing decisions."""

    ANTHROPIC = "anthropic"
    """Anthropic Claude family."""

    OPENAI = "openai"
    """OpenAI GPT / o-series family."""

    GOOGLE = "google"
    """Google Gemini family."""

    LOCAL = "local"
    """Locally-hosted model (vLLM, Ollama, etc.)."""

    UNKNOWN = "unknown"
    """Provider cannot be determined."""


__all__: list[str] = ["EnumProvider"]
