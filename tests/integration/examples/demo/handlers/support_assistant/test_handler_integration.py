# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Integration tests for SupportAssistantHandler with local LLM.

These tests verify the handler works correctly with a real local LLM server.
Tests are marked with @pytest.mark.integration and may be skipped if the
local model is unavailable.

Note:
    These tests require a running local LLM server at the configured endpoint.
    Default endpoint: http://192.168.86.100:8200 (configurable via env var).

    To run these tests:
        poetry run pytest tests/integration/examples/demo/handlers/support_assistant/ -v

    To skip if server unavailable:
        These tests will be automatically skipped if the local server is not reachable.
"""

import asyncio
import json
import os
from typing import Any
from unittest.mock import MagicMock

import pytest

from examples.demo.handlers.support_assistant import SupportRequest, SupportResponse
from examples.demo.handlers.support_assistant.handler_local import LocalLLMClient
from examples.demo.handlers.support_assistant.handler_support_assistant import (
    SupportAssistantHandler,
)
from examples.demo.handlers.support_assistant.protocol_llm_client import (
    ProtocolLLMClient,
)

# Configuration
LOCAL_LLM_URL = os.getenv("LLM_LOCAL_URL", "http://192.168.86.100:8200")
INTEGRATION_TEST_TIMEOUT_SECONDS = 120  # LLM calls can be slow


def is_local_server_available() -> bool:
    """Check if the local LLM server is reachable.

    Returns:
        True if server responds to health check, False otherwise.
    """
    try:
        # Synchronous check for pytest.mark.skipif
        import socket

        host = LOCAL_LLM_URL.replace("http://", "").split(":")[0]
        port = int(LOCAL_LLM_URL.split(":")[-1])

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


# Skip all tests if local server is not available
pytestmark = [
    pytest.mark.integration,
    pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS),
    pytest.mark.skipif(
        not is_local_server_available(),
        reason=f"Local LLM server not available at {LOCAL_LLM_URL}",
    ),
]


@pytest.fixture
def local_llm_client() -> LocalLLMClient:
    """Create a LocalLLMClient configured for the test server.

    Returns:
        Configured LocalLLMClient instance.
    """
    return LocalLLMClient(
        endpoint_url=LOCAL_LLM_URL,
        model_name=os.getenv("LLM_LOCAL_MODEL", "qwen2.5-14b"),
        temperature=0.7,
        max_tokens=500,
    )


@pytest.fixture
def integration_container(local_llm_client: LocalLLMClient) -> MagicMock:
    """Create a mock container with real LocalLLMClient.

    Args:
        local_llm_client: The real LLM client for integration tests.

    Returns:
        Mock container with real LLM client registered.
    """
    container = MagicMock()
    mock_logger = MagicMock()

    def get_service(protocol_name: str) -> Any:
        if protocol_name == "ProtocolLLMClient":
            return local_llm_client
        if protocol_name == "ProtocolLogger":
            return mock_logger
        raise ValueError(f"Unknown protocol: {protocol_name}")

    container.get_service = MagicMock(side_effect=get_service)
    return container


@pytest.fixture
def sample_billing_request() -> SupportRequest:
    """Create a sample billing support request."""
    return SupportRequest(
        user_identifier="integration-test-user",
        message="I have a question about my recent invoice. The amount seems incorrect.",
        urgency="medium",
    )


@pytest.fixture
def sample_technical_request() -> SupportRequest:
    """Create a sample technical support request."""
    return SupportRequest(
        user_identifier="integration-test-user-tech",
        message="My application keeps crashing when I try to upload files. Error: 500.",
        urgency="high",
    )


class TestLocalModelIntegration:
    """Integration tests verifying local LLM server connectivity and responses."""

    def test_local_model_responds(self, local_llm_client: LocalLLMClient) -> None:
        """Local model at configured endpoint responds to requests."""
        # Simple completion request
        response = asyncio.run(
            local_llm_client.complete(
                "Say hello.",
                system_prompt="Respond with a brief greeting.",
            )
        )

        assert response is not None
        assert len(response) > 0

    def test_local_model_health_check(self, local_llm_client: LocalLLMClient) -> None:
        """Local model health check returns True when available."""
        is_healthy = asyncio.run(local_llm_client.health_check())

        assert is_healthy is True

    def test_local_llm_client_protocol_compliant(
        self, local_llm_client: LocalLLMClient
    ) -> None:
        """LocalLLMClient implements ProtocolLLMClient."""
        assert isinstance(local_llm_client, ProtocolLLMClient)


class TestHandlerWithLocalModel:
    """Integration tests for SupportAssistantHandler with local LLM."""

    def test_handler_processes_billing_request(
        self,
        integration_container: MagicMock,
        sample_billing_request: SupportRequest,
    ) -> None:
        """Handler successfully processes a billing request via local LLM."""
        handler = SupportAssistantHandler(integration_container)

        response = asyncio.run(handler.handle(sample_billing_request))

        # Verify response is valid
        assert isinstance(response, SupportResponse)
        assert response.response_text
        assert len(response.response_text) > 0

    def test_handler_processes_technical_request(
        self,
        integration_container: MagicMock,
        sample_technical_request: SupportRequest,
    ) -> None:
        """Handler successfully processes a technical request via local LLM."""
        handler = SupportAssistantHandler(integration_container)

        response = asyncio.run(handler.handle(sample_technical_request))

        assert isinstance(response, SupportResponse)
        assert response.response_text
        assert len(response.suggested_actions) > 0

    def test_response_matches_schema(
        self,
        integration_container: MagicMock,
        sample_billing_request: SupportRequest,
    ) -> None:
        """Response from local model matches SupportResponse schema."""
        handler = SupportAssistantHandler(integration_container)

        response = asyncio.run(handler.handle(sample_billing_request))

        # All required fields should be present and valid
        assert isinstance(response, SupportResponse)
        assert isinstance(response.response_text, str)
        assert isinstance(response.suggested_actions, list)
        assert isinstance(response.confidence, float)
        assert 0.0 <= response.confidence <= 1.0
        assert isinstance(response.requires_escalation, bool)
        assert response.category in ["billing", "technical", "general", "account"]
        assert response.sentiment in ["positive", "neutral", "negative"]

    def test_response_has_meaningful_content(
        self,
        integration_container: MagicMock,
        sample_billing_request: SupportRequest,
    ) -> None:
        """Response contains meaningful, non-empty content."""
        handler = SupportAssistantHandler(integration_container)

        response = asyncio.run(handler.handle(sample_billing_request))

        # Response text should be substantial (not just "OK" or similar)
        assert len(response.response_text) > 20

        # Should have at least one actionable suggestion
        assert len(response.suggested_actions) >= 1
        for action in response.suggested_actions:
            assert len(action) > 5  # Not just "ok" or "yes"


class TestJSONResponseQuality:
    """Tests for JSON response quality from local LLM."""

    def test_response_is_valid_json(self, local_llm_client: LocalLLMClient) -> None:
        """Local model returns valid JSON when instructed."""
        system_prompt = """Respond only with valid JSON matching this schema:
{
    "response_text": "your response",
    "suggested_actions": ["action1"],
    "confidence": 0.9,
    "requires_escalation": false,
    "category": "general",
    "sentiment": "neutral"
}"""

        response = asyncio.run(
            local_llm_client.complete(
                "Help me with my account settings.",
                system_prompt=system_prompt,
            )
        )

        # Should be parseable as JSON
        try:
            data = json.loads(response)
            assert "response_text" in data or "responseText" in data
        except json.JSONDecodeError:
            # Some models wrap in markdown, try to extract
            import re

            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                assert data is not None
            else:
                pytest.fail(f"Could not parse JSON from response: {response[:200]}")


class TestProviderClientCreation:
    """Tests for creating provider clients from config."""

    def test_local_client_from_config(self) -> None:
        """LocalLLMClient can be created from ModelConfig."""
        from examples.demo.handlers.support_assistant.model_config import LOCAL_CONFIG

        client = LocalLLMClient.from_config(LOCAL_CONFIG)

        assert client is not None
        assert client.endpoint_url == LOCAL_CONFIG.endpoint_url
        assert client.model_name == LOCAL_CONFIG.model_name

    def test_local_client_invalid_provider_raises(self) -> None:
        """Creating LocalLLMClient with wrong provider raises ValueError."""
        from examples.demo.handlers.support_assistant.model_config import OPENAI_CONFIG

        with pytest.raises(ValueError, match="Expected local provider"):
            LocalLLMClient.from_config(OPENAI_CONFIG)


class TestErrorRecovery:
    """Tests for error recovery with local model."""

    def test_handles_timeout_gracefully(self) -> None:
        """Handler handles timeout errors gracefully."""
        # Create client with very short timeout
        client = LocalLLMClient(
            endpoint_url=LOCAL_LLM_URL,
            timeout=0.001,  # Nearly instant timeout
        )

        container = MagicMock()
        mock_logger = MagicMock()

        def get_service(protocol_name: str) -> Any:
            if protocol_name == "ProtocolLLMClient":
                return client
            if protocol_name == "ProtocolLogger":
                return mock_logger
            raise ValueError(f"Unknown protocol: {protocol_name}")

        container.get_service = MagicMock(side_effect=get_service)

        handler = SupportAssistantHandler(container)
        request = SupportRequest(user_identifier="test", message="Hello")

        # Should return error response, not raise
        response = asyncio.run(handler.handle(request))

        assert isinstance(response, SupportResponse)
        assert response.confidence < 0.5  # Low confidence for errors
