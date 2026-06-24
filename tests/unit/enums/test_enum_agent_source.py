# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for EnumAgentSource."""

import json

import pytest
import yaml
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.hooks.enum_agent_source import EnumAgentSource


@pytest.mark.unit
class TestEnumAgentSource:
    """Test basic enum structure and values."""

    def test_claude_value(self) -> None:
        assert EnumAgentSource.CLAUDE.value == "claude"

    def test_cursor_value(self) -> None:
        assert EnumAgentSource.CURSOR.value == "cursor"

    def test_str_returns_value(self) -> None:
        assert str(EnumAgentSource.CLAUDE) == "claude"
        assert str(EnumAgentSource.CURSOR) == "cursor"

    def test_enum_is_unique(self) -> None:
        values = [m.value for m in EnumAgentSource.__members__.values()]
        assert len(values) == len(set(values))

    def test_enum_is_string_subclass(self) -> None:
        assert isinstance(EnumAgentSource.CLAUDE, str)

    def test_enum_equality_with_string(self) -> None:
        assert EnumAgentSource.CLAUDE == "claude"
        assert EnumAgentSource.CURSOR == "cursor"

    def test_enum_membership(self) -> None:
        assert EnumAgentSource.CLAUDE in list(EnumAgentSource)
        assert EnumAgentSource.CURSOR in list(EnumAgentSource)

    def test_enum_from_value(self) -> None:
        assert EnumAgentSource("claude") is EnumAgentSource.CLAUDE
        assert EnumAgentSource("cursor") is EnumAgentSource.CURSOR

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            EnumAgentSource("codex")

    def test_reexported_from_hooks_package(self) -> None:
        from omnibase_core.enums.hooks import EnumAgentSource as Reexported

        assert Reexported is EnumAgentSource


@pytest.mark.unit
class TestEnumAgentSourceSerialization:
    """Test serialization compatibility."""

    def test_json_serialization_via_value(self) -> None:
        data = {"agent_source": EnumAgentSource.CURSOR.value}
        assert json.dumps(data) == '{"agent_source": "cursor"}'

    def test_yaml_round_trip(self) -> None:
        data = {"agent_source": EnumAgentSource.CURSOR.value}
        loaded = yaml.safe_load(yaml.dump(data))
        assert loaded["agent_source"] == "cursor"
        assert EnumAgentSource(loaded["agent_source"]) is EnumAgentSource.CURSOR

    def test_pydantic_field_assignment(self) -> None:
        class M(BaseModel):
            agent_source: EnumAgentSource

        m = M(agent_source=EnumAgentSource.CURSOR)
        assert m.agent_source is EnumAgentSource.CURSOR

    def test_pydantic_string_coercion(self) -> None:
        class M(BaseModel):
            agent_source: EnumAgentSource

        m = M(agent_source="cursor")
        assert m.agent_source is EnumAgentSource.CURSOR

    def test_pydantic_invalid_raises(self) -> None:
        class M(BaseModel):
            agent_source: EnumAgentSource

        with pytest.raises(ValidationError):
            M(agent_source="invalid")

    def test_pydantic_model_dump(self) -> None:
        class M(BaseModel):
            agent_source: EnumAgentSource

        m = M(agent_source=EnumAgentSource.CLAUDE)
        assert m.model_dump() == {"agent_source": "claude"}

    def test_pydantic_model_dump_json(self) -> None:
        class M(BaseModel):
            agent_source: EnumAgentSource

        m = M(agent_source=EnumAgentSource.CLAUDE)
        assert m.model_dump_json() == '{"agent_source":"claude"}'


@pytest.mark.unit
class TestEnumAgentSourceDefaultField:
    """Test use as a defaulted field — the route_hook_event seam pattern."""

    def test_default_is_claude(self) -> None:
        class M(BaseModel):
            agent_source: EnumAgentSource = EnumAgentSource.CLAUDE

        assert M().agent_source is EnumAgentSource.CLAUDE

    def test_default_overridden_with_cursor(self) -> None:
        class M(BaseModel):
            agent_source: EnumAgentSource = EnumAgentSource.CLAUDE

        assert M(agent_source=EnumAgentSource.CURSOR).agent_source is (
            EnumAgentSource.CURSOR
        )
