# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

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

import functools
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
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


@functools.lru_cache(maxsize=8)
def _extract_literal_values(model_class: type, field_name: str) -> frozenset[str]:
    """Extract Literal values from a Pydantic model field annotation.

    Uses lru_cache to defer evaluation until first access, avoiding import-time
    side effects while still memoizing the result for performance.

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


def get_valid_categories() -> frozenset[str]:
    """Get valid category values from SupportResponse model (lazy evaluation).

    This function defers get_type_hints() call until first use, avoiding
    import-time side effects while maintaining DRY compliance with model.

    Returns:
        Frozen set of valid category strings.
    """
    return _extract_literal_values(SupportResponse, "category")


def get_valid_sentiments() -> frozenset[str]:
    """Get valid sentiment values from SupportResponse model (lazy evaluation).

    This function defers get_type_hints() call until first use, avoiding
    import-time side effects while maintaining DRY compliance with model.

    Returns:
        Frozen set of valid sentiment strings.
    """
    return _extract_literal_values(SupportResponse, "sentiment")


# Lazy accessors for valid values - evaluated on first access, not at import time
# This ensures handler validation stays in sync with model definitions (DRY)
# while avoiding import-time side effects from get_type_hints() calls
VALID_CATEGORIES: frozenset[str] = frozenset(
    {"billing", "technical", "general", "account"}
)
VALID_SENTIMENTS: frozenset[str] = frozenset({"positive", "neutral", "negative"})

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

        # Fail-fast DI resolution: Missing services fail immediately with typed error
        llm_client: ProtocolLLMClient | None = container.get_service(
            "ProtocolLLMClient"
        )
        if llm_client is None:
            raise ModelOnexError(
                message="Required service 'ProtocolLLMClient' not found in container",
                error_code=EnumCoreErrorCode.SERVICE_UNAVAILABLE,
                context={"service_name": "ProtocolLLMClient"},
            )
        # Verify protocol compliance via duck-typing (check required method exists)
        if not callable(getattr(llm_client, "complete", None)):
            raise ModelOnexError(
                message=(
                    "Service 'ProtocolLLMClient' does not implement "
                    "required 'complete' method"
                ),
                error_code=EnumCoreErrorCode.CONTRACT_VIOLATION,
                context={
                    "service_name": "ProtocolLLMClient",
                    "missing_method": "complete",
                    "protocol": "ProtocolLLMClient",
                },
            )
        self.llm_client: ProtocolLLMClient = llm_client

        # Fail-fast DI resolution: Missing logger fails immediately with typed error
        logger: object | None = container.get_service("ProtocolLogger")
        if logger is None:
            raise ModelOnexError(
                message="Required service 'ProtocolLogger' not found in container",
                error_code=EnumCoreErrorCode.SERVICE_UNAVAILABLE,
                context={"service_name": "ProtocolLogger"},
            )
        # Verify protocol compliance via duck-typing (check required method exists)
        if not callable(getattr(logger, "error", None)):
            raise ModelOnexError(
                message=(
                    "Service 'ProtocolLogger' does not implement "
                    "required 'error' method"
                ),
                error_code=EnumCoreErrorCode.CONTRACT_VIOLATION,
                context={
                    "service_name": "ProtocolLogger",
                    "missing_method": "error",
                    "protocol": "ProtocolLogger",
                },
            )
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
        except json.JSONDecodeError as e:
            # Structured handling for JSON parse errors - no raw details in message
            self._log_error(f"Response parsing failed: {type(e).__name__}")
            raise ModelOnexError(
                message="Failed to parse LLM response as JSON",
                error_code=EnumCoreErrorCode.PARSING_ERROR,
                context={"error_type": "JSONDecodeError"},
            ) from e
        except ValidationError as e:
            # Structured handling for Pydantic validation errors - no raw details
            self._log_error(f"Response validation failed: {type(e).__name__}")
            raise ModelOnexError(
                message="LLM response failed schema validation",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
                context={
                    "error_type": "ValidationError",
                    "error_count": e.error_count(),
                },
            ) from e
        except (AttributeError, KeyError, TypeError) as e:
            # catch-all-ok: common runtime errors during response processing
            # Log error class without exposing raw message (may contain PII)
            self._log_error(f"Response processing failed: {type(e).__name__}")
            raise ModelOnexError(
                message="Failed to process LLM response",
                error_code=EnumCoreErrorCode.PROCESSING_ERROR,
                context={"error_type": type(e).__name__},
            ) from e
        except Exception as e:
            # boundary-ok: handler entry point must not crash; structured error response
            # Log error class without exposing raw message (may contain PII)
            self._log_error(f"Request handling failed: {type(e).__name__}")
            raise ModelOnexError(
                message="An error occurred processing your request",
                error_code=EnumCoreErrorCode.HANDLER_EXECUTION_ERROR,
                context={"error_type": type(e).__name__},
            ) from e

    def _format_prompt(self, request: SupportRequest) -> str:
        """Format the user request into an LLM prompt.

        Note: User identifiers and other PII are intentionally excluded from
        the prompt to prevent PII leakage to the LLM. Only the message content
        and non-PII metadata are included.

        PII Validation:
            - User identifier is NEVER included in prompts
            - Context fields are filtered via _filter_pii_from_context()
            - Validation asserts PII fields are removed before LLM call

        Args:
            request: The support request to format.

        Returns:
            Formatted prompt string for the LLM.
        """
        parts = []

        # Add user message (content only, no identifiers)
        parts.append(f"User Message: {request.message}")

        # SECURITY: User identifier intentionally excluded to minimize PII in prompts
        # The identifier is tracked server-side for request correlation

        # Add urgency level (non-PII metadata)
        parts.append(f"Urgency Level: {request.urgency}")

        # Add context if provided, filtering out potential PII fields
        if request.context:
            # Filter context to exclude common PII fields
            safe_context = self._filter_pii_from_context(request.context)

            # PII Validation: Assert that known PII fields were filtered out
            self._validate_pii_filtered(request.context, safe_context)

            if safe_context:
                context_str = json.dumps(safe_context, indent=2)
                parts.append(f"Previous Context:\n{context_str}")

        return "\n\n".join(parts)

    def _validate_pii_filtered(
        self, original: dict[str, str], filtered: dict[str, str]
    ) -> None:
        """Validate that PII fields were properly filtered from context.

        This is a defense-in-depth check to ensure PII filtering is working
        correctly before sending data to the LLM.

        Args:
            original: The original context dictionary.
            filtered: The filtered context dictionary.

        Raises:
            ModelOnexError: If PII fields are detected in the filtered output.
        """
        # Critical PII fields that MUST be filtered
        critical_pii_fields = {
            "email",
            "phone",
            "ssn",
            "social_security",
            "credit_card",
            "password",
            "api_key",
            "user_id",
            "user_identifier",
        }

        # Check that no critical PII fields exist in filtered output
        leaked_fields = critical_pii_fields & set(filtered.keys())
        if leaked_fields:
            raise ModelOnexError(
                message="PII filtering failed: critical fields detected in output",
                error_code=EnumCoreErrorCode.SECURITY_VIOLATION,
                context={
                    "leaked_field_count": len(leaked_fields),
                    # Don't log actual field names to avoid PII in logs
                },
            )

    def _filter_pii_from_context(self, context: dict[str, str]) -> dict[str, str]:
        """Filter potential PII fields from context before sending to LLM.

        Args:
            context: The context dictionary to filter.

        Returns:
            Filtered context with PII fields removed.
        """
        # Fields that commonly contain PII - comprehensive list for robust filtering
        # Expanded list addresses PR review nitpick for robustness
        pii_fields = {
            # Names
            "name",
            "full_name",
            "first_name",
            "last_name",
            "middle_name",
            "maiden_name",
            "nickname",
            "display_name",
            # Contact information
            "email",
            "email_address",
            "phone",
            "phone_number",
            "mobile",
            "mobile_number",
            "cell",
            "cell_phone",
            "telephone",
            "fax",
            "fax_number",
            "address",
            "street_address",
            "mailing_address",
            "home_address",
            "work_address",
            "billing_address",
            "shipping_address",
            "city",
            "state",
            "province",
            "country",
            "zip_code",
            "postal_code",
            "zipcode",
            # Identity documents
            "ssn",
            "social_security",
            "social_security_number",
            "passport",
            "passport_number",
            "drivers_license",
            "driver_license",
            "license_number",
            "national_id",
            "id_number",
            "tax_id",
            "ein",
            "itin",
            "sin",  # Social Insurance Number (Canada)
            "nino",  # National Insurance Number (UK)
            # Financial information
            "credit_card",
            "card_number",
            "cvv",
            "cvc",
            "expiry_date",
            "expiration_date",
            "bank_account",
            "account_number",
            "routing_number",
            "iban",
            "swift",
            "bic",
            "sort_code",
            # Credentials and secrets
            "password",
            "passwd",
            "pwd",
            "api_key",
            "apikey",
            "token",
            "auth_token",
            "access_token",
            "refresh_token",
            "secret",
            "secret_key",
            "access_key",
            "private_key",
            "encryption_key",
            "session_id",
            "session_token",
            # User identifiers
            "user_id",
            "userid",
            "user_identifier",
            "customer_id",
            "customerid",
            "member_id",
            "account_id",
            "username",
            "user_name",
            "login",
            "login_id",
            # Date of birth and age
            "date_of_birth",
            "dob",
            "birthdate",
            "birth_date",
            "birth_year",
            "birth_month",
            "birth_day",
            "age",
            # Demographics
            "gender",
            "sex",
            "race",
            "ethnicity",
            "nationality",
            "religion",
            "marital_status",
            # Employment
            "employer",
            "occupation",
            "job_title",
            "salary",
            "income",
            "employee_id",
            # Network and device identifiers
            "ip_address",
            "ip",
            "ipv4",
            "ipv6",
            "mac_address",
            "device_id",
            "imei",
            "imsi",
            "serial_number",
            # Medical information (HIPAA)
            "medical_record",
            "patient_id",
            "health_id",
            "diagnosis",
            "treatment",
            "prescription",
            "insurance_id",
            "policy_number",
            # Biometric data
            "fingerprint",
            "face_id",
            "retina",
            "voice_print",
            "dna",
            # Education
            "student_id",
            "school",
            "grade",
            "gpa",
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
            "I apologize, but I had trouble processing your request. Please try again."
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
        """Validate that parsed JSON has the expected SupportResponse schema shape.

        JSON Schema Validation:
            This method performs structural validation BEFORE creating the Pydantic
            model. This two-phase validation (shape check then Pydantic) provides:
            1. Early rejection of malformed LLM responses
            2. Clear separation between parsing errors and validation errors
            3. Defense against injection attacks via unexpected field types

        Expected Schema Shape:
            {
                "response_text": str (non-empty, required),
                "suggested_actions": list[str] (optional),
                "confidence": float (0.0-1.0, required),
                "requires_escalation": bool (required),
                "category": Literal["billing", "technical", "general", "account"],
                "sentiment": Literal["positive", "neutral", "negative"]
            }

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

        # Schema validation: Check all required fields are present
        if not required_fields.issubset(set(data.keys())):
            return False

        # Schema validation: response_text must be a non-empty string
        response_text = data.get("response_text")
        if not isinstance(response_text, str) or not response_text.strip():
            return False

        # Schema validation: confidence must be a number (int or float)
        confidence = data.get("confidence")
        if not isinstance(confidence, (int, float)):
            return False

        # Schema validation: requires_escalation must be boolean
        requires_escalation = data.get("requires_escalation")
        if not isinstance(requires_escalation, bool):
            return False

        # Schema validation: category must be one of the valid Literal values
        # Uses lazy accessor for DRY compliance with model annotations
        category = data.get("category")
        valid_categories = get_valid_categories()
        if not isinstance(category, str) or category.lower() not in valid_categories:
            return False

        # Schema validation: sentiment must be one of the valid Literal values
        # Uses lazy accessor for DRY compliance with model annotations
        sentiment = data.get("sentiment")
        valid_sentiments = get_valid_sentiments()
        if not isinstance(sentiment, str) or sentiment.lower() not in valid_sentiments:
            return False

        # Optional field validation: suggested_actions must be a list if present
        suggested_actions = data.get("suggested_actions")
        if suggested_actions is not None and not isinstance(suggested_actions, list):
            return False

        return True

    # NOTE(OMN-1201): allow_dict_any decorator is untyped; safe because it only
    # suppresses dict[str, Any] type checking for LLM response parsing.
    @allow_dict_any(reason="LLM JSON responses have arbitrary structure")  # type: ignore[untyped-decorator]
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
            # NOTE(OMN-1201): value is typed as object but float() handles any type
            # at runtime, raising TypeError/ValueError on invalid input (caught below).
            conf = float(value)  # type: ignore[arg-type]
            return max(0.0, min(1.0, conf))
        except (TypeError, ValueError):
            # fallback-ok: return safe default when conversion fails
            return 0.5

    def _ensure_category(
        self, value: object
    ) -> Literal["billing", "technical", "general", "account"]:
        """Ensure category is a valid literal.

        Uses lazy accessor get_valid_categories() for DRY compliance with
        model annotations, avoiding import-time side effects.

        Args:
            value: The value to validate.

        Returns:
            Valid category literal.
        """
        str_value = str(value).lower()
        if str_value in get_valid_categories():
            # NOTE(OMN-1201): str_value is validated against Literal values above;
            # mypy can't narrow str to Literal from set membership check.
            return str_value  # type: ignore[return-value]
        return "general"

    def _ensure_sentiment(
        self, value: object
    ) -> Literal["positive", "neutral", "negative"]:
        """Ensure sentiment is a valid literal.

        Uses lazy accessor get_valid_sentiments() for DRY compliance with
        model annotations, avoiding import-time side effects.

        Args:
            value: The value to validate.

        Returns:
            Valid sentiment literal.
        """
        str_value = str(value).lower()
        if str_value in get_valid_sentiments():
            # NOTE(OMN-1201): str_value is validated against Literal values above;
            # mypy can't narrow str to Literal from set membership check.
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
    "get_valid_categories",
    "get_valid_sentiments",
]
