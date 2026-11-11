# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Version taken from git at build time (OMN-23834, core slice of OMN-18549).

Under a git-derived version no change edits a version line, and two code states
can never ship under one version string because the build names each commit.
The gate keeps that true: a declared static version, or a configured fallback
version that would name two code states alike, is refused. The legacy
static-version rule (version ahead of the newest tag) is untouched and is
covered by the sibling test files.
"""

from pathlib import Path

import pytest

from omnibase_core.models.nodes.release_identity_check.model_release_identity_check_input import (
    ModelReleaseIdentityCheckInput,
)
from omnibase_core.models.nodes.release_identity_check.model_release_identity_gather_input import (
    ModelReleaseIdentityGatherInput,
)
from omnibase_core.nodes.node_release_identity_check_compute.handler import (
    NodeReleaseIdentityCheckCompute,
)
from omnibase_core.nodes.node_release_identity_check_compute.runtime_release_identity_check import (
    main,
)
from omnibase_core.nodes.node_release_identity_gather_effect.handler import (
    NodeReleaseIdentityGatherEffect,
)

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[4]

VCS_PYPROJECT = """\
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[project]
name = "demo"
dynamic = ["version"]

[tool.hatch.version]
source = "vcs"
"""

VCS_FALLBACK_PYPROJECT = (
    VCS_PYPROJECT + '\n[tool.hatch.version.raw-options]\nfallback_version = "0.47.72"\n'
)

STATIC_PYPROJECT = '[project]\nname = "demo"\nversion = "0.47.99"\n'


def _check(**facts: object) -> tuple[str, list[str | None]]:
    report = NodeReleaseIdentityCheckCompute().handle(
        ModelReleaseIdentityCheckInput(required_version_source="vcs", **facts)
    )
    return report.overall_status, [finding.rule_id for finding in report.findings]


def test_git_derived_version_passes_with_source_change_and_no_version_edit():
    status, rules = _check(
        version_source="vcs",
        published_tags=("v0.47.72",),
        changed_files=("src/omnibase_core/example.py",),
    )
    assert (status, rules) == ("PASS", [])


def test_planted_fallback_version_that_names_two_code_states_alike_fails():
    status, rules = _check(
        version_source="vcs",
        vcs_fallback_setting="0.47.72",
        published_tags=("v0.47.72",),
        changed_files=("src/omnibase_core/example.py",),
    )
    assert status == "FAIL"
    assert rules == ["aliasing_fallback_version"]


def test_declared_static_version_is_refused_even_when_ahead_of_every_tag():
    status, rules = _check(
        version_source="static",
        pyproject_version_raw="0.47.99",
        published_tags=("v0.47.72",),
        changed_files=("src/omnibase_core/example.py",),
    )
    assert status == "FAIL"
    assert rules == ["version_not_from_git"]


def test_legacy_rule_still_fails_a_static_version_on_a_published_tag():
    report = NodeReleaseIdentityCheckCompute().handle(
        ModelReleaseIdentityCheckInput(
            pyproject_version_raw="0.47.72",
            published_tags=("v0.47.72",),
            changed_files=("src/omnibase_core/example.py",),
        )
    )
    assert report.overall_status == "FAIL"


@pytest.mark.parametrize(
    ("pyproject", "source", "fallback"),
    [
        (VCS_PYPROJECT, "vcs", None),
        (VCS_FALLBACK_PYPROJECT, "vcs", "0.47.72"),
        (STATIC_PYPROJECT, "static", None),
    ],
)
def test_gather_reads_the_declared_version_source(
    tmp_path, pyproject, source, fallback
):
    (tmp_path / "pyproject.toml").write_text(pyproject)
    facts = NodeReleaseIdentityGatherEffect().handle(
        ModelReleaseIdentityGatherInput(
            repo_root=str(tmp_path), required_version_source="vcs"
        )
    )
    assert facts.required_version_source == "vcs"
    assert facts.version_source == source
    assert facts.vcs_fallback_setting == fallback


def test_this_repository_takes_its_version_from_git():
    """The running tree must hold the declaration the gate demands."""
    assert (
        main(["--root", str(REPO), "--require-version-source", "vcs", "docs/x.md"]) == 0
    )
    facts = NodeReleaseIdentityGatherEffect().handle(
        ModelReleaseIdentityGatherInput(
            repo_root=str(REPO), required_version_source="vcs"
        )
    )
    assert facts.version_source == "vcs"
    assert facts.pyproject_version_raw is None
    assert facts.vcs_fallback_setting is None
