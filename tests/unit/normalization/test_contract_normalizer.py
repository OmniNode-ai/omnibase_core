# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for contract_normalizer.strip_legacy_metadata (OMN-9761).

Phase 2 Task 4 of the corpus classification and normalization layer
(parent epic OMN-9757). strip_legacy_metadata is a compatibility-stripping
function: it makes legacy YAML pass canonical validation by removing
legacy top-level fields (metadata block, contract_name, node_name).

NOTE: this normalizer is migration scaffolding, not a semantic-preserving
transform. Callers that need to retain dropped content (e.g. metadata.author)
must capture it from the raw dict before invoking the normalizer.
"""

import pytest

from omnibase_core.normalization.contract_normalizer import strip_legacy_metadata


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
