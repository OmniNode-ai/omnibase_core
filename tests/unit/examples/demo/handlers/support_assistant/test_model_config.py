# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ModelConfig - LLM provider configuration for demo support assistant.

This module tests the ModelConfig Pydantic model used for swapping between
different LLM providers (OpenAI, Anthropic, Local) in the OMN-1201 demo
support assistant handler.
"""

import json

import pytest
from pydantic import ValidationError


@pytest.mark.unit
class TestModelConfigBasics:
    """Test basic ModelConfig creation and defaults."""

    def test_create_with_minimal_required_fields(self):
        """ModelConfig can be created with only required fields."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        config = ModelConfig(provider="openai", model_name="gpt-4")
        assert config.provider == "openai"
        assert config.model_name == "gpt-4"

    def test_default_temperature(self):
        """Default temperature is 0.7."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        config = ModelConfig(provider="openai", model_name="gpt-4")
        assert config.temperature == 0.7

    def test_default_max_tokens(self):
        """Default max_tokens is 500."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        config = ModelConfig(provider="openai", model_name="gpt-4")
        assert config.max_tokens == 500

    def test_default_api_key_env(self):
        """Default api_key_env is OPENAI_API_KEY."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        config = ModelConfig(provider="openai", model_name="gpt-4")
        assert config.api_key_env == "OPENAI_API_KEY"

    def test_endpoint_url_default_none(self):
        """endpoint_url defaults to None for cloud providers."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        config = ModelConfig(provider="openai", model_name="gpt-4")
        assert config.endpoint_url is None


@pytest.mark.unit
class TestModelConfigValidation:
    """Test ModelConfig field validation."""

    def test_invalid_provider_rejected(self):
        """Invalid provider value is rejected."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(provider="invalid", model_name="some-model")
        assert "provider" in str(exc_info.value)

    def test_temperature_valid_range_lower_bound(self):
        """Temperature at 0.0 is valid."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        config = ModelConfig(provider="openai", model_name="gpt-4", temperature=0.0)
        assert config.temperature == 0.0

    def test_temperature_valid_range_upper_bound(self):
        """Temperature at 2.0 is valid."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        config = ModelConfig(provider="openai", model_name="gpt-4", temperature=2.0)
        assert config.temperature == 2.0

    def test_temperature_below_range_rejected(self):
        """Temperature below 0.0 is rejected."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(provider="openai", model_name="gpt-4", temperature=-0.1)
        assert "temperature" in str(exc_info.value)

    def test_temperature_above_range_rejected(self):
        """Temperature above 2.0 is rejected."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(provider="openai", model_name="gpt-4", temperature=2.1)
        assert "temperature" in str(exc_info.value)

    def test_max_tokens_positive_integer(self):
        """max_tokens accepts positive integers."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        config = ModelConfig(provider="openai", model_name="gpt-4", max_tokens=1000)
        assert config.max_tokens == 1000

    def test_max_tokens_zero_rejected(self):
        """max_tokens of zero is rejected."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(provider="openai", model_name="gpt-4", max_tokens=0)
        assert "max_tokens" in str(exc_info.value)

    def test_max_tokens_negative_rejected(self):
        """Negative max_tokens is rejected."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(provider="openai", model_name="gpt-4", max_tokens=-100)
        assert "max_tokens" in str(exc_info.value)


