# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""Support assistant handler for OMN-1201 Demo.

This module provides the complete AI support assistant implementation including:
- Input/output schemas (SupportRequest, SupportResponse)
- LLM client protocol (ProtocolLLMClient)
- Main handler (SupportAssistantHandler)
- Provider implementations (OpenAI, Anthropic, Local, Mock)

Example:
    Using with mock for testing::

        from examples.demo.handlers.support_assistant import (
            SupportAssistantHandler,
            SupportRequest,
            MockLLMClient,
        )

        container = MagicMock()
        container.get_service = lambda x: MockLLMClient() if x == "ProtocolLLMClient" else MagicMock()

        handler = SupportAssistantHandler(container)
        request = SupportRequest(user_identifier="123", message="Help!")
        response = await handler.handle(request)

    Using with local LLM::

        from examples.demo.handlers.support_assistant import (
            SupportAssistantHandler,
            LocalLLMClient,
            LOCAL_CONFIG,
        )

        client = LocalLLMClient.from_config(LOCAL_CONFIG)
        # Register in container and use handler

Note:
    This module uses lazy imports to avoid import-time side effects.
    All exports are loaded on first access via __getattr__. The __all__ list
    defines the complete public interface.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from examples.demo.handlers.support_assistant.handler_anthropic import (
        AnthropicLLMClient as AnthropicLLMClient,
    )
    from examples.demo.handlers.support_assistant.handler_local import (
        LocalLLMClient as LocalLLMClient,
    )
    from examples.demo.handlers.support_assistant.handler_mock import (
        MockLLMClient as MockLLMClient,
    )
    from examples.demo.handlers.support_assistant.handler_openai import (
        OpenAILLMClient as OpenAILLMClient,
    )
    from examples.demo.handlers.support_assistant.handler_support_assistant import (
        SYSTEM_PROMPT as SYSTEM_PROMPT,
        SupportAssistantHandler as SupportAssistantHandler,
    )
    from examples.demo.handlers.support_assistant.model_config import (
        ANTHROPIC_CONFIG as ANTHROPIC_CONFIG,
        LOCAL_CONFIG as LOCAL_CONFIG,
        OPENAI_CONFIG as OPENAI_CONFIG,
        ModelConfig as ModelConfig,
    )
    from examples.demo.handlers.support_assistant.model_support_request import (
        SupportRequest as SupportRequest,
    )
    from examples.demo.handlers.support_assistant.model_support_response import (
        SupportResponse as SupportResponse,
    )
    from examples.demo.handlers.support_assistant.protocol_llm_client import (
        ProtocolLLMClient as ProtocolLLMClient,
    )

__all__ = [
    # Models
    "ModelConfig",
    "OPENAI_CONFIG",
    "ANTHROPIC_CONFIG",
    "LOCAL_CONFIG",
    "SupportRequest",
    "SupportResponse",
    # Protocol
    "ProtocolLLMClient",
    # Handler
    "SupportAssistantHandler",
    "SYSTEM_PROMPT",
    # Provider implementations
    "MockLLMClient",
    "LocalLLMClient",
    "OpenAILLMClient",
    "AnthropicLLMClient",
]

# Mapping of attribute names to their module and import name
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # Models
    "ModelConfig": ("model_config", "ModelConfig"),
    "OPENAI_CONFIG": ("model_config", "OPENAI_CONFIG"),
    "ANTHROPIC_CONFIG": ("model_config", "ANTHROPIC_CONFIG"),
    "LOCAL_CONFIG": ("model_config", "LOCAL_CONFIG"),
    "SupportRequest": ("model_support_request", "SupportRequest"),
    "SupportResponse": ("model_support_response", "SupportResponse"),
    # Protocol
    "ProtocolLLMClient": ("protocol_llm_client", "ProtocolLLMClient"),
    # Handler
    "SupportAssistantHandler": ("handler_support_assistant", "SupportAssistantHandler"),
    "SYSTEM_PROMPT": ("handler_support_assistant", "SYSTEM_PROMPT"),
    # Provider implementations
    "MockLLMClient": ("handler_mock", "MockLLMClient"),
    "LocalLLMClient": ("handler_local", "LocalLLMClient"),
    "OpenAILLMClient": ("handler_openai", "OpenAILLMClient"),
    "AnthropicLLMClient": ("handler_anthropic", "AnthropicLLMClient"),
}


def __getattr__(name: str) -> object:
    """Lazy import attributes on first access."""
    if name in _LAZY_IMPORTS:
        module_name, attr_name = _LAZY_IMPORTS[name]
        import importlib

        module = importlib.import_module(
            f"examples.demo.handlers.support_assistant.{module_name}"
        )
        return getattr(module, attr_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """List available attributes including lazy imports."""
    return list(__all__)
