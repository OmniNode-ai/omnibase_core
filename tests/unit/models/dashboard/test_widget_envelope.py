# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One versioned widget envelope — the unit Plane 1 distributes (OMN-16883, Phase C2).

Two shipped contracts each hold half a widget: ``ModelComponentContract`` has
bindings and actions but no config; ``ModelWidgetDefinition`` has config and grid
placement but no bindings, no actions, no component version, no provenance, and
no hash. Nothing held a whole one, so "a pack ships a widget contract" named no
object.

These tests pin the envelope that does, and gate **GC.3**: the envelope
round-trips Python → JSON Schema → a validated discovered widget, with the seal
proving the bytes were not edited in transit.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_empty_state_reason import EnumEmptyStateReason
from omnibase_core.enums.enum_widget_type import EnumWidgetType
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.dashboard.model_component_contract import (
    ModelComponentContract,
)
from omnibase_core.models.dashboard.model_data_binding_contract import (
    ModelDataBindingContract,
)
from omnibase_core.models.dashboard.model_widget_config_metric_card import (
    ModelWidgetConfigMetricCard,
)
from omnibase_core.models.dashboard.model_widget_config_table import (
    ModelWidgetConfigTable,
)
from omnibase_core.models.dashboard.model_widget_envelope import ModelWidgetEnvelope
from omnibase_core.models.dashboard.model_widget_provenance import ModelWidgetProvenance
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.util_widget_envelope import (
    compute_widget_envelope_digest,
    seal_widget_envelope,
    verify_widget_envelope,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]
# A synthetic 40-hex git object id used as provenance test data, not a credential.
_SOURCE_REVISION = "0" * 40


def _component(
    kind: EnumWidgetType = EnumWidgetType.TABLE,
) -> ModelComponentContract:
    """A component contract with bindings, actions, and empty-state reasons."""
    return ModelComponentContract(
        component_id="onex.component.system_health",
        component_kind=kind,
        title="System Health",
        contract_version=ModelSemVer(major=1, minor=2, patch=0),
        data_bindings=(
            ModelDataBindingContract(
                binding_id="consumer_flow",
                projection_topic="onex.projection.consumer_flow",
                ordering_authority_field="observed_at",
                required_fields=("consumer_group", "classification"),
            ),
        ),
        supported_empty_state_reasons=(EnumEmptyStateReason.NO_DATA,),
    )


def _provenance() -> ModelWidgetProvenance:
    return ModelWidgetProvenance(
        pack_namespace="onex.packs.platform",
        pack_name="system-health",
        pack_version=ModelSemVer(major=0, minor=4, patch=1),
        source_revision=_SOURCE_REVISION,
    )


def _config(kind: EnumWidgetType) -> Any:
    """A config of the requested kind.

    ``STATUS_GRID`` is deliberately absent: ``ModelWidgetConfigStatusGrid``
    cannot be JSON-serialised at all today, because ``status_colors`` defaults
    to a ``MappingProxyType`` of raw hex that Pydantic refuses in ``mode="json"``
    (`PydanticSerializationError: Unable to serialize unknown type:
    mappingproxy`). OMN-16884 (Phase C3) removes that default; until it lands, a
    status-grid widget cannot cross the wire an envelope exists to cross.
    """
    if kind is EnumWidgetType.TABLE:
        return ModelWidgetConfigTable()
    return ModelWidgetConfigMetricCard(metric_key="queue_depth", label="Queue depth")


def _envelope(kind: EnumWidgetType = EnumWidgetType.TABLE) -> ModelWidgetEnvelope:
    """A sealed envelope for one published widget."""
    config: Any = _config(kind)
    return seal_widget_envelope(
        widget_id="onex.widget.system_health",
        widget_version=ModelSemVer(major=1, minor=0, patch=0),
        component=_component(kind),
        config=config,
        provenance=_provenance(),
    )


