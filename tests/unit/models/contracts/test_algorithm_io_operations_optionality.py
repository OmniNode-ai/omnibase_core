# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Temporary legacy-corpus optionality for compute/effect contract fields."""

import logging

import pytest

from omnibase_core.enums import EnumNodeType
from omnibase_core.models.contracts.model_contract_compute import ModelContractCompute
from omnibase_core.models.contracts.model_contract_effect import ModelContractEffect

_BASE_CONTRACT: dict[str, object] = {
    "name": "node_foo",
    "contract_version": {"major": 1, "minor": 0, "patch": 0},
    "description": "Legacy contract missing a field added after authoring.",
    "input_model": "foo.ModelFooRequest",
    "output_model": "foo.ModelFooResult",
    "performance": {"single_operation_max_ms": 1000},
}


@pytest.mark.unit
class TestAlgorithmIoOperationsOptionality:
    """OMN-9770 migration-audit compatibility for legacy contracts."""

    def test_effect_without_io_operations_validates(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        caplog.set_level(logging.WARNING)

        model = ModelContractEffect.model_validate(
            {
                **_BASE_CONTRACT,
                "node_type": EnumNodeType.EFFECT_GENERIC,
            }
        )

        assert model.io_operations is None
        assert "missing io_operations" in caplog.text
        assert "OMN-9770" in caplog.text

    def test_compute_without_algorithm_validates(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        caplog.set_level(logging.WARNING)

        model = ModelContractCompute.model_validate(
            {
                **_BASE_CONTRACT,
                "node_type": EnumNodeType.COMPUTE_GENERIC,
            }
        )

        assert model.algorithm is None
        assert "missing algorithm" in caplog.text
        assert "OMN-9770" in caplog.text
