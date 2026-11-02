# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""AC2 (OMN-21997): view contract, field map and manifest.

Selectors: ``view_contract``, ``field_map`` and ``view_manifest`` in test names.
"""

from __future__ import annotations

from typing import Any

import pytest
from omnibase_core.models.dashboard.model_view_contract import ModelViewContract
from omnibase_core.models.dashboard.model_view_field_map import ModelViewFieldMap
from omnibase_core.models.dashboard.model_view_manifest import ModelViewManifest
from omnibase_core.models.dashboard.model_view_section_contract import (
    ModelViewSectionContract,
)
from pydantic import ValidationError

from omnibase_core.enums.enum_empty_state_reason import EnumEmptyStateReason
from omnibase_core.enums.enum_widget_type import EnumWidgetType
from tests.unit.models.dashboard.view_builders import VERSION


def _field_map(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "selection": {
            "exposure": "line_status",
            "unique_key": ["line_id"],
            "order_by": [{"column": "line_name", "direction": "ascending"}],
            "limit": 50,
        },
        "fields": [
            {
                "target": "label",
                "source": {"source_kind": "column", "column": "line_name"},
            },
            {
                "target": "status_text",
                "source": {"source_kind": "constant", "value": "Running"},
            },
            {
                "target": "severity",
                "source": {"source_kind": "reference", "ref_id": "default-severity"},
            },
        ],
    }
    payload.update(overrides)
    return payload


def _section_contract(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "section_id": "lines",
        "kind": "line_card",
        "title": "Lines",
        "field_map": _field_map(),
        "supported_empty_state_reasons": ["no-data"],
    }
    payload.update(overrides)
    return payload


def _contract(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "view_id": "line-board",
        "title": "Line board",
        "contract_version": VERSION.model_dump(mode="json"),
        "sections": [_section_contract()],
    }
    payload.update(overrides)
    return payload


@pytest.mark.unit
class TestFieldMap:
    def test_field_map_accepts_columns_constants_and_references(self) -> None:
        field_map = ModelViewFieldMap.model_validate(_field_map())

        assert field_map.selection.unique_key == ("line_id",)
        assert [f.target for f in field_map.fields] == [
            "label",
            "status_text",
            "severity",
        ]

    def test_field_map_is_frozen_and_forbids_extra(self) -> None:
        field_map = ModelViewFieldMap.model_validate(_field_map())

        with pytest.raises(ValidationError):
            field_map.fields = ()
        with pytest.raises(ValidationError):
            ModelViewFieldMap.model_validate({**_field_map(), "expression": "a + b"})

    @pytest.mark.parametrize(
        "column",
        ["a + b", "count(*)", "price * qty", "coalesce(a, b)", "a.b", "$.a", "{{a}}"],
    )
    def test_field_map_refuses_an_expression_as_a_column(self, column: str) -> None:
        payload = _field_map()
        payload["fields"][0]["source"]["column"] = column

        with pytest.raises(ValidationError):
            ModelViewFieldMap.model_validate(payload)

    @pytest.mark.parametrize("value", ["={A1}+1", "{{ line_name }}", "${line_name}"])
    def test_field_map_refuses_an_expression_smuggled_in_a_constant(
        self, value: str
    ) -> None:
        payload = _field_map()
        payload["fields"][1]["source"]["value"] = value

        with pytest.raises(ValidationError, match="expression"):
            ModelViewFieldMap.model_validate(payload)

    def test_field_map_refuses_an_unknown_source_kind(self) -> None:
        payload = _field_map()
        payload["fields"][0]["source"] = {"source_kind": "expression", "text": "a+b"}

        with pytest.raises(ValidationError):
            ModelViewFieldMap.model_validate(payload)

    def test_field_map_selection_needs_a_declared_unique_key(self) -> None:
        payload = _field_map()
        payload["selection"]["unique_key"] = []

        with pytest.raises(ValidationError):
            ModelViewFieldMap.model_validate(payload)

    def test_field_map_refuses_duplicate_targets(self) -> None:
        payload = _field_map()
        payload["fields"][1]["target"] = "label"

        with pytest.raises(ValidationError, match="duplicate"):
            ModelViewFieldMap.model_validate(payload)


@pytest.mark.unit
class TestViewContract:
    def test_view_contract_accepts_a_slug_view_id_and_known_kinds(self) -> None:
        contract = ModelViewContract.model_validate(_contract())

        assert contract.view_id == "line-board"
        assert contract.sections[0].kind is EnumWidgetType.LINE_CARD
        assert contract.sections[0].supported_empty_state_reasons == (
            EnumEmptyStateReason.NO_DATA,
        )

    def test_view_contract_is_frozen_and_forbids_extra(self) -> None:
        contract = ModelViewContract.model_validate(_contract())

        with pytest.raises(ValidationError):
            contract.view_id = "other"
        with pytest.raises(ValidationError):
            ModelViewContract.model_validate({**_contract(), "formula": "a+b"})

    @pytest.mark.parametrize(
        "view_id",
        ["Line Board", "line board", "-line", "line-", "line--board", "", "é"],
    )
    def test_view_contract_refuses_a_view_id_that_is_not_a_slug(
        self, view_id: str
    ) -> None:
        with pytest.raises(ValidationError):
            ModelViewContract.model_validate(_contract(view_id=view_id))

    def test_view_contract_refuses_a_section_id_that_is_not_a_slug(self) -> None:
        with pytest.raises(ValidationError):
            ModelViewSectionContract.model_validate(
                _section_contract(section_id="Not A Slug")
            )

    def test_view_contract_refuses_an_unknown_kind(self) -> None:
        with pytest.raises(ValidationError):
            ModelViewContract.model_validate(
                _contract(sections=[_section_contract(kind="hologram")])
            )

    @pytest.mark.parametrize("kind", ["chart", "table", "status_grid", "event_feed"])
    def test_view_contract_refuses_a_widget_kind_that_is_not_a_view_kind(
        self, kind: str
    ) -> None:
        with pytest.raises(ValidationError, match="view kind"):
            ModelViewContract.model_validate(
                _contract(sections=[_section_contract(kind=kind)])
            )

    def test_view_contract_refuses_duplicate_section_ids(self) -> None:
        with pytest.raises(ValidationError, match="duplicate"):
            ModelViewContract.model_validate(
                _contract(sections=[_section_contract(), _section_contract()])
            )

    def test_view_contract_needs_at_least_one_section(self) -> None:
        with pytest.raises(ValidationError):
            ModelViewContract.model_validate(_contract(sections=[]))


@pytest.mark.unit
class TestViewManifest:
    def _manifest(self, **overrides: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "manifest_version": VERSION.model_dump(mode="json"),
            "views": [_contract(), _contract(view_id="stop-board")],
        }
        payload.update(overrides)
        return payload

    def test_view_manifest_lists_views_by_unique_view_id(self) -> None:
        manifest = ModelViewManifest.model_validate(self._manifest())

        assert [view.view_id for view in manifest.views] == [
            "line-board",
            "stop-board",
        ]

    def test_view_manifest_is_frozen_and_forbids_extra(self) -> None:
        manifest = ModelViewManifest.model_validate(self._manifest())

        with pytest.raises(ValidationError):
            manifest.views = ()
        with pytest.raises(ValidationError):
            ModelViewManifest.model_validate({**self._manifest(), "extra": 1})

    def test_view_manifest_refuses_duplicate_view_ids(self) -> None:
        with pytest.raises(ValidationError, match="duplicate"):
            ModelViewManifest.model_validate(
                self._manifest(views=[_contract(), _contract()])
            )

    def test_view_manifest_refuses_a_view_with_a_bad_slug(self) -> None:
        with pytest.raises(ValidationError):
            ModelViewManifest.model_validate(
                self._manifest(views=[_contract(view_id="Bad Id")])
            )
