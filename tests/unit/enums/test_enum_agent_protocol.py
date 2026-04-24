# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for EnumAgentProtocol."""

import json

import pytest
import yaml
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_agent_protocol import EnumAgentProtocol


@pytest.mark.unit
class TestEnumAgentProtocol:
    """Test basic enum structure and values."""

    def test_a2a_value(self) -> None:
        assert EnumAgentProtocol.A2A.value == "A2A"

    def test_str_returns_value(self) -> None:
        assert str(EnumAgentProtocol.A2A) == "A2A"

    def test_enum_is_unique(self) -> None:
        values = [m.value for m in EnumAgentProtocol]
        assert len(values) == len(set(values))

    def test_enum_is_string_subclass(self) -> None:
        assert isinstance(EnumAgentProtocol.A2A, str)

    def test_enum_equality_with_string(self) -> None:
        assert EnumAgentProtocol.A2A == "A2A"

    def test_enum_membership(self) -> None:
        assert EnumAgentProtocol.A2A in EnumAgentProtocol

    def test_enum_from_value(self) -> None:
        assert EnumAgentProtocol("A2A") is EnumAgentProtocol.A2A

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            EnumAgentProtocol("UNKNOWN")


@pytest.mark.unit
class TestEnumAgentProtocolSerialization:
    """Test serialization compatibility."""

    def test_json_serialization_via_value(self) -> None:
        data = {"protocol": EnumAgentProtocol.A2A.value}
        assert json.dumps(data) == '{"protocol": "A2A"}'

    def test_yaml_round_trip(self) -> None:
        data = {"agent_protocol": EnumAgentProtocol.A2A.value}
        loaded = yaml.safe_load(yaml.dump(data))
        assert loaded["agent_protocol"] == "A2A"
        assert EnumAgentProtocol(loaded["agent_protocol"]) is EnumAgentProtocol.A2A

    def test_pydantic_field_assignment(self) -> None:
        class M(BaseModel):
            protocol: EnumAgentProtocol

        m = M(protocol=EnumAgentProtocol.A2A)
        assert m.protocol is EnumAgentProtocol.A2A

    def test_pydantic_string_coercion(self) -> None:
        class M(BaseModel):
            protocol: EnumAgentProtocol

        m = M(protocol="A2A")
        assert m.protocol is EnumAgentProtocol.A2A

    def test_pydantic_invalid_raises(self) -> None:
        class M(BaseModel):
            protocol: EnumAgentProtocol

        with pytest.raises(ValidationError):
            M(protocol="INVALID")

    def test_pydantic_model_dump(self) -> None:
        class M(BaseModel):
            protocol: EnumAgentProtocol

        m = M(protocol=EnumAgentProtocol.A2A)
        assert m.model_dump() == {"protocol": "A2A"}

    def test_pydantic_model_dump_json(self) -> None:
        class M(BaseModel):
            protocol: EnumAgentProtocol

        m = M(protocol=EnumAgentProtocol.A2A)
        assert m.model_dump_json() == '{"protocol":"A2A"}'


@pytest.mark.unit
class TestEnumAgentProtocolOptionalField:
    """Test use as an Optional field — primary consumer pattern."""

    def test_optional_field_none(self) -> None:
        class M(BaseModel):
            protocol: EnumAgentProtocol | None = None

        m = M()
        assert m.protocol is None

    def test_optional_field_set(self) -> None:
        class M(BaseModel):
            protocol: EnumAgentProtocol | None = None

        m = M(protocol=EnumAgentProtocol.A2A)
        assert m.protocol is EnumAgentProtocol.A2A

    def test_optional_field_dump_none(self) -> None:
        class M(BaseModel):
            protocol: EnumAgentProtocol | None = None

        assert M().model_dump() == {"protocol": None}
