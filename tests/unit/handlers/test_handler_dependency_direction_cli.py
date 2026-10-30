# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the dependency-direction CLI runtime (OMN-19998).

Each test builds a throwaway git repository under ``tmp_path`` so the tracked
file listing, the baseline file, the base-ref ratchet and the report and event
writes run the way the hook and the reusable workflow run them.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from omnibase_core.nodes.node_dependency_direction_check_effect.runtime_dependency_direction_check import (
    main,
)

pytestmark = pytest.mark.unit

_UP = "omnimarket"
_DOCKERFILE = f'RUN uv pip install --no-deps "{_UP} @ file:///workspace/{_UP}"\n'


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.invalid",
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(root),
        },
    )


def _repo(tmp_path: Path, files: dict[str, str]) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "dev")
    (root / "pyproject.toml").write_text('[project]\nname = "omnibase-infra"\n')
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    return root


def _baseline_text(path: str = "docker/Dockerfile") -> str:
    return (
        "repo: omnibase_infra\nviolations:\n"
        f"- path: {path}\n  channel: dockerfile\n  target: {_UP}\n  ticket: OMN-19998\n"
    )


def test_full_tree_upward_install_fails_and_writes_events(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"docker/Dockerfile": _DOCKERFILE})
    report = tmp_path / "report.json"
    assert main(["--root", str(root), "--report-json", str(report)]) == 1
    data = json.loads(report.read_text())
    assert data["overall_status"] == "FAIL"
    events = Path(f"{report}.events.jsonl").read_text().splitlines()
    assert len(events) == 2  # one run event, one fire event


def test_repo_is_inferred_from_pyproject(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path, {"docker/Dockerfile": _DOCKERFILE})
    main(["--root", str(root)])
    assert "omnibase_infra (layer 3) depends on omnimarket" in capsys.readouterr().out


def test_baselined_violation_passes(tmp_path: Path) -> None:
    root = _repo(
        tmp_path,
        {
            "docker/Dockerfile": _DOCKERFILE,
            ".onex_ratchets/dependency_direction_baseline.yaml": _baseline_text(),
        },
    )
    assert main(["--root", str(root)]) == 0


def test_clean_repository_passes(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"src/a.py": "import omnibase_core\n"})
    assert main(["--root", str(root)]) == 0


def test_staged_file_mode_reads_only_named_files(tmp_path: Path) -> None:
    root = _repo(
        tmp_path, {"docker/Dockerfile": _DOCKERFILE, "src/a.py": "import os\n"}
    )
    assert main(["--root", str(root), str(root / "src/a.py")]) == 0
    assert main(["--root", str(root), str(root / "docker/Dockerfile")]) == 1


def test_baseline_growth_against_base_ref_fails(tmp_path: Path) -> None:
    root = _repo(
        tmp_path,
        {
            "docker/Dockerfile": _DOCKERFILE,
            ".onex_ratchets/dependency_direction_baseline.yaml": "violations: []\n",
        },
    )
    (root / ".onex_ratchets/dependency_direction_baseline.yaml").write_text(
        _baseline_text()
    )
    assert main(["--root", str(root), "--ratchet-base-ref", "HEAD"]) == 1


def test_baseline_introduction_passes_the_ratchet(tmp_path: Path) -> None:
    # introduction: the base has no baseline file at all
    root = _repo(tmp_path, {"docker/Dockerfile": _DOCKERFILE})
    (root / ".onex_ratchets").mkdir()
    (root / ".onex_ratchets/dependency_direction_baseline.yaml").write_text(
        _baseline_text()
    )
    assert main(["--root", str(root), "--ratchet-base-ref", "HEAD"]) == 0


def test_write_baseline_records_current_violations(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path, {"docker/Dockerfile": _DOCKERFILE})
    assert main(["--root", str(root), "--write-baseline"]) == 0
    out = capsys.readouterr().out
    assert "path: docker/Dockerfile" in out
    assert "channel: dockerfile" in out
    assert f"target: {_UP}" in out


def test_missing_ratchet_base_ref_is_error(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"src/a.py": "import os\n"})
    assert main(["--root", str(root), "--ratchet-base-ref", "0" * 40]) == 1