@pytest.mark.unit
class TestEnvelopeIsAWholeWidget:
    """One object carries every half a widget was previously split across."""

    def test_envelope_carries_identity_kind_config_bindings_and_provenance(
        self,
    ) -> None:
        envelope = _envelope()

        assert envelope.widget_id == "onex.widget.system_health"
        assert envelope.widget_version == ModelSemVer(major=1, minor=0, patch=0)
        assert envelope.component.component_kind is EnumWidgetType.TABLE
        # The half ModelComponentContract never had:
        assert envelope.config.config_kind == "table"
        # The half ModelWidgetDefinition never had:
        assert envelope.component.data_bindings[0].binding_id == "consumer_flow"
        assert envelope.component.contract_version == ModelSemVer(
            major=1, minor=2, patch=0
        )
        assert envelope.provenance.pack_namespace == "onex.packs.platform"
        assert envelope.provenance.source_revision == _SOURCE_REVISION
        assert envelope.content_digest.startswith("sha256:")

    def test_config_is_the_discriminated_union_not_an_untyped_blob(self) -> None:
        """A metric-card envelope deserializes to the metric-card config, by discriminator."""
        payload = _envelope(EnumWidgetType.METRIC_CARD).model_dump(mode="json")

        restored = ModelWidgetEnvelope.model_validate(payload)

        assert isinstance(restored.config, ModelWidgetConfigMetricCard)

    def test_envelope_is_frozen(self) -> None:
        envelope = _envelope()

        with pytest.raises(ValidationError):
            envelope.widget_id = "other"  # type: ignore[misc]

    def test_component_kind_must_agree_with_the_config_kind(self) -> None:
        """A table component carrying a metric-card config is not a widget."""
        with pytest.raises(ValidationError, match="component_kind"):
            seal_widget_envelope(
                widget_id="onex.widget.mismatch",
                widget_version=ModelSemVer(major=1, minor=0, patch=0),
                component=_component(EnumWidgetType.TABLE),
                config=_config(EnumWidgetType.METRIC_CARD),
                provenance=_provenance(),
            )


@pytest.mark.unit
class TestProvenanceIsVerifiable:
    """Provenance names a pack and an exact source revision, or it is refused."""

    def test_abbreviated_source_revision_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="source_revision"):
            ModelWidgetProvenance(
                pack_namespace="onex.packs.platform",
                pack_name="system-health",
                pack_version=ModelSemVer(major=0, minor=4, patch=1),
                source_revision=_SOURCE_REVISION[:7],
            )

    def test_source_revision_with_trailing_newline_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="source_revision"):
            ModelWidgetProvenance(
                pack_namespace="onex.packs.platform",
                pack_name="system-health",
                pack_version=ModelSemVer(major=0, minor=4, patch=1),
                source_revision=f"{_SOURCE_REVISION}\n",
            )

    def test_source_revision_schema_exposes_exact_hex_constraints(self) -> None:
        schema = ModelWidgetProvenance.model_json_schema()
        source_revision = schema["properties"]["source_revision"]

        assert source_revision["minLength"] == 40
        assert source_revision["maxLength"] == 40
        assert source_revision["pattern"] == r"^[0-9a-f]{40}$"

    def test_provenance_is_required_on_the_envelope(self) -> None:
        payload = _envelope().model_dump(mode="json")
        del payload["provenance"]

        with pytest.raises(ValidationError, match="provenance"):
            ModelWidgetEnvelope.model_validate(payload)


