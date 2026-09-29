# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The declared-lab-state overlay documents (OMN-19933, plan task C1).

Plan ``2026-09-28-verification-before-and-after-merge-and-declared-lab-state``
section 3.4: three overlay keys a deployment supplies, each a frozen
``extra="forbid"`` document with a JSON Schema export. Nothing here names a lane,
host or principal: every fixture value is an invented placeholder.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_config_overlay_key import EnumConfigOverlayKey
from omnibase_core.models.config_overlay import (
    ModelBrokerPrincipalGrantsOverlay,
    ModelDeclaredStateObservation,
    ModelHostSettingsOverlay,
    ModelLaneServicesOverlay,
)

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SHA = "a" * 64

_PRINCIPAL: dict[str, object] = {
    "principal": "fixture-principal-1",
    "broker_id": "fixture-broker",
    "contract_set": ["fixture-contract-a"],
    "client_profile": None,
    "extra_grants": [
        {
            "resource_type": "topic",
            "resource_name": "fixture.topic.v1",
            "operation": "describe",
            "reason": "a client that lists group offsets",
        }
    ],
}
_HOST: dict[str, object] = {
    "host_id": "fixture-host-1",
    "kernel_parameters": {"vm.swappiness": "10"},
    "systemd_units": [
        {
            "unit_name": "fixture.service",
            "content_sha256": _SHA,
            "drop_ins": [{"file_name": "10-fixture.conf", "content_sha256": _SHA}],
        }
    ],
    "network_interfaces": [
        {"interface": "fixture0", "settings": {"mtu": "1500"}},
    ],
    "power_settings": {"sleep": "disabled"},
}
_LANE: dict[str, object] = {
    "lane_id": "fixture-lane-1",
    "services": [{"service_name": "fixture-svc", "restart_policy": "unless-stopped"}],
    "one_shot_jobs": [
        {"job_name": "fixture-init", "prepares_service": "fixture-svc"},
    ],
}

_VALID: dict[type[BaseModel], dict[str, object]] = {
    ModelBrokerPrincipalGrantsOverlay: {
        "schema_version": "broker_principal_grants.v1",
        "principals": [_PRINCIPAL],
    },
    ModelHostSettingsOverlay: {
        "schema_version": "host_settings.v1",
        "hosts": [_HOST],
    },
    ModelLaneServicesOverlay: {
        "schema_version": "lane_services.v1",
        **_LANE,
    },
    ModelDeclaredStateObservation: {
        "surface_kind": "broker_acl",
        "surface_id": "fixture-broker",
        "item_key": "fixture-principal-1",
        "observed_digest": _SHA,
        "read_ok": True,
        "detail": "",
    },
}


@pytest.mark.parametrize("model", list(_VALID), ids=lambda m: m.__name__)
def test_valid_documents_validate_and_are_frozen(model: type[BaseModel]) -> None:
    doc = model.model_validate(_VALID[model])
    with pytest.raises(ValidationError):
        setattr(doc, next(iter(model.model_fields)), "x")


@pytest.mark.parametrize("model", list(_VALID), ids=lambda m: m.__name__)
def test_an_unknown_field_is_refused(model: type[BaseModel]) -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        model.model_validate({**_VALID[model], "surprise": 1})


def test_an_unknown_field_nested_in_a_principal_is_refused() -> None:
    body = copy.deepcopy(_VALID[ModelBrokerPrincipalGrantsOverlay])
    body["principals"][0]["surprise"] = 1  # type: ignore[index]
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ModelBrokerPrincipalGrantsOverlay.model_validate(body)


@pytest.mark.parametrize("value", ["", "   "])
def test_an_empty_principal_is_refused(value: str) -> None:
    body = copy.deepcopy(_VALID[ModelBrokerPrincipalGrantsOverlay])
    body["principals"][0]["principal"] = value  # type: ignore[index]
    with pytest.raises(ValidationError, match="principal"):
        ModelBrokerPrincipalGrantsOverlay.model_validate(body)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("principal",), "  "),
        (("client_profile",), "  "),
        (("contract_set",), ["  "]),
        (("extra_grants", 0, "resource_name"), " "),
        (("extra_grants", 0, "reason"), "   "),
    ],
)
def test_whitespace_only_text_is_refused_everywhere(
    path: tuple[object, ...], value: object
) -> None:
    body = copy.deepcopy(_VALID[ModelBrokerPrincipalGrantsOverlay])
    target = body["principals"][0]  # type: ignore[index]
    for step in path[:-1]:
        target = target[step]
    target[path[-1]] = value
    with pytest.raises(ValidationError):
        ModelBrokerPrincipalGrantsOverlay.model_validate(body)


def test_a_document_declaring_no_principal_is_refused() -> None:
    with pytest.raises(ValidationError, match="principals"):
        ModelBrokerPrincipalGrantsOverlay.model_validate(
            {"schema_version": "broker_principal_grants.v1", "principals": []}
        )


