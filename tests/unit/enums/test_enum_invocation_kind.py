# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_invocation_kind import EnumInvocationKind


@pytest.mark.unit
class TestEnumInvocationKind:
    def test_values_present(self) -> None:
        assert EnumInvocationKind.AGENT.value == "agent"
        assert EnumInvocationKind.MODEL.value == "model"

    def test_total_member_count(self) -> None:
        assert len(list(EnumInvocationKind)) == 2

    def test_str_representation(self) -> None:
        assert str(EnumInvocationKind.AGENT) == "agent"
        assert str(EnumInvocationKind.MODEL) == "model"

    def test_equality(self) -> None:
        assert EnumInvocationKind.AGENT is EnumInvocationKind.AGENT
        assert EnumInvocationKind.AGENT != EnumInvocationKind.MODEL

    def test_str_comparison(self) -> None:
        assert EnumInvocationKind.AGENT == "agent"
        assert EnumInvocationKind.MODEL == "model"

    def test_membership(self) -> None:
        members = list(EnumInvocationKind)
        assert EnumInvocationKind.AGENT in members
        assert EnumInvocationKind.MODEL in members

    def test_json_serialization(self) -> None:
        data = {"kind": EnumInvocationKind.AGENT.value}
        assert json.dumps(data) == '{"kind": "agent"}'

    def test_pydantic_integration(self) -> None:
        class M(BaseModel):
            kind: EnumInvocationKind

        m = M(kind=EnumInvocationKind.AGENT)
        assert m.kind == EnumInvocationKind.AGENT

        m2 = M(kind="model")
        assert m2.kind == EnumInvocationKind.MODEL

        assert m.model_dump() == {"kind": "agent"}

    def test_pydantic_rejects_invalid(self) -> None:
        class M(BaseModel):
            kind: EnumInvocationKind

        with pytest.raises(ValidationError):
            M(kind="invalid_kind")

    def test_case_sensitivity(self) -> None:
        assert EnumInvocationKind.AGENT.value != "AGENT"
        assert EnumInvocationKind.MODEL.value != "MODEL"
