# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Integration tests for SupportAssistantHandler with local LLM.

These tests verify the handler works correctly with a real local LLM server.
Tests are marked with @pytest.mark.integration and may be skipped if the
local model is unavailable.

Note:
    The endpoint comes from the variable named by
    metadata.provider_config.local.endpoint_env in
    examples/demo/handlers/support_assistant/support_assistant.yaml, currently
    LOCAL_LLM_ENDPOINT. Tests that need a server are skipped when it is unset.

    To run these tests:
        LOCAL_LLM_ENDPOINT=<scheme>://<host>:<port> uv run pytest tests/integration/examples/demo/handlers/support_assistant/ -v

    To skip if server unavailable:
        These tests will be automatically skipped if the local server is not reachable.
"""

import ast
import asyncio
import json
import socket
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from urllib.parse import urlparse

import pytest
from pydantic import ValidationError

from examples.demo.handlers.support_assistant import SupportRequest, SupportResponse
from examples.demo.handlers.support_assistant.handler_local import LocalLLMClient
from examples.demo.handlers.support_assistant.handler_support_assistant import (
    SupportAssistantHandler,
)
from examples.demo.handlers.support_assistant.model_config import (
    ModelConfig,
    load_config_from_contract,
)
from examples.demo.handlers.support_assistant.protocol_llm_client import (
    ProtocolLLMClient,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError

# Must equal the contract's provider_config.local.endpoint_env.
_LOCAL_ENDPOINT_ENV = "LOCAL_LLM_ENDPOINT"
INTEGRATION_TEST_TIMEOUT_SECONDS = 120  # LLM calls can be slow


def resolve_local_config() -> tuple[ModelConfig | None, str]:
    """Resolve local configuration through the contract-aware boundary."""
    try:
        return load_config_from_contract("local"), ""
    except ValidationError:
        raise
    except ValueError as exc:
        return None, str(exc)


def endpoint_socket_address(endpoint_url: str) -> tuple[str, int]:
    """Extract the required host and explicit port from an HTTP endpoint."""
    try:
        parsed = urlparse(endpoint_url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ModelOnexError(
            message="Local LLM endpoint must have a valid hostname and explicit port",
            error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
            context={"endpoint_url": endpoint_url},
        ) from exc

    if parsed.scheme not in {"http", "https"} or hostname is None or port is None:
        raise ModelOnexError(
            message="Local LLM endpoint requires HTTP or HTTPS, a hostname and explicit port",
            error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
            context={"endpoint_url": endpoint_url},
        )
    return hostname, port


def is_local_server_available(config: ModelConfig | None) -> bool:
    """Check if the local LLM server is reachable.

    Returns:
        True if server responds to health check, False otherwise.
    """
    if config is None or config.endpoint_url is None:
        return False
    host, port = endpoint_socket_address(config.endpoint_url)

    try:
        # Synchronous check for pytest.mark.skipif
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            return result == 0
    except OSError:
        # boundary-ok: availability check must not crash pytest collection
        return False


LOCAL_CONFIG, _LOCAL_CONFIG_REASON = resolve_local_config()
requires_local_server = pytest.mark.skipif(
    not is_local_server_available(LOCAL_CONFIG),
    reason=_LOCAL_CONFIG_REASON
    or (
        f"Local LLM server not reachable at {LOCAL_CONFIG.endpoint_url}"
        if LOCAL_CONFIG is not None
        else "Local LLM configuration is unavailable"
    ),
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS),
]


@pytest.fixture
def local_llm_client() -> LocalLLMClient:
    """Create a LocalLLMClient configured for the test server.

    Returns:
        Configured LocalLLMClient instance.
    """
    config = LOCAL_CONFIG
    assert config is not None
    return LocalLLMClient.from_config(config)


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


@requires_local_server
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


@requires_local_server
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


@requires_local_server
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
        """LocalLLMClient accepts an explicitly configured local endpoint."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        config = ModelConfig(
            provider="local",
            model_name="qwen2.5-coder-14b",
            endpoint_url="https://llm.example.test:8200",
        )
        client = LocalLLMClient.from_config(config)

        assert client is not None
        assert client.endpoint_url == config.endpoint_url
        assert client.model_name == config.model_name

    def test_local_client_invalid_provider_raises(self) -> None:
        """Creating LocalLLMClient with wrong provider raises ModelOnexError."""
        from examples.demo.handlers.support_assistant.model_config import OPENAI_CONFIG

        with pytest.raises(ModelOnexError, match="Expected local provider"):
            LocalLLMClient.from_config(OPENAI_CONFIG)


