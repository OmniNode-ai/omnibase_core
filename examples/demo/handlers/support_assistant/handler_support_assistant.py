# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""SupportAssistantHandler for OMN-1201 Demo.

This module provides the main handler for the AI support assistant that uses
protocol-based dependency injection for LLM client resolution.

Example:
    Using with DI container::

        from omnibase_core.models.container.model_onex_container import (
            ModelONEXContainer,
        )

        container = ModelONEXContainer()
        # Register LLM client implementation
        container.register("ProtocolLLMClient", LocalLLMClient())

        handler = SupportAssistantHandler(container)
        request = SupportRequest(user_identifier="123", message="Help!")
        response = await handler.handle(request)

    Using with mock for testing::

        from examples.demo.handlers.support_assistant.handler_mock import (
            MockLLMClient,
        )

        container = MagicMock()
        container.get_service = lambda x: MockLLMClient()

        handler = SupportAssistantHandler(container)
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Literal

from omnibase_core.decorators.decorator_allow_dict_any import allow_dict_any

from examples.demo.handlers.support_assistant.model_support_request import (
    SupportRequest,
)
from examples.demo.handlers.support_assistant.model_support_response import (
    SupportResponse,
)
from examples.demo.handlers.support_assistant.protocol_llm_client import (
    ProtocolLLMClient,
)

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# System prompt for the LLM
SYSTEM_PROMPT = """You are a helpful customer support assistant.

Your responses should be:
1. Friendly and professional
2. Concise but complete
3. Actionable when possible

Always categorize the request and assess if escalation is needed.
Output must be valid JSON matching the SupportResponse schema:
{
    "response_text": "Your response to the user",
    "suggested_actions": ["action1", "action2"],
    "confidence": 0.0 to 1.0,
    "requires_escalation": true or false,
    "category": "billing" | "technical" | "general" | "account",
    "sentiment": "positive" | "neutral" | "negative"
}

IMPORTANT: Return ONLY the JSON object, no other text."""


