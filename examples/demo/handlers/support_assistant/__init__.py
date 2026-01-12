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
    This module uses eager imports intentionally to provide a clean public API.
    All exports are lightweight Pydantic models and handler classes with no
    import-time side effects beyond module loading. The __all__ list defines
    the complete public interface.
"""

# Provider implementations
from examples.demo.handlers.support_assistant.handler_anthropic import \
    AnthropicLLMClient
from examples.demo.handlers.support_assistant.handler_local import \
    LocalLLMClient
from examples.demo.handlers.support_assistant.handler_mock import MockLLMClient
from examples.demo.handlers.support_assistant.handler_openai import \
    OpenAILLMClient
# Handler
from examples.demo.handlers.support_assistant.handler_support_assistant import (
    SYSTEM_PROMPT, SupportAssistantHandler)
# Models
from examples.demo.handlers.support_assistant.model_config import (
    ANTHROPIC_CONFIG, LOCAL_CONFIG, OPENAI_CONFIG, ModelConfig)
from examples.demo.handlers.support_assistant.model_support_request import \
    SupportRequest
from examples.demo.handlers.support_assistant.model_support_response import \
    SupportResponse
# Protocol
from examples.demo.handlers.support_assistant.protocol_llm_client import \
    ProtocolLLMClient

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
