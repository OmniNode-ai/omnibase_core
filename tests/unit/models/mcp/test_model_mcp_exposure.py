# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed MCP exposure list: one entry per operation (OMN-15920, PR 1)."""

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.mcp.model_mcp_exposure import ModelMcpExposure
from omnibase_core.models.mcp.model_mcp_tool_entry import ModelMcpToolEntry

SCHEMA_PATH = (
    Path(__file__).resolve().parents[4]
    / "src"
    / "omnibase_core"
    / "schemas"
    / "mcp"
    / "mcp_exposure.schema.json"
)


def _entry(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "tool_name": "agent_message_send",
        "description": "Send one agent message.",
        "timeout_seconds": 30,
        "input_model": "pkg.models.ModelSendInput",
        "output_model": "pkg.models.ModelSendOutput",
        "command_route": "onex.cmd.agent-message-send.v1",
        "completed_route": "onex.evt.agent-message-send-completed.v1",
        "failed_route": "onex.evt.agent-message-send-failed.v1",
    }
    base.update(over)
    return base


def _block(*entries: dict[str, Any], expose: bool = True) -> dict[str, Any]:
    return {"expose": expose, "tools": list(entries)}


@pytest.mark.unit
class TestParse:
    def test_two_operations_of_one_node(self) -> None:
        parsed = ModelMcpExposure.from_contract_block(
            _block(
                _entry(),
                _entry(
                    tool_name="agent_message_read",
                    command_route="onex.cmd.agent-message-read.v1",
                    completed_route="onex.evt.agent-message-read-completed.v1",
                    failed_route="onex.evt.agent-message-read-failed.v1",
                ),
            )
        )
        assert [t.tool_name for t in parsed.tools] == [
            "agent_message_send",
            "agent_message_read",
        ]
        assert parsed.expose is True

    def test_entry_is_frozen(self) -> None:
        entry = ModelMcpToolEntry.model_validate(_entry())
        with pytest.raises(ValidationError):
            entry.__setattr__("timeout_seconds", 5)

    def test_expose_false_with_no_tools_is_valid(self) -> None:
        parsed = ModelMcpExposure.from_contract_block(_block(expose=False))
        assert parsed.tools == ()


@pytest.mark.unit
class TestKnownBad:
    @pytest.mark.parametrize(
        "field",
        [
            "tool_name",
            "description",
            "timeout_seconds",
            "input_model",
            "output_model",
            "command_route",
            "completed_route",
            "failed_route",
        ],
    )
    def test_every_entry_field_is_required(self, field: str) -> None:
        data = _entry()
        del data[field]
        with pytest.raises(ValidationError) as exc:
            ModelMcpToolEntry.model_validate(data)
        assert any(e["loc"] == (field,) for e in exc.value.errors())

    def test_duplicate_tool_name_refused_by_name(self) -> None:
        with pytest.raises(ValueError, match="duplicate MCP tool name"):
            ModelMcpExposure.from_contract_block(_block(_entry(), _entry()))

    def test_exposed_with_no_tools_refused(self) -> None:
        with pytest.raises(ValueError, match="no tool entries"):
            ModelMcpExposure.from_contract_block(_block(expose=True))

    def test_extra_key_on_entry_refused(self) -> None:
        with pytest.raises(ValidationError) as exc:
            ModelMcpToolEntry.model_validate(_entry(retries=3))
        assert any(e["type"] == "extra_forbidden" for e in exc.value.errors())

    def test_extra_key_on_block_refused(self) -> None:
        data = _block(_entry())
        data["tags"] = ["x"]
        with pytest.raises(ValidationError):
            ModelMcpExposure.from_contract_block(data)

    def test_legacy_single_tool_block_refused_by_name(self) -> None:
        legacy = {
            "expose": True,
            "tool_name": "register_node",
            "description": "d",
            "timeout_seconds": 30,
        }
        with pytest.raises(ModelOnexError, match="legacy single-tool"):
            ModelMcpExposure.from_contract_block(legacy)

    def test_non_mapping_refused(self) -> None:
        with pytest.raises(ModelOnexError, match="must be a mapping"):
            ModelMcpExposure.from_contract_block(["not", "a", "mapping"])

    @pytest.mark.parametrize("name", ["Send-Msg", "1send", "", "send msg"])
    def test_bad_tool_name_refused(self, name: str) -> None:
        with pytest.raises(ValidationError):
            ModelMcpToolEntry.model_validate(_entry(tool_name=name))

    @pytest.mark.parametrize("seconds", [0, -1])
    def test_non_positive_timeout_refused(self, seconds: int) -> None:
        with pytest.raises(ValidationError):
            ModelMcpToolEntry.model_validate(_entry(timeout_seconds=seconds))

    def test_failed_route_equal_to_completed_refused(self) -> None:
        with pytest.raises(ValidationError, match="distinct"):
            ModelMcpToolEntry.model_validate(
                _entry(failed_route="onex.evt.agent-message-send-completed.v1")
            )

    def test_command_route_equal_to_reply_route_refused(self) -> None:
        with pytest.raises(ValidationError, match="distinct"):
            ModelMcpToolEntry.model_validate(
                _entry(completed_route="onex.cmd.agent-message-send.v1")
            )

    def test_input_model_must_be_dotted_path(self) -> None:
        with pytest.raises(ValidationError):
            ModelMcpToolEntry.model_validate(_entry(input_model="NoDots"))


@pytest.mark.unit
class TestSchema:
    def test_committed_schema_matches_model(self) -> None:
        expected = (
            json.dumps(ModelMcpExposure.model_json_schema(), indent=2, sort_keys=True)
            + "\n"
        )
        assert SCHEMA_PATH.read_text(encoding="utf-8") == expected

    def test_schema_requires_the_entry_fields(self) -> None:
        schema = ModelMcpToolEntry.model_json_schema()
        assert set(schema["required"]) == set(_entry())