def test_a_principal_needs_a_contract_set_or_a_client_profile() -> None:
    body = copy.deepcopy(_VALID[ModelBrokerPrincipalGrantsOverlay])
    body["principals"][0]["contract_set"] = []  # type: ignore[index]
    with pytest.raises(ValidationError, match="contract_set"):
        ModelBrokerPrincipalGrantsOverlay.model_validate(body)
    body["principals"][0]["client_profile"] = "fixture-profile"  # type: ignore[index]
    ModelBrokerPrincipalGrantsOverlay.model_validate(body)


def test_an_extra_grant_needs_a_reason() -> None:
    body = copy.deepcopy(_VALID[ModelBrokerPrincipalGrantsOverlay])
    body["principals"][0]["extra_grants"][0]["reason"] = ""  # type: ignore[index]
    with pytest.raises(ValidationError, match="reason"):
        ModelBrokerPrincipalGrantsOverlay.model_validate(body)


def test_a_unit_digest_must_be_lowercase_sha256() -> None:
    body = copy.deepcopy(_VALID[ModelHostSettingsOverlay])
    body["hosts"][0]["systemd_units"][0]["content_sha256"] = "XYZ"  # type: ignore[index]
    with pytest.raises(ValidationError, match="content_sha256"):
        ModelHostSettingsOverlay.model_validate(body)


def test_an_empty_host_id_and_an_unknown_restart_policy_are_refused() -> None:
    body = copy.deepcopy(_VALID[ModelHostSettingsOverlay])
    body["hosts"][0]["host_id"] = ""  # type: ignore[index]
    with pytest.raises(ValidationError, match="host_id"):
        ModelHostSettingsOverlay.model_validate(body)
    lane = copy.deepcopy(_VALID[ModelLaneServicesOverlay])
    lane["services"][0]["restart_policy"] = "sometimes"  # type: ignore[index]
    with pytest.raises(ValidationError, match="restart_policy"):
        ModelLaneServicesOverlay.model_validate(lane)


def test_a_one_shot_job_must_prepare_a_declared_service() -> None:
    lane = copy.deepcopy(_VALID[ModelLaneServicesOverlay])
    lane["one_shot_jobs"][0]["prepares_service"] = "undeclared"  # type: ignore[index]
    with pytest.raises(ValidationError, match="prepares_service"):
        ModelLaneServicesOverlay.model_validate(lane)


def test_the_new_keys_and_their_owners() -> None:
    assert (
        EnumConfigOverlayKey.BROKER_PRINCIPAL_GRANTS.value == "broker.principal_grants"
    )
    assert (
        EnumConfigOverlayKey.HOST_SETTINGS.schema_ref == "omnibase_core:host_settings"
    )
    assert (
        EnumConfigOverlayKey.LANE_SERVICES.schema_ref == "omnibase_core:lane_services"
    )


@pytest.mark.parametrize("model", list(_VALID), ids=lambda m: m.__name__)
def test_no_default_names_a_value(model: type[BaseModel]) -> None:
    for name, field in model.model_fields.items():
        if field.is_required():
            continue
        default = field.get_default(call_default_factory=True)
        assert default in (None, "", (), {}), f"{model.__name__}.{name}={default!r}"


def _schema_script() -> ModuleType:
    path = _REPO_ROOT / "scripts" / "gen_config_overlay_schemas.py"
    spec = importlib.util.spec_from_file_location("gen_config_overlay_schemas", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_schema_exports_round_trip() -> None:
    script = _schema_script()
    expected = {
        "broker_principal_grants.schema.json": ModelBrokerPrincipalGrantsOverlay,
        "host_settings.schema.json": ModelHostSettingsOverlay,
        "lane_services.schema.json": ModelLaneServicesOverlay,
    }
    for filename, model in expected.items():
        assert script.SCHEMA_EXPORTS[filename] is model
        committed = json.loads((script.SCHEMA_DIR / filename).read_text("utf-8"))
        assert committed == model.model_json_schema(), filename
        # the exported schema refuses what the model refuses
        assert committed["additionalProperties"] is False
    assert script.main(["--check"]) == 0


def test_the_core_source_names_no_lab_principal_host_or_lane() -> None:
    pattern = re.compile(r"compose-dev|stability-test|judge|prepr-")
    roots = [
        _REPO_ROOT / "src" / "omnibase_core" / "enums",
        _REPO_ROOT / "src" / "omnibase_core" / "models" / "config_overlay",
        _REPO_ROOT / "src" / "omnibase_core" / "schemas" / "config_overlay",
    ]
    prefixes = (
        "model_broker",
        "model_host",
        "model_lane",
        "model_declared",
        "enum_declared",
        "broker_principal",
        "host_settings",
        "lane_services",
    )
    files = [
        f
        for root in roots
        for f in sorted(root.rglob("*"))
        if f.is_file() and f.suffix in {".py", ".json"} and f.name.startswith(prefixes)
    ]
    assert files, "the scan found no files: the new files are missing"
    hits = [str(f) for f in files if pattern.search(f.read_text("utf-8"))]
    assert hits == []


def test_the_lane_scan_pattern_catches_the_positive_control() -> None:
    control = (
        _REPO_ROOT
        / "src"
        / "omnibase_core"
        / "constants"
        / "constants_runtime_lanes.py"
    )
    assert re.search(
        r"compose-dev|stability-test|judge|prepr-", control.read_text("utf-8")
    )
