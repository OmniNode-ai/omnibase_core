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
from typing import TYPE_CHECKING, Literal, cast, get_args, get_type_hints

from pydantic import ValidationError

from examples.demo.handlers.support_assistant.model_support_request import (
    SupportRequest,
)
from examples.demo.handlers.support_assistant.model_support_response import (
    SupportResponse,
)
from examples.demo.handlers.support_assistant.protocol_llm_client import (
    ProtocolLLMClient,
)
from omnibase_core.decorators.decorator_allow_dict_any import allow_dict_any
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import (
        ModelONEXContainer,
    )


def _extract_literal_values(model_class: type, field_name: str) -> frozenset[str]:
    """Extract Literal values from a Pydantic model field annotation.

    Args:
        model_class: The Pydantic model class.
        field_name: Name of the field to extract values from.

    Returns:
        Frozen set of valid string values for the Literal field.
    """
    hints = get_type_hints(model_class)
    field_type = hints.get(field_name)
    if field_type is None:
        return frozenset()
    args = get_args(field_type)
    return frozenset(str(arg) for arg in args if isinstance(arg, str))


# Extract valid values from SupportResponse model annotations (DRY principle)
# This ensures handler validation stays in sync with model definitions
VALID_CATEGORIES: frozenset[str] = _extract_literal_values(SupportResponse, "category")
VALID_SENTIMENTS: frozenset[str] = _extract_literal_values(SupportResponse, "sentiment")

