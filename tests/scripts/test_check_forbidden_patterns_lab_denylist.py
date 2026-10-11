# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""check_forbidden_patterns.sh reads a deployment's dead endpoints from the private vocabulary (OMN-20939)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_forbidden_patterns.sh"

# Synthetic dead endpoint in the RFC 5737 documentation range.
DEAD_ENDPOINT = "192.0.2.88:29092"


def _run(scan_dir: Path, env_extra: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), "--scan-dir", str(scan_dir)],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", **env_extra},
        check=False,
    )


@pytest.fixture
def scan_dir(tmp_path: Path) -> Path:
    target = tmp_path / "src"
    target.mkdir()
    (target / "client.py").write_text(
        f'BOOTSTRAP = "{DEAD_ENDPOINT}"\n', encoding="utf-8"
    )
    return target


@pytest.fixture
def config_root(tmp_path: Path) -> Path:
    root = tmp_path / "config_root"
    (root / "vocabularies").mkdir(parents=True)
    (root / "vocabularies" / "decommissioned_patterns.lab.conf").write_text(
        f"# synthetic lab denylist\n{DEAD_ENDPOINT}\n", encoding="utf-8"
    )
    return root


@pytest.mark.unit
def test_shipped_patterns_name_no_lab_endpoint() -> None:
    shipped = SCRIPT.parent / "validation" / "decommissioned_patterns.conf"
    assert "192.168." not in shipped.read_text(encoding="utf-8")


@pytest.mark.unit
def test_private_denylist_flags_the_dead_endpoint(
    scan_dir: Path, config_root: Path
) -> None:
    result = _run(scan_dir, {"ONEX_WORKSPACE_CONFIG_ROOT": str(config_root)})
    assert result.returncode == 1, result.stdout + result.stderr
    assert DEAD_ENDPOINT in result.stderr


@pytest.mark.unit
def test_sibling_of_omni_home_is_the_default_root(
    scan_dir: Path, config_root: Path, tmp_path: Path
) -> None:
    omni_home = tmp_path / "omni_home"
    omni_home.mkdir()
    (tmp_path / "omnibase_internal").symlink_to(config_root)
    result = _run(scan_dir, {"OMNI_HOME": str(omni_home)})
    assert result.returncode == 1, result.stdout + result.stderr


@pytest.mark.unit
def test_without_a_private_denylist_only_shipped_patterns_apply(
    scan_dir: Path,
) -> None:
    result = _run(scan_dir, {})
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.unit
def test_shipped_pattern_still_fails_without_the_private_denylist(
    tmp_path: Path,
) -> None:
    target = tmp_path / "src"
    target.mkdir()
    (target / "bus.py").write_text(
        "X = 'ONEX_EVENT_BUS_TYPE=inmemory'\n", encoding="utf-8"
    )
    result = _run(target, {})
    assert result.returncode == 1, result.stdout + result.stderr
