# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fixture-backed acceptance tests for OMN-21420."""

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as SchemaValidationError
from pydantic import ValidationError

from omnibase_core.models.contracts.model_contract_base import ModelContractBase

pytestmark = pytest.mark.unit
FIXTURES = Path(__file__).parent / "fixtures" / "placement_leases"


class PlacementContract(ModelContractBase):
    """Exercise the common contract surface for every node type."""

    def validate_node_specific_config(self) -> None:
        """No specialization requirements beyond the base contract."""


def _fixture(name: str) -> dict[str, object]:
    data: dict[str, object] = yaml.safe_load((FIXTURES / f"{name}.yaml").read_text())
    return data


@pytest.mark.parametrize(
    ("node_type", "mode"),
    [
        ("effect", "any"),
        ("compute", "any"),
        ("orchestrator", "primary"),
        ("reducer", "primary"),
    ],
)
def test_ac1_default_mode(node_type: str, mode: str) -> None:
    contract = PlacementContract.model_validate(_fixture(f"ac1_{node_type}"))
    assert contract.placement.mode == mode
    assert contract.leases == []
    assert PlacementContract.model_validate_json(contract.model_dump_json()) == contract


@pytest.mark.parametrize("node_type", ["ORCHESTRATOR_GENERIC", "REDUCER_GENERIC"])
@pytest.mark.parametrize(
    "state", [None, {}, {"store": "projection"}, {"store": "lease_store"}]
)
def test_ac2_any_requires_explicit_stateless(node_type: str, state: object) -> None:
    data = _fixture("ac2_any_stateful")
    data["node_type"] = node_type
    placement: dict[str, object] = {"mode": "any"}
    if state is not None:
        placement["state"] = state
    data["placement"] = placement
    with pytest.raises(ValidationError, match=r"state\.store.*none"):
        PlacementContract.model_validate(data)


@pytest.mark.parametrize("node_type", ["ORCHESTRATOR_GENERIC", "REDUCER_GENERIC"])
def test_ac2_any_accepts_explicit_stateless(node_type: str) -> None:
    data = _fixture("ac2_any_stateful")
    data.update(
        node_type=node_type, placement={"mode": "any", "state": {"store": "none"}}
    )
    state = PlacementContract.model_validate(data).placement.state
    assert state is not None
    assert state.store == "none"


def test_ac3_consumer_group_forbidden() -> None:
    with pytest.raises(ValidationError) as exc:
        PlacementContract.model_validate(_fixture("ac3_consumer_group"))
    assert any(
        error["loc"] == ("placement", "consumer_group")
        and error["type"] == "extra_forbidden"
        for error in exc.value.errors()
    )


@pytest.mark.parametrize("missing", ["kind", "max_ttl_s"])
def test_ac4_lease_required_fields(missing: str) -> None:
    data = _fixture("ac4_leases")
    entry = {"kind": "worker_slot", "max_ttl_s": 30}
    del entry[missing]
    data["leases"] = [entry]
    with pytest.raises(ValidationError) as exc:
        PlacementContract.model_validate(data)
    assert any(
        error["loc"] == ("leases", 0, missing) and error["type"] == "missing"
        for error in exc.value.errors()
    )


def test_ac4_valid_lease() -> None:
    contract = PlacementContract.model_validate(_fixture("ac4_leases"))
    assert contract.leases[0].kind == "worker_slot"
    assert contract.leases[0].max_ttl_s == 30


def test_rendered_schema_declares_optional_fields_and_strict_blocks() -> None:
    schema = PlacementContract.model_json_schema()
    assert {"placement", "leases"} <= schema["properties"].keys()
    assert not {"placement", "leases"} & set(schema["required"])
    definitions = schema["$defs"]
    assert definitions["ModelContractPlacement"]["additionalProperties"] is False
    assert set(definitions["ModelContractLease"]["required"]) == {"kind", "max_ttl_s"}


def test_exported_schema_matches_model() -> None:
    """The committed schema is generated from the owning model, never hand edited."""
    path = (
        Path(__file__).parents[4]
        / "src/omnibase_core/schemas/node_contract.schema.json"
    )
    assert json.loads(path.read_text()) == ModelContractBase.model_json_schema()


@pytest.mark.parametrize(
    "fixture",
    ["ac1_effect", "ac1_compute", "ac1_orchestrator", "ac1_reducer", "ac4_leases"],
)
def test_schema_accepts_valid_fixtures(fixture: str) -> None:
    Draft202012Validator(ModelContractBase.model_json_schema()).validate(
        _fixture(fixture)
    )


@pytest.mark.parametrize("fixture", ["ac2_any_stateful", "ac3_consumer_group"])
def test_schema_rejects_invalid_fixtures(fixture: str) -> None:
    with pytest.raises(SchemaValidationError):
        Draft202012Validator(ModelContractBase.model_json_schema()).validate(
            _fixture(fixture)
        )


@pytest.mark.parametrize("missing", ["kind", "max_ttl_s"])
def test_schema_requires_lease_fields(missing: str) -> None:
    data = _fixture("ac4_leases")
    entry = {"kind": "worker_slot", "max_ttl_s": 30}
    del entry[missing]
    data["leases"] = [entry]
    with pytest.raises(SchemaValidationError):
        Draft202012Validator(ModelContractBase.model_json_schema()).validate(data)