@pytest.mark.unit
class TestModelConfigLocalProvider:
    """Test local provider specific validation."""

    def test_local_provider_requires_endpoint_url(self):
        """Local provider must have endpoint_url set."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(provider="local", model_name="qwen2.5-14b")
        assert "endpoint_url" in str(exc_info.value).lower()

    def test_local_provider_with_valid_endpoint(self):
        """Local provider with valid endpoint_url succeeds."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        config = ModelConfig(
            provider="local",
            model_name="qwen2.5-14b",
            endpoint_url="http://localhost:8200",
        )
        assert config.provider == "local"
        assert config.endpoint_url == "http://localhost:8200"

    def test_cloud_provider_without_endpoint_url(self):
        """Cloud providers (openai, anthropic) work without endpoint_url."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        config_openai = ModelConfig(provider="openai", model_name="gpt-4")
        assert config_openai.endpoint_url is None

        config_anthropic = ModelConfig(
            provider="anthropic",
            model_name="claude-3-5-sonnet",
            api_key_env="ANTHROPIC_API_KEY",
        )
        assert config_anthropic.endpoint_url is None


@pytest.mark.unit
class TestModelProviderInjection:
    """Test provider injection pattern - from OMN-1201 requirements."""

    def test_openai_provider_configured(self):
        """OpenAI provider creates correct config."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        config = ModelConfig(
            provider="openai",
            model_name="gpt-4",
            temperature=0.7,
            api_key_env="OPENAI_API_KEY",
        )
        assert config.provider == "openai"
        assert config.model_name == "gpt-4"
        assert config.api_key_env == "OPENAI_API_KEY"

    def test_anthropic_provider_configured(self):
        """Anthropic provider creates correct config."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        config = ModelConfig(
            provider="anthropic",
            model_name="claude-3-5-sonnet",
            temperature=0.7,
            api_key_env="ANTHROPIC_API_KEY",
        )
        assert config.provider == "anthropic"
        assert config.model_name == "claude-3-5-sonnet"
        assert config.api_key_env == "ANTHROPIC_API_KEY"

    def test_local_provider_configured(self):
        """Local provider uses custom endpoint."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        config = ModelConfig(
            provider="local",
            model_name="qwen2.5-14b",
            endpoint_url="http://localhost:8200",
        )
        assert config.provider == "local"
        assert config.model_name == "qwen2.5-14b"
        assert config.endpoint_url == "http://localhost:8200"

    def test_config_swap_changes_behavior(self):
        """Different config = different provider."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        openai_config = ModelConfig(provider="openai", model_name="gpt-4")
        anthropic_config = ModelConfig(
            provider="anthropic",
            model_name="claude-3-5-sonnet",
            api_key_env="ANTHROPIC_API_KEY",
        )

        assert openai_config.provider != anthropic_config.provider
        assert openai_config.model_name != anthropic_config.model_name

    def test_provider_is_injectable(self):
        """Can create config with custom values."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        config = ModelConfig(
            provider="openai",
            model_name="gpt-3.5-turbo",
            temperature=0.5,
            max_tokens=1000,
            api_key_env="MY_CUSTOM_API_KEY",
        )
        assert config.provider == "openai"
        assert config.model_name == "gpt-3.5-turbo"
        assert config.temperature == 0.5
        assert config.max_tokens == 1000
        assert config.api_key_env == "MY_CUSTOM_API_KEY"


@pytest.mark.unit
class TestPredefinedConfigs:
    """Test pre-defined configuration constants."""

    def test_openai_config_exists(self):
        """OPENAI_CONFIG is defined and valid."""
        from examples.demo.handlers.support_assistant.model_config import OPENAI_CONFIG

        assert OPENAI_CONFIG.provider == "openai"
        assert OPENAI_CONFIG.model_name == "gpt-4o"
        assert OPENAI_CONFIG.temperature == 0.7

    def test_anthropic_config_exists(self):
        """ANTHROPIC_CONFIG is defined and valid."""
        from examples.demo.handlers.support_assistant.model_config import (
            ANTHROPIC_CONFIG,
        )

        assert ANTHROPIC_CONFIG.provider == "anthropic"
        assert ANTHROPIC_CONFIG.model_name == "claude-sonnet-4-20250514"
        assert ANTHROPIC_CONFIG.temperature == 0.7
        assert ANTHROPIC_CONFIG.api_key_env == "ANTHROPIC_API_KEY"

    def test_local_config_exists(self):
        """LOCAL_CONFIG is defined and valid.

        Note: endpoint_url uses LOCAL_LLM_ENDPOINT env var with default http://localhost:8000.
        """
        from examples.demo.handlers.support_assistant.model_config import LOCAL_CONFIG

        assert LOCAL_CONFIG.provider == "local"
        assert LOCAL_CONFIG.model_name == "qwen2.5-coder-14b"
        # endpoint_url uses env var LOCAL_LLM_ENDPOINT with default http://localhost:8000
        assert LOCAL_CONFIG.endpoint_url is not None


