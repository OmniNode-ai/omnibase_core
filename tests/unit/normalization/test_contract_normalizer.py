# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for contract_normalizer functions (parent epic OMN-9757).

Phase 2 of the corpus classification and normalization layer. Tests cover:
    - strip_legacy_metadata (OMN-9761, Task 4): removes legacy top-level
      fields (metadata block, contract_name, node_name) so legacy YAML
      passes canonical validation.
    - normalize_event_bus (OMN-9762): strips the legacy event_bus block
      and top-level topic list keys (subscribe_topics, publish_topics,
      topics).
    - normalize_io_model_ref (OMN-9763): converts dict-shaped
      input_model/output_model refs to canonical dotted-string form.
    - normalize_handler_routing (OMN-9764): derives canonical routing fields.
    - normalize_omnimarket_v0_contract (OMN-9765): strips legacy omnimarket
      v0 handler, descriptor, and terminal_event blocks while hoisting
      handler.input_model when needed.

NOTE: these normalizers are migration scaffolding, not semantic-preserving
transforms. Callers that need to retain dropped content must capture it from
the raw dict before invoking the normalizer.
"""

from __future__ import annotations

import copy

import pytest

from omnibase_core.normalization.contract_normalizer import (
    compose_normalization_pipeline,
    is_omnimarket_v0,
    normalize_dod_evidence,
    normalize_event_bus,
    normalize_handler_routing,
    normalize_io_model_ref,
    normalize_omnimarket_v0_contract,
    strip_legacy_metadata,
)
from omnibase_core.types.type_json import JsonType


@pytest.mark.unit
class TestStripLegacyMetadata:
    """Test cases for strip_legacy_metadata."""

    def test_strips_metadata_block(self) -> None:
        """All three legacy keys are removed; canonical keys are preserved."""
        raw = {
            "name": "node_foo_effect",
            "metadata": {"description": "Foo", "author": "Team"},
            "contract_name": "node_foo_effect",
            "node_name": "node_foo_effect",
            "node_type": "EFFECT_GENERIC",
        }
        result = strip_legacy_metadata(raw)
        assert "metadata" not in result
        assert "contract_name" not in result
        assert "node_name" not in result
        assert result["name"] == "node_foo_effect"
        assert result["node_type"] == "EFFECT_GENERIC"

    def test_idempotent_on_clean_dict(self) -> None:
        """A dict with no legacy keys passes through unchanged."""
        raw = {"name": "node_foo_effect", "node_type": "EFFECT_GENERIC"}
        result = strip_legacy_metadata(raw)
        assert result == raw

    def test_idempotent_on_repeated_application(self) -> None:
        """Calling strip twice produces the same result as calling once."""
        raw = {
            "name": "node_foo",
            "metadata": {"author": "x"},
            "contract_name": "node_foo",
            "node_type": "EFFECT_GENERIC",
        }
        once = strip_legacy_metadata(raw)
        twice = strip_legacy_metadata(once)
        assert once == twice

    def test_does_not_mutate_input(self) -> None:
        """The input dict must not be modified in place."""
        raw = {"name": "foo", "metadata": {"author": "x"}}
        raw_copy = {"name": "foo", "metadata": {"author": "x"}}
        strip_legacy_metadata(raw)
        assert raw == raw_copy


@pytest.mark.unit
def test_io_model_ref_dict_shape_to_string() -> None:
    raw: dict[str, object] = {
        "name": "node_foo",
        "input_model": {
            "name": "ModelFooRequest",
            "module": "foo.bar.models",
            "description": "...",
        },
        "output_model": {"name": "ModelFooResult", "module": "foo.bar.models"},
    }
    result = normalize_io_model_ref(raw)
    assert result["input_model"] == "foo.bar.models.ModelFooRequest"
    assert result["output_model"] == "foo.bar.models.ModelFooResult"


@pytest.mark.unit
def test_io_model_ref_string_shape_passthrough() -> None:
    raw: dict[str, object] = {
        "name": "node_foo",
        "input_model": "foo.bar.ModelFooRequest",
    }
    result = normalize_io_model_ref(raw)
    assert result["input_model"] == "foo.bar.ModelFooRequest"


@pytest.mark.unit
def test_io_model_ref_missing_field_not_added() -> None:
    raw: dict[str, object] = {"name": "node_foo"}
    result = normalize_io_model_ref(raw)
    assert "input_model" not in result
    assert "output_model" not in result


@pytest.mark.unit
def test_io_model_ref_does_not_mutate_input() -> None:
    raw: dict[str, object] = {"input_model": {"name": "Foo", "module": "bar"}}
    raw_copy: dict[str, object] = {
        "input_model": {"name": "Foo", "module": "bar"},
    }
    normalize_io_model_ref(raw)
    assert raw == raw_copy


@pytest.mark.unit
def test_io_model_ref_idempotent() -> None:
    raw: dict[str, object] = {"input_model": {"name": "Foo", "module": "bar"}}
    once = normalize_io_model_ref(raw)
    twice = normalize_io_model_ref(once)
    assert once == twice
    assert twice["input_model"] == "bar.Foo"


@pytest.mark.unit
def test_io_model_ref_incomplete_dict_module_only_preserved() -> None:
    raw: dict[str, object] = {"input_model": {"module": "foo.bar.models"}}
    result = normalize_io_model_ref(raw)
    assert result["input_model"] == {"module": "foo.bar.models"}


@pytest.mark.unit
def test_io_model_ref_incomplete_dict_name_only_preserved() -> None:
    raw: dict[str, object] = {"input_model": {"name": "ModelFooRequest"}}
    result = normalize_io_model_ref(raw)
    assert result["input_model"] == {"name": "ModelFooRequest"}


@pytest.mark.unit
def test_io_model_ref_dict_with_empty_module_preserved() -> None:
    raw: dict[str, object] = {"input_model": {"name": "ModelFoo", "module": ""}}
    result = normalize_io_model_ref(raw)
    assert result["input_model"] == {"name": "ModelFoo", "module": ""}


@pytest.mark.unit
def test_io_model_ref_dict_with_non_string_fields_preserved() -> None:
    raw: dict[str, object] = {"input_model": {"name": "ModelFoo", "module": 42}}
    result = normalize_io_model_ref(raw)
    assert result["input_model"] == {"name": "ModelFoo", "module": 42}


@pytest.mark.unit
class TestNormalizeEventBus:
    """Test cases for normalize_event_bus (family_legacy_event_bus)."""

    def test_strips_event_bus_block(self) -> None:
        """The full legacy event_bus block is removed."""
        raw: dict[str, JsonType] = {
            "name": "node_foo_effect",
            "event_bus": {
                "subscribe_topics": ["onex.evt.foo.bar.v1"],
                "publish_topics": ["onex.evt.foo.baz.v1"],
                "consumer_group": "node_foo",
            },
        }
        result = normalize_event_bus(raw)
        assert "event_bus" not in result

    def test_strips_top_level_topic_list_keys(self) -> None:
        """Top-level subscribe_topics, publish_topics, and topics keys are dropped."""
        raw: dict[str, JsonType] = {
            "name": "node_foo_effect",
            "subscribe_topics": ["onex.evt.foo.in.v1"],
            "publish_topics": ["onex.evt.foo.out.v1"],
            "topics": ["onex.evt.foo.aux.v1"],
        }
        result = normalize_event_bus(raw)
        assert "subscribe_topics" not in result
        assert "publish_topics" not in result
        assert "topics" not in result
        assert result == {"name": "node_foo_effect"}

    def test_preserves_non_event_bus_fields(self) -> None:
        """Fields outside the legacy event-bus key set are preserved verbatim."""
        raw: dict[str, JsonType] = {
            "name": "node_foo",
            "node_type": "EFFECT_GENERIC",
            "event_bus": {},
        }
        result = normalize_event_bus(raw)
        assert result["name"] == "node_foo"
        assert result["node_type"] == "EFFECT_GENERIC"
        assert "event_bus" not in result

    def test_idempotent_when_no_event_bus(self) -> None:
        """Calling on a clean dict returns an equal dict."""
        raw: dict[str, JsonType] = {"name": "node_foo"}
        result = normalize_event_bus(raw)
        assert result == raw

    def test_idempotent_under_repeated_application(self) -> None:
        """Two applications produce the same result as one."""
        raw: dict[str, JsonType] = {
            "name": "node_foo",
            "event_bus": {"subscribe_topics": ["t"]},
            "publish_topics": ["p"],
        }
        once = normalize_event_bus(raw)
        twice = normalize_event_bus(once)
        assert once == twice

    def test_does_not_mutate_input(self) -> None:
        """Input dict is not modified in place."""
        raw: dict[str, JsonType] = {
            "name": "foo",
            "event_bus": {"subscribe_topics": ["t"]},
        }
        raw_copy = dict(raw)
        normalize_event_bus(raw)
        assert raw == raw_copy


@pytest.mark.unit
class TestIsOmnimarketV0:
    """Detection helper for the legacy omnimarket v0 contract shape."""

    def test_detects_omnimarket_v0_shape(self) -> None:
        raw = {
            "handler": {
                "module": "omnimarket.nodes.x.handlers.h",
                "class": "NodeX",
                "input_model": "...",
            },
            "descriptor": {"node_archetype": "compute"},
            "terminal_event": "onex.evt.omnimarket.x-completed.v1",
        }
        assert is_omnimarket_v0(raw) is True

    def test_non_omnimarket_v0_shape(self) -> None:
        raw = {"name": "node_foo", "node_type": "EFFECT_GENERIC"}
        assert is_omnimarket_v0(raw) is False


@pytest.mark.unit
class TestNormalizeOmnimarketV0Contract:
    """Rewrite legacy v0 contract dicts to the canonical layout."""

    def test_extracts_input_model_from_handler(self) -> None:
        raw = {
            "name": "node_aislop_sweep",
            "handler": {
                "module": "omnimarket.nodes.node_aislop_sweep.handlers.h",
                "class": "NodeAislopSweep",
                "input_model": "omnimarket.nodes.node_aislop_sweep.handlers.h.AislopSweepRequest",
            },
            "descriptor": {"node_archetype": "compute", "timeout_ms": 120000},
            "terminal_event": "onex.evt.omnimarket.aislop-sweep-completed.v1",
        }
        result = normalize_omnimarket_v0_contract(raw)
        assert (
            result.get("input_model")
            == "omnimarket.nodes.node_aislop_sweep.handlers.h.AislopSweepRequest"
        )
        assert "handler" not in result
        assert "descriptor" not in result
        assert "terminal_event" not in result

    def test_hoisted_handler_input_model_can_be_normalized(self) -> None:
        raw = {
            "name": "node_aislop_sweep",
            "handler": {
                "module": "omnimarket.nodes.node_aislop_sweep.handlers.h",
                "class": "NodeAislopSweep",
                "input_model": {
                    "module": "omnimarket.nodes.node_aislop_sweep.handlers.h",
                    "name": "AislopSweepRequest",
                },
            },
        }
        result = normalize_io_model_ref(normalize_omnimarket_v0_contract(raw))
        assert (
            result["input_model"]
            == "omnimarket.nodes.node_aislop_sweep.handlers.h.AislopSweepRequest"
        )

    def test_does_not_mutate_input(self) -> None:
        raw = {
            "handler": {"module": "m", "class": "C", "input_model": "m.M"},
            "descriptor": {},
        }
        raw_copy = copy.deepcopy(raw)
        normalize_omnimarket_v0_contract(raw)
        assert raw == raw_copy


@pytest.mark.unit
def test_handler_routing_adds_version_default() -> None:
    raw = {"handler_routing": {"routing_strategy": "operation_match", "handlers": []}}
    result = normalize_handler_routing(raw)
    assert result["handler_routing"]["version"] == {"major": 1, "minor": 0, "patch": 0}


@pytest.mark.unit
def test_handler_routing_derives_routing_key_from_supported_operation() -> None:
    raw = {
        "handler_routing": {
            "routing_strategy": "operation_match",
            "handlers": [
                {
                    "handler_type": "auth_gate",
                    "supported_operations": ["auth_gate.evaluate"],
                    "handler": {"name": "HandlerAuthGate", "module": "foo.bar"},
                }
            ],
        }
    }
    result = normalize_handler_routing(raw)
    h = result["handler_routing"]["handlers"][0]
    assert h["routing_key"] == "auth_gate.evaluate"
    assert h["handler_key"] == "handler_auth_gate"


@pytest.mark.unit
def test_handler_routing_preserves_non_dict_handler_entries() -> None:
    raw = {
        "handler_routing": {
            "routing_strategy": "operation_match",
            "handlers": [
                "legacy-malformed-handler",
                {
                    "handler_type": "auth_gate",
                    "supported_operations": ["auth_gate.evaluate"],
                },
            ],
        }
    }
    result = normalize_handler_routing(raw)
    handlers = result["handler_routing"]["handlers"]
    assert handlers[0] == "legacy-malformed-handler"
    assert handlers[1]["routing_key"] == "auth_gate.evaluate"


@pytest.mark.unit
def test_handler_routing_multi_operation_handler_flagged() -> None:
    raw = {
        "handler_routing": {
            "routing_strategy": "operation_match",
            "handlers": [
                {
                    "handler_type": "foo",
                    "supported_operations": ["foo.a", "foo.b"],
                    "handler": {"name": "HandlerFoo", "module": "bar"},
                }
            ],
        }
    }
    result = normalize_handler_routing(raw)
    h = result["handler_routing"]["handlers"][0]
    assert h["routing_key"] == "foo.a"
    assert h.get("_normalization_flag") == "multi_operation_requires_human_review"


@pytest.mark.unit
def test_handler_routing_passthrough_when_absent() -> None:
    raw = {"name": "node_foo"}
    result = normalize_handler_routing(raw)
    assert result == raw


@pytest.mark.unit
def test_handler_routing_does_not_mutate_input() -> None:
    raw = {
        "handler_routing": {
            "handlers": [
                {
                    "handler_type": "x",
                    "supported_operations": ["x.y"],
                    "handler": {"name": "H", "module": "m"},
                }
            ]
        }
    }
    raw_copy = copy.deepcopy(raw)
    normalize_handler_routing(raw)
    assert raw == raw_copy


@pytest.mark.unit
class TestNormalizeDodEvidence:
    """Tests for normalize_dod_evidence (OMN-9766, family_dod_evidence_kind).

    Maps the legacy ``kind`` discriminator on dod_evidence entries to the
    canonical ``type`` discriminator. String entries pass through; entries
    that already declare ``type`` are not double-mapped.
    """

    def test_no_op_when_dod_evidence_absent(self) -> None:
        raw = {"name": "n", "node_type": "EFFECT_GENERIC"}
        result = normalize_dod_evidence(raw)
        assert result == raw

    def test_string_list_passthrough(self) -> None:
        raw = {"dod_evidence": ["test_passes", "pr_merged"]}
        result = normalize_dod_evidence(raw)
        assert result["dod_evidence"] == ["test_passes", "pr_merged"]

    def test_kind_test_maps_to_type_unit_test(self) -> None:
        raw = {"dod_evidence": [{"kind": "test", "command": "uv run pytest"}]}
        result = normalize_dod_evidence(raw)
        item = result["dod_evidence"][0]
        assert item == {"type": "unit_test", "command": "uv run pytest"}
        assert "kind" not in item

    def test_kind_unit_test_passthrough_value(self) -> None:
        raw = {"dod_evidence": [{"kind": "unit_test", "command": "x"}]}
        result = normalize_dod_evidence(raw)
        assert result["dod_evidence"][0]["type"] == "unit_test"

    def test_kind_unmapped_falls_back_to_kind_value(self) -> None:
        raw = {"dod_evidence": [{"kind": "novel_kind", "command": "x"}]}
        result = normalize_dod_evidence(raw)
        assert result["dod_evidence"][0]["type"] == "novel_kind"

    def test_existing_type_not_overwritten(self) -> None:
        """Entries with both kind and type keep type and drop kind quietly.

        The function does not overwrite a pre-existing ``type`` value with
        the mapping derived from ``kind``; the canonical ``type`` wins.
        """
        raw = {
            "dod_evidence": [
                {"kind": "test", "type": "integration_test", "command": "x"}
            ]
        }
        result = normalize_dod_evidence(raw)
        # Pre-canonical entries are left alone — kind is not stripped here.
        item = result["dod_evidence"][0]
        assert item["type"] == "integration_test"

    def test_does_not_mutate_input(self) -> None:
        raw = {"dod_evidence": [{"kind": "test", "command": "x"}]}
        snapshot = copy.deepcopy(raw)
        normalize_dod_evidence(raw)
        assert raw == snapshot

    def test_idempotent(self) -> None:
        raw = {"dod_evidence": [{"kind": "test", "command": "x"}]}
        once = normalize_dod_evidence(raw)
        twice = normalize_dod_evidence(once)
        assert once == twice

    def test_non_list_dod_evidence_passthrough(self) -> None:
        """Garbage shapes (non-list) are not transformed; we don't fabricate."""
        raw = {"dod_evidence": "not_a_list"}
        result = normalize_dod_evidence(raw)
        assert result == raw


