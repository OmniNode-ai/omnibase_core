# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Fixture-backed acceptance tests for the MCP ``tools`` block (OMN-15920)."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as SchemaValidationError
from pydantic import ValidationError

from omnibase_core.models.contracts.model_contract_base import ModelContractBase

pytestmark = pytest.mark.unit
FIXTURES = Path(__file__).parent / "fixtures" / "mcp_tools"
SCHEMA_PATH = (
    Path(__file__).parents[4] / "src/omnibase_core/schemas/node_contract.schema.json"
)
ENTRY_FIELDS = (
    "tool_name",
    "description",
    "timeout_seconds",
    "input_model",
    "output_model",
    "command_topic",
    "completed_topic",
    "failed_topic",
)


class McpContract(ModelContractBase):
    """Concrete reader: ModelContractBase is abstract and cannot be built."""

    def validate_node_specific_config(self) -> None:
        """No specialization requirements beyond the base contract."""


def _fixture() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load((FIXTURES / "two_entries.yaml").read_text())
    return data


def _with_tools(**mcp: Any) -> dict[str, Any]:
    data = _fixture()
    data["mcp"] = mcp
    return data


def test_two_entries_parse_with_all_eight_fields() -> None:
    contract = McpContract.model_validate(_fixture())
    assert contract.mcp is not None
    assert [t.tool_name for t in contract.mcp.tools] == [
        "probe_note_send",
        "probe_note_read",
    ]
    for tool in contract.mcp.tools:
        assert set(tool.model_dump()) == set(ENTRY_FIELDS)


@pytest.mark.parametrize("field", ENTRY_FIELDS)
def test_missing_entry_field_is_refused_and_named(field: str) -> None:
    data = _fixture()
    del data["mcp"]["tools"][0][field]
    with pytest.raises(ValidationError) as exc_info:
        McpContract.model_validate(data)
    assert field in str(exc_info.value)
    assert any(e["loc"][-1] == field for e in exc_info.value.errors())


def test_duplicate_tool_name_is_refused_by_name() -> None:
    data = _fixture()
    data["mcp"]["tools"][1]["tool_name"] = "probe_note_send"
    with pytest.raises(ValidationError, match="probe_note_send"):
        McpContract.model_validate(data)


@pytest.mark.parametrize("tools", [[], None])
def test_expose_true_needs_an_entry(tools: object) -> None:
    mcp: dict[str, Any] = {"expose": True}
    if tools is not None:
        mcp["tools"] = tools
    data = _fixture()
    data["mcp"] = mcp
    with pytest.raises(ValidationError, match="at least one"):
        McpContract.model_validate(data)


def test_expose_false_with_no_entries_is_accepted() -> None:
    assert McpContract.model_validate(_with_tools(expose=False)).mcp is not None


@pytest.mark.parametrize(
    "bad",
    ["SendInput", "a..B", "pkg.", ".Cls", "pkg.Cls name", "", "pkg.Cls\n"],
)
def test_model_path_must_be_dotted(bad: str) -> None:
    data = _fixture()
    data["mcp"]["tools"][0]["input_model"] = bad
    with pytest.raises(ValidationError, match="dotted path"):
        McpContract.model_validate(data)
    data = _fixture()
    data["mcp"]["tools"][0]["output_model"] = bad
    with pytest.raises(ValidationError, match="dotted path"):
        McpContract.model_validate(data)


@pytest.mark.parametrize("field", ["command_topic", "completed_topic", "failed_topic"])
@pytest.mark.parametrize(
    "bad",
    [
        " onex.cmd.probe-pkg.x.v1",
        "onex.cmd.probe-pkg.x.v1 ",
        "dev.onex.cmd.probe-pkg.x.v1",
        "onex.cmd.x.v1",
    ],
)
def test_topic_must_be_canonical(field: str, bad: str) -> None:
    data = _fixture()
    data["mcp"]["tools"][0][field] = bad
    with pytest.raises(ValidationError, match=field):
        McpContract.model_validate(data)


