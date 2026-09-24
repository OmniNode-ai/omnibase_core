# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed config overlay documents (OMN-19391, plan task B2).

Every schema is frozen and ``extra="forbid"``; each refuses an unknown field
and a missing required field; no field defaults to a model, an endpoint or a
price; the committed JSON Schema exports equal the pydantic models; and the
A1 guard finds no model id or endpoint in the new package.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_config_overlay_key import EnumConfigOverlayKey
from omnibase_core.enums.enum_config_overlay_source import EnumConfigOverlaySource
from omnibase_core.enums.enum_llm_pricing_source import EnumLlmPricingSource
from omnibase_core.enums.enum_llm_tier_class import EnumLlmTierClass
from omnibase_core.models.config_overlay import (
    ModelConfigOverlayDocument,
    ModelConfigOverlayScope,
    ModelEmbeddingEndpointOverlay,
    ModelLlmCatalogEntry,
    ModelLlmCatalogOverlay,
    ModelLlmComputeCostEntry,
    ModelLlmPricingEntry,
    ModelLlmPricingEvidence,
    ModelLlmPricingOverlay,
    ModelLlmRunnerCostPolicy,
)
from omnibase_core.validation.hardcoded_model_config.handler import scan
from omnibase_core.validation.hardcoded_model_config.runtime_hardcoded_model_config import (
    load_policy,
)

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SHA = "a" * 64

_EVIDENCE: dict[str, object] = {
    "generated_at": "2026-09-24T00:00:00+00:00",
    "sample_window_days": 7,
    "sample_count": 40,
    "min_samples": 20,
    "query": "usage rows over the window",
    "authoritative": True,
}
_PRICE: dict[str, object] = {
    "input_price_per_1m": 3.0,
    "output_price_per_1m": 15.0,
    "currency": "USD",
    "effective_date": "2026-09-01",
    "source": "vendor_list",
}
_CATALOG_ENTRY: dict[str, object] = {
    "served_model_names": ["fixture-model-a-served"],
    "provider": "openai_compatible",
    "context_window_tokens": 32768,
    "capability_tags": ["code"],
    "tier_class": "local",
    "free": True,
}
_COMPUTE: dict[str, object] = {
    "electricity_per_hour": 0.1,
    "amortization_per_hour": 0.2,
}
_RUNNER: dict[str, object] = {"github_hosted_per_minute_usd": 0.008}

_VALID: dict[type[BaseModel], dict[str, object]] = {
    ModelConfigOverlayScope: {"environment": "lab", "lane": "dev"},
    ModelConfigOverlayDocument: {
        "key": "llm.pricing",
        "schema_ref": "omnibase_core:llm_pricing",
        "schema_version": "llm_pricing.v1",
        "source": "store",
        "sha256": _SHA,
        "content": {"schema_version": "llm_pricing.v1", "models": {}},
    },
    ModelLlmCatalogEntry: _CATALOG_ENTRY,
    ModelLlmCatalogOverlay: {
        "schema_version": "llm_catalog.v1",
        "models": {"fixture-model-a": _CATALOG_ENTRY},
    },
    ModelLlmPricingEvidence: _EVIDENCE,
    ModelLlmPricingEntry: _PRICE,
    ModelLlmComputeCostEntry: _COMPUTE,
    ModelLlmRunnerCostPolicy: _RUNNER,
    ModelLlmPricingOverlay: {
        "schema_version": "llm_pricing.v1",
        "models": {"fixture-model-b": _PRICE},
        "compute_cost": {"fixture-gpu": _COMPUTE},
        "runner_cost": _RUNNER,
    },
    ModelEmbeddingEndpointOverlay: {
        "schema_version": "embedding_endpoint.v1",
        "endpoint_url": "http://embeddings.test:8000",
        "model_name": "fixture-embedder",
        "dimension": 1024,
    },
}