@pytest.mark.unit
class TestComposeNormalizationPipeline:
    """Tests for compose_normalization_pipeline (OMN-9766).

    The pipeline is the migration_audit entry point that funnels every
    per-family normalizer into a single dict→dict transform. Step order
    is fixed; each step is documented in the function docstring.
    """

    def test_full_pipeline_compose(self) -> None:
        raw: dict[str, object] = {
            "name": "node_foo_effect",
            "node_type": "EFFECT_GENERIC",
            "metadata": {"author": "Team"},
            "contract_name": "node_foo_effect",
            "event_bus": {"subscribe_topics": ["t"]},
            "input_model": {"name": "ModelFooRequest", "module": "foo.bar"},
            "handler_routing": {
                "routing_strategy": "operation_match",
                "handlers": [
                    {
                        "handler_type": "foo",
                        "supported_operations": ["foo.run"],
                        "handler": {"name": "HandlerFoo", "module": "bar"},
                    }
                ],
            },
        }
        result = compose_normalization_pipeline(raw)
        assert "metadata" not in result
        assert "contract_name" not in result
        assert "event_bus" not in result
        assert result["input_model"] == "foo.bar.ModelFooRequest"
        hr = result["handler_routing"]
        assert isinstance(hr, dict)
        assert hr["version"] == {"major": 1, "minor": 0, "patch": 0}
        handlers = hr["handlers"]
        assert isinstance(handlers, list)
        first = handlers[0]
        assert isinstance(first, dict)
        assert first["routing_key"] == "foo.run"

    def test_pipeline_does_not_mutate_input(self) -> None:
        raw: dict[str, object] = {
            "name": "n",
            "metadata": {"author": "x"},
            "input_model": {"name": "M", "module": "m"},
        }
        snapshot = copy.deepcopy(raw)
        compose_normalization_pipeline(raw)
        assert raw == snapshot

    def test_pipeline_idempotent_on_canonical_input(self) -> None:
        """Running the pipeline on already-canonical input is a near-no-op
        (modulo dict-copy semantics)."""
        raw: dict[str, object] = {
            "name": "n",
            "node_type": "EFFECT_GENERIC",
            "input_model": "x.y.Z",
            "output_model": "x.y.W",
        }
        once = compose_normalization_pipeline(raw)
        twice = compose_normalization_pipeline(once)
        assert once == twice

    def test_pipeline_runs_dod_evidence_step(self) -> None:
        """The dod_evidence step is wired into the composed pipeline."""
        raw: dict[str, object] = {
            "name": "n",
            "node_type": "EFFECT_GENERIC",
            "dod_evidence": [{"kind": "test", "command": "uv run pytest"}],
        }
        result = compose_normalization_pipeline(raw)
        evidence = result["dod_evidence"]
        assert isinstance(evidence, list)
        first = evidence[0]
        assert isinstance(first, dict)
        assert first["type"] == "unit_test"
        assert "kind" not in first

    def test_pipeline_runs_omnimarket_v0_only_when_detected(self) -> None:
        """Non-omnimarket-v0 contracts are not rewritten by that step."""
        raw: dict[str, object] = {
            "name": "n",
            "node_type": "EFFECT_GENERIC",
            "input_model": "x.y.Z",
        }
        result = compose_normalization_pipeline(raw)
        assert result["input_model"] == "x.y.Z"  # unchanged
