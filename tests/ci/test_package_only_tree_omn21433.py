# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""This repository ships no deployment artifact, so the deploy gate's package-only exemption holds.

The deploy gate (omniclaude, ``deploy-gate``) exempts a declared library-package repository from the
deploy-evidence requirement only while its checked-out tree corroborates the declaration: any file
named like a container build file, any compose file and any top-level deployment tree ends the
exemption for every pull request, and each pull request that touches ``src/*/nodes`` or
``src/*/handlers`` then fails the gate until its ticket contract carries a live-surface probe. A test
fixture named ``Dockerfile.in`` did exactly that from 2026-10-05 until OMN-21433. The scan below
reads the tree the way the gate does (dot-directories are skipped) and fails on the first artifact
shape, so a later fixture cannot end the exemption unnoticed.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[2]
_FILE_PATTERNS = (
    "Dockerfile*",
    "*.Dockerfile",
    "docker-compose*.yml",
    "docker-compose*.yaml",
    "compose.yml",
    "compose.yaml",
)
_TREE_ROOTS = frozenset(
    {
        "docker",
        "k8s",
        "kubernetes",
        "helm",
        "charts",
        "terraform",
        "ansible",
        "deploy",
        "deployment",
        "infra",
    }
)


def deployment_artifacts(root: Path) -> list[str]:
    """Return every path under ``root`` the deploy gate would read as a deployment artifact."""
    found: list[str] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part.startswith(".") for part in relative.parts):
            continue
        if path.is_dir():
            if len(relative.parts) == 1 and relative.name in _TREE_ROOTS:
                found.append(relative.as_posix())
            continue
        if any(fnmatch.fnmatch(path.name, pattern) for pattern in _FILE_PATTERNS):
            found.append(relative.as_posix())
    return found


def test_the_tree_ships_no_deployment_artifact() -> None:
    assert deployment_artifacts(_ROOT) == []


@pytest.mark.parametrize(
    "planted",
    [
        "Dockerfile",
        "nested/Dockerfile.in",
        "nested/base.Dockerfile",
        "docker-compose.dev.yml",
        "compose.yaml",
        "k8s/deployment.yaml",
    ],
)
def test_a_planted_deployment_artifact_is_found(tmp_path: Path, planted: str) -> None:
    target = tmp_path / planted
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("FROM scratch\n", encoding="utf-8")
    assert planted.split("/")[0] in {
        found.split("/")[0] for found in deployment_artifacts(tmp_path)
    }


def test_a_dot_directory_artifact_is_not_scanned_like_the_gate(tmp_path: Path) -> None:
    hidden = tmp_path / ".cache" / "Dockerfile"
    hidden.parent.mkdir()
    hidden.write_text("FROM scratch\n", encoding="utf-8")
    assert deployment_artifacts(tmp_path) == []
