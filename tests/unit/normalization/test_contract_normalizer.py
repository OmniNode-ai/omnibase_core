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

NOTE: these normalizers are migration scaffolding, not semantic-preserving
transforms. Callers that need to retain dropped content (e.g. metadata.author
or event_bus.subscribe_topics) must capture it from the raw dict before
invoking the normalizer.
"""

import pytest

from omnibase_core.normalization.contract_normalizer import (
    normalize_event_bus,
    normalize_io_model_ref,
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
def test_dict_shape_to_string() -> None:
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
def test_string_shape_passthrough() -> None:
    raw: dict[str, object] = {
        "name": "node_foo",
        "input_model": "foo.bar.ModelFooRequest",
    }
    result = normalize_io_model_ref(raw)
    assert result["input_model"] == "foo.bar.ModelFooRequest"


@pytest.mark.unit
def test_missing_field_not_added() -> None:
    raw: dict[str, object] = {"name": "node_foo"}
    result = normalize_io_model_ref(raw)
    assert "input_model" not in result
    assert "output_model" not in result


@pytest.mark.unit
def test_does_not_mutate_input() -> None:
    raw: dict[str, object] = {"input_model": {"name": "Foo", "module": "bar"}}
    raw_copy: dict[str, object] = {
        "input_model": {"name": "Foo", "module": "bar"},
    }
    normalize_io_model_ref(raw)
    assert raw == raw_copy


@pytest.mark.unit
def test_idempotent() -> None:
    raw: dict[str, object] = {"input_model": {"name": "Foo", "module": "bar"}}
    once = normalize_io_model_ref(raw)
    twice = normalize_io_model_ref(once)
    assert once == twice
    assert twice["input_model"] == "bar.Foo"


@pytest.mark.unit
def test_incomplete_dict_module_only_preserved() -> None:
    raw: dict[str, object] = {"input_model": {"module": "foo.bar.models"}}
    result = normalize_io_model_ref(raw)
    assert result["input_model"] == {"module": "foo.bar.models"}


@pytest.mark.unit
def test_incomplete_dict_name_only_preserved() -> None:
    raw: dict[str, object] = {"input_model": {"name": "ModelFooRequest"}}
    result = normalize_io_model_ref(raw)
    assert result["input_model"] == {"name": "ModelFooRequest"}


@pytest.mark.unit
def test_dict_with_empty_module_preserved() -> None:
    raw: dict[str, object] = {"input_model": {"name": "ModelFoo", "module": ""}}
    result = normalize_io_model_ref(raw)
    assert result["input_model"] == {"name": "ModelFoo", "module": ""}


@pytest.mark.unit
def test_dict_with_non_string_fields_preserved() -> None:
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
