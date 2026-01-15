# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for SupportAssistantHandler.

This module tests the SupportAssistantHandler using MockLLMClient for fast,
deterministic unit tests without making actual LLM API calls.

Test Categories:
    TestHandlerContract: Verifies DI container usage and contract compliance.
    TestResponseQuality: Verifies response quality and structure.
    TestErrorHandling: Verifies error handling and edge cases.
    TestJSONParsing: Verifies LLM response JSON parsing.
"""

import asyncio
import inspect
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from examples.demo.handlers.support_assistant import SupportRequest, SupportResponse
from examples.demo.handlers.support_assistant.handler_mock import MockLLMClient
from examples.demo.handlers.support_assistant.handler_support_assistant import (
    SupportAssistantHandler,
)
from examples.demo.handlers.support_assistant.protocol_llm_client import (
    ProtocolLLMClient,
)


@pytest.fixture
def mock_container() -> MagicMock:
    """Create a mock ONEX container with MockLLMClient registered.

    Returns:
        MagicMock container with get_service returning appropriate mocks.
    """
    container = MagicMock()
    mock_llm = MockLLMClient()
    mock_logger = MagicMock()

    def get_service(protocol_name: str) -> Any:
        if protocol_name == "ProtocolLLMClient":
            return mock_llm
        if protocol_name == "ProtocolLogger":
            return mock_logger
        raise ValueError(f"Unknown protocol: {protocol_name}")

    container.get_service = MagicMock(side_effect=get_service)
    return container


@pytest.fixture
def mock_container_with_escalation() -> MagicMock:
    """Create a mock container with escalation scenario LLM client."""
    container = MagicMock()
    mock_llm = MockLLMClient(scenario="escalation")
    mock_logger = MagicMock()

    def get_service(protocol_name: str) -> Any:
        if protocol_name == "ProtocolLLMClient":
            return mock_llm
        if protocol_name == "ProtocolLogger":
            return mock_logger
        raise ValueError(f"Unknown protocol: {protocol_name}")

    container.get_service = MagicMock(side_effect=get_service)
    return container


@pytest.fixture
def mock_container_with_invalid_json() -> MagicMock:
    """Create a mock container with invalid JSON scenario."""
    container = MagicMock()
    mock_llm = MockLLMClient(scenario="invalid_json")
    mock_logger = MagicMock()

    def get_service(protocol_name: str) -> Any:
        if protocol_name == "ProtocolLLMClient":
            return mock_llm
        if protocol_name == "ProtocolLogger":
            return mock_logger
        raise ValueError(f"Unknown protocol: {protocol_name}")

    container.get_service = MagicMock(side_effect=get_service)
    return container


@pytest.fixture(scope="module")
def sample_request() -> SupportRequest:
    """Create a sample support request for testing.

    Uses module scope since SupportRequest is immutable after creation.
    """
    return SupportRequest(
        user_identifier="user-123",
        message="I need help with my billing statement.",
        urgency="medium",
    )


@pytest.fixture(scope="module")
def high_urgency_request() -> SupportRequest:
    """Create a high urgency request that may trigger escalation.

    Uses module scope since SupportRequest is immutable after creation.
    """
    return SupportRequest(
        user_identifier="user-456",
        message="I'm very frustrated! My payment failed and I've been charged twice!",
        urgency="high",
    )


@pytest.mark.unit
class TestHandlerContract:
    """Tests for handler contract and DI compliance."""

    def test_handler_uses_di_container_correctly(
        self, mock_container: MagicMock
    ) -> None:
        """Handler correctly resolves services from DI container."""
        handler = SupportAssistantHandler(mock_container)

        # Verify get_service was called for required protocols
        mock_container.get_service.assert_any_call("ProtocolLLMClient")
        mock_container.get_service.assert_any_call("ProtocolLogger")

        # Verify handler has required attributes
        assert hasattr(handler, "llm_client")
        assert hasattr(handler, "logger")
        assert hasattr(handler, "container")

    def test_handler_llm_client_implements_protocol(
        self, mock_container: MagicMock
    ) -> None:
        """LLM client from container implements ProtocolLLMClient."""
        handler = SupportAssistantHandler(mock_container)

        # Verify LLM client satisfies protocol
        assert isinstance(handler.llm_client, ProtocolLLMClient)

    def test_handle_method_is_async(self, mock_container: MagicMock) -> None:
        """Handle method must be async."""
        handler = SupportAssistantHandler(mock_container)

        # Verify handle is a coroutine function
        assert asyncio.iscoroutinefunction(handler.handle)

    def test_handle_method_signature(self, mock_container: MagicMock) -> None:
        """Handle method has correct signature."""
        handler = SupportAssistantHandler(mock_container)

        sig = inspect.signature(handler.handle)
        params = list(sig.parameters.keys())

        # Should have 'self' (implicit) and 'request' parameter
        assert "request" in params

    def test_input_schema_validated(self, mock_container: MagicMock) -> None:
        """Invalid input raises ValidationError."""
        # Test missing required field user_identifier
        with pytest.raises(ValidationError):
            SupportRequest(
                message="Test",
            )  # type: ignore[call-arg]

        # Test missing required field message
        with pytest.raises(ValidationError):
            SupportRequest(
                user_identifier="user-123",
            )  # type: ignore[call-arg]

        # Test invalid urgency value
        with pytest.raises(ValidationError):
            SupportRequest(
                user_identifier="user-123",
                message="Test",
                urgency="critical",  # type: ignore[arg-type]
            )

    def test_output_schema_validated(
        self, mock_container: MagicMock, sample_request: SupportRequest
    ) -> None:
        """Output always matches SupportResponse schema."""
        handler = SupportAssistantHandler(mock_container)

        response = asyncio.run(handler.handle(sample_request))

        # Verify response is valid SupportResponse
        assert isinstance(response, SupportResponse)

        # Verify all required fields are present
        assert response.response_text is not None
        assert response.suggested_actions is not None
        assert 0.0 <= response.confidence <= 1.0
        assert isinstance(response.requires_escalation, bool)
        assert response.category in ["billing", "technical", "general", "account"]
        assert response.sentiment in ["positive", "neutral", "negative"]


@pytest.mark.unit
class TestResponseQuality:
    """Tests for response quality and content."""

    def test_response_is_not_empty(
        self, mock_container: MagicMock, sample_request: SupportRequest
    ) -> None:
        """Response text is never empty."""
        handler = SupportAssistantHandler(mock_container)

        response = asyncio.run(handler.handle(sample_request))

        assert response.response_text
        assert len(response.response_text) > 0

    def test_response_addresses_input(
        self, mock_container: MagicMock, sample_request: SupportRequest
    ) -> None:
        """Response relates to the input message."""
        handler = SupportAssistantHandler(mock_container)

        response = asyncio.run(handler.handle(sample_request))

        # Response should not be generic - should relate to billing
        assert response.category == "billing"

    def test_suggested_actions_are_actionable(
        self, mock_container: MagicMock, sample_request: SupportRequest
    ) -> None:
        """Suggested actions are concrete steps."""
        handler = SupportAssistantHandler(mock_container)

        response = asyncio.run(handler.handle(sample_request))

        # Should have at least one suggested action
        assert len(response.suggested_actions) > 0

        # Each action should be a non-empty string
        for action in response.suggested_actions:
            assert isinstance(action, str)
            assert len(action) > 0

    def test_escalation_for_high_urgency(
        self,
        mock_container_with_escalation: MagicMock,
        high_urgency_request: SupportRequest,
    ) -> None:
        """High urgency with negative sentiment may trigger escalation flag."""
        handler = SupportAssistantHandler(mock_container_with_escalation)

        response = asyncio.run(handler.handle(high_urgency_request))

        # With escalation scenario, should be escalated
        assert response.requires_escalation is True

    def test_confidence_in_valid_range(
        self, mock_container: MagicMock, sample_request: SupportRequest
    ) -> None:
        """Confidence score is always between 0 and 1."""
        handler = SupportAssistantHandler(mock_container)

        response = asyncio.run(handler.handle(sample_request))

        assert 0.0 <= response.confidence <= 1.0

    def test_category_is_valid(
        self, mock_container: MagicMock, sample_request: SupportRequest
    ) -> None:
        """Category is one of the valid categories."""
        handler = SupportAssistantHandler(mock_container)

        response = asyncio.run(handler.handle(sample_request))

        valid_categories = {"billing", "technical", "general", "account"}
        assert response.category in valid_categories

    def test_sentiment_is_valid(
        self, mock_container: MagicMock, sample_request: SupportRequest
    ) -> None:
        """Sentiment is one of the valid sentiments."""
        handler = SupportAssistantHandler(mock_container)

        response = asyncio.run(handler.handle(sample_request))

        valid_sentiments = {"positive", "neutral", "negative"}
        assert response.sentiment in valid_sentiments


@pytest.mark.unit
class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_handles_llm_api_error_gracefully(
        self, sample_request: SupportRequest
    ) -> None:
        """Handler raises ModelOnexError when LLM API fails.

        This ensures structured error handling with proper error codes
        rather than silently returning error responses.
        """
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
        from omnibase_core.errors import ModelOnexError

        container = MagicMock()
        mock_llm = MockLLMClient(should_fail=True, error_message="API timeout")
        mock_logger = MagicMock()

        def get_service(protocol_name: str) -> Any:
            if protocol_name == "ProtocolLLMClient":
                return mock_llm
            if protocol_name == "ProtocolLogger":
                return mock_logger
            raise ValueError(f"Unknown protocol: {protocol_name}")

        container.get_service = MagicMock(side_effect=get_service)

        handler = SupportAssistantHandler(container)

        # Should raise ModelOnexError with structured error info
        with pytest.raises(ModelOnexError) as exc_info:
            asyncio.run(handler.handle(sample_request))

        # Verify structured error properties
        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.HANDLER_EXECUTION_ERROR
        # Context may be nested; check error_type is captured somewhere in context
        context_str = str(error.context)
        assert "error_type" in context_str
        assert "RuntimeError" in context_str
        # Error message should not expose raw exception details (security)
        assert "API timeout" not in error.message

    def test_handles_empty_message(self, mock_container: MagicMock) -> None:
        """Handler handles empty message gracefully."""
        request = SupportRequest(
            user_identifier="user-789",
            message="",
        )

        handler = SupportAssistantHandler(mock_container)
        response = asyncio.run(handler.handle(request))

        # Should still return valid response
        assert isinstance(response, SupportResponse)

    def test_handles_very_long_message(self, mock_container: MagicMock) -> None:
        """Handler handles very long messages."""
        long_message = "Help with billing issue. " * 1000

        request = SupportRequest(
            user_identifier="user-999",
            message=long_message,
            urgency="low",
        )

        handler = SupportAssistantHandler(mock_container)
        response = asyncio.run(handler.handle(request))

        assert isinstance(response, SupportResponse)


@pytest.mark.unit
class TestJSONParsing:
    """Tests for JSON parsing of LLM responses."""

    def test_parses_valid_json_response(
        self, mock_container: MagicMock, sample_request: SupportRequest
    ) -> None:
        """Handler correctly parses valid JSON from LLM."""
        handler = SupportAssistantHandler(mock_container)

        response = asyncio.run(handler.handle(sample_request))

        # Should have parsed correctly into SupportResponse
        assert isinstance(response, SupportResponse)
        assert response.response_text

    def test_handles_invalid_json_gracefully(
        self,
        mock_container_with_invalid_json: MagicMock,
        sample_request: SupportRequest,
    ) -> None:
        """Handler returns fallback response for invalid JSON."""
        handler = SupportAssistantHandler(mock_container_with_invalid_json)

        response = asyncio.run(handler.handle(sample_request))

        # Should return a valid SupportResponse with low confidence
        assert isinstance(response, SupportResponse)
        assert response.confidence < 0.5

    def test_extracts_json_from_text(self, sample_request: SupportRequest) -> None:
        """Handler can extract JSON embedded in text."""
        container = MagicMock()

        # Create a client that returns JSON wrapped in text
        class EmbeddedJSONClient(MockLLMClient):
            async def complete(
                self, prompt: str, system_prompt: str | None = None
            ) -> str:
                return """Here is my response:

