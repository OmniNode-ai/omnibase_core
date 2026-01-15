# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Mock LLM client for unit testing.

This module provides a configurable mock LLM client that implements
ProtocolLLMClient for use in unit tests. It allows testing different
response scenarios without making actual LLM API calls.

Example:
    Basic usage with default response::

        client = MockLLMClient()
        response = await client.complete("Hello")
        # Returns valid JSON matching SupportResponse schema

    Custom response scenario::

        client = MockLLMClient(
            scenario="escalation",
            response_text="I need to escalate this issue.",
        )
        response = await client.complete("I'm very frustrated!")

    Simulating errors::

        client = MockLLMClient(should_fail=True, error_message="API Error")
        response = await client.complete("Hello")  # Raises RuntimeError
"""

from __future__ import annotations

import json
from typing import Literal

from examples.demo.handlers.support_assistant.protocol_llm_client import (
    ProtocolLLMClient,
)


class MockLLMClient:
    """Mock LLM client for unit testing.

    This client returns configurable mock responses that match the
    SupportResponse schema. It supports different scenarios for testing
    various handler behaviors.

    Attributes:
        scenario: The response scenario (normal, escalation, error).
        response_text: Custom response text (optional).
        should_fail: Whether to simulate API failures.
        error_message: Error message when should_fail is True.
        is_healthy: Whether health check returns True.
        call_count: Number of times complete() was called.
        last_prompt: The last prompt sent to complete().
        last_system_prompt: The last system prompt sent to complete().
    """

    def __init__(
        self,
        *,
        scenario: Literal["normal", "escalation", "error", "invalid_json"] = "normal",
        response_text: str | None = None,
        should_fail: bool = False,
        error_message: str = "Mock API error",
        is_healthy: bool = True,
    ) -> None:
        """Initialize the mock LLM client.

        Args:
            scenario: Response scenario determining mock behavior.
            response_text: Custom response text override.
            should_fail: If True, complete() raises RuntimeError.
            error_message: Error message when should_fail is True.
            is_healthy: Return value for health_check().
        """
        self.scenario = scenario
        self.response_text = response_text
        self.should_fail = should_fail
        self.error_message = error_message
        self.is_healthy = is_healthy
        self.call_count = 0
        self.last_prompt: str | None = None
        self.last_system_prompt: str | None = None

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """Return a mock LLM response based on the configured scenario.

        Args:
            prompt: The user prompt (stored for inspection).
            system_prompt: The system prompt (stored for inspection).

        Returns:
            JSON string matching SupportResponse schema.

        Raises:
            RuntimeError: If should_fail is True.
        """
        self.call_count += 1
        self.last_prompt = prompt
        self.last_system_prompt = system_prompt

        if self.should_fail:
            raise RuntimeError(self.error_message)

        if self.scenario == "invalid_json":
            return "This is not valid JSON response from the LLM."

        return self._generate_mock_response(prompt)

    async def health_check(self) -> bool:
        """Return the configured health status.

        Returns:
            The value of is_healthy attribute.
        """
        return self.is_healthy

    def _generate_mock_response(self, prompt: str) -> str:
        """Generate a mock JSON response based on scenario.

        Args:
            prompt: The user prompt for context.

        Returns:
            JSON string matching SupportResponse schema.
        """
        # Determine category from prompt keywords
        category = self._detect_category(prompt)
        sentiment = self._detect_sentiment(prompt)

        if self.scenario == "escalation":
            escalation_text = (
                "I understand your frustration. I'm escalating this to a specialist."
            )
            response = {
                "response_text": self.response_text or escalation_text,
                "suggested_actions": [
                    "A specialist will contact you within 24 hours",
                    "Check your email for case confirmation",
                ],
                "confidence": 0.85,
                "requires_escalation": True,
                "category": category,
                "sentiment": "negative",
            }
        elif self.scenario == "error":
            response = {
                "response_text": self.response_text
                or "I apologize, but I encountered an issue processing your request.",
                "suggested_actions": [
                    "Please try again later",
                    "Contact support if issue persists",
                ],
                "confidence": 0.3,
                "requires_escalation": False,
                "category": "general",
                "sentiment": "neutral",
            }
        else:  # normal scenario
            response = {
                "response_text": self.response_text
                or f"Thank you for your {category} inquiry. I'm happy to help.",
                "suggested_actions": [
                    "Review our help documentation",
                    "Update your account settings if needed",
                    "Contact us if you need further assistance",
                ],
                "confidence": 0.92,
                "requires_escalation": False,
                "category": category,
                "sentiment": sentiment,
            }

        return json.dumps(response)

    def _detect_category(
        self, prompt: str
    ) -> Literal["billing", "technical", "general", "account"]:
        """Detect category from prompt keywords.

        Args:
            prompt: The user prompt to analyze.

        Returns:
            Category literal based on keywords.
        """
        prompt_lower = prompt.lower()
        if any(
            word in prompt_lower for word in ["bill", "payment", "charge", "invoice"]
        ):
            return "billing"
        if any(
            word in prompt_lower for word in ["error", "bug", "crash", "not working"]
        ):
            return "technical"
        if any(
            word in prompt_lower for word in ["account", "password", "login", "email"]
        ):
            return "account"
        return "general"

    def _detect_sentiment(
        self, prompt: str
    ) -> Literal["positive", "neutral", "negative"]:
        """Detect sentiment from prompt keywords.

        Args:
            prompt: The user prompt to analyze.

        Returns:
            Sentiment literal based on keywords.
        """
        prompt_lower = prompt.lower()
        if any(
            word in prompt_lower
            for word in ["frustrated", "angry", "terrible", "worst", "hate"]
        ):
            return "negative"
        if any(
            word in prompt_lower
            for word in ["thank", "great", "love", "excellent", "happy"]
        ):
            return "positive"
        return "neutral"


def _verify_protocol_compliance() -> None:
    """Verify MockLLMClient implements ProtocolLLMClient.

    This function is provided for test suites to verify protocol compliance
    without import-time side effects. Tests should call this explicitly.

    Note: We verify all protocol-required methods exist on the class rather
    than instantiating, for consistency with other LLM client implementations.

    Raises:
        AssertionError: If MockLLMClient does not implement ProtocolLLMClient.
    """
    # Get required methods from the protocol
    protocol_methods = {
        name
        for name in dir(ProtocolLLMClient)
        if not name.startswith("_") and callable(getattr(ProtocolLLMClient, name))
    }

    # Verify all protocol methods exist on the client class
    for method_name in protocol_methods:
        assert hasattr(
            MockLLMClient, method_name
        ), f"MockLLMClient must have '{method_name}' method per ProtocolLLMClient"


__all__ = ["MockLLMClient", "_verify_protocol_compliance"]
