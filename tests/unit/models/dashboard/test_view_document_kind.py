# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""AC3 (OMN-21997): the view document's sections agree with their kind."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_empty_state_reason import EnumEmptyStateReason
from omnibase_core.models.dashboard.model_view_document import ModelViewDocument
from omnibase_core.models.dashboard.model_view_empty_state import ModelViewEmptyState
from omnibase_core.models.dashboard.model_view_section_line_card import (
    ModelViewSectionLineCard,
)
from omnibase_core.models.dashboard.model_view_section_stop import (
    ModelViewSectionStop,
)
from tests.unit.models.dashboard.view_builders import (
    CONFIG_BUILDERS,
    NEW_KINDS,
    ROW_BUILDERS,
    SECTION_CLASSES,
    VIEW_ID,
    document,
    envelope,
    metric_card_envelope,
    row_id,
    section,
    section_id_for,
)


@pytest.mark.unit
class TestViewDocumentKind:
    @pytest.mark.parametrize("kind", NEW_KINDS)
    def test_view_document_kind_discriminates_each_section_by_kind(
        self, kind: str
    ) -> None:
        wire = document((kind,)).model_dump(mode="json")

        parsed = ModelViewDocument.model_validate(wire)

        assert type(parsed.sections[0]) is SECTION_CLASSES[kind]
        assert parsed.sections[0].kind == kind

    def test_view_document_kind_holds_every_kind_in_one_document(self) -> None:
        parsed = document(NEW_KINDS)

        assert [s.kind for s in parsed.sections] == list(NEW_KINDS)

    @pytest.mark.parametrize("kind", NEW_KINDS)
    def test_view_document_kind_section_is_frozen_and_forbids_extra(
        self, kind: str
    ) -> None:
        built = section(kind)

        with pytest.raises(ValidationError):
            built.section_id = "other"
        with pytest.raises(ValidationError):
            type(built).model_validate({**built.model_dump(mode="json"), "x": 1})

    @pytest.mark.parametrize("kind", NEW_KINDS)
    def test_view_document_kind_refuses_rows_and_empty_state_together(
        self, kind: str
    ) -> None:
        with pytest.raises(ValidationError, match="rows or an empty_state"):
            SECTION_CLASSES[kind](
                section_id=section_id_for(kind),
                envelope=envelope(kind),
                rows=(ROW_BUILDERS[kind](row_id(kind)),),
                empty_state=ModelViewEmptyState(reason=EnumEmptyStateReason.NO_DATA),
            )

    @pytest.mark.parametrize("kind", NEW_KINDS)
    def test_view_document_kind_refuses_neither_rows_nor_empty_state(
        self, kind: str
    ) -> None:
        with pytest.raises(ValidationError, match="rows or an empty_state"):
            SECTION_CLASSES[kind](
                section_id=section_id_for(kind), envelope=envelope(kind)
            )

    @pytest.mark.parametrize("kind", NEW_KINDS)
    def test_view_document_kind_accepts_a_typed_empty_state_alone(
        self, kind: str
    ) -> None:
        built = section(kind, empty=True)

        assert built.rows == ()
        assert built.empty_state is not None
        assert built.empty_state.reason is EnumEmptyStateReason.NO_DATA

    def test_view_document_kind_refuses_an_envelope_of_another_kind(self) -> None:
        with pytest.raises(ValidationError, match="envelope"):
            ModelViewSectionStop(
                section_id=section_id_for("stop"),
                envelope=envelope("line_card"),
                rows=(ROW_BUILDERS["stop"](row_id("stop")),),
            )

    def test_view_document_kind_refuses_the_metric_card_envelope_in_a_stop(
        self,
    ) -> None:
        with pytest.raises(ValidationError, match="envelope"):
            ModelViewSectionStop(
                section_id=section_id_for("stop"),
                envelope=metric_card_envelope(),
                rows=(ROW_BUILDERS["stop"](row_id("stop")),),
            )

    def test_view_document_kind_refuses_rows_of_another_kind(self) -> None:
        with pytest.raises(ValidationError):
            ModelViewSectionStop(
                section_id=section_id_for("stop"),
                envelope=envelope("stop"),
                rows=(ROW_BUILDERS["line_card"](row_id("stop")),),
            )

    def test_view_document_kind_refuses_a_kind_field_that_disagrees(self) -> None:
        wire = section("stop").model_dump(mode="json")
        wire["kind"] = "line_card"

        with pytest.raises(ValidationError):
            ModelViewSectionLineCard.model_validate(wire)

    def test_view_document_kind_refuses_a_cross_kind_section_in_a_document(
        self,
    ) -> None:
        wire = document(("stop",)).model_dump(mode="json")
        wire["sections"][0]["kind"] = "line_card"

        with pytest.raises(ValidationError):
            ModelViewDocument.model_validate(wire)

    def test_view_document_kind_refuses_an_unknown_kind(self) -> None:
        wire: dict[str, Any] = document(("stop",)).model_dump(mode="json")
        wire["sections"][0]["kind"] = "hologram"

        with pytest.raises(ValidationError):
            ModelViewDocument.model_validate(wire)

    def test_view_document_kind_refuses_a_config_of_another_kind_in_the_envelope(
        self,
    ) -> None:
        wire = section("stop").model_dump(mode="json")
        wire["envelope"]["config"] = CONFIG_BUILDERS["line_card"]().model_dump(
            mode="json"
        )

        with pytest.raises(ValidationError):
            ModelViewSectionStop.model_validate(wire)

    def test_view_document_kind_refuses_a_row_from_another_section(self) -> None:
        with pytest.raises(ValidationError, match="section_id"):
            ModelViewSectionStop(
                section_id=section_id_for("stop"),
                envelope=envelope("stop"),
                rows=(ROW_BUILDERS["stop"](row_id("line_card")),),
            )

    def test_view_document_kind_refuses_a_row_from_another_view(self) -> None:
        built = section("stop")
        wire = document(("stop",)).model_dump(mode="json")
        wire["view_id"] = "other-view"
        assert VIEW_ID != "other-view"
        assert built.rows

        with pytest.raises(ValidationError, match="view_id"):
            ModelViewDocument.model_validate(wire)

    def test_view_document_kind_refuses_duplicate_section_ids(self) -> None:
        wire = document(("stop",)).model_dump(mode="json")
        wire["sections"] = [wire["sections"][0], wire["sections"][0]]

        with pytest.raises(ValidationError, match="duplicate"):
            ModelViewDocument.model_validate(wire)

    def test_view_document_kind_refuses_duplicate_row_ids_in_a_section(self) -> None:
        row = ROW_BUILDERS["stop"](row_id("stop"))
        with pytest.raises(ValidationError, match="duplicate"):
            ModelViewSectionStop(
                section_id=section_id_for("stop"),
                envelope=envelope("stop"),
                rows=(row, row),
            )

    def test_view_document_kind_refuses_a_view_id_that_is_not_a_slug(self) -> None:
        wire = document(("stop",)).model_dump(mode="json")
        wire["view_id"] = "Not A Slug"

        with pytest.raises(ValidationError):
            ModelViewDocument.model_validate(wire)
