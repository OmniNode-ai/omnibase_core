# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelAgentConfig and ModelActivationPatterns (OCC agent YAML schema)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.agents.model_agent_yaml_activation_patterns import (
    ModelActivationPatterns,
)
from omnibase_core.models.agents.model_agent_yaml_config import ModelAgentConfig


class TestModelActivationPatterns:
    """Tests for ModelActivationPatterns (strict OCC variant with required explicit_triggers)."""

    def test_minimal_valid(self) -> None:
        patterns = ModelActivationPatterns(explicit_triggers=["deploy", "push"])
        assert patterns.explicit_triggers == ["deploy", "push"]
        assert patterns.context_triggers == []

    def test_with_context_triggers(self) -> None:
        patterns = ModelActivationPatterns(
            explicit_triggers=["deploy"],
            context_triggers=["ci context", "release context"],
        )
        assert patterns.context_triggers == ["ci context", "release context"]

    def test_missing_explicit_triggers_raises(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ModelActivationPatterns.model_validate(
                {"context_triggers": ["some context"]}
            )
        assert "explicit_triggers" in str(exc_info.value)

    def test_empty_explicit_triggers_raises(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ModelActivationPatterns(explicit_triggers=[])
        assert "explicit_triggers" in str(exc_info.value)

    def test_extra_fields_ignored(self) -> None:
        patterns = ModelActivationPatterns.model_validate(
            {"explicit_triggers": ["test"], "unknown_field": "ignored"}
        )
        assert patterns.explicit_triggers == ["test"]
        assert not hasattr(patterns, "unknown_field")


class TestModelAgentConfig:
    """Tests for ModelAgentConfig (top-level agent YAML config schema)."""

    @pytest.fixture
    def minimal_config_data(self) -> dict:
        return {
            "schema_version": "1.0.0",
            "agent_type": "builder",
            "agent_identity": {
                "name": "test-builder",
                "description": "A test builder agent",
            },
            "activation_patterns": {
                "explicit_triggers": ["build", "create"],
            },
        }

    def test_minimal_valid_config(self, minimal_config_data: dict) -> None:
        config = ModelAgentConfig.model_validate(minimal_config_data)
        assert config.schema_version == "1.0.0"
        assert config.agent_type == "builder"
        assert config.agent_identity.name == "test-builder"
        assert config.agent_identity.description == "A test builder agent"
        assert config.activation_patterns.explicit_triggers == ["build", "create"]

    def test_disallowed_tools_defaults_empty(self, minimal_config_data: dict) -> None:
        config = ModelAgentConfig.model_validate(minimal_config_data)
        assert config.disallowed_tools == []

    def test_disallowed_tools_via_alias(self, minimal_config_data: dict) -> None:
        minimal_config_data["disallowedTools"] = ["Bash", "Edit"]
        config = ModelAgentConfig.model_validate(minimal_config_data)
        assert config.disallowed_tools == ["Bash", "Edit"]

    def test_missing_schema_version_raises(self, minimal_config_data: dict) -> None:
        del minimal_config_data["schema_version"]
        with pytest.raises(ValidationError) as exc_info:
            ModelAgentConfig.model_validate(minimal_config_data)
        assert "schema_version" in str(exc_info.value)

    def test_missing_agent_type_raises(self, minimal_config_data: dict) -> None:
        del minimal_config_data["agent_type"]
        with pytest.raises(ValidationError) as exc_info:
            ModelAgentConfig.model_validate(minimal_config_data)
        assert "agent_type" in str(exc_info.value)

    def test_missing_agent_identity_raises(self, minimal_config_data: dict) -> None:
        del minimal_config_data["agent_identity"]
        with pytest.raises(ValidationError) as exc_info:
            ModelAgentConfig.model_validate(minimal_config_data)
        assert "agent_identity" in str(exc_info.value)

    def test_missing_activation_patterns_raises(
        self, minimal_config_data: dict
    ) -> None:
        del minimal_config_data["activation_patterns"]
        with pytest.raises(ValidationError) as exc_info:
            ModelAgentConfig.model_validate(minimal_config_data)
        assert "activation_patterns" in str(exc_info.value)

    def test_extra_fields_ignored(self, minimal_config_data: dict) -> None:
        minimal_config_data["custom_section"] = {"key": "value"}
        config = ModelAgentConfig.model_validate(minimal_config_data)
        assert config.schema_version == "1.0.0"
        assert not hasattr(config, "custom_section")

    def test_importable_from_agents_namespace(self) -> None:
        from omnibase_core.models.agents import ModelAgentConfig as ImportedConfig

        assert ImportedConfig is ModelAgentConfig

    def test_activation_patterns_empty_triggers_raises(
        self, minimal_config_data: dict
    ) -> None:
        minimal_config_data["activation_patterns"]["explicit_triggers"] = []
        with pytest.raises(ValidationError):
            ModelAgentConfig.model_validate(minimal_config_data)
