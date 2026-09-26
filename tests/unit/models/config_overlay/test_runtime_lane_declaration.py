# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The runtime lane declaration, its roles and its resolution rules (OMN-19746).

Plan task LO1 of knowledge-base-internal
``beta/plans/2026-09-26-runtime-lane-overlays-plan.md``. A runtime learns which
lane it is only from an overlay document whoever runs it supplies; core owns
the typed declaration and the refusals and names no lane.
"""

from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_config_overlay_key import EnumConfigOverlayKey
from omnibase_core.enums.enum_config_overlay_source import EnumConfigOverlaySource
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_runtime_lane_role import EnumRuntimeLaneRole
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.config_overlay import (
    RUNTIME_LANE_ENV_VAR,
    ModelConfigOverlayDocument,
    ModelRuntimeLaneDeclaration,
)
from omnibase_core.models.contracts.subcontracts.model_runtime_lane_role_requirement import (
    ModelRuntimeLaneRoleRequirement,
)
from omnibase_core.types.type_json import JsonType

pytestmark = pytest.mark.unit

# A lane id no deployment has ever used: the model must accept any slug.
_LANE = "customer-edge-7"
_WHERE = "local-home ~/.omninode/config/prod/customer-edge-7/runtime.lane.json"


def _content(**overrides: JsonType) -> dict[str, JsonType]:
    body: dict[str, JsonType] = {
        "schema_version": "runtime_lane.v1",
        "lane_id": _LANE,
        "roles": ["dev", "lab"],
        "description": "A customer's edge deployment",
    }
    body.update(overrides)
    return body


def _document(content: dict[str, JsonType]) -> ModelConfigOverlayDocument:
    raw = json.dumps(content, sort_keys=True).encode()
    return ModelConfigOverlayDocument(
        key=EnumConfigOverlayKey.RUNTIME_LANE,
        schema_ref=EnumConfigOverlayKey.RUNTIME_LANE.schema_ref,
        schema_version="runtime_lane.v1",
        source=EnumConfigOverlaySource.LOCAL_HOME,
        sha256=hashlib.sha256(raw).hexdigest(),
        content=content,
    )


# --- the declaration model ----------------------------------------------------


def test_a_valid_declaration_validates_and_is_frozen() -> None:
    declaration = ModelRuntimeLaneDeclaration.model_validate(_content())
    assert declaration.lane_id == _LANE
    assert declaration.roles == (EnumRuntimeLaneRole.DEV, EnumRuntimeLaneRole.LAB)
    with pytest.raises(ValidationError):
        declaration.lane_id = "other"  # type: ignore[misc]


def test_an_unknown_role_is_refused() -> None:
    with pytest.raises(ValidationError, match="roles"):
        ModelRuntimeLaneDeclaration.model_validate(_content(roles=["labb"]))


def test_an_empty_role_list_is_refused() -> None:
    with pytest.raises(ValidationError, match="roles"):
        ModelRuntimeLaneDeclaration.model_validate(_content(roles=[]))


def test_duplicate_roles_are_collapsed_in_declaration_order() -> None:
    declaration = ModelRuntimeLaneDeclaration.model_validate(
        _content(roles=["lab", "dev", "lab"])
    )
    assert declaration.roles == (EnumRuntimeLaneRole.LAB, EnumRuntimeLaneRole.DEV)


@pytest.mark.parametrize("lane_id", ["", "Dev", "a/b", "../x", "-lead", "x" * 65])
def test_a_lane_id_outside_the_slug_pattern_is_refused(lane_id: str) -> None:
    with pytest.raises(ValidationError, match="lane_id"):
        ModelRuntimeLaneDeclaration.model_validate(_content(lane_id=lane_id))


def test_an_extra_field_is_refused() -> None:
    with pytest.raises(ValidationError, match="extra"):
        ModelRuntimeLaneDeclaration.model_validate(_content(compose_project="x"))


def test_the_wrong_schema_version_is_refused() -> None:
    with pytest.raises(ValidationError, match="schema_version"):
        ModelRuntimeLaneDeclaration.model_validate(
            _content(schema_version="runtime_lane.v2")
        )


def test_a_blank_description_is_refused() -> None:
    with pytest.raises(ValidationError, match="description"):
        ModelRuntimeLaneDeclaration.model_validate(_content(description=""))


def test_every_field_is_required() -> None:
    for name in ModelRuntimeLaneDeclaration.model_fields:
        body = _content()
        del body[name]
        with pytest.raises(ValidationError, match=name):
            ModelRuntimeLaneDeclaration.model_validate(body)


def test_has_roles_is_all_of() -> None:
    declaration = ModelRuntimeLaneDeclaration.model_validate(_content())
    assert declaration.has_roles((EnumRuntimeLaneRole.LAB,))
    assert declaration.has_roles((EnumRuntimeLaneRole.LAB, EnumRuntimeLaneRole.DEV))
    assert not declaration.has_roles(
        (EnumRuntimeLaneRole.LAB, EnumRuntimeLaneRole.PRODUCTION)
    )


# --- the role requirement a contract declares ---------------------------------


def test_a_requirement_admits_a_lane_holding_every_role() -> None:
    declaration = ModelRuntimeLaneDeclaration.model_validate(_content())
    assert ModelRuntimeLaneRoleRequirement.model_validate({"roles": ["lab"]}).admits(
        declaration
    )
    assert not ModelRuntimeLaneRoleRequirement.model_validate(
        {"roles": ["lab", "proof"]}
    ).admits(declaration)


def test_a_requirement_accepts_one_role_as_a_string() -> None:
    requirement = ModelRuntimeLaneRoleRequirement.model_validate({"roles": "lab"})
    assert requirement.roles == (EnumRuntimeLaneRole.LAB,)


@pytest.mark.parametrize("roles", [[], ["labb"], [""], [3]])
def test_a_requirement_with_no_or_an_unknown_role_is_refused(roles: object) -> None:
    with pytest.raises(ValidationError):
        ModelRuntimeLaneRoleRequirement.model_validate({"roles": roles})


# --- resolve(): the startup refusals ------------------------------------------


def test_resolve_returns_the_declaration_the_overlay_supplies() -> None:
    declaration = ModelRuntimeLaneDeclaration.resolve(
        declared_lane_id=_LANE, document=_document(_content()), where=_WHERE
    )
    assert declaration.lane_id == _LANE
    assert declaration.has_roles((EnumRuntimeLaneRole.LAB,))


def test_resolve_normalises_surrounding_whitespace_in_the_declared_lane() -> None:
    declaration = ModelRuntimeLaneDeclaration.resolve(
        declared_lane_id=f"  {_LANE}\n", document=_document(_content()), where=_WHERE
    )
    assert declaration.lane_id == _LANE


@pytest.mark.parametrize("declared", [None, "", "   "])
def test_resolve_refuses_an_unset_lane_naming_the_variable(
    declared: str | None,
) -> None:
    with pytest.raises(ModelOnexError) as caught:
        ModelRuntimeLaneDeclaration.resolve(
            declared_lane_id=declared, document=_document(_content()), where=_WHERE
        )
    assert RUNTIME_LANE_ENV_VAR in caught.value.message
    assert "not set" in caught.value.message
    assert caught.value.error_code == EnumCoreErrorCode.CONFIGURATION_NOT_FOUND


def test_resolve_refuses_a_lane_that_is_not_a_slug_naming_the_value() -> None:
    with pytest.raises(ModelOnexError) as caught:
        ModelRuntimeLaneDeclaration.resolve(
            declared_lane_id="Compose Dev", document=None, where=_WHERE
        )
    assert RUNTIME_LANE_ENV_VAR in caught.value.message
    assert "'Compose Dev'" in caught.value.message
    assert caught.value.error_code == EnumCoreErrorCode.INVALID_CONFIGURATION


def test_resolve_refuses_a_lane_the_overlay_does_not_declare() -> None:
    with pytest.raises(ModelOnexError) as caught:
        ModelRuntimeLaneDeclaration.resolve(
            declared_lane_id=_LANE, document=None, where=_WHERE
        )
    message = caught.value.message
    assert _LANE in message
    assert "runtime.lane" in message
    assert _WHERE in message
    assert caught.value.error_code == EnumCoreErrorCode.CONFIGURATION_NOT_FOUND


def test_resolve_refuses_a_document_for_another_key() -> None:
    other = ModelConfigOverlayDocument(
        key=EnumConfigOverlayKey.EMBEDDING_ENDPOINT,
        schema_ref=EnumConfigOverlayKey.EMBEDDING_ENDPOINT.schema_ref,
        schema_version="embedding_endpoint.v1",
        source=EnumConfigOverlaySource.LOCAL_HOME,
        sha256="0" * 64,
        content={},
    )
    with pytest.raises(ModelOnexError) as caught:
        ModelRuntimeLaneDeclaration.resolve(
            declared_lane_id=_LANE, document=other, where=_WHERE
        )
    assert "embedding.endpoint" in caught.value.message
    assert caught.value.error_code == EnumCoreErrorCode.INVALID_CONFIGURATION


def test_resolve_refuses_an_invalid_document_naming_the_field() -> None:
    with pytest.raises(ModelOnexError) as caught:
        ModelRuntimeLaneDeclaration.resolve(
            declared_lane_id=_LANE,
            document=_document(_content(roles=["labb"])),
            where=_WHERE,
        )
    message = caught.value.message
    assert "roles" in message
    assert _WHERE in message
    assert caught.value.error_code == EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR


def test_resolve_refuses_a_document_declaring_another_lane_naming_both() -> None:
    with pytest.raises(ModelOnexError) as caught:
        ModelRuntimeLaneDeclaration.resolve(
            declared_lane_id=_LANE,
            document=_document(_content(lane_id="someone-else")),
            where=_WHERE,
        )
    message = caught.value.message
    assert _LANE in message
    assert "someone-else" in message
    assert _WHERE in message
    assert caught.value.error_code == EnumCoreErrorCode.INVALID_CONFIGURATION


def test_the_role_vocabulary_is_the_closed_set_the_plan_names() -> None:
    assert {role.value for role in EnumRuntimeLaneRole} == {
        "lab",
        "dev",
        "proof",
        "read_only",
        "collaborator",
        "ephemeral",
        "fault_injection",
        "staging",
        "production",
        "local",
    }
