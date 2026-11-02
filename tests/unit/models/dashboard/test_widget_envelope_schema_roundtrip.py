# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A sealed widget envelope satisfies its seal AND its published schema (OMN-16948).

``ModelWidgetConfigMetricCard.value_format`` (alias ``format``),
``ModelWidgetConfigEventFeed.event_filter`` (alias ``filter``) and
``ModelTableColumnConfig.display_format`` (alias ``format``) are aliased fields.
The published JSON Schema (``model_json_schema()``, via ``scripts/emit_ts_types.py``)
describes them by alias; the seal digested ``model_dump(mode="json")``, which
used the field name. A sealed envelope was therefore rejected by its own schema
as an additional property, and an envelope written in the schema's form digested
to something other than its seal. No consumer could both validate a discovered
widget and verify its seal.

This test is the one that makes the class of defect visible: for **every**
``config_kind`` in the discriminated union it seals an envelope, validates the
wire form against the published schema, and verifies the seal over the same
bytes. The builders cover the aliased fields with non-default values, and a
union member with no builder fails the suite rather than going untested.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, get_args

import jsonschema
import pytest

from omnibase_core.enums.enum_status_severity import EnumStatusSeverity
from omnibase_core.enums.enum_widget_type import EnumWidgetType
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.dashboard.model_chart_series_config import (
    ModelChartSeriesConfig,
)
from omnibase_core.models.dashboard.model_component_contract import (
    ModelComponentContract,
)
from omnibase_core.models.dashboard.model_event_filter import ModelEventFilter
from omnibase_core.models.dashboard.model_metric_threshold import ModelMetricThreshold
from omnibase_core.models.dashboard.model_severity_verdict import ModelSeverityVerdict
from omnibase_core.models.dashboard.model_status_item_config import (
    ModelStatusItemConfig,
)
from omnibase_core.models.dashboard.model_table_column_config import (
    ModelTableColumnConfig,
)
from omnibase_core.models.dashboard.model_widget_config_chart import (
    ModelWidgetConfigChart,
)
from omnibase_core.models.dashboard.model_widget_config_event_feed import (
    ModelWidgetConfigEventFeed,
)
from omnibase_core.models.dashboard.model_widget_config_metric_card import (
    ModelWidgetConfigMetricCard,
)
from omnibase_core.models.dashboard.model_widget_config_status_grid import (
    ModelWidgetConfigStatusGrid,
)
from omnibase_core.models.dashboard.model_widget_config_table import (
    ModelWidgetConfigTable,
)
from omnibase_core.models.dashboard.model_widget_definition import ModelWidgetConfig
from omnibase_core.models.dashboard.model_widget_envelope import ModelWidgetEnvelope
from omnibase_core.models.dashboard.model_widget_provenance import ModelWidgetProvenance
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.util_canonical_hash import compute_canonical_hash
from omnibase_core.utils.util_widget_envelope import (
    seal_widget_envelope,
    verify_widget_envelope,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]
_VERSION = ModelSemVer(major=1, minor=0, patch=0)


def _union_members() -> tuple[Any, ...]:
    """The config models of the discriminated ``ModelWidgetConfig`` union."""
    union = get_args(ModelWidgetConfig)[0]
    return get_args(union)


def _kind_of(model: Any) -> str:
    kind: str = model.model_fields["config_kind"].default
    return kind


def _status_grid() -> ModelWidgetConfigStatusGrid:
    return ModelWidgetConfigStatusGrid(
        items=(
            ModelStatusItemConfig(
                key="dlq",
                label="DLQ",
                verdict=ModelSeverityVerdict(
                    severity=EnumStatusSeverity.CRITICAL,
                    status_value="QUARANTINED",
                    policy_id="onex.policy.dlq_health",
                    policy_version=_VERSION,
                    policy_digest="sha256:" + "1" * 64,
                ),
            ),
        )
    )


#: One config per ``config_kind``, with every aliased field set to a non-default
#: value so an alias/field-name disagreement shows up in the wire form.
_CONFIG_BUILDERS: dict[str, Any] = {
    "chart": lambda: ModelWidgetConfigChart(
        series=(ModelChartSeriesConfig(name="CPU", data_key="cpu"),)
    ),
    "table": lambda: ModelWidgetConfigTable(
        columns=(
            ModelTableColumnConfig(
                key="cost", header="Cost", display_format="currency"
            ),
        )
    ),
    "metric_card": lambda: ModelWidgetConfigMetricCard(
        metric_key="error_rate",
        label="Error rate",
        value_format="percent",
        thresholds=(ModelMetricThreshold(value=5.0, color="color_status_warning"),),
    ),
    "status_grid": _status_grid,
    "event_feed": lambda: ModelWidgetConfigEventFeed(
        event_filter=ModelEventFilter(event_types=("error",))
    ),
}


