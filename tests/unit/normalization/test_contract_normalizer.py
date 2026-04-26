# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for omnibase_core.normalization.contract_normalizer (OMN-9761, OMN-9763).

Covers two compatibility-stripping normalizers:

- ``strip_legacy_metadata`` (OMN-9761): removes legacy top-level fields
  (metadata block, contract_name, node_name) so legacy YAML passes
  canonical validation. Migration scaffolding, not semantic-preserving.
- ``normalize_io_model_ref`` (OMN-9763): converts dict-shaped
  ``input_model``/``output_model`` refs to canonical dotted-string form.
"""

import pytest

from omnibase_core.normalization.contract_normalizer import (
    normalize_io_model_ref,
    strip_legacy_metadata,
)


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
