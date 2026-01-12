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
from typing import TYPE_CHECKING, Literal, cast

from pydantic import ValidationError

from examples.demo.handlers.support_assistant.model_support_request import \
    SupportRequest
from examples.demo.handlers.support_assistant.model_support_response import \
    SupportResponse
from examples.demo.handlers.support_assistant.protocol_llm_client import \
    ProtocolLLMClient
from omnibase_core.decorators.decorator_allow_dict_any import allow_dict_any
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import \
        ModelONEXContainer

# System prompt for the LLM
SYSTEM_PROMPT = """You are a helpful customer support assistant.

Your responses should be:
1. Friendly and professional
2. Concise but complete
3. Actionable when possible

Always categorize the request and assess if escalation is needed.
Output must be valid JSON matching the SupportResponse schema.

Example response:
{
    "response_text": "I'd be happy to help you with that billing question.",
    "suggested_actions": ["Check your invoice online", "Contact billing support"],
    "confidence": 0.85,
    "requires_escalation": false,
    "category": "billing",
    "sentiment": "neutral"
}

Field requirements:
- response_text: string (your helpful response to the user)
- suggested_actions: array of strings (can be empty [])
- confidence: number between 0.0 and 1.0
- requires_escalation: boolean (true or false)
- category: one of "billing", "technical", "general", "account"
- sentiment: one of "positive", "neutral", "negative"

IMPORTANT: Return ONLY a valid JSON object, no other text or markdown."""


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

    def __init__(self, container: ModelONEXContainer) -> None:
        """Initialize handler with DI container.

        Args:
            container: ONEX container for protocol-based service resolution.

        Raises:
            ModelOnexError: If required services are not registered in the container.
        """
        self.container = container

        # Fail-fast: Resolve LLM client with explicit type checking
        llm_client = container.get_service("ProtocolLLMClient")
        if llm_client is None:
            raise ModelOnexError(
                message="Required service 'ProtocolLLMClient' not found in container",
                error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
                context={"service_name": "ProtocolLLMClient"},
            )
        self.llm_client: ProtocolLLMClient = llm_client

        # Fail-fast: Resolve logger with explicit type checking
        logger = container.get_service("ProtocolLogger")
        if logger is None:
            raise ModelOnexError(
                message="Required service 'ProtocolLogger' not found in container",
                error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
                context={"service_name": "ProtocolLogger"},
            )
        self.logger = logger

    async def handle(self, request: SupportRequest) -> SupportResponse:
        """Process support request and return structured response.

        Args:
            request: The support request from the user.

        Returns:
            SupportResponse with AI-generated response, suggested actions,
            and metadata about the classification.
        """
        try:
            # 1. Format prompt from request (sanitized, no PII in logs)
            prompt = self._format_prompt(request)

            # 2. Call LLM via protocol
            raw_response = await self.llm_client.complete(prompt, SYSTEM_PROMPT)

            # 3. Parse and validate response to structured output
            response = self._parse_response(raw_response)

            return response

        except ModelOnexError:
            # Re-raise ONEX errors as-is (already structured)
            raise
        except (json.JSONDecodeError, ValidationError) as e:
            # Structured handling for parse/validation errors
            # Log error type without exposing raw details
            self._log_error(f"Response parsing failed: {type(e).__name__}")
            raise ModelOnexError(
                message="Failed to parse LLM response",
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                context={"error_type": type(e).__name__},
            ) from e
        except Exception as e:
            # boundary-ok: handler entry point must not crash; structured error response
            # Log error class without exposing raw message (may contain PII)
            self._log_error(f"Request handling failed: {type(e).__name__}")
            raise ModelOnexError(
                message="An error occurred processing your request",
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                context={"error_type": type(e).__name__},
            ) from e

    def _format_prompt(self, request: SupportRequest) -> str:
        """Format the user request into an LLM prompt.

        Note: User identifiers and other PII are intentionally excluded from
        the prompt to prevent PII leakage to the LLM. Only the message content
        and non-PII metadata are included.

        Args:
            request: The support request to format.

        Returns:
            Formatted prompt string for the LLM.
        """
        parts = []

        # Add user message (content only, no identifiers)
        parts.append(f"User Message: {request.message}")

        # Note: User identifier intentionally excluded to minimize PII in prompts
        # The identifier is tracked server-side for request correlation

        # Add urgency level (non-PII metadata)
        parts.append(f"Urgency Level: {request.urgency}")

        # Add context if provided, filtering out potential PII fields
        if request.context:
            # Filter context to exclude common PII fields
            safe_context = self._filter_pii_from_context(request.context)
            if safe_context:
                context_str = json.dumps(safe_context, indent=2)
                parts.append(f"Previous Context:\n{context_str}")

        return "\n\n".join(parts)

    def _filter_pii_from_context(self, context: dict[str, str]) -> dict[str, str]:
        """Filter potential PII fields from context before sending to LLM.

        Args:
            context: The context dictionary to filter.

        Returns:
            Filtered context with PII fields removed.
        """
        # Fields that commonly contain PII
        pii_fields = {
            "email",
            "phone",
            "address",
            "ssn",
            "social_security",
            "credit_card",
            "password",
            "api_key",
            "token",
            "secret",
            "user_id",
            "user_identifier",
            "name",
            "full_name",
            "first_name",
            "last_name",
        }
        return {k: v for k, v in context.items() if k.lower() not in pii_fields}

    def _parse_response(self, raw_response: str) -> SupportResponse:
        """Parse LLM response into SupportResponse.

        Handles multiple response formats:
        - Pure JSON response
        - JSON embedded in markdown code blocks
        - Plain text (fallback with low confidence)

        Args:
            raw_response: The raw response string from the LLM.

        Returns:
            Parsed and validated SupportResponse.

        Raises:
            ValidationError: If parsed JSON fails Pydantic validation.
        """
        # Try to parse as pure JSON first
        try:
            data = json.loads(raw_response)
            if self._validate_json_structure(data):
                return cast(SupportResponse, self._create_validated_response(data))
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from code blocks
        json_match = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```", raw_response, re.DOTALL
        )
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if self._validate_json_structure(data):
                    return cast(SupportResponse, self._create_validated_response(data))
            except json.JSONDecodeError:
                pass

        # Try to find any JSON object in the response
        json_object_match = re.search(r"\{[^{}]*\}", raw_response, re.DOTALL)
        if json_object_match:
            try:
                data = json.loads(json_object_match.group(0))
                if self._validate_json_structure(data):
                    return cast(SupportResponse, self._create_validated_response(data))
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

    def _validate_json_structure(self, data: object) -> bool:
        """Validate that parsed JSON has the expected structure.

        Performs strict validation to ensure the parsed JSON matches the
        expected SupportResponse schema. Required fields must be present
        and have valid types.

        Args:
            data: The parsed JSON object to validate.

        Returns:
            True if the structure is valid (dict with required fields and valid types).
        """
        if not isinstance(data, dict):
            return False

        # Required fields that MUST be present for a valid response
        # These correspond to SupportResponse fields with `...` (no default)
        required_fields = {"response_text", "confidence", "requires_escalation", "category", "sentiment"}

        # Check all required fields are present
        if not required_fields.issubset(set(data.keys())):
            return False

        # Validate response_text is a non-empty string
        response_text = data.get("response_text")
        if not isinstance(response_text, str) or not response_text.strip():
            return False

        # Validate confidence is a number
        confidence = data.get("confidence")
        if not isinstance(confidence, (int, float)):
            return False

        # Validate requires_escalation is boolean
        requires_escalation = data.get("requires_escalation")
        if not isinstance(requires_escalation, bool):
            return False

        # Validate category is a valid string
        category = data.get("category")
        valid_categories = {"billing", "technical", "general", "account"}
        if not isinstance(category, str) or category.lower() not in valid_categories:
            return False

        # Validate sentiment is a valid string
        sentiment = data.get("sentiment")
        valid_sentiments = {"positive", "neutral", "negative"}
        if not isinstance(sentiment, str) or sentiment.lower() not in valid_sentiments:
            return False

        return True

    @allow_dict_any(  # type: ignore[misc]
        reason="LLM JSON responses have arbitrary structure requiring dynamic type handling"
    )
    def _create_validated_response(self, data: dict[str, object]) -> SupportResponse:
        """Create and validate SupportResponse using Pydantic.

        Uses Pydantic model_validate for proper type coercion and validation.

        Args:
            data: Dictionary parsed from LLM JSON response.

        Returns:
            Validated SupportResponse.

        Raises:
            ValidationError: If the data fails Pydantic validation.
        """
        # Normalize the data before validation
        normalized = {
            "response_text": str(
                data.get("response_text", "Thank you for your message.")
            ),
            "suggested_actions": self._ensure_string_list(
                data.get(
                    "suggested_actions", ["Please let me know if you need more help"]
                )
            ),
            "confidence": self._ensure_confidence(data.get("confidence", 0.5)),
            "requires_escalation": bool(data.get("requires_escalation", False)),
            "category": self._ensure_category(data.get("category", "general")),
            "sentiment": self._ensure_sentiment(data.get("sentiment", "neutral")),
        }

        # Use Pydantic model_validate for strict validation
        return SupportResponse.model_validate(normalized)

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

    def _log_error(self, message: str) -> None:
        """Log an error message if logger is available.

        Args:
            message: The error message to log.
        """
        if hasattr(self.logger, "error"):
            self.logger.error(message)


__all__ = ["SupportAssistantHandler", "SYSTEM_PROMPT"]