class SupportAssistantHandler:
    """AI support assistant that responds to user requests.

    This handler uses protocol-based dependency injection to resolve the LLM
    client at runtime. This enables swapping between different LLM providers
    (OpenAI, Anthropic, Local) without changing the handler code.

    Attributes:
        container: The ONEX DI container for service resolution.
        llm_client: The LLM client resolved from the container.
        logger: The logger resolved from the container.
    """

    def __init__(self, container: "ModelONEXContainer") -> None:
        """Initialize handler with DI container.

        Args:
            container: ONEX container for protocol-based service resolution.
        """
        self.container = container
        self.llm_client: ProtocolLLMClient = container.get_service("ProtocolLLMClient")
        self.logger = container.get_service("ProtocolLogger")

    async def handle(self, request: SupportRequest) -> SupportResponse:
        """Process support request and return structured response.

        Args:
            request: The support request from the user.

        Returns:
            SupportResponse with AI-generated response, suggested actions,
            and metadata about the classification.
        """
        try:
            # 1. Format prompt from request
            prompt = self._format_prompt(request)

            # 2. Call LLM via protocol
            raw_response = await self.llm_client.complete(prompt, SYSTEM_PROMPT)

            # 3. Parse response to structured output
            response = self._parse_response(raw_response)

            return response

        except Exception as e:
            # Return error response on any failure
            self._log_error(f"Error handling request: {e}")
            return self._create_error_response(str(e))

    def _format_prompt(self, request: SupportRequest) -> str:
        """Format the user request into an LLM prompt.

        Args:
            request: The support request to format.

        Returns:
            Formatted prompt string for the LLM.
        """
        parts = []

        # Add user message
        parts.append(f"User Message: {request.message}")

        # Add user ID for context
        parts.append(f"User ID: {request.user_identifier}")

        # Add urgency level
        parts.append(f"Urgency Level: {request.urgency}")

        # Add context if provided
        if request.context:
            context_str = json.dumps(request.context, indent=2)
            parts.append(f"Previous Context:\n{context_str}")

        return "\n\n".join(parts)

    def _parse_response(self, raw_response: str) -> SupportResponse:
        """Parse LLM response into SupportResponse.

        Handles multiple response formats:
        - Pure JSON response
        - JSON embedded in markdown code blocks
        - Plain text (fallback with low confidence)

        Args:
            raw_response: The raw response string from the LLM.

        Returns:
            Parsed SupportResponse.
        """
        # Try to parse as pure JSON first
        try:
            data = json.loads(raw_response)
            return self._create_response_from_dict(data)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from code blocks
        json_match = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```", raw_response, re.DOTALL
        )
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return self._create_response_from_dict(data)
            except json.JSONDecodeError:
                pass

        # Try to find any JSON object in the response
        json_object_match = re.search(r"\{[^{}]*\}", raw_response, re.DOTALL)
        if json_object_match:
            try:
                data = json.loads(json_object_match.group(0))
                return self._create_response_from_dict(data)
            except json.JSONDecodeError:
                pass

        # Fallback: return error response with low confidence
        return SupportResponse(
            response_text="I apologize, but I had trouble processing your request. Please try again.",
            suggested_actions=[
                "Please rephrase your question",
                "Try providing more details",
                "Contact support if the issue persists",
            ],
            confidence=0.2,
            requires_escalation=False,
            category="general",
            sentiment="neutral",
        )

    @allow_dict_any(
        reason="LLM JSON responses have arbitrary structure requiring dynamic type handling"
    )
    def _create_response_from_dict(self, data: dict[str, object]) -> SupportResponse:
        """Create SupportResponse from parsed dictionary.

        Handles missing fields and type coercion gracefully.

        Args:
            data: Dictionary parsed from LLM JSON response.

        Returns:
            Validated SupportResponse.
        """
        return SupportResponse(
            response_text=str(data.get("response_text", "Thank you for your message.")),
            suggested_actions=self._ensure_string_list(
                data.get("suggested_actions", ["Please let me know if you need more help"])
            ),
            confidence=self._ensure_confidence(data.get("confidence", 0.5)),
            requires_escalation=bool(data.get("requires_escalation", False)),
            category=self._ensure_category(data.get("category", "general")),
            sentiment=self._ensure_sentiment(data.get("sentiment", "neutral")),
        )

    def _ensure_string_list(self, value: object) -> list[str]:
        """Ensure value is a list of strings.

        Args:
            value: The value to convert.

        Returns:
            List of strings.
        """
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)] if value else ["Contact support for assistance"]

    def _ensure_confidence(self, value: object) -> float:
        """Ensure confidence is a valid float between 0 and 1.

        Args:
            value: The value to convert.

        Returns:
            Float between 0.0 and 1.0.
        """
        try:
            conf = float(value)  # type: ignore[arg-type]
            return max(0.0, min(1.0, conf))
        except (TypeError, ValueError):
            return 0.5

    def _ensure_category(
        self, value: object
    ) -> Literal["billing", "technical", "general", "account"]:
        """Ensure category is a valid literal.

        Args:
            value: The value to validate.

        Returns:
            Valid category literal.
        """
        valid = {"billing", "technical", "general", "account"}
        str_value = str(value).lower()
        if str_value in valid:
            return str_value  # type: ignore[return-value]
        return "general"

    def _ensure_sentiment(
        self, value: object
    ) -> Literal["positive", "neutral", "negative"]:
        """Ensure sentiment is a valid literal.

        Args:
            value: The value to validate.

        Returns:
            Valid sentiment literal.
        """
        valid = {"positive", "neutral", "negative"}
        str_value = str(value).lower()
        if str_value in valid:
            return str_value  # type: ignore[return-value]
        return "neutral"

    def _create_error_response(self, error_msg: str) -> SupportResponse:
        """Create an error response for failed requests.

        Args:
            error_msg: The error message to include.

        Returns:
            SupportResponse indicating an error occurred.
        """
        return SupportResponse(
            response_text=f"I'm sorry, but I encountered an error processing your request. {error_msg}",
            suggested_actions=[
                "Please try again in a moment",
                "Contact support if the issue persists",
            ],
            confidence=0.1,
            requires_escalation=False,
            category="general",
            sentiment="neutral",
        )

    def _log_error(self, message: str) -> None:
        """Log an error message if logger is available.

        Args:
            message: The error message to log.
        """
        if hasattr(self.logger, "error"):
            self.logger.error(message)


__all__ = ["SupportAssistantHandler", "SYSTEM_PROMPT"]
