# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for contract_normalizer functions (parent epic OMN-9757)."""

from __future__ import annotations

import copy

import pytest

from omnibase_core.normalization.contract_normalizer import (
    is_omnimarket_v0,
    normalize_event_bus,
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

    def test_does_not_mutate_input(self) -> None:
        raw = {
            "handler": {"module": "m", "class": "C", "input_model": "m.M"},
            "descriptor": {},
        }
        raw_copy = copy.deepcopy(raw)
        normalize_omnimarket_v0_contract(raw)
        assert raw == raw_copy
