# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the governed runtime-ops verb allowlist loader (OMN-14168)."""

from __future__ import annotations

import pytest

import omnibase_core.utils.util_runtime_ops_verb_loader as verb_loader
from omnibase_core.validation.runtime_ops_verb_loader import (
    load_runtime_ops_verb_allowlist,
)


@pytest.mark.unit
class TestRuntimeOpsVerbLoader:
    def test_null_allowlist_preserves_public_validation_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A present null governed document cannot be treated as an empty allowlist."""
        verb_loader.load_runtime_ops_verb_allowlist.cache_clear()
        monkeypatch.setattr(
            verb_loader,
            "load_typed_yaml_content_document",
            lambda *_args, **_kwargs: None,
        )

        with pytest.raises(ValueError, match="must declare a non-empty"):
            verb_loader.load_runtime_ops_verb_allowlist()

        verb_loader.load_runtime_ops_verb_allowlist.cache_clear()

    def test_bundled_allowlist_contains_expected_verbs(self) -> None:
        allowlist = load_runtime_ops_verb_allowlist()
        assert allowlist == frozenset(
            {"patch", "rollout", "scale", "restart", "recreate", "config-repair"}
        )

    def test_git_is_not_in_allowlist(self) -> None:
        # A source change (git) produces a diff/PR and must route through the
        # normal merged-PR gate, never the RUNTIME_OPS class.
        assert "git" not in load_runtime_ops_verb_allowlist()

    def test_result_is_cached_frozenset(self) -> None:
        first = load_runtime_ops_verb_allowlist()
        second = load_runtime_ops_verb_allowlist()
        assert first is second
        assert isinstance(first, frozenset)
