# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Test that ModelHandlerContractExtended accepts infra-specific fields.

Verifies OMN-6483: extension model inherits from base but accepts
handler_routing, operation_bindings, activation, and dict-form
input_model/output_model.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.model_handler_contract import (
    ModelHandlerContract,
)
from omnibase_core.models.contracts.model_handler_contract_extended import (
    ModelHandlerContractExtended,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.runtime.model_handler_behavior import ModelHandlerBehavior


def _base_data() -> dict[str, object]:
    """Return minimal valid handler contract data."""
    return {
        "handler_id": "node.test.handler",
        "name": "Test Handler",
        "contract_version": ModelSemVer(major=1, minor=0, patch=0),
        "descriptor": ModelHandlerBehavior(
            node_archetype="compute",
            purity="pure",
            idempotent=True,
        ),
        "input_model": "test.Input",
        "output_model": "test.Output",
    }


@pytest.mark.unit
def test_extended_contract_accepts_handler_routing() -> None:
    """Extended contract must accept handler_routing field."""
    data = {**_base_data(), "handler_routing": {"strategy": "round-robin"}}
    contract = ModelHandlerContractExtended(**data)
    assert contract.handler_routing == {"strategy": "round-robin"}


@pytest.mark.unit
def test_extended_contract_accepts_operation_bindings() -> None:
    """Extended contract must accept operation_bindings field."""
    bindings = [{"op": "create", "handler": "create_handler"}]
    data = {**_base_data(), "operation_bindings": bindings}
    contract = ModelHandlerContractExtended(**data)
    assert contract.operation_bindings == bindings


@pytest.mark.unit
def test_extended_contract_accepts_activation() -> None:
    """Extended contract must accept activation field."""
    data = {**_base_data(), "activation": {"auto_start": True}}
    contract = ModelHandlerContractExtended(**data)
    assert contract.activation == {"auto_start": True}


@pytest.mark.unit
def test_extended_contract_accepts_dict_input_model() -> None:
    """Extended contract must accept dict-form input_model."""
    data = {**_base_data(), "input_model": {"type": "object", "properties": {}}}
    contract = ModelHandlerContractExtended(**data)
    assert isinstance(contract.input_model, dict)


@pytest.mark.unit
def test_extended_contract_accepts_dict_output_model() -> None:
    """Extended contract must accept dict-form output_model."""
    data = {**_base_data(), "output_model": {"type": "object", "properties": {}}}
    contract = ModelHandlerContractExtended(**data)
    assert isinstance(contract.output_model, dict)


@pytest.mark.unit
def test_base_contract_ignores_extra_fields() -> None:
    """Base contract silently ignores extra fields (extra='ignore')."""
    data = {**_base_data(), "handler_routing": {"strategy": "round-robin"}}
    contract = ModelHandlerContract(**data)
    # extra="ignore" means the field is accepted but not stored
    assert not hasattr(contract, "handler_routing")


@pytest.mark.unit
def test_extended_inherits_from_base() -> None:
    """Extended contract must be a subclass of base."""
    assert issubclass(ModelHandlerContractExtended, ModelHandlerContract)


@pytest.mark.unit
def test_extended_contract_is_frozen() -> None:
    """Extended contract must be immutable."""
    data = _base_data()
    contract = ModelHandlerContractExtended(**data)
    with pytest.raises(ValidationError):
        setattr(contract, "name", "Changed")
