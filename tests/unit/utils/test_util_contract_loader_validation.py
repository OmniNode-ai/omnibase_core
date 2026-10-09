# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Document-validation regressions for OMN-18712, through the public loader."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest
import yaml

from omnibase_core.infrastructure.node_base import NodeBase
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.core.model_contract_content import ModelContractContent
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.utils.util_contract_loader import UtilContractLoader


@pytest.fixture
def document() -> dict[str, object]:
    """A complete NodeBase contract with declared schemas, topics and routing."""
    version = {"major": 1, "minor": 0, "patch": 0}
    return {
        "contract_version": version,
        "node_name": "ValidationNode",
        "node_type": "COMPUTE_GENERIC",
        "tool_specification": {"main_tool_class": "ValidationTool"},
        "input_state": {
            "object_type": "object",
            "properties": {"request": {"property_type": "string"}},
            "required_properties": ["request"],
        },
        "output_state": {
            "object_type": "object",
            "properties": {"result": {"property_type": "string"}},
        },
        "definitions": {
            "definitions": {"payload": {"object_type": "object"}},
        },
        "description": "A declaration that must survive parsing",
        "event_bus": {
            "version": version,
            "publish_topics": ["onex.evt.validation.result.v1"],
            "subscribe_topics": ["onex.cmd.validation.request.v1"],
        },
        "handler_routing": {
            "version": version,
            "handlers": [
                {
                    "handler": {
                        "name": "ValidationHandler",
                        "module": "example.handlers",
                    },
                    "event_model": {
                        "name": "ValidationRequest",
                        "module": "example.models",
                    },
                },
            ],
        },
    }


def write_contract(tmp_path: Path, document: dict[str, object]) -> Path:
    """Write the document as YAML so tests exercise the real file load path."""
    path = tmp_path / "contract.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    return path


@pytest.mark.parametrize("cache_enabled", [False, True])
def test_declared_fields_survive_load_and_cache(
    tmp_path: Path, document: dict[str, object], cache_enabled: bool
) -> None:
    """AC1/AC4: no successful load loses topics, bindings, or schema content."""
    path = write_contract(tmp_path, document)
    loader = UtilContractLoader(tmp_path, cache_enabled=cache_enabled)
    first = loader.load_contract(path)
    assert first.event_bus is not None
    assert first.event_bus.publish_topics == ["onex.evt.validation.result.v1"]
    assert first.event_bus.subscribe_topics == ["onex.cmd.validation.request.v1"]
    assert first.handler_routing is not None
    assert first.handler_routing.handlers[0].handler.name == "ValidationHandler"
    assert first.input_state.required_properties == ["request"]
    assert "result" in first.output_state.properties
    assert "payload" in first.definitions.definitions
    assert first.description == document["description"]
    assert loader.load_contract(path) == first
    # Exercise the parsed-file cache, independently of the resolved-object cache.
    loader.state.loaded_contracts.clear()
    assert loader.load_contract(path) == first


def test_unknown_key_is_refused_with_positive_control(
    tmp_path: Path, document: dict[str, object]
) -> None:
    """AC2: the model sees undeclared fields instead of the loader dropping them."""
    path = write_contract(tmp_path, document)
    assert (
        UtilContractLoader(tmp_path).load_contract(path).node_name == "ValidationNode"
    )
    document["undeclared_setting"] = True
    write_contract(tmp_path, document)
    with pytest.raises(ModelOnexError, match="undeclared_setting") as exc:
        UtilContractLoader(tmp_path).load_contract(path)
    assert "Extra inputs are not permitted" in exc.value.message


def test_node_base_retains_declared_topics_and_bindings(
    tmp_path: Path, document: dict[str, object]
) -> None:
    """AC4: the production caller keeps the validated contract, without a mock loader."""
    document["tool_specification"] = {
        "main_tool_class": "omnibase_core.nodes.node_compute.NodeCompute",
    }
    node = NodeBase(
        contract_path=write_contract(tmp_path, document),
        container=ModelONEXContainer(),
    )
    contract = node.state.contract_content
    assert isinstance(contract, ModelContractContent)
    assert contract.event_bus is not None
    assert contract.event_bus.publish_topics == ["onex.evt.validation.result.v1"]
    assert contract.event_bus.subscribe_topics == ["onex.cmd.validation.request.v1"]
    assert contract.handler_routing is not None
    assert contract.handler_routing.handlers[0].handler.name == "ValidationHandler"