@pytest.mark.unit
class TestSealDetectsTampering:
    """The hash is what lets a consumer skip trusting the publisher."""

    def test_seal_is_deterministic_across_independent_seals(self) -> None:
        assert _envelope().content_digest == _envelope().content_digest

    def test_seal_survives_a_serialize_reload_round_trip(self) -> None:
        envelope = _envelope()

        restored = ModelWidgetEnvelope.model_validate(
            json.loads(envelope.model_dump_json())
        )

        assert restored.content_digest == envelope.content_digest
        verify_widget_envelope(restored)

    def test_seal_does_not_cover_itself(self) -> None:
        """The digest is computed over every field except the digest."""
        envelope = _envelope()

        assert compute_widget_envelope_digest(envelope) == envelope.content_digest

    def test_an_edited_config_fails_verification(self) -> None:
        """A publisher-side edit after sealing is caught by the consumer."""
        payload = _envelope().model_dump(mode="json")
        payload["config"]["page_size"] = 100

        tampered = ModelWidgetEnvelope.model_validate(payload)

        with pytest.raises(ModelOnexError, match="content_digest"):
            verify_widget_envelope(tampered)

    def test_an_edited_binding_fails_verification(self) -> None:
        """Repointing a binding at another projection is a tamper, not a config tweak."""
        payload = _envelope().model_dump(mode="json")
        payload["component"]["data_bindings"][0]["projection_topic"] = (
            "onex.projection.other"
        )

        tampered = ModelWidgetEnvelope.model_validate(payload)

        with pytest.raises(ModelOnexError, match="content_digest"):
            verify_widget_envelope(tampered)

    def test_a_malformed_digest_is_rejected_at_construction(self) -> None:
        payload = _envelope().model_dump(mode="json")
        payload["content_digest"] = "deadbeef"

        with pytest.raises(ValidationError, match="content_digest"):
            ModelWidgetEnvelope.model_validate(payload)


@pytest.mark.unit
class TestGateGC3:
    """GC.3 — Python → JSON Schema → a validated discovered widget."""

    @staticmethod
    def _emitter_models() -> dict[str, type[BaseModel]]:
        path = _REPO_ROOT / "scripts" / "emit_ts_types.py"
        spec = importlib.util.spec_from_file_location("_emit_ts_probe_envelope", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        models: dict[str, type[BaseModel]] = dict(module.MODELS)
        return models

    def test_emitter_registers_the_envelope_and_its_provenance(self) -> None:
        models = self._emitter_models()

        assert "ModelWidgetEnvelope" in models
        assert "ModelWidgetProvenance" in models

    def test_emitted_schema_validates_a_discovered_widget(self, tmp_path: Path) -> None:
        """The full pipeline: run the emitter, validate a widget against its output.

        This is the consumer's position — a JSON document arrives, and the only
        thing available to judge it is the emitted schema plus the seal. No
        publisher is trusted at any step.
        """
        output = tmp_path / "onex-models.json"
        result = subprocess.run(
            [
                sys.executable,
                str(_REPO_ROOT / "scripts" / "emit_ts_types.py"),
                str(output),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

        combined = json.loads(output.read_text())
        envelope_schema = {**combined, "$ref": "#/$defs/ModelWidgetEnvelope"}
        provenance_schema = {**combined, "$ref": "#/$defs/ModelWidgetProvenance"}
        discovered: dict[str, Any] = json.loads(_envelope().model_dump_json())

        jsonschema.validate(instance=discovered, schema=envelope_schema)
        jsonschema.validate(
            instance=discovered["provenance"],
            schema=provenance_schema,
        )

        # …and the consumer can then parse it into typed objects and check the seal.
        parsed = ModelWidgetEnvelope.model_validate(discovered)
        verify_widget_envelope(parsed)
        assert isinstance(parsed.config, ModelWidgetConfigTable)

    def test_emitted_schema_rejects_a_widget_whose_config_kind_is_unknown(
        self, tmp_path: Path
    ) -> None:
        """A config kind outside the union is not silently accepted as extra data."""
        output = tmp_path / "onex-models.json"
        subprocess.run(
            [
                sys.executable,
                str(_REPO_ROOT / "scripts" / "emit_ts_types.py"),
                str(output),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        combined = json.loads(output.read_text())
        envelope_schema = {**combined, "$ref": "#/$defs/ModelWidgetEnvelope"}
        discovered: dict[str, Any] = json.loads(_envelope().model_dump_json())
        discovered["config"]["config_kind"] = "sparkline"

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=discovered, schema=envelope_schema)
