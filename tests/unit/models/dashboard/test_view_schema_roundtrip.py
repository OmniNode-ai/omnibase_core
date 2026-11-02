# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""AC6 (OMN-21997): a sealed, serialised view document satisfies the published schema.

The schema is the one ``scripts/emit_ts_types.py`` publishes. Each of the seven new
section variants is sealed, serialised and validated against it, and a cross-kind
section is refused by both the model and the schema.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from pydantic import ValidationError

from omnibase_core.models.dashboard.model_view_document import ModelViewDocument
from omnibase_core.models.dashboard.model_view_document_digest import (
    verify_view_document,
)
from omnibase_core.utils.util_canonical_hash import compute_canonical_hash
from tests.unit.models.dashboard.view_builders import (
    NEW_KINDS,
    ROW_BUILDERS,
    document,
    envelope,
    row_id,
    section,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]


def _published_schema(root: str = "ModelViewDocument") -> dict[str, Any]:
    path = _REPO_ROOT / "scripts" / "emit_ts_types.py"
    spec = importlib.util.spec_from_file_location("_emit_ts_probe_views", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    defs: dict[str, object] = module._combined_defs()
    return {
        "$id": "https://omninode.ai/schemas/omnidash-v2.json",
        "$defs": defs,
        "$ref": f"#/$defs/{root}",
    }


def _wire(doc: ModelViewDocument) -> dict[str, Any]:
    wire: dict[str, Any] = json.loads(doc.model_dump_json())
    return wire


@pytest.mark.unit
class TestViewSchemaRoundtrip:
    def test_view_schema_roundtrip_emitter_publishes_the_view_models(self) -> None:
        defs = _published_schema()["$defs"]

        for name in (
            "ModelViewDocument",
            "ModelViewContract",
            "ModelViewManifest",
            "ModelViewFieldMap",
        ):
            assert name in defs

    @pytest.mark.parametrize("kind", NEW_KINDS)
    def test_view_schema_roundtrip_each_kind_validates_after_sealing(
        self, kind: str
    ) -> None:
        doc = document((kind,))
        wire = _wire(doc)

        jsonschema.validate(instance=wire, schema=_published_schema())

        unsealed = {k: v for k, v in wire.items() if k != "document_digest"}
        assert wire["document_digest"] == f"sha256:{compute_canonical_hash(unsealed)}"
        verify_view_document(ModelViewDocument.model_validate(wire))

    def test_view_schema_roundtrip_all_kinds_in_one_document(self) -> None:
        jsonschema.validate(instance=_wire(document()), schema=_published_schema())

    @pytest.mark.parametrize("kind", NEW_KINDS)
    def test_view_schema_roundtrip_empty_state_section_validates(
        self, kind: str
    ) -> None:
        from omnibase_core.models.dashboard.model_view_document_digest import (
            seal_view_document,
        )
        from tests.unit.models.dashboard.view_builders import (
            MOMENT,
            VERSION,
            VIEW_ID,
        )

        doc = seal_view_document(
            view_id=VIEW_ID,
            contract_version=VERSION,
            generated_at=MOMENT,
            sections=(section(kind, empty=True),),
        )

        jsonschema.validate(instance=_wire(doc), schema=_published_schema())

    @pytest.mark.parametrize("kind", NEW_KINDS)
    def test_view_schema_roundtrip_refuses_a_cross_kind_envelope(
        self, kind: str
    ) -> None:
        other = NEW_KINDS[(NEW_KINDS.index(kind) + 1) % len(NEW_KINDS)]
        wire = _wire(document((kind,)))
        wire["sections"][0]["envelope"] = json.loads(envelope(other).model_dump_json())

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=wire, schema=_published_schema())
        with pytest.raises(ValidationError):
            ModelViewDocument.model_validate(wire)

    @pytest.mark.parametrize("kind", NEW_KINDS)
    def test_view_schema_roundtrip_refuses_a_cross_kind_discriminator(
        self, kind: str
    ) -> None:
        other = NEW_KINDS[(NEW_KINDS.index(kind) + 1) % len(NEW_KINDS)]
        wire = _wire(document((kind,)))
        wire["sections"][0]["kind"] = other

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=wire, schema=_published_schema())
        with pytest.raises(ValidationError):
            ModelViewDocument.model_validate(wire)

    @pytest.mark.parametrize("kind", NEW_KINDS)
    def test_view_schema_roundtrip_refuses_cross_kind_rows(self, kind: str) -> None:
        other = NEW_KINDS[(NEW_KINDS.index(kind) + 1) % len(NEW_KINDS)]
        wire = _wire(document((kind,)))
        foreign = ROW_BUILDERS[other](row_id(kind))
        wire["sections"][0]["rows"] = [json.loads(foreign.model_dump_json())]

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=wire, schema=_published_schema())
        with pytest.raises(ValidationError):
            ModelViewDocument.model_validate(wire)

    def test_view_schema_roundtrip_schema_has_no_hex_colour_default(self) -> None:
        text = json.dumps(_published_schema()["$defs"]["ModelViewDocument"])

        assert "#" not in text.replace("#/$defs/", "")