```json
{
    "response_text": "I can help with that billing question.",
    "suggested_actions": ["Check your statement", "Contact billing"],
    "confidence": 0.88,
    "requires_escalation": false,
    "category": "billing",
    "sentiment": "neutral"
}
```

Let me know if you need anything else!"""

        mock_logger = MagicMock()

        def get_service(protocol_name: str) -> Any:
            if protocol_name == "ProtocolLLMClient":
                return EmbeddedJSONClient()
            if protocol_name == "ProtocolLogger":
                return mock_logger
            raise ValueError(f"Unknown protocol: {protocol_name}")

        container.get_service = MagicMock(side_effect=get_service)

        handler = SupportAssistantHandler(container)
        response = asyncio.run(handler.handle(sample_request))

        assert isinstance(response, SupportResponse)
        # Should have extracted the JSON successfully
        assert response.confidence >= 0.5


@pytest.mark.unit
class TestContextHandling:
    """Tests for context handling in requests."""

    def test_uses_context_when_provided(self, mock_container: MagicMock) -> None:
        """Handler uses provided context in prompt."""
        request = SupportRequest(
            user_identifier="user-ctx",
            message="What about my previous question?",
            context={"previous_message": "I asked about billing"},
            urgency="medium",
        )

        handler = SupportAssistantHandler(mock_container)
        response = asyncio.run(handler.handle(request))

        # Should process successfully
        assert isinstance(response, SupportResponse)

        # Verify LLM was called with context in prompt
        llm_client = mock_container.get_service("ProtocolLLMClient")
        assert llm_client.last_prompt is not None
        assert "previous_message" in llm_client.last_prompt

    def test_handles_none_context(self, mock_container: MagicMock) -> None:
        """Handler handles None context gracefully."""
        request = SupportRequest(
            user_identifier="user-no-ctx",
            message="Help me please",
            context=None,
        )

        handler = SupportAssistantHandler(mock_container)
        response = asyncio.run(handler.handle(request))

        assert isinstance(response, SupportResponse)


@pytest.mark.unit
class TestUrgencyHandling:
    """Tests for urgency level handling."""

    def test_low_urgency_processed(self, mock_container: MagicMock) -> None:
        """Low urgency requests are processed normally."""
        request = SupportRequest(
            user_identifier="user-low",
            message="Just a quick question about features",
            urgency="low",
        )

        handler = SupportAssistantHandler(mock_container)
        response = asyncio.run(handler.handle(request))

        assert isinstance(response, SupportResponse)

    def test_high_urgency_included_in_prompt(self, mock_container: MagicMock) -> None:
        """High urgency is communicated to LLM in prompt."""
        request = SupportRequest(
            user_identifier="user-high",
            message="Critical issue with my account!",
            urgency="high",
        )

        handler = SupportAssistantHandler(mock_container)
        asyncio.run(handler.handle(request))

        # Verify urgency was included in prompt
        llm_client = mock_container.get_service("ProtocolLLMClient")
        assert llm_client.last_prompt is not None
        assert "high" in llm_client.last_prompt.lower()


@pytest.mark.unit
class TestProtocolCompliance:
    """Tests for ProtocolLLMClient compliance."""

    def test_mock_client_is_protocol_compliant(self) -> None:
        """MockLLMClient implements ProtocolLLMClient."""
        client = MockLLMClient()
        assert isinstance(client, ProtocolLLMClient)

    def test_mock_client_health_check(self) -> None:
        """MockLLMClient health check works."""
        client = MockLLMClient(is_healthy=True)
        assert asyncio.run(client.health_check()) is True

        client_unhealthy = MockLLMClient(is_healthy=False)
        assert asyncio.run(client_unhealthy.health_check()) is False