@pytest.mark.unit
class TestModelConfigSerialization:
    """Test serialization and deserialization."""

    def test_model_dump(self):
        """ModelConfig can be serialized to dict."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        config = ModelConfig(
            provider="openai",
            model_name="gpt-4",
            temperature=0.8,
            max_tokens=1000,
        )
        data = config.model_dump()

        assert data["provider"] == "openai"
        assert data["model_name"] == "gpt-4"
        assert data["temperature"] == 0.8
        assert data["max_tokens"] == 1000

    def test_model_validate_roundtrip(self):
        """ModelConfig can roundtrip through dict."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        original = ModelConfig(
            provider="anthropic",
            model_name="claude-3-5-sonnet",
            temperature=0.5,
            max_tokens=800,
            api_key_env="ANTHROPIC_API_KEY",
        )
        data = original.model_dump()
        restored = ModelConfig.model_validate(data)

        assert restored.provider == original.provider
        assert restored.model_name == original.model_name
        assert restored.temperature == original.temperature
        assert restored.max_tokens == original.max_tokens
        assert restored.api_key_env == original.api_key_env

    def test_model_dump_json(self):
        """ModelConfig can be serialized to JSON string."""
        from examples.demo.handlers.support_assistant.model_config import ModelConfig

        config = ModelConfig(provider="openai", model_name="gpt-4")
        json_str = config.model_dump_json()

        # Parse JSON to avoid format-brittle string comparison
        parsed = json.loads(json_str)
        assert parsed["provider"] == "openai"
        assert parsed["model_name"] == "gpt-4"


