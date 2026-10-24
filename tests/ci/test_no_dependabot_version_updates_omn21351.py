# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-21351: dependency version updates belong to the release train."""

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("filename", ["dependabot.yml", "dependabot.yaml"])
def test_no_dependabot_version_updates(filename: str) -> None:
    """AC1: neither supported config filename declares version-update entries."""
    path = REPO_ROOT / ".github" / filename
    if not path.exists():
        return

    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    assert not config.get("updates"), (
        f"{path.relative_to(REPO_ROOT)} declares Dependabot version updates; "
        "dependency refreshes belong in the release train."
    )
