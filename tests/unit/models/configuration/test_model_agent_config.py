# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelAgentConfig.hooks migration to list[ModelHookActivation] (OMN-9739)."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_hook_bit import EnumHookBit
from omnibase_core.models.configuration.model_agent_config import ModelAgentConfig
from omnibase_core.models.contracts.subcontracts.model_hook_activation import (
    ModelHookActivation,
)


def _minimal_config(**overrides: object) -> dict:
    base: dict = {
        "agent_id": str(uuid.uuid4()),
        "permissions": {
            "tools": {"Bash": True, "Read": True},
            "file_system": {"read": ["/tmp"], "write": []},
            "git": {"commit": False},
            "event_bus": {"publish": [], "subscribe": []},
        },
        "working_directory": "/tmp/agent",
        "environment_vars": {},
        "safety": {
            "max_file_changes": 10,
            "max_execution_time": 300,
            "require_tests": True,
            "auto_rollback": False,
            "validation_timeout": 30,
        },
        "onex": {
            "enforce_naming_conventions": True,
            "enforce_strong_typing": True,
            "require_contract_compliance": True,
            "generate_documentation": False,
            "validate_imports": True,
        },
    }
    base.update(overrides)
    return base


class TestModelAgentConfigHooksField:
    """hooks field must be list[ModelHookActivation] with default []."""

    def test_hooks_defaults_to_empty_list(self) -> None:
        config = ModelAgentConfig.model_validate(_minimal_config())
        assert config.hooks == []
        assert isinstance(config.hooks, list)

    def test_hooks_accepts_list_of_model_hook_activation(self) -> None:
        activation = ModelHookActivation(
            hook_bit=EnumHookBit.CI_REMINDER,
            enabled_by_default=True,
            description="CI reminder hook",
        )
        data = _minimal_config(
            hooks=[
                {
                    "hook_bit": "CI_REMINDER",
                    "enabled_by_default": True,
                    "description": "CI reminder hook",
                }
            ]
        )
        config = ModelAgentConfig.model_validate(data)
        assert len(config.hooks) == 1
        assert config.hooks[0].hook_bit == activation.hook_bit
        assert config.hooks[0].enabled_by_default is True

    def test_hooks_field_is_list_not_dict(self) -> None:
        config = ModelAgentConfig.model_validate(_minimal_config())
        assert not isinstance(config.hooks, dict)

    def test_hooks_rejects_dict_style(self) -> None:
        data = _minimal_config(hooks={"session_start": "/path/to/hook.sh"})
        with pytest.raises((ValidationError, TypeError)):
            ModelAgentConfig.model_validate(data)

    def test_hooks_multiple_activations(self) -> None:
        data = _minimal_config(
            hooks=[
                {"hook_bit": "CI_REMINDER", "enabled_by_default": True},
                {"hook_bit": "RUFF_FIX", "enabled_by_default": False},
            ]
        )
        config = ModelAgentConfig.model_validate(data)
        assert len(config.hooks) == 2
        bits = {h.hook_bit for h in config.hooks}
        assert EnumHookBit.CI_REMINDER in bits
        assert EnumHookBit.RUFF_FIX in bits

    def test_hooks_items_are_model_hook_activation_instances(self) -> None:
        data = _minimal_config(
            hooks=[{"hook_bit": "CI_REMINDER", "enabled_by_default": True}]
        )
        config = ModelAgentConfig.model_validate(data)
        assert isinstance(config.hooks[0], ModelHookActivation)
