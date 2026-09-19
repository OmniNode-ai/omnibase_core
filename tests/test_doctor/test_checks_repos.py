# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock, patch

import pytest

from omnibase_core.doctor.checks.check_repos_synced import CheckReposSynced

pytestmark = pytest.mark.unit
from omnibase_core.doctor.checks.check_stale_worktrees import CheckStaleWorktrees
from omnibase_core.enums.enum_doctor_category import EnumDoctorCategory
from omnibase_core.enums.enum_health_status_value import EnumHealthStatusValue


def test_repos_synced_all_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMNI_HOME", "/some/registry")
    with patch("subprocess.run") as mock_run:
        # git rev-parse returns same hash for HEAD and origin/main
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "abc123\n"
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.iterdir") as mock_iter:
                mock_dir = MagicMock()
                mock_dir.is_dir.return_value = True
                mock_dir.name = "omnibase_core"
                mock_dir.__truediv__ = lambda self, x: MagicMock(exists=lambda: True)
                mock_iter.return_value = [mock_dir]
                result = CheckReposSynced().run()
    assert result.category == EnumDoctorCategory.REPOS
    assert result.status != EnumHealthStatusValue.UNKNOWN


def test_repos_synced_skipped_when_omni_home_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OMNI_HOME", raising=False)
    result = CheckReposSynced().run()
    assert result.status == EnumHealthStatusValue.UNKNOWN
    assert "OMNI_HOME not set" in result.message


def test_repos_synced_skipped_when_customer_facing_omnibase_path_set_instead(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OMN-16849 boundary ruling (2026-08-28): this walks the OPERATOR's own
    registry checkout, which no customer has -- OMNIBASE_PATH alone must
    NOT satisfy it. This is the OMN-16851/#1712 regression this test exists
    to catch.
    """
    monkeypatch.delenv("OMNI_HOME", raising=False)
    monkeypatch.setenv("OMNIBASE_PATH", "/some/customer/registry")
    result = CheckReposSynced().run()
    assert result.status == EnumHealthStatusValue.UNKNOWN
    assert "OMNI_HOME not set" in result.message


def test_stale_worktrees_none():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.iterdir", return_value=[]):
                result = CheckStaleWorktrees().run()
    assert result.category == EnumDoctorCategory.REPOS
