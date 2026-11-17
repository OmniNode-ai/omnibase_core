# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A fallback version declared directly under ``[tool.hatch.version]`` is read too (OMN-25336).

hatch-vcs takes ``fallback-version`` straight under ``[tool.hatch.version]`` as well as
``fallback_version`` under ``raw-options``. The gather handler read only ``raw-options``, so a tree
that declared the hatch-vcs key directly never reached the ``aliasing_fallback_version`` rule. The
failing control is the direct key: before this change the gathered ``vcs_fallback_setting`` is None.
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
from omnibase_core.nodes.node_release_identity_gather_effect.handler import (
    NodeReleaseIdentityGatherEffect,
)

pytestmark = pytest.mark.unit

_HEAD = """\
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[project]
name = "demo"
dynamic = ["version"]

[tool.hatch.version]
source = "vcs"
"""


def _gather_fallback(tmp_path: Path, pyproject: str) -> str | None:
    (tmp_path / "pyproject.toml").write_text(pyproject)
    facts = NodeReleaseIdentityGatherEffect().handle(
        ModelReleaseIdentityGatherInput(
            repo_root=str(tmp_path),
            required_version_source="vcs",
        )
    )
    return facts.vcs_fallback_setting


@pytest.mark.parametrize(
    "direct_key", ["fallback-version", "fallback_version"], ids=["hyphen", "underscore"]
)
def test_aliasing_fallback_version_direct_key_under_hatch_version_is_gathered(
    tmp_path: Path, direct_key: str
) -> None:
    pyproject = _HEAD + f'{direct_key} = "0.47.72"\n'
    assert _gather_fallback(tmp_path, pyproject) == "0.47.72"


def test_aliasing_fallback_version_raw_options_key_is_still_gathered(
    tmp_path: Path,
) -> None:
    """Positive control: the raw-options spelling keeps working."""
    pyproject = (
        _HEAD + '\n[tool.hatch.version.raw-options]\nfallback_version = "0.47.72"\n'
    )
    assert _gather_fallback(tmp_path, pyproject) == "0.47.72"


def test_aliasing_fallback_version_absent_key_gathers_none(tmp_path: Path) -> None:
    """Negative control: no fallback anywhere reads None, not a stringified None."""
    assert _gather_fallback(tmp_path, _HEAD) is None


def test_aliasing_fallback_version_fires_for_the_direct_key(tmp_path: Path) -> None:
    """The gathered direct key reaches the rule: the check fails with the aliasing finding."""
    fallback = _gather_fallback(tmp_path, _HEAD + 'fallback-version = "0.47.72"\n')
    report = NodeReleaseIdentityCheckCompute().handle(
        ModelReleaseIdentityCheckInput(
            required_version_source="vcs",
            version_source="vcs",
            vcs_fallback_setting=fallback,
            published_tags=("v0.47.72",),
            changed_files=("src/omnibase_core/example.py",),
        )
    )
    assert report.overall_status == "FAIL"
    assert [finding.rule_id for finding in report.findings] == [
        "aliasing_fallback_version"
    ]
