# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import pytest

from omnibase_core.enums.enum_hook_bit import EnumHookBit
from omnibase_core.models.contracts.subcontracts.model_package_hook_activations import (
    ModelPackageHookActivations,
)


@pytest.mark.unit
def test_package_hook_activations_round_trips() -> None:
    raw = {
        "hook_activations": [
            {"hook_bit": "CI_REMINDER", "enabled_by_default": True},
            {"hook_bit": "AUTO_HOSTILE_REVIEW", "enabled_by_default": False},
        ]
    }
    m = ModelPackageHookActivations.model_validate(raw)
    assert len(m.hook_activations) == 2
    assert m.hook_activations[0].hook_bit == EnumHookBit.CI_REMINDER


@pytest.mark.unit
def test_package_hook_activations_defaults_to_empty() -> None:
    m = ModelPackageHookActivations.model_validate({})
    assert m.hook_activations == []


@pytest.mark.unit
def test_package_hook_activations_rejects_unknown_bit() -> None:
    with pytest.raises(ValueError, match="hook_bit"):
        ModelPackageHookActivations.model_validate(
            {
                "hook_activations": [
                    {"hook_bit": "DOES_NOT_EXIST", "enabled_by_default": True}
                ]
            }
        )