def _published_schema() -> dict[str, Any]:
    """The schema ``scripts/emit_ts_types.py`` publishes, rooted at the envelope."""
    path = _REPO_ROOT / "scripts" / "emit_ts_types.py"
    spec = importlib.util.spec_from_file_location("_emit_ts_probe_roundtrip", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    defs: dict[str, object] = module._combined_defs()
    return {
        "$id": "https://omninode.ai/schemas/omnidash-v2.json",
        "$defs": defs,
        "$ref": "#/$defs/ModelWidgetEnvelope",
    }


def _seal(kind: str) -> ModelWidgetEnvelope:
    return seal_widget_envelope(
        widget_id=f"onex.widget.roundtrip_{kind}",
        widget_version=_VERSION,
        component=ModelComponentContract(
            component_id=f"onex.component.roundtrip_{kind}",
            component_kind=EnumWidgetType(kind),
            title=f"Round trip {kind}",
            contract_version=_VERSION,
        ),
        config=_CONFIG_BUILDERS[kind](),
        provenance=ModelWidgetProvenance(
            pack_namespace="onex.packs.platform",
            pack_name="roundtrip",
            pack_version=_VERSION,
            source_revision="0" * 40,
        ),
    )


@pytest.mark.unit
class TestSealedEnvelopeSatisfiesItsPublishedSchema:
    """AC1 + AC2: the digest and the schema describe the same bytes."""

    def test_every_config_kind_in_the_union_has_a_builder(self) -> None:
        kinds = {_kind_of(model) for model in _union_members()}

        assert kinds == set(_CONFIG_BUILDERS)

    @pytest.mark.parametrize("kind", sorted(_CONFIG_BUILDERS))
    def test_sealed_envelope_validates_against_the_published_schema_and_its_seal(
        self, kind: str
    ) -> None:
        envelope = _seal(kind)
        wire: dict[str, Any] = json.loads(envelope.model_dump_json())

        # The consumer's first check: the published schema accepts the wire form.
        jsonschema.validate(instance=wire, schema=_published_schema())

        # The consumer's second check, over those same bytes and with no help
        # from the model: the seal is the canonical hash of the wire form.
        unsealed = {k: v for k, v in wire.items() if k != "content_digest"}
        assert wire["content_digest"] == f"sha256:{compute_canonical_hash(unsealed)}"

        # And the typed route agrees.
        verify_widget_envelope(ModelWidgetEnvelope.model_validate(wire))

    def test_aliased_fields_appear_under_their_wire_names(self) -> None:
        metric = json.loads(_seal("metric_card").model_dump_json())["config"]
        feed = json.loads(_seal("event_feed").model_dump_json())["config"]
        table = json.loads(_seal("table").model_dump_json())["config"]

        assert metric["format"] == "percent"
        assert "value_format" not in metric
        assert feed["filter"]["event_types"] == ["error"]
        assert "event_filter" not in feed
        assert table["columns"][0]["format"] == "currency"
        assert "display_format" not in table["columns"][0]

    def test_an_envelope_sealed_before_the_fix_fails_verification(self) -> None:
        """Migration consequence: a seal over the field-name form no longer holds.

        Before this change the seal covered ``model_dump(mode="json")`` — the
        field name ``value_format``. The seal now covers the wire form
        (``format``), so a metric-card or event-feed envelope sealed earlier
        must be re-sealed by its publisher. Failing closed is the point: a
        silent re-seal would launder an edit.
        """
        current = _seal("metric_card")
        old_payload = current.model_dump(
            mode="json", by_alias=False, exclude={"content_digest"}
        )
        assert old_payload["config"]["value_format"] == "percent"
        old_digest = f"sha256:{compute_canonical_hash(old_payload)}"
        assert old_digest != current.content_digest

        legacy = ModelWidgetEnvelope.model_validate(
            {**old_payload, "content_digest": old_digest}
        )

        with pytest.raises(ModelOnexError, match="fails its seal"):
            verify_widget_envelope(legacy)
