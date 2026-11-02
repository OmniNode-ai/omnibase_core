# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""AC4 (OMN-21997): the document digest covers rows; the envelope seal covers config."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.dashboard.model_view_document import ModelViewDocument
from omnibase_core.models.dashboard.model_view_document_digest import (
    compute_view_document_digest,
    seal_view_document,
    verify_view_document,
)
from omnibase_core.utils.util_canonical_hash import compute_canonical_hash
from omnibase_core.utils.util_widget_envelope import verify_widget_envelope
from tests.unit.models.dashboard.view_builders import (
    MOMENT,
    NEW_KINDS,
    VERSION,
    document,
    section,
)


def _wire(doc: ModelViewDocument) -> dict[str, Any]:
    wire: dict[str, Any] = json.loads(doc.model_dump_json())
    return wire


def _stop_index() -> int:
    return NEW_KINDS.index("stop")


@pytest.mark.unit
class TestViewDocumentDigest:
    def test_view_document_digest_same_inputs_give_the_same_digest_twice(self) -> None:
        first = document()
        second = document()

        assert first.document_digest == second.document_digest
        assert compute_view_document_digest(first) == first.document_digest
        assert compute_view_document_digest(first) == compute_view_document_digest(
            first
        )

    def test_view_document_digest_is_the_canonical_hash_of_the_wire_form(self) -> None:
        wire = _wire(document())
        unsealed = {k: v for k, v in wire.items() if k != "document_digest"}

        assert wire["document_digest"] == f"sha256:{compute_canonical_hash(unsealed)}"

    def test_view_document_digest_a_sealed_document_verifies(self) -> None:
        verify_view_document(document())

    def test_view_document_digest_a_changed_row_fails_the_document_digest(
        self,
    ) -> None:
        wire = _wire(document())
        wire["sections"][_stop_index()]["rows"][0]["reason_text"] = "Edited"
        tampered = ModelViewDocument.model_validate(wire)

        assert compute_view_document_digest(tampered) != tampered.document_digest
        with pytest.raises(ModelOnexError, match="fails its document digest"):
            verify_view_document(tampered)

    def test_view_document_digest_an_added_row_fails_the_document_digest(self) -> None:
        wire = _wire(document())
        rows = wire["sections"][_stop_index()]["rows"]
        extra = json.loads(json.dumps(rows[0]))
        extra["row_id"]["key_values"] = ["k99"]
        rows.append(extra)

        with pytest.raises(ModelOnexError, match="fails its document digest"):
            verify_view_document(ModelViewDocument.model_validate(wire))

    def test_view_document_digest_a_changed_config_fails_the_envelope_seal(
        self,
    ) -> None:
        wire = _wire(document())
        wire["sections"][_stop_index()]["envelope"]["config"]["show_duration"] = True
        tampered = ModelViewDocument.model_validate(wire)

        with pytest.raises(ModelOnexError, match="fails its seal"):
            verify_widget_envelope(tampered.sections[_stop_index()].envelope)
        with pytest.raises(ModelOnexError, match="envelope"):
            verify_view_document(tampered)

    def test_view_document_digest_a_resealed_document_cannot_launder_a_config_edit(
        self,
    ) -> None:
        wire = _wire(document())
        wire["sections"][_stop_index()]["envelope"]["config"]["show_duration"] = True
        stale = ModelViewDocument.model_validate(wire)
        wire["document_digest"] = compute_view_document_digest(stale)
        resealed = ModelViewDocument.model_validate(wire)

        assert compute_view_document_digest(resealed) == resealed.document_digest
        with pytest.raises(ModelOnexError, match=r"fails its seal|envelope"):
            verify_view_document(resealed)

    def test_view_document_digest_covers_the_empty_state_and_generated_at(self) -> None:
        base = document(("stop",))
        wire = _wire(base)
        wire["generated_at"] = "2026-11-02T11:00:00Z"

        assert (
            compute_view_document_digest(ModelViewDocument.model_validate(wire))
            != base.document_digest
        )

        empty = seal_view_document(
            view_id=base.view_id,
            contract_version=VERSION,
            generated_at=MOMENT,
            sections=(section("stop", empty=True),),
        )
        assert empty.document_digest != base.document_digest

    def test_view_document_digest_rejects_a_malformed_digest(self) -> None:
        wire = _wire(document())
        wire["document_digest"] = "md5:abc"

        with pytest.raises(ValidationError, match="document_digest"):
            ModelViewDocument.model_validate(wire)

    def test_view_document_digest_changes_with_section_order(self) -> None:
        forward = document(("stop", "freshness"))
        reverse = document(("freshness", "stop"))

        assert forward.document_digest != reverse.document_digest
