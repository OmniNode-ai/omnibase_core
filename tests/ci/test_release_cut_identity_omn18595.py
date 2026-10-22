# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-18595: a release cut respects the README-only documentation policy.

The release train cuts a version by merging a titled pull request. The tree it
cuts must carry no generated ``CHANGELOG.md`` (OMN-17427 keeps README.md as the
only tracked prose), and the project version must match the editable
``omnibase-core`` entry in ``uv.lock`` so the tag names the package it builds.
"""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

import pytest

from omnibase_core.models.nodes.readme_only_docs.model_readme_only_docs_input import (
    ModelReadmeOnlyDocsInput,
)
from omnibase_core.nodes.node_git_file_listing_effect.handler_readme_only_docs import (
    HandlerReadmeOnlyDocs,
)
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], env=scrub_git_location_env(), text=True
    )


def _scan(root: Path) -> tuple[str, list[str]]:
    report = HandlerReadmeOnlyDocs().handle(ModelReadmeOnlyDocsInput(root=root))
    return report.overall_status, [f.location for f in report.findings]


def test_release_tree_tracks_no_changelog() -> None:
    assert _git(REPO_ROOT, "ls-files", "--", "CHANGELOG.md").strip() == ""
    status, findings = _scan(REPO_ROOT)
    assert "CHANGELOG.md" not in findings
    assert status == "PASS", findings


def test_release_generated_changelog_is_refused(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    for name, body in (
        ("README.md", "readme\n"),
        ("CHANGELOG.md", "## v0.0.1 (2026-01-01)\n\n- release\n"),
    ):
        (tmp_path / name).write_text(body)
        _git(tmp_path, "add", "--", name)
    status, findings = _scan(tmp_path)
    assert status == "FAIL"
    assert findings == ["CHANGELOG.md"]


def test_project_version_matches_locked_editable_package() -> None:
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((REPO_ROOT / "uv.lock").read_text(encoding="utf-8"))
    packages = [p for p in lock["package"] if p["name"] == "omnibase-core"]
    assert len(packages) == 1
    assert packages[0]["source"] == {"editable": "."}
    assert packages[0]["version"] == project["project"]["version"]


def test_release_changelog_retains_version_0_47_50_in_root_readme() -> None:
    """Keep this cut's public notes while rejecting a standalone changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.50 (2026-10-20)" in readme
    assert "### Included Since v0.47.49" in readme
    assert (
        "- fix: cascade legs and CI Summary stop going red on a release head (#2062)"
        in readme
    )
    assert (
        "- feat: the delegation wire request admits the context_compaction task class (#2061)"
        in readme
    )


def test_release_changelog_retains_version_0_47_51_in_root_readme() -> None:
    """Keep the 0.47.51 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.51 (2026-10-20)" in readme
    assert "### Included Since v0.47.50" in readme
    assert (
        "- feat: the ticket contract item declares supersedes_ac_binding (#2067)"
        in readme
    )


def test_release_changelog_retains_version_0_47_52_in_root_readme() -> None:
    """Keep the 0.47.52 cut's public notes in root README, not a changelog."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## v0.47.52 (2026-10-22)" in readme
    assert "### Included Since v0.47.51" in readme
    assert (
        "- fix: ticket contract dod_evidence items accept ac_bindings (#2076)" in readme
    )
