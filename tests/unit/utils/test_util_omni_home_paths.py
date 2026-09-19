# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit tests for util_omni_home_paths (OMN-13136, OMN-16849 boundary reclassification).

This resolver is INTERNAL orchestration under the operator's 2026-08-28
boundary ruling (relayed via OMN-16849): it locates the operator's own
multi-repo registry checkout, which no customer has (goal row L1). It reads
OMNI_HOME, not OMNIBASE_PATH -- OMNIBASE_PATH is reserved for parameters a
customer actually sets (installer, KB runbooks, shipped CLI/skill docs).

Verifies that each resolver:
- derives the correct sub-path from OMNI_HOME
- raises a typed refusal (fail-fast) when OMNI_HOME is absent
- does NOT read the customer-facing OMNIBASE_PATH name (this is the
  regression this test exists to catch: OMN-16851/#1712 briefly flipped
  this resolver to OMNIBASE_PATH, in violation of the boundary ruling,
  before being reverted here)
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
    def test_derives_from_omni_home(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OMNI_HOME", "/some/registry")
        result = resolve_worktrees_root()
        assert str(result) == "/some/registry/omni_worktrees"

    def test_raises_typed_refusal_when_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OMNI_HOME", raising=False)
        with pytest.raises(ModelOnexError, match="OMNI_HOME"):
            resolve_worktrees_root()

    def test_does_not_read_customer_facing_omnibase_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """This is internal orchestration (2026-08-28 boundary ruling): it
        must key on OMNI_HOME only. Setting OMNIBASE_PATH alone must NOT
        satisfy it -- that would be exactly the OMN-16851/#1712 regression.
        """
        monkeypatch.delenv("OMNI_HOME", raising=False)
        monkeypatch.setenv("OMNIBASE_PATH", "/some/customer/registry")
        with pytest.raises(ModelOnexError, match="OMNI_HOME"):
            resolve_worktrees_root()

    def test_returns_path_type(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from pathlib import Path

        monkeypatch.setenv("OMNI_HOME", "/some/registry")
        assert isinstance(resolve_worktrees_root(), Path)


@pytest.mark.unit
class TestResolveEvidenceRoot:
    def test_derives_from_omni_home(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OMNI_HOME", "/some/registry")
        result = resolve_evidence_root()
        assert str(result) == "/some/registry/onex_change_control/evidence"

    def test_raises_typed_refusal_when_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OMNI_HOME", raising=False)
        with pytest.raises(ModelOnexError, match="OMNI_HOME"):
            resolve_evidence_root()

    def test_returns_path_type(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from pathlib import Path

        monkeypatch.setenv("OMNI_HOME", "/some/registry")
        assert isinstance(resolve_evidence_root(), Path)


@pytest.mark.unit
class TestResolveOmnibaseInfraPath:
    def test_derives_from_omni_home(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OMNI_HOME", "/some/registry")
        result = resolve_omnibase_infra_path()
        assert str(result) == "/some/registry/omnibase_infra"

    def test_raises_typed_refusal_when_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OMNI_HOME", raising=False)
        with pytest.raises(ModelOnexError, match="OMNI_HOME"):
            resolve_omnibase_infra_path()

    def test_returns_path_type(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from pathlib import Path

        monkeypatch.setenv("OMNI_HOME", "/some/registry")
        assert isinstance(resolve_omnibase_infra_path(), Path)
