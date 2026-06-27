# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for util_omni_home_paths (OMN-13136).

Verifies that each resolver:
- derives the correct sub-path from OMNI_HOME
- raises KeyError (fail-fast) when OMNI_HOME is absent
"""

from __future__ import annotations

import pytest

from omnibase_core.utils.util_omni_home_paths import (
    resolve_evidence_root,
    resolve_omnibase_infra_path,
    resolve_worktrees_root,
)


@pytest.mark.unit
class TestResolveWorktreesRoot:
    def test_derives_from_omni_home(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OMNI_HOME", "/some/monorepo")
        result = resolve_worktrees_root()
        assert str(result) == "/some/monorepo/omni_worktrees"

    def test_raises_key_error_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OMNI_HOME", raising=False)
        with pytest.raises(KeyError):
            resolve_worktrees_root()

    def test_returns_path_type(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from pathlib import Path

        monkeypatch.setenv("OMNI_HOME", "/some/monorepo")
        assert isinstance(resolve_worktrees_root(), Path)


@pytest.mark.unit
class TestResolveEvidenceRoot:
    def test_derives_from_omni_home(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OMNI_HOME", "/some/monorepo")
        result = resolve_evidence_root()
        assert str(result) == "/some/monorepo/onex_change_control/evidence"

    def test_raises_key_error_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OMNI_HOME", raising=False)
        with pytest.raises(KeyError):
            resolve_evidence_root()

    def test_returns_path_type(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from pathlib import Path

        monkeypatch.setenv("OMNI_HOME", "/some/monorepo")
        assert isinstance(resolve_evidence_root(), Path)


@pytest.mark.unit
class TestResolveOmnibaseInfraPath:
    def test_derives_from_omni_home(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OMNI_HOME", "/some/monorepo")
        result = resolve_omnibase_infra_path()
        assert str(result) == "/some/monorepo/omnibase_infra"

    def test_raises_key_error_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OMNI_HOME", raising=False)
        with pytest.raises(KeyError):
            resolve_omnibase_infra_path()

    def test_returns_path_type(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from pathlib import Path

        monkeypatch.setenv("OMNI_HOME", "/some/monorepo")
        assert isinstance(resolve_omnibase_infra_path(), Path)
