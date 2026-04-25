# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import pytest

from omnibase_core.enums.enum_hook_bit import EnumHookBit
from omnibase_core.models.contracts.subcontracts.model_hook_activation import (
    ModelHookActivation,
)


def test_model_hook_activation_round_trips() -> None:
    raw = {
        "hook_bit": "BRANCH_PROTECTION_GUARD",
        "enabled_by_default": True,
        "description": "Enforces worktree discipline",
    }
    m = ModelHookActivation.model_validate(raw)
    assert m.hook_bit == EnumHookBit.BRANCH_PROTECTION_GUARD
    assert m.enabled_by_default is True


def test_model_hook_activation_rejects_unknown_bit() -> None:
    with pytest.raises(Exception):
        ModelHookActivation.model_validate(
            {"hook_bit": "DOES_NOT_EXIST", "enabled_by_default": True}
        )


def test_model_hook_activation_extra_fields_forbidden() -> None:
    with pytest.raises(Exception):
        ModelHookActivation.model_validate(
            {
                "hook_bit": "BRANCH_PROTECTION_GUARD",
                "enabled_by_default": True,
                "garbage": 1,
            }
        )


def test_model_hook_activation_defaults() -> None:
    m = ModelHookActivation.model_validate({"hook_bit": "BRANCH_PROTECTION_GUARD"})
    assert m.enabled_by_default is True
    assert m.description == ""


def test_model_hook_activation_is_frozen() -> None:
    m = ModelHookActivation.model_validate(
        {"hook_bit": "BRANCH_PROTECTION_GUARD", "enabled_by_default": True}
    )
    with pytest.raises(Exception):
        m.enabled_by_default = False  # type: ignore[misc]