@requires_local_server
class TestErrorRecovery:
    """Tests for error recovery with local model."""

    def test_timeout_raises_model_onex_error(self) -> None:
        """Handler raises ModelOnexError on timeout rather than returning gracefully.

        The handler converts timeout errors to structured ModelOnexError exceptions,
        which is the expected ONEX error handling pattern.
        """
        # Create client with very short timeout to force timeout error
        config = LOCAL_CONFIG
        assert config is not None
        assert config.endpoint_url is not None
        client = LocalLLMClient(
            endpoint_url=config.endpoint_url,
            model_name=config.model_name,
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

        # Handler raises ModelOnexError on timeout - this is the expected behavior
        # for ONEX structured error handling
        with pytest.raises(ModelOnexError):
            asyncio.run(handler.handle(request))


class TestLocalEndpointConfiguration:
    """The local endpoint comes from the contract-aware config boundary only.

    These tests need no server: they cover the missing, malformed and explicit
    endpoint paths of the configuration this module runs against.
    """

    def test_module_reads_no_environment_and_names_no_default_host(self) -> None:
        """Neither this module nor its conftest reads the environment or a default host."""
        package_dir = Path(__file__).parent
        # Joined so this guard does not itself carry the host name it refuses.
        default_host = "".join(("local", "host"))
        for source_path in (Path(__file__), package_dir / "conftest.py"):
            if not source_path.exists():
                continue
            tree = ast.parse(source_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr in {
                    "getenv",
                    "environ",
                }:
                    pytest.fail(
                        f"{source_path.name}:{node.lineno} reads os.{node.attr}"
                    )
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    assert default_host not in node.value, (
                        f"{source_path.name}:{node.lineno} names a default host"
                    )

    def test_missing_endpoint_resolves_to_no_config_with_reason(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An unset endpoint variable yields no config and names the variable."""
        monkeypatch.delenv(_LOCAL_ENDPOINT_ENV, raising=False)

        config, reason = resolve_local_config()

        assert config is None
        assert _LOCAL_ENDPOINT_ENV in reason
        assert is_local_server_available(config) is False

    def test_explicit_endpoint_is_taken_from_contract_boundary(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A set endpoint is used verbatim with the contract's model name."""
        monkeypatch.setenv(_LOCAL_ENDPOINT_ENV, "https://llm.example.test:8200")

        config, reason = resolve_local_config()

        assert reason == ""
        assert config is not None
        assert config.endpoint_url == "https://llm.example.test:8200"
        assert config.model_name == load_config_from_contract("local").model_name
        assert endpoint_socket_address(config.endpoint_url) == (
            "llm.example.test",
            8200,
        )

    @pytest.mark.parametrize(
        "endpoint_url",
        [
            "llm.example.test:8200",
            "ftp://llm.example.test:8200",
            "http://:8200",
            "https://llm.example.test",
            "https://llm.example.test:port",
            "",
        ],
    )
    def test_malformed_endpoint_raises_configuration_error(
        self, endpoint_url: str
    ) -> None:
        """An endpoint without scheme, host or explicit port is refused, not defaulted."""
        with pytest.raises(ModelOnexError) as exc_info:
            endpoint_socket_address(endpoint_url)

        assert exc_info.value.error_code == EnumCoreErrorCode.CONFIGURATION_ERROR
