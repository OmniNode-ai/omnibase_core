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


# --- OMN-25394 (review finding 10): both places set -------------------------------------------------
#
# hatch-vcs names ``fallback-version`` directly under ``[tool.hatch.version]`` and takes the setuptools-scm
# spelling ``fallback_version`` under ``raw-options``. hatch-vcs is not installed where this was written,
# so which of the two it prefers when both are set was not read; the gather handler answers only "is a
# fallback declared, and what string does the tree say", and the aliasing rule fires on any declared
# fallback. These tests pin the handler's own order: the direct hyphenated key is reported first, either
# place alone is reported, and a fallback in either place is never read as none.


def test_hatch_vcs_precedence_direct_key_is_reported_when_both_places_are_set(
    tmp_path: Path,
) -> None:
    pyproject = (
        _HEAD
        + 'fallback-version = "0.47.72"\n'
        + '\n[tool.hatch.version.raw-options]\nfallback_version = "9.9.9"\n'
    )
    assert _gather_fallback(tmp_path, pyproject) == "0.47.72"


def test_hatch_vcs_precedence_raw_options_alone_is_reported_in_either_spelling(
    tmp_path: Path,
) -> None:
    for spelling in ("fallback_version", "fallback-version"):
        pyproject = (
            _HEAD + f'\n[tool.hatch.version.raw-options]\n{spelling} = "1.2.3"\n'
        )
        assert _gather_fallback(tmp_path, pyproject) == "1.2.3", spelling


def test_hatch_vcs_precedence_a_fallback_in_either_place_is_never_read_as_none(
    tmp_path: Path,
) -> None:
    """Both places declare one: the rule still has a fallback to refuse."""
    pyproject = (
        _HEAD
        + 'fallback_version = "0.47.72"\n'
        + '\n[tool.hatch.version.raw-options]\nfallback-version = "9.9.9"\n'
    )
    assert _gather_fallback(tmp_path, pyproject) is not None
