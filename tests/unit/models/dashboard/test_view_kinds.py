# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""AC1 (OMN-21997): the seven view kinds are widget kinds like any other."""

from __future__ import annotations

from typing import get_args

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_widget_type import EnumWidgetType
from omnibase_core.models.dashboard.model_component_contract import (
    ModelComponentContract,
)
from omnibase_core.models.dashboard.model_widget_config_line_card import (
    ModelWidgetConfigLineCard,
)
from omnibase_core.models.dashboard.model_widget_definition import ModelWidgetConfig
from omnibase_core.models.dashboard.model_widget_envelope import ModelWidgetEnvelope
from omnibase_core.utils.util_widget_envelope import verify_widget_envelope
from tests.unit.models.dashboard.view_builders import (
    CONFIG_BUILDERS,
    NEW_KINDS,
    ROW_BUILDERS,
    VERSION,
    envelope,
    row_id,
)


def _union_kinds() -> set[str]:
    members = get_args(get_args(ModelWidgetConfig)[0])
    return {member.model_fields["config_kind"].default for member in members}


@pytest.mark.unit
class TestViewKindEnum:
    def test_view_kind_enum_has_the_seven_new_kinds_beside_the_existing_ones(
        self,
    ) -> None:
        values = {member.value for member in EnumWidgetType}

        assert set(NEW_KINDS) <= values
        assert {"metric_card", "chart"} <= values

    def test_view_kind_is_view_kind_marks_the_eight_view_kinds(self) -> None:
        view_kinds = {m.value for m in EnumWidgetType if m.is_view_kind}

        assert view_kinds == {"metric_card", *NEW_KINDS}

    def test_view_kind_data_bound_and_aggregation_stay_exclusive(self) -> None:
        for member in EnumWidgetType:
            assert not (member.is_data_bound and member.is_aggregation)


@pytest.mark.unit
class TestViewKindConfigs:
    def test_view_kind_every_new_kind_is_in_the_config_union(self) -> None:
        assert set(NEW_KINDS) <= _union_kinds()

    def test_every_new_kind_has_a_builder(self) -> None:
        assert set(NEW_KINDS) == set(CONFIG_BUILDERS) == set(ROW_BUILDERS)

    @pytest.mark.parametrize("kind", NEW_KINDS)
    def test_view_kind_config_is_frozen_and_forbids_extra(self, kind: str) -> None:
        config = CONFIG_BUILDERS[kind]()

        assert config.config_kind == kind
        assert config.widget_type is EnumWidgetType(kind)
        with pytest.raises(ValidationError):
            config.model_copy().__class__(unexpected_field=1)
        with pytest.raises(ValidationError):
            config.config_kind = "other"

    @pytest.mark.parametrize("kind", NEW_KINDS)
    def test_view_kind_config_refuses_a_mismatched_widget_type(self, kind: str) -> None:
        other = EnumWidgetType.CHART
        with pytest.raises(ValidationError):
            type(CONFIG_BUILDERS[kind]())(widget_type=other)

    def test_view_kind_trend_color_names_a_theme_token_never_hex(self) -> None:
        from omnibase_core.models.dashboard.model_widget_config_trend import (
            ModelWidgetConfigTrend,
        )

        with pytest.raises(ValidationError, match="theme token"):
            ModelWidgetConfigTrend(line_color="#ff0000")

    @pytest.mark.parametrize("kind", NEW_KINDS)
    def test_view_kind_component_contract_and_envelope_accept_it_unchanged(
        self, kind: str
    ) -> None:
        component = ModelComponentContract(
            component_id=f"onex.component.{kind}",
            component_kind=EnumWidgetType(kind),
            title=kind,
            contract_version=VERSION,
        )
        sealed = envelope(kind)

        assert component.component_kind.value == kind
        assert isinstance(sealed, ModelWidgetEnvelope)
        assert sealed.config.config_kind == kind
        verify_widget_envelope(sealed)

    @pytest.mark.parametrize("kind", [k for k in NEW_KINDS if k != "line_card"])
    def test_view_kind_envelope_refuses_a_config_of_another_kind(
        self, kind: str
    ) -> None:
        with pytest.raises(ValidationError, match="does not match config_kind"):
            envelope(kind, config=ModelWidgetConfigLineCard())


@pytest.mark.unit
class TestViewKindRows:
    @pytest.mark.parametrize("kind", NEW_KINDS)
    def test_view_kind_row_is_frozen_and_carries_a_typed_row_id(
        self, kind: str
    ) -> None:
        rid = row_id(kind)
        row = ROW_BUILDERS[kind](rid)

        assert row.row_id == rid
        with pytest.raises(ValidationError):
            row.row_id = row_id(kind, "other")

    @pytest.mark.parametrize("kind", NEW_KINDS)
    def test_view_kind_row_forbids_extra_fields(self, kind: str) -> None:
        row = ROW_BUILDERS[kind](row_id(kind))
        payload = row.model_dump(mode="json")

        with pytest.raises(ValidationError):
            type(row).model_validate({**payload, "order_by_position": 3})

    def test_view_kind_row_id_is_view_section_and_unique_key_values(self) -> None:
        rid = row_id("stop", "press 2/a")

        assert rid.view_id == "line-board"
        assert rid.section_id == "stop-section"
        assert rid.key_values == ("press 2/a",)
        assert rid.as_string() == "line-board/stop-section/press%202%2Fa"

    def test_view_kind_row_id_needs_a_unique_key_and_refuses_empty_parts(
        self,
    ) -> None:
        from omnibase_core.models.dashboard.model_view_row_id import ModelViewRowId

        with pytest.raises(ValidationError):
            ModelViewRowId(view_id="v", section_id="s", key_values=())
        with pytest.raises(ValidationError):
            ModelViewRowId(view_id="v", section_id="s", key_values=("",))
        with pytest.raises(ValidationError):
            ModelViewRowId(view_id="Not A Slug", section_id="s", key_values=("1",))

    def test_view_kind_row_id_has_no_position_field(self) -> None:
        from omnibase_core.models.dashboard.model_view_row_id import ModelViewRowId

        assert set(ModelViewRowId.model_fields) == {
            "view_id",
            "section_id",
            "key_values",
        }
