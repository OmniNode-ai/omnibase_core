# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""AC5 (OMN-21997): count_view_document returns ids by disposition."""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_view_disposition import EnumViewDisposition
from omnibase_core.models.dashboard.model_view_document_counter import (
    count_view_document,
)
from omnibase_core.models.dashboard.model_view_document_digest import seal_view_document
from tests.unit.models.dashboard.view_builders import (
    MOMENT,
    NEW_KINDS,
    VERSION,
    VIEW_ID,
    row_id,
    section,
    section_id_for,
)


@pytest.mark.unit
class TestCountViewDocument:
    @pytest.mark.parametrize("kind", NEW_KINDS)
    def test_count_view_document_populated_section_of_each_kind(
        self, kind: str
    ) -> None:
        doc = seal_view_document(
            view_id=VIEW_ID,
            contract_version=VERSION,
            generated_at=MOMENT,
            sections=(section(kind, rows=2),),
        )

        counted = count_view_document(doc)
        populated = counted.by_disposition(EnumViewDisposition.POPULATED)
        empty = counted.by_disposition(EnumViewDisposition.EMPTY)

        assert populated.section_ids == (section_id_for(kind),)
        assert populated.row_ids == (
            row_id(kind, "k0").as_string(),
            row_id(kind, "k1").as_string(),
        )
        assert empty.section_ids == ()
        assert empty.row_ids == ()

    @pytest.mark.parametrize("kind", NEW_KINDS)
    def test_count_view_document_empty_section_of_each_kind(self, kind: str) -> None:
        doc = seal_view_document(
            view_id=VIEW_ID,
            contract_version=VERSION,
            generated_at=MOMENT,
            sections=(section(kind, empty=True),),
        )

        counted = count_view_document(doc)

        assert counted.by_disposition(EnumViewDisposition.EMPTY).section_ids == (
            section_id_for(kind),
        )
        assert counted.by_disposition(EnumViewDisposition.EMPTY).row_ids == ()
        assert counted.by_disposition(EnumViewDisposition.POPULATED).section_ids == ()

    def test_count_view_document_mixed_document_keeps_document_order(self) -> None:
        doc = seal_view_document(
            view_id=VIEW_ID,
            contract_version=VERSION,
            generated_at=MOMENT,
            sections=(
                section("stop", rows=1),
                section("freshness", empty=True),
                section("trend", rows=3),
            ),
        )

        counted = count_view_document(doc)

        assert counted.view_id == VIEW_ID
        assert counted.by_disposition(EnumViewDisposition.POPULATED).section_ids == (
            "stop-section",
            "trend-section",
        )
        assert counted.by_disposition(EnumViewDisposition.EMPTY).section_ids == (
            "freshness-section",
        )
        assert len(counted.by_disposition(EnumViewDisposition.POPULATED).row_ids) == 4

    def test_count_view_document_names_every_disposition_even_when_zero(self) -> None:
        doc = seal_view_document(
            view_id=VIEW_ID,
            contract_version=VERSION,
            generated_at=MOMENT,
            sections=(section("stop", rows=1),),
        )

        counted = count_view_document(doc)

        assert {d.disposition for d in counted.dispositions} == set(EnumViewDisposition)

    def test_count_view_document_is_deterministic(self) -> None:
        doc = seal_view_document(
            view_id=VIEW_ID,
            contract_version=VERSION,
            generated_at=MOMENT,
            sections=(section("stop", rows=2), section("trend", empty=True)),
        )

        assert count_view_document(doc) == count_view_document(doc)