# System prompt for the LLM - uses only valid JSON examples to avoid model confusion
SYSTEM_PROMPT = """You are a helpful customer support assistant.

Your responses should be:
1. Friendly and professional
2. Concise but complete
3. Actionable when possible

Always categorize the request and assess if escalation is needed.
Return ONLY a valid JSON object with no additional text or markdown.

Required JSON structure:
{
    "response_text": "Your helpful response to the user (required string)",
    "suggested_actions": ["action1", "action2"],
    "confidence": 0.85,
    "requires_escalation": false,
    "category": "billing",
    "sentiment": "neutral"
}

Field constraints:
- category: one of "billing", "technical", "general", "account"
- sentiment: one of "positive", "neutral", "negative"
- confidence: a number between 0.0 and 1.0
- requires_escalation: true or false (boolean)

Example response for a billing question:
{
    "response_text": "I'd be happy to help you with that billing question.",
    "suggested_actions": ["Check your invoice online", "Contact billing support"],
    "confidence": 0.85,
    "requires_escalation": false,
    "category": "billing",
    "sentiment": "neutral"
}"""


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
            ModelOnexError: If required services are not registered in the container
                or do not implement required protocol methods.
        """
        self.container = container

        # Fail-fast: Resolve LLM client with explicit type and protocol checking
        llm_client = container.get_service("ProtocolLLMClient")
        if llm_client is None:
            raise ModelOnexError(
                message="Required service 'ProtocolLLMClient' not found in container",
                error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
                context={"service_name": "ProtocolLLMClient"},
            )
        # Verify protocol compliance via duck-typing (check required method exists)
        if not callable(getattr(llm_client, "complete", None)):
            raise ModelOnexError(
                message=(
                    "Service 'ProtocolLLMClient' does not implement "
                    "required 'complete' method"
                ),
                error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
                context={
                    "service_name": "ProtocolLLMClient",
                    "missing_method": "complete",
                },
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
        # Logger protocol compliance is verified at usage time via hasattr in _log_error
        self.logger: object = logger

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
            # fallback-ok: try alternative parsing strategies below
            pass

        # Try to extract JSON from markdown code blocks.
        # Note: The regex uses code block markers (```) as delimiters, so nested
        # braces within the JSON are captured correctly. For JSON without code
        # block markers, _extract_json_object provides balanced brace matching.
        json_match = re.search(
            r"```(?:json)?\s*(\{.*\})\s*```", raw_response, re.DOTALL
        )
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if self._validate_json_structure(data):
                    return cast(SupportResponse, self._create_validated_response(data))
            except json.JSONDecodeError:
                # fallback-ok: try balanced brace extraction below
                pass

        # Try to find any JSON object in the response using balanced brace matching
        extracted_json = self._extract_json_object(raw_response)
        if extracted_json:
            try:
                data = json.loads(extracted_json)
                if self._validate_json_structure(data):
                    return cast(SupportResponse, self._create_validated_response(data))
            except json.JSONDecodeError:
                # fallback-ok: return safe fallback response below
                pass

        # Fallback: return error response with low confidence
        fallback_text = (
            "I apologize, but I had trouble processing your request. "
            "Please try again."
        )
        return SupportResponse(
            response_text=fallback_text,
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

    def _extract_json_object(self, text: str) -> str | None:
        """Extract the first valid JSON object from text using balanced brace matching.

        This method handles nested JSON objects that simple regex patterns miss.
        It finds the first '{' and then tracks brace balance to find the matching '}'.

        Args:
            text: The text to search for a JSON object.

        Returns:
            The extracted JSON string, or None if no valid object found.
        """
        start_idx = text.find("{")
        if start_idx == -1:
            return None

        brace_count = 0
        in_string = False
        escape_next = False

        for i, char in enumerate(text[start_idx:], start=start_idx):
            if escape_next:
                escape_next = False
                continue

            if char == "\\":
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    return text[start_idx : i + 1]

        return None

    def _validate_json_structure(self, data: object) -> bool:
        """Validate that parsed JSON has the expected structure.

        Performs strict validation to ensure the parsed JSON matches the
        expected SupportResponse schema. Required fields must be present
        and have valid types. Uses module-level constants extracted from
        the model annotations for DRY compliance.

        Args:
            data: The parsed JSON object to validate.

        Returns:
            True if the structure is valid (dict with required fields and valid types).
        """
        if not isinstance(data, dict):
            return False

        # Required fields that MUST be present for a valid response
        # These correspond to SupportResponse fields with `...` (no default)
        required_fields = {
            "response_text",
            "confidence",
            "requires_escalation",
            "category",
            "sentiment",
        }

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

        # Validate category using module-level constant extracted from model
        category = data.get("category")
        if not isinstance(category, str) or category.lower() not in VALID_CATEGORIES:
            return False

        # Validate sentiment using module-level constant extracted from model
        sentiment = data.get("sentiment")
        if not isinstance(sentiment, str) or sentiment.lower() not in VALID_SENTIMENTS:
            return False

        return True

    @allow_dict_any(  # type: ignore[untyped-decorator]
        reason="LLM JSON responses have arbitrary structure"
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
            # fallback-ok: return safe default when conversion fails
            return 0.5

    def _ensure_category(
        self, value: object
    ) -> Literal["billing", "technical", "general", "account"]:
        """Ensure category is a valid literal.

        Uses module-level VALID_CATEGORIES constant extracted from model
        annotations for DRY compliance.

        Args:
            value: The value to validate.

        Returns:
            Valid category literal.
        """
        str_value = str(value).lower()
        if str_value in VALID_CATEGORIES:
            return str_value  # type: ignore[return-value]
        return "general"

    def _ensure_sentiment(
        self, value: object
    ) -> Literal["positive", "neutral", "negative"]:
        """Ensure sentiment is a valid literal.

        Uses module-level VALID_SENTIMENTS constant extracted from model
        annotations for DRY compliance.

        Args:
            value: The value to validate.

        Returns:
            Valid sentiment literal.
        """
        str_value = str(value).lower()
        if str_value in VALID_SENTIMENTS:
            return str_value  # type: ignore[return-value]
        return "neutral"

    def _log_error(self, message: str) -> None:
        """Log an error message if logger is available.

        Args:
            message: The error message to log.
        """
        try:
            if hasattr(self.logger, "error"):
                self.logger.error(message)
        except Exception:
            # cleanup-resilience-ok: logging must not prevent error propagation
            pass


__all__ = [
    "SupportAssistantHandler",
    "SYSTEM_PROMPT",
    "VALID_CATEGORIES",
    "VALID_SENTIMENTS",
]
