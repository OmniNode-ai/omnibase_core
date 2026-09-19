# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for util_omni_home_paths (OMN-13136, OMN-16851).

Verifies that each resolver:
- derives the correct sub-path from OMNIBASE_PATH
- raises a typed refusal (fail-fast) when OMNIBASE_PATH is absent
- does NOT fall back to the retired OMNI_HOME name (clean break, OMN-16849)
"""

from __future__ import annotations

import pytest

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.utils.util_omni_home_paths import (
    resolve_evidence_root,
    resolve_omnibase_infra_path,
    resolve_worktrees_root,
)


@pytest.mark.unit
class TestResolveWorktreesRoot:
    def test_derives_from_omnibase_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OMNIBASE_PATH", "/some/monorepo")
        result = resolve_worktrees_root()
        assert str(result) == "/some/monorepo/omni_worktrees"

    def test_raises_typed_refusal_when_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OMNIBASE_PATH", raising=False)
        with pytest.raises(ModelOnexError, match="OMNIBASE_PATH"):
            resolve_worktrees_root()

    def test_does_not_fall_back_to_legacy_omni_home(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OMNIBASE_PATH", raising=False)
        monkeypatch.setenv("OMNI_HOME", "/some/legacy/monorepo")
        with pytest.raises(ModelOnexError, match="OMNIBASE_PATH"):
            resolve_worktrees_root()

    def test_returns_path_type(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from pathlib import Path

        monkeypatch.setenv("OMNIBASE_PATH", "/some/monorepo")
        assert isinstance(resolve_worktrees_root(), Path)


@pytest.mark.unit
class TestResolveEvidenceRoot:
    def test_derives_from_omnibase_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OMNIBASE_PATH", "/some/monorepo")
        result = resolve_evidence_root()
        assert str(result) == "/some/monorepo/onex_change_control/evidence"

    def test_raises_typed_refusal_when_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OMNIBASE_PATH", raising=False)
        with pytest.raises(ModelOnexError, match="OMNIBASE_PATH"):
            resolve_evidence_root()

    def test_returns_path_type(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from pathlib import Path

        monkeypatch.setenv("OMNIBASE_PATH", "/some/monorepo")
        assert isinstance(resolve_evidence_root(), Path)


@pytest.mark.unit
class TestResolveOmnibaseInfraPath:
    def test_derives_from_omnibase_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OMNIBASE_PATH", "/some/monorepo")
        result = resolve_omnibase_infra_path()
        assert str(result) == "/some/monorepo/omnibase_infra"

    def test_raises_typed_refusal_when_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OMNIBASE_PATH", raising=False)
        with pytest.raises(ModelOnexError, match="OMNIBASE_PATH"):
            resolve_omnibase_infra_path()

    def test_returns_path_type(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from pathlib import Path

        monkeypatch.setenv("OMNIBASE_PATH", "/some/monorepo")
        assert isinstance(resolve_omnibase_infra_path(), Path)
