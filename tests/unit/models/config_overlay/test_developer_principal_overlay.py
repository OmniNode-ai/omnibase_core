# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The ``developer.principal`` overlay document (OMN-19975, plan task T4.2).

A deployment declares which developer machines hold a broker principal. The
document carries the identity rows and a reference to the grant declaration
the grants are derived from; it has no field that could hold a grant, so a
grant cannot be typed into it. Every fixture value is an invented placeholder.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_config_overlay_key import EnumConfigOverlayKey
from omnibase_core.enums.enum_developer_principal_role import (
    EnumDeveloperPrincipalRole,
)
from omnibase_core.models.config_overlay import (
    ModelDeveloperPrincipalDeclaration,
    ModelDeveloperPrincipalOverlay,
)

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[4]

_VALID: dict[str, Any] = {
    "schema_version": "developer_principal.v1",
    "grants_source": "fixture/grants-declaration.yaml",
    "principals": [
        {
            "principal": "fx-alice-laptop",
            "login": "alice@example.invalid",
            "device": "laptop",
        },
        {
            "principal": "fx-alice-desktop",
            "login": "alice@example.invalid",
            "device": "desktop",
        },
        {
            "principal": "fx-bob-laptop",
            "login": "bob@example.invalid",
            "device": "laptop",
        },
    ],
}


def _body() -> dict[str, Any]:
    return copy.deepcopy(_VALID)


def test_a_valid_document_validates_and_is_frozen() -> None:
    doc = ModelDeveloperPrincipalOverlay.model_validate(_VALID)
    assert [p.principal for p in doc.principals] == [
        "fx-alice-laptop",
        "fx-alice-desktop",
        "fx-bob-laptop",
    ]
    with pytest.raises(ValidationError):
        setattr(doc, "grants_source", "x")


def test_the_key_and_its_owner() -> None:
    assert EnumConfigOverlayKey.DEVELOPER_PRINCIPAL.value == "developer.principal"
    assert (
        EnumConfigOverlayKey.DEVELOPER_PRINCIPAL.schema_ref
        == "omnibase_core:developer_principal"
    )


def test_a_document_cannot_carry_a_hand_typed_grant() -> None:
    # grants are derived from grants_source, never written on a row or the document
    body = _body()
    body["principals"][0]["extra_grants"] = []
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ModelDeveloperPrincipalOverlay.model_validate(body)
    for field in ("grants", "extra_grants", "contract_set", "client_profile"):
        with pytest.raises(ValidationError, match="extra_forbidden"):
            ModelDeveloperPrincipalOverlay.model_validate({**_VALID, field: []})
    assert not {"grants", "extra_grants", "contract_set"} & set(
        ModelDeveloperPrincipalDeclaration.model_fields
    )


def test_an_unknown_field_is_refused() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ModelDeveloperPrincipalOverlay.model_validate({**_VALID, "surprise": 1})


@pytest.mark.parametrize("field", ["schema_version", "grants_source", "principals"])
def test_every_document_field_is_required(field: str) -> None:
    body = _body()
    del body[field]
    with pytest.raises(ValidationError, match=field):
        ModelDeveloperPrincipalOverlay.model_validate(body)


def test_a_document_declaring_no_principal_is_refused() -> None:
    with pytest.raises(ValidationError, match="principals"):
        ModelDeveloperPrincipalOverlay.model_validate({**_VALID, "principals": []})


@pytest.mark.parametrize("value", ["", "   "])
def test_a_blank_grants_source_is_refused(value: str) -> None:
    with pytest.raises(ValidationError, match="grants_source"):
        ModelDeveloperPrincipalOverlay.model_validate(
            {**_VALID, "grants_source": value}
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("principal", ""),
        ("principal", "  "),
        ("principal", "Upper-case"),
        ("principal", "has space"),
        ("principal", "under_score"),
        ("principal", "-leading-dash"),
        ("login", ""),
        ("login", "   "),
        ("device", ""),
        ("device", "Has Space"),
        ("device", "UPPER"),
    ],
)
def test_a_malformed_principal_row_is_refused(field: str, value: str) -> None:
    body = _body()
    body["principals"][0][field] = value
    with pytest.raises(ValidationError, match=field):
        ModelDeveloperPrincipalOverlay.model_validate(body)


def test_a_principal_name_is_declared_once() -> None:
    body = _body()
    body["principals"][1]["principal"] = "fx-alice-laptop"
    with pytest.raises(ValidationError, match="principal"):
        ModelDeveloperPrincipalOverlay.model_validate(body)


def test_a_login_device_pair_is_declared_once() -> None:
    body = _body()
    body["principals"][1]["device"] = "laptop"
    with pytest.raises(ValidationError, match="device"):
        ModelDeveloperPrincipalOverlay.model_validate(body)


def test_the_same_device_name_under_two_logins_is_two_principals() -> None:
    doc = ModelDeveloperPrincipalOverlay.model_validate(_VALID)
    assert {p.device for p in doc.principals} == {"laptop", "desktop"}
    assert len(doc.principals) == 3


def test_a_row_without_a_role_is_a_developer_machine() -> None:
    # rows written before roles existed keep exactly the shared grant set
    doc = ModelDeveloperPrincipalOverlay.model_validate(_VALID)
    assert {p.role for p in doc.principals} == {EnumDeveloperPrincipalRole.DEVELOPER}


def test_a_row_may_select_the_machine_role() -> None:
    body = _body()
    body["principals"][0]["role"] = "machine"
    doc = ModelDeveloperPrincipalOverlay.model_validate(body)
    assert doc.principals[0].role is EnumDeveloperPrincipalRole.MACHINE
    assert doc.principals[1].role is EnumDeveloperPrincipalRole.DEVELOPER


@pytest.mark.parametrize("value", ["admin", "Machine", "", "grants"])
def test_a_role_outside_the_vocabulary_is_refused(value: str) -> None:
    body = _body()
    body["principals"][0]["role"] = value
    with pytest.raises(ValidationError, match="role"):
        ModelDeveloperPrincipalOverlay.model_validate(body)


def _schema_script() -> ModuleType:
    path = _REPO_ROOT / "scripts" / "gen_config_overlay_schemas.py"
    spec = importlib.util.spec_from_file_location("gen_config_overlay_schemas", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_schema_export_round_trips() -> None:
    script = _schema_script()
    filename = "developer_principal.schema.json"
    assert script.SCHEMA_EXPORTS[filename] is ModelDeveloperPrincipalOverlay
    committed = json.loads((script.SCHEMA_DIR / filename).read_text("utf-8"))
    assert committed == ModelDeveloperPrincipalOverlay.model_json_schema()
    assert committed["additionalProperties"] is False
    assert script.main(["--check"]) == 0
