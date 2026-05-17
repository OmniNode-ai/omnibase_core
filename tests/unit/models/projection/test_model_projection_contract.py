# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for ModelProjectionContract and ModelCursorContract (OMN-11192)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_degraded_behavior import EnumDegradedBehavior
from omnibase_core.models.projection.model_cursor_contract import ModelCursorContract
from omnibase_core.models.projection.model_projection_contract import (
    ModelProjectionContract,
)


def _make_cursor(**kwargs: object) -> ModelCursorContract:
    defaults: dict[str, object] = {
        "cursor_type": "kafka_offset",
        "supports_replay": True,
    }
    defaults.update(kwargs)
    return ModelCursorContract(**defaults)  # type: ignore[arg-type]


def _make_contract(**kwargs: object) -> ModelProjectionContract:
    defaults: dict[str, object] = {
        "projection_name": "node_status",
        "source_topics": ("onex.evt.nodes.status_changed.v1",),
        "schema_model": "omnibase_infra.projections.ModelNodeStatusRow",
        "freshness_sla_seconds": 30,
        "freshness_field": "updated_at",
        "freshness_source_table": "node_status_projection",
        "degraded_semantics": EnumDegradedBehavior.SERVE_STALE_WITH_WARNING,
        "cursor": _make_cursor(),
    }
    defaults.update(kwargs)
    return ModelProjectionContract(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestModelCursorContract:
    def test_valid_kafka_offset(self) -> None:
        cursor = _make_cursor(cursor_type="kafka_offset", supports_replay=True)
        assert cursor.cursor_type == "kafka_offset"
        assert cursor.supports_replay is True

    def test_valid_timestamp(self) -> None:
        cursor = _make_cursor(cursor_type="timestamp", supports_replay=False)
        assert cursor.cursor_type == "timestamp"
        assert cursor.supports_replay is False

    def test_valid_sequence(self) -> None:
        cursor = _make_cursor(cursor_type="sequence", supports_replay=True)
        assert cursor.cursor_type == "sequence"

    def test_invalid_cursor_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelCursorContract(cursor_type="invalid", supports_replay=True)  # type: ignore[arg-type]

    def test_frozen(self) -> None:
        cursor = _make_cursor()
        with pytest.raises(ValidationError):
            cursor.supports_replay = False  # type: ignore[misc]

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelCursorContract(
                cursor_type="kafka_offset", supports_replay=True, extra="bad"
            )  # type: ignore[call-arg]


@pytest.mark.unit
class TestModelProjectionContractRequiresDegradedSemantics:
    def test_requires_degraded_semantics_no_default(self) -> None:
        """Constructing without degraded_semantics must raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelProjectionContract(  # type: ignore[call-arg]
                projection_name="node_status",
                source_topics=("onex.evt.nodes.status_changed.v1",),
                schema_model="omnibase_infra.projections.ModelNodeStatusRow",
                freshness_sla_seconds=30,
                freshness_field="updated_at",
                freshness_source_table="node_status_projection",
                # degraded_semantics intentionally omitted
                cursor=_make_cursor(),
            )
        assert "degraded_semantics" in str(exc_info.value)

    def test_requires_freshness_field_and_source_table(self) -> None:
        """Both freshness_field and freshness_source_table are required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelProjectionContract(  # type: ignore[call-arg]
                projection_name="node_status",
                source_topics=("onex.evt.nodes.status_changed.v1",),
                schema_model="omnibase_infra.projections.ModelNodeStatusRow",
                freshness_sla_seconds=30,
                # freshness_field omitted
                freshness_source_table="node_status_projection",
                degraded_semantics=EnumDegradedBehavior.SERVE_STALE_WITH_WARNING,
                cursor=_make_cursor(),
            )
        assert "freshness_field" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectionContract(  # type: ignore[call-arg]
                projection_name="node_status",
                source_topics=("onex.evt.nodes.status_changed.v1",),
                schema_model="omnibase_infra.projections.ModelNodeStatusRow",
                freshness_sla_seconds=30,
                freshness_field="updated_at",
                # freshness_source_table omitted
                degraded_semantics=EnumDegradedBehavior.SERVE_STALE_WITH_WARNING,
                cursor=_make_cursor(),
            )
        assert "freshness_source_table" in str(exc_info.value)

    def test_frozen(self) -> None:
        """ModelProjectionContract must be immutable after construction."""
        contract = _make_contract()
        with pytest.raises(ValidationError):
            contract.projection_name = "new_name"  # type: ignore[misc]


@pytest.mark.unit
class TestModelProjectionContractFieldConstraints:
    def test_valid_construction(self) -> None:
        contract = _make_contract()
        assert contract.projection_name == "node_status"
        assert contract.freshness_sla_seconds == 30
        assert contract.freshness_field == "updated_at"
        assert contract.freshness_source_table == "node_status_projection"
        assert contract.degraded_semantics == EnumDegradedBehavior.SERVE_STALE_WITH_WARNING
        assert contract.ordering_contract_ref is None

    def test_empty_projection_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_contract(projection_name="")

    def test_empty_schema_model_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_contract(schema_model="")

    def test_zero_freshness_sla_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_contract(freshness_sla_seconds=0)

    def test_negative_freshness_sla_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_contract(freshness_sla_seconds=-1)

    def test_empty_freshness_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_contract(freshness_field="")

    def test_empty_freshness_source_table_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_contract(freshness_source_table="")

    def test_ordering_contract_ref_optional(self) -> None:
        contract = _make_contract(ordering_contract_ref="NodeStatusOrdering")
        assert contract.ordering_contract_ref == "NodeStatusOrdering"

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make_contract(unknown_field="value")  # type: ignore[arg-type]

    def test_all_degraded_semantics_values_accepted(self) -> None:
        for value in EnumDegradedBehavior:
            contract = _make_contract(degraded_semantics=value)
            assert contract.degraded_semantics == value

    def test_source_topics_tuple(self) -> None:
        contract = _make_contract(
            source_topics=("onex.evt.nodes.created.v1", "onex.evt.nodes.updated.v1")
        )
        assert len(contract.source_topics) == 2