_REQUIRED: list[tuple[type[BaseModel], str]] = [
    (model, name)
    for model in _VALID
    for name, field in model.model_fields.items()
    if field.is_required()
]


def _schema_script() -> ModuleType:
    path = _REPO_ROOT / "scripts" / "gen_config_overlay_schemas.py"
    spec = importlib.util.spec_from_file_location("gen_config_overlay_schemas", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("model", list(_VALID), ids=lambda m: m.__name__)
def test_valid_document_validates_and_is_frozen(model: type[BaseModel]) -> None:
    instance = model.model_validate(_VALID[model])
    first_field = next(iter(model.model_fields))
    with pytest.raises(ValidationError):
        setattr(instance, first_field, getattr(instance, first_field))


@pytest.mark.parametrize("model", list(_VALID), ids=lambda m: m.__name__)
def test_extra_field_is_refused(model: type[BaseModel]) -> None:
    data = copy.deepcopy(_VALID[model])
    data["unexpected_field"] = 1
    with pytest.raises(ValidationError, match="unexpected_field"):
        model.model_validate(data)


@pytest.mark.parametrize(
    ("model", "field_name"), _REQUIRED, ids=lambda v: getattr(v, "__name__", v)
)
def test_missing_required_field_is_refused(
    model: type[BaseModel], field_name: str
) -> None:
    data = copy.deepcopy(_VALID[model])
    del data[field_name]
    with pytest.raises(ValidationError, match=field_name):
        model.model_validate(data)


def test_the_required_fields_the_plan_names() -> None:
    required = set(_REQUIRED)
    assert (ModelLlmPricingEntry, "source") in required
    assert (ModelLlmPricingEntry, "effective_date") in required
    assert (ModelLlmCatalogEntry, "tier_class") in required
    assert (ModelLlmCatalogEntry, "free") in required
    assert (ModelEmbeddingEndpointOverlay, "endpoint_url") in required
    assert (ModelEmbeddingEndpointOverlay, "model_name") in required


def test_nested_catalog_entry_without_tier_class_is_refused() -> None:
    entry = {k: v for k, v in _CATALOG_ENTRY.items() if k != "tier_class"}
    with pytest.raises(ValidationError, match="tier_class"):
        ModelLlmCatalogOverlay.model_validate(
            {"schema_version": "llm_catalog.v1", "models": {"fixture-model-a": entry}}
        )


def test_nested_price_without_source_is_refused() -> None:
    price = {k: v for k, v in _PRICE.items() if k != "source"}
    with pytest.raises(ValidationError, match="source"):
        ModelLlmPricingOverlay.model_validate(
            {"schema_version": "llm_pricing.v1", "models": {"fixture-model-b": price}}
        )


def test_pricing_source_is_closed() -> None:
    with pytest.raises(ValidationError, match="source"):
        ModelLlmPricingEntry.model_validate({**_PRICE, "source": "guessed"})


def test_measured_price_requires_evidence() -> None:
    with pytest.raises(ValidationError, match="evidence"):
        ModelLlmPricingEntry.model_validate({**_PRICE, "source": "measured"})
    entry = ModelLlmPricingEntry.model_validate(
        {**_PRICE, "source": "measured", "evidence": _EVIDENCE}
    )
    assert entry.source is EnumLlmPricingSource.MEASURED


def test_evidence_time_must_be_timezone_aware() -> None:
    with pytest.raises(ValidationError, match="generated_at"):
        ModelLlmPricingEvidence.model_validate(
            {**_EVIDENCE, "generated_at": "2026-09-24T00:00:00"}
        )


def test_currency_is_an_iso_code() -> None:
    with pytest.raises(ValidationError, match="currency"):
        ModelLlmPricingEntry.model_validate({**_PRICE, "currency": "usd"})


def test_negative_price_is_refused() -> None:
    with pytest.raises(ValidationError, match="input_price_per_1m"):
        ModelLlmPricingEntry.model_validate({**_PRICE, "input_price_per_1m": -1})


def test_empty_catalog_is_refused() -> None:
    with pytest.raises(ValidationError, match="models"):
        ModelLlmCatalogOverlay.model_validate(
            {"schema_version": "llm_catalog.v1", "models": {}}
        )


def test_wrong_schema_version_is_refused() -> None:
    with pytest.raises(ValidationError, match="schema_version"):
        ModelLlmCatalogOverlay.model_validate(
            {**_VALID[ModelLlmCatalogOverlay], "schema_version": "llm_catalog.v2"}
        )


@pytest.mark.parametrize("url", ["embeddings.test:8000", "ftp://embeddings.test"])
def test_embedding_endpoint_must_be_an_http_url(url: str) -> None:
    with pytest.raises(ValidationError, match="endpoint_url"):
        ModelEmbeddingEndpointOverlay.model_validate(
            {**_VALID[ModelEmbeddingEndpointOverlay], "endpoint_url": url}
        )


def test_document_schema_ref_must_match_its_key() -> None:
    with pytest.raises(ValidationError, match="schema_ref"):
        ModelConfigOverlayDocument.model_validate(
            {
                **_VALID[ModelConfigOverlayDocument],
                "schema_ref": "omnibase_core:llm_catalog",
            }
        )


def test_document_sha256_is_lowercase_hex() -> None:
    with pytest.raises(ValidationError, match="sha256"):
        ModelConfigOverlayDocument.model_validate(
            {**_VALID[ModelConfigOverlayDocument], "sha256": "A" * 64}
        )


@pytest.mark.parametrize("segment", ["../dev", "dev/x", "Dev", ""])
def test_scope_segments_are_single_safe_path_parts(segment: str) -> None:
    with pytest.raises(ValidationError):
        ModelConfigOverlayScope.model_validate({"environment": "lab", "lane": segment})


def test_the_five_overlay_keys_and_their_owners() -> None:
    assert {k.value: k.schema_ref for k in EnumConfigOverlayKey} == {
        "delegation.lane_overlay": "omnibase_infra:bifrost_lane_overlay",
        "routing.tiers": "omnimarket:routing_tiers",
        "llm.catalog": "omnibase_core:llm_catalog",
        "llm.pricing": "omnibase_core:llm_pricing",
        "embedding.endpoint": "omnibase_core:embedding_endpoint",
    }
    assert {s.value for s in EnumConfigOverlaySource} == {"store", "local-home"}
    assert {t.value for t in EnumLlmTierClass} == {"local", "cheap_cloud", "frontier"}


@pytest.mark.parametrize("model", list(_VALID), ids=lambda m: m.__name__)
def test_no_default_names_a_model_an_endpoint_or_a_price(
    model: type[BaseModel],
) -> None:
    # A default may only be an absence: None, empty text or an empty collection.
    for name, field in model.model_fields.items():
        if field.is_required():
            continue
        default = field.get_default(call_default_factory=True)
        assert default in (None, "", (), {}), f"{model.__name__}.{name}={default!r}"


def test_schema_export_matches_model() -> None:
    script = _schema_script()
    for filename, model in script.SCHEMA_EXPORTS.items():
        committed = json.loads((script.SCHEMA_DIR / filename).read_text("utf-8"))
        assert committed == model.model_json_schema(), filename
    assert script.main(["--check"]) == 0


def test_no_model_or_endpoint_literal_in_the_new_package() -> None:
    policy = load_policy()
    roots = [
        _REPO_ROOT / "src" / "omnibase_core" / "models" / "config_overlay",
        _REPO_ROOT / "src" / "omnibase_core" / "schemas" / "config_overlay",
    ]
    findings = [
        f"{f.path}:{f.line}:{f.family}"
        for root in roots
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.suffix in {".py", ".json"}
        for f in scan(
            path.relative_to(_REPO_ROOT).as_posix(), path.read_text("utf-8"), policy
        )
    ]
    assert findings == []
