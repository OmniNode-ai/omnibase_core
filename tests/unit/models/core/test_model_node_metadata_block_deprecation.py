# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for deprecation fields on ModelNodeMetadataBlock.

Tests:
- deprecated field defaults to False
- deprecated_by field defaults to None
- deprecated_reason field defaults to None
- Existing metadata.yaml-style instantiation parses without error
- Deprecation field combinations
"""

from __future__ import annotations

import pytest

from omnibase_core.models.core.model_node_metadata_block import ModelNodeMetadataBlock
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Minimal required fields for ModelNodeMetadataBlock
_MINIMAL = dict(
    name="test-node",
    version=ModelSemVer(major=1, minor=0, patch=0),
    author="test_author",
    created_at="2024-01-01T00:00:00Z",
    last_modified_at="2024-01-01T00:00:00Z",
    hash="a" * 64,
    entrypoint="python://main.py",
    namespace="onex.tools.test",
)


@pytest.mark.unit
class TestModelNodeMetadataBlockDeprecationDefaults:
    """Deprecation fields have correct defaults."""

    def test_deprecated_defaults_to_false(self) -> None:
        block = ModelNodeMetadataBlock(**_MINIMAL)
        assert block.deprecated is False

    def test_deprecated_by_defaults_to_none(self) -> None:
        block = ModelNodeMetadataBlock(**_MINIMAL)
        assert block.deprecated_by is None

    def test_deprecated_reason_defaults_to_none(self) -> None:
        block = ModelNodeMetadataBlock(**_MINIMAL)
        assert block.deprecated_reason is None

    def test_existing_instantiation_unchanged(self) -> None:
        """Nodes that don't pass deprecation fields parse without error."""
        block = ModelNodeMetadataBlock(**_MINIMAL)
        assert block.name == "test-node"
        assert block.deprecated is False
        assert block.deprecated_by is None
        assert block.deprecated_reason is None


@pytest.mark.unit
class TestModelNodeMetadataBlockDeprecationCombinations:
    """Deprecation field combinations behave correctly."""

    def test_deprecated_true_without_replacement(self) -> None:
        block = ModelNodeMetadataBlock(**_MINIMAL, deprecated=True)
        assert block.deprecated is True
        assert block.deprecated_by is None
        assert block.deprecated_reason is None

    def test_deprecated_true_with_replacement_node(self) -> None:
        block = ModelNodeMetadataBlock(
            **_MINIMAL,
            deprecated=True,
            deprecated_by="python://omninode.tools.new_node",
        )
        assert block.deprecated is True
        assert block.deprecated_by == "python://omninode.tools.new_node"
        assert block.deprecated_reason is None

    def test_deprecated_true_with_reason(self) -> None:
        block = ModelNodeMetadataBlock(
            **_MINIMAL,
            deprecated=True,
            deprecated_reason="Replaced by new_node with improved API.",
        )
        assert block.deprecated is True
        assert block.deprecated_by is None
        assert block.deprecated_reason == "Replaced by new_node with improved API."

    def test_deprecated_true_with_all_fields(self) -> None:
        block = ModelNodeMetadataBlock(
            **_MINIMAL,
            deprecated=True,
            deprecated_by="python://omninode.tools.new_node",
            deprecated_reason="Superseded by new_node.",
        )
        assert block.deprecated is True
        assert block.deprecated_by == "python://omninode.tools.new_node"
        assert block.deprecated_reason == "Superseded by new_node."

    def test_deprecated_false_with_no_other_fields(self) -> None:
        block = ModelNodeMetadataBlock(**_MINIMAL, deprecated=False)
        assert block.deprecated is False
        assert block.deprecated_by is None
        assert block.deprecated_reason is None

    def test_deprecated_by_without_deprecated_true(self) -> None:
        """deprecated_by can be set independently (no cross-field constraint)."""
        block = ModelNodeMetadataBlock(
            **_MINIMAL,
            deprecated_by="python://omninode.tools.other_node",
        )
        assert block.deprecated is False
        assert block.deprecated_by == "python://omninode.tools.other_node"

    def test_deprecated_reason_without_deprecated_true(self) -> None:
        """deprecated_reason can be set independently (no cross-field constraint)."""
        block = ModelNodeMetadataBlock(
            **_MINIMAL,
            deprecated_reason="Will be removed in v2.",
        )
        assert block.deprecated is False
        assert block.deprecated_reason == "Will be removed in v2."


@pytest.mark.unit
class TestModelNodeMetadataBlockDeprecationSerialization:
    """Deprecation fields serialize and round-trip correctly."""

    def test_model_dump_includes_deprecated(self) -> None:
        block = ModelNodeMetadataBlock(**_MINIMAL, deprecated=True)
        data = block.model_dump()
        assert data["deprecated"] is True

    def test_model_dump_deprecated_false_present(self) -> None:
        block = ModelNodeMetadataBlock(**_MINIMAL)
        data = block.model_dump()
        assert "deprecated" in data
        assert data["deprecated"] is False

    def test_model_dump_deprecated_by_present_when_set(self) -> None:
        block = ModelNodeMetadataBlock(
            **_MINIMAL, deprecated_by="python://omninode.tools.replacement"
        )
        data = block.model_dump()
        assert data["deprecated_by"] == "python://omninode.tools.replacement"

    def test_model_dump_deprecated_reason_present_when_set(self) -> None:
        block = ModelNodeMetadataBlock(**_MINIMAL, deprecated_reason="Use v2.")
        data = block.model_dump()
        assert data["deprecated_reason"] == "Use v2."

    def test_roundtrip_deprecated_fields(self) -> None:
        original = ModelNodeMetadataBlock(
            **_MINIMAL,
            deprecated=True,
            deprecated_by="python://omninode.tools.new_node",
            deprecated_reason="Superseded.",
        )
        data = original.model_dump()
        restored = ModelNodeMetadataBlock.model_validate(data)
        assert restored.deprecated == original.deprecated
        assert restored.deprecated_by == original.deprecated_by
        assert restored.deprecated_reason == original.deprecated_reason