def test_completed_and_failed_suffix_must_differ() -> None:
    data = _fixture()
    entry = data["mcp"]["tools"][0]
    entry["failed_topic"] = entry["completed_topic"]
    with pytest.raises(ValidationError, match="must differ"):
        McpContract.model_validate(data)


@pytest.mark.parametrize("seed", ["block", "entry"])
def test_unknown_keys_are_refused(seed: str) -> None:
    data = _fixture()
    target = data["mcp"] if seed == "block" else data["mcp"]["tools"][0]
    target["retries"] = 3
    with pytest.raises(ValidationError) as exc_info:
        McpContract.model_validate(data)
    assert any(e["type"] == "extra_forbidden" for e in exc_info.value.errors())


@pytest.mark.parametrize("old_key", ["tool_name", "description", "timeout_seconds"])
def test_old_block_level_keys_are_refused(old_key: str) -> None:
    data = _fixture()
    data["mcp"][old_key] = "register_node" if old_key != "timeout_seconds" else 30
    with pytest.raises(ValidationError) as exc_info:
        McpContract.model_validate(data)
    assert any(
        e["type"] == "extra_forbidden" and e["loc"][-1] == old_key
        for e in exc_info.value.errors()
    )


def test_timeout_must_be_above_zero() -> None:
    data = _fixture()
    data["mcp"]["tools"][0]["timeout_seconds"] = 0
    with pytest.raises(ValidationError):
        McpContract.model_validate(data)


def test_exported_schema_matches_model() -> None:
    """The committed schema is generated from the owning model, never hand edited."""
    assert json.loads(SCHEMA_PATH.read_text()) == ModelContractBase.model_json_schema()


def test_two_entry_fixture_validates_against_model_and_committed_schema() -> None:
    """Hosted acceptance 1: the fixture passes the model and the committed schema."""
    data = _fixture()
    McpContract.model_validate(data)
    Draft202012Validator(json.loads(SCHEMA_PATH.read_text())).validate(data)


def test_schema_refuses_expose_true_without_entries() -> None:
    validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_text()))
    for mcp in ({"expose": True}, {"expose": True, "tools": []}):
        data = copy.deepcopy(_fixture())
        data["mcp"] = mcp
        with pytest.raises(SchemaValidationError):
            validator.validate(data)
    data = copy.deepcopy(_fixture())
    data["mcp"] = {"expose": False}
    validator.validate(data)


def _schema_validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA_PATH.read_text()))


@pytest.mark.parametrize("field", ["input_model", "output_model"])
@pytest.mark.parametrize(
    "bad", ["SendInput", "a..B", "pkg.", ".Cls", "pkg.Cls name", ""]
)
def test_schema_refuses_model_path_that_is_not_dotted(field: str, bad: str) -> None:
    data = _fixture()
    data["mcp"]["tools"][0][field] = bad
    with pytest.raises(SchemaValidationError):
        _schema_validator().validate(data)


def test_schema_refuses_timeout_of_zero() -> None:
    data = _fixture()
    data["mcp"]["tools"][0]["timeout_seconds"] = 0
    with pytest.raises(SchemaValidationError):
        _schema_validator().validate(data)


@pytest.mark.parametrize("bad", ["SendInput", "1send", "send-input", ""])
def test_schema_refuses_tool_name_of_the_wrong_shape(bad: str) -> None:
    data = _fixture()
    data["mcp"]["tools"][0]["tool_name"] = bad
    with pytest.raises(SchemaValidationError):
        _schema_validator().validate(data)


@pytest.mark.parametrize("seed", ["block", "entry"])
def test_schema_refuses_unknown_keys(seed: str) -> None:
    data = _fixture()
    target = data["mcp"] if seed == "block" else data["mcp"]["tools"][0]
    target["retries"] = 3
    with pytest.raises(SchemaValidationError):
        _schema_validator().validate(data)