def test_contract_without_optional_bus_sections_parses(
    tmp_path: Path, document: dict[str, object]
) -> None:
    """The valid control needs no topics when the document declares none."""
    del document["event_bus"]
    del document["handler_routing"]
    parsed = UtilContractLoader(tmp_path).load_contract(
        write_contract(tmp_path, document)
    )
    assert parsed.event_bus is None
    assert parsed.handler_routing is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("node_type", "compute"),
        ("node_type", 12),
        ("contract_version", "invalid"),
        ("tool_specification", "invalid"),
        ("dependencies", ["invalid"]),
        ("dependencies", "invalid"),
        (
            "event_bus",
            {
                "version": {"major": 1, "minor": 0, "patch": 0},
                "subscribe_topics": ["invalid"],
            },
        ),
        (
            "handler_routing",
            {"version": {"major": 1, "minor": 0, "patch": 0}, "handlers": ["invalid"]},
        ),
        ("version", {"major": 1, "minor": 0, "patch": 0}),
    ],
)
def test_invalid_fields_have_actionable_refusals(
    tmp_path: Path, document: dict[str, object], field: str, value: object
) -> None:
    """AC2/AC3: invalid values cannot turn into fabricated defaults."""
    document[field] = value
    with pytest.raises(ModelOnexError, match=field) as exc:
        UtilContractLoader(tmp_path).load_contract(write_contract(tmp_path, document))
    assert "validation error for ModelContractContent" not in exc.value.message
    assert "errors.pydantic.dev" not in exc.value.message


@pytest.mark.parametrize(
    "field", ["node_name", "input_state", "output_state", "definitions"]
)
def test_required_fields_are_not_synthesized(
    tmp_path: Path, document: dict[str, object], field: str
) -> None:
    """AC1: a required declaration must come from the document."""
    del document[field]
    with pytest.raises(ModelOnexError, match=field):
        UtilContractLoader(tmp_path).load_contract(write_contract(tmp_path, document))


def test_parser_validates_document_without_placeholder_construction() -> None:
    """AC1's source falsifier: the parser does not construct replacement schemas."""
    tree = ast.parse(inspect.getsource(inspect.getmodule(UtilContractLoader)))
    parser = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_parse_contract_content"
    )
    calls = [node.func for node in ast.walk(parser) if isinstance(node, ast.Call)]
    assert any(
        isinstance(call, ast.Attribute)
        and call.attr == "model_validate"
        and isinstance(call.value, ast.Name)
        and call.value.id == "ModelContractContent"
        for call in calls
    )
    assert not any(
        isinstance(call, ast.Name)
        and call.id
        in {
            "ModelContractContent",
            "ModelYamlSchemaObject",
            "ModelContractDefinitions",
            "ModelToolSpecification",
        }
        for call in calls
    )


@pytest.mark.parametrize(
    "node",
    [
        "node_contract_resolve_compute",
        "node_source_file_gather_effect",
        "node_compliance_orchestrator",
        "node_compliance_report_reducer",
    ],
)
def test_real_contracts_parse_or_name_the_refused_field(node: str) -> None:
    """AC3: tracked real contracts get a field-specific refusal, never a raw dump."""
    root = Path(__file__).resolve().parents[3]
    path = root / "src" / "omnibase_core" / "nodes" / node / "contract.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    try:
        parsed = UtilContractLoader(path.parent).load_contract(path)
    except ModelOnexError as exc:
        assert "Contract schema validation failed" in exc.message
        assert "node_type:" in exc.message or "version" in exc.message
        assert "validation error for ModelContractContent" not in exc.message
        assert "errors.pydantic.dev" not in exc.message
    else:
        if document.get("event_bus", {}).get("publish_topics"):
            assert parsed.event_bus is not None and parsed.event_bus.publish_topics
