# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Protocol definition for LLM client implementations.

This module defines the ProtocolLLMClient interface that all LLM client
implementations must follow. This enables protocol-based dependency injection
in the SupportAssistantHandler.

Example:
    Implementing a custom LLM client::

        class MyLLMClient:
            async def complete(
                self, prompt: str, system_prompt: str | None = None
            ) -> str:
                # Custom implementation
                return "response"

            async def health_check(self) -> bool:
                return True

    Using with container::

        container.register("ProtocolLLMClient", MyLLMClient())
        handler = SupportAssistantHandler(container)
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolLLMClient(Protocol):
    """Protocol for LLM client implementations.

    This protocol defines the interface for all LLM clients used by the
    SupportAssistantHandler. Implementations can be swapped via dependency
    injection to support different providers (OpenAI, Anthropic, Local).

    The protocol is runtime_checkable to support duck typing and isinstance
    checks when needed.

    Methods:
        complete: Send a completion request to the LLM.
        health_check: Check if the LLM client is healthy.
    """

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """Send a completion request to the LLM and return response text.

        Args:
            prompt: The user prompt/message to send to the LLM.
            system_prompt: Optional system prompt for context/instructions.

        Returns:
            The LLM's response as a string.

        Raises:
            Exception: If the LLM request fails (implementation-specific).
        """
        ...

    async def health_check(self) -> bool:
        """Check if the LLM client is healthy and reachable.

        Returns:
            True if the client is healthy and can accept requests,
            False otherwise.
        """
        ...


__all__ = ["ProtocolLLMClient"]