@pytest.mark.unit
class TestLoadConfigFromContract:
    """Tests for load_config_from_contract function.

    This function loads ModelConfig from the contract's provider_config section,
    making the contract the single source of truth for configuration values.
    """

    def test_load_openai_config_from_contract(self, tmp_path):
        """Load OpenAI config from contract YAML."""
        from examples.demo.handlers.support_assistant.model_config import (
            load_config_from_contract,
        )

        # Create a minimal contract YAML
        contract_content = """
metadata:
  provider_config:
    openai:
      model_name: "gpt-4o-test"
      temperature: 0.8
      max_tokens: 600
      api_key_env: "TEST_OPENAI_KEY"
    anthropic:
      model_name: "claude-test"
      temperature: 0.5
      max_tokens: 400
      api_key_env: "TEST_ANTHROPIC_KEY"
    local:
      model_name: "local-test"
      temperature: 0.6
      max_tokens: 300
      endpoint_env: "TEST_LOCAL_ENDPOINT"
      default_endpoint: "http://localhost:9999"
"""
        contract_path = tmp_path / "test_contract.yaml"
        contract_path.write_text(contract_content)

        config = load_config_from_contract("openai", contract_path=contract_path)

        assert config.provider == "openai"
        assert config.model_name == "gpt-4o-test"
        assert config.temperature == 0.8
        assert config.max_tokens == 600
        assert config.api_key_env == "TEST_OPENAI_KEY"

    def test_load_anthropic_config_from_contract(self, tmp_path):
        """Load Anthropic config from contract YAML."""
        from examples.demo.handlers.support_assistant.model_config import (
            load_config_from_contract,
        )

        contract_content = """
metadata:
  provider_config:
    openai:
      model_name: "gpt-4o"
      temperature: 0.7
      max_tokens: 500
      api_key_env: "OPENAI_API_KEY"
    anthropic:
      model_name: "claude-sonnet-test"
      temperature: 0.9
      max_tokens: 750
      api_key_env: "MY_ANTHROPIC_KEY"
    local:
      model_name: "local-model"
      temperature: 0.5
      max_tokens: 400
      endpoint_env: "LOCAL_ENDPOINT"
      default_endpoint: "http://localhost:8000"
"""
        contract_path = tmp_path / "test_contract.yaml"
        contract_path.write_text(contract_content)

        config = load_config_from_contract("anthropic", contract_path=contract_path)

        assert config.provider == "anthropic"
        assert config.model_name == "claude-sonnet-test"
        assert config.temperature == 0.9
        assert config.max_tokens == 750
        assert config.api_key_env == "MY_ANTHROPIC_KEY"

    def test_load_local_config_from_contract(self, tmp_path, monkeypatch):
        """Load local config from contract with endpoint from env var."""
        from examples.demo.handlers.support_assistant.model_config import (
            load_config_from_contract,
        )

        # Clear the env var so default is used
        monkeypatch.delenv("TEST_LOCAL_VAR", raising=False)

        contract_content = """
metadata:
  provider_config:
    openai:
      model_name: "gpt-4o"
      temperature: 0.7
      max_tokens: 500
      api_key_env: "OPENAI_API_KEY"
    anthropic:
      model_name: "claude"
      temperature: 0.7
      max_tokens: 500
      api_key_env: "ANTHROPIC_API_KEY"
    local:
      model_name: "qwen-test-model"
      temperature: 0.3
      max_tokens: 250
      endpoint_env: "TEST_LOCAL_VAR"
      default_endpoint: "http://127.0.0.1:7777"
"""
        contract_path = tmp_path / "test_contract.yaml"
        contract_path.write_text(contract_content)

        config = load_config_from_contract("local", contract_path=contract_path)

        assert config.provider == "local"
        assert config.model_name == "qwen-test-model"
        assert config.temperature == 0.3
        assert config.max_tokens == 250
        # Should use default_endpoint since env var is not set
        assert config.endpoint_url == "http://127.0.0.1:7777"

    def test_load_local_config_uses_env_var(self, tmp_path, monkeypatch):
        """Local config uses endpoint from environment variable when set."""
        from examples.demo.handlers.support_assistant.model_config import (
            load_config_from_contract,
        )

        # Set the env var
        monkeypatch.setenv("CUSTOM_LOCAL_ENDPOINT", "http://192.168.1.100:8080")

        contract_content = """
metadata:
  provider_config:
    openai:
      model_name: "gpt-4o"
      temperature: 0.7
      max_tokens: 500
      api_key_env: "OPENAI_API_KEY"
    anthropic:
      model_name: "claude"
      temperature: 0.7
      max_tokens: 500
      api_key_env: "ANTHROPIC_API_KEY"
    local:
      model_name: "local-model"
      temperature: 0.5
      max_tokens: 400
      endpoint_env: "CUSTOM_LOCAL_ENDPOINT"
      default_endpoint: "http://localhost:8000"
"""
        contract_path = tmp_path / "test_contract.yaml"
        contract_path.write_text(contract_content)

        config = load_config_from_contract("local", contract_path=contract_path)

        # Should use env var value, not default
        assert config.endpoint_url == "http://192.168.1.100:8080"

    def test_load_config_file_not_found(self, tmp_path):
        """FileNotFoundError raised when contract file not found."""
        from examples.demo.handlers.support_assistant.model_config import (
            load_config_from_contract,
        )

        nonexistent_path = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            load_config_from_contract("openai", contract_path=nonexistent_path)

    def test_load_config_invalid_contract_structure(self, tmp_path):
        """ValidationError raised when contract structure is invalid."""
        from examples.demo.handlers.support_assistant.model_config import (
            load_config_from_contract,
        )

        # Contract missing required provider_config section
        contract_content = """
metadata:
  owner: test-team
"""
        contract_path = tmp_path / "invalid_contract.yaml"
        contract_path.write_text(contract_content)

        with pytest.raises(ValidationError):
            load_config_from_contract("openai", contract_path=contract_path)

    def test_load_config_default_contract_path(self):
        """Uses default contract path when not specified.

        This test uses the actual support_assistant.yaml contract file.
        """
        from examples.demo.handlers.support_assistant.model_config import (
            load_config_from_contract,
        )

        # Should work without specifying contract_path (uses default)
        config = load_config_from_contract("openai")

        # Verify it loaded valid config from the actual contract
        assert config.provider == "openai"
        assert config.model_name is not None
        assert config.temperature >= 0.0
        assert config.temperature <= 2.0
