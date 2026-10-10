# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-20032: the caller-mode verifier install refuses a release below the floor.

omnimarket#3511 (e565ba5ba, first released in omnimarket 0.4.303) makes
node_dod_verify refuse a contract that leaves an acceptance criterion
unbound. A caller pinning an older verifier would still admit a partly-bound
contract, so the reusable's "Install the pinned verifier" step refuses any
verifier-version below the floor before it installs anything. The floor lives
in one place, the step's VERIFIER_FLOOR env value; raising it is a one-line
change. These tests execute the step's own script with a stub uv on PATH.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "receipt-gate.yml"
)
VERIFIER_STEP = "Install the pinned verifier"
# The first omnimarket release carrying omnimarket#3511's refusal of a partly
# bound contract.
REFUSAL_RELEASE = (0, 4, 303)


def _workflow() -> dict[Any, Any]:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    assert isinstance(data, dict)
    return data


def _verifier_step() -> dict[str, Any]:
    steps = _workflow()["jobs"]["dod-verify"]["steps"]
    return next(step for step in steps if step.get("name") == VERIFIER_STEP)


def _version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def _run_step(tmp_path: Path, version: str) -> tuple[int, str, Path]:
    """Run the step's script with VERIFIER_VERSION and a stub uv that logs calls."""
    step = _verifier_step()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    uv_log = tmp_path / "uv.log"
    stub = bin_dir / "uv"
    # The stub records each call; `uv venv <dir>` lays a python that exits 0.
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f'printf "%s\\n" "$*" >> "{uv_log}"\n'
        'if [ "$1" = venv ]; then\n'
        '  dir="${@: -1}"\n'
        '  mkdir -p "$dir/bin"\n'
        "  printf '#!/usr/bin/env bash\\nexit 0\\n' > \"$dir/bin/python\"\n"
        '  chmod +x "$dir/bin/python"\n'
        "fi\n"
    )
    stub.chmod(0o755)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    github_env = tmp_path / "github_env"
    github_env.write_text("")
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "GITHUB_WORKSPACE": str(workspace),
        "GITHUB_ENV": str(github_env),
        **{key: str(value) for key, value in step["env"].items()},
        "VERIFIER_VERSION": version,
    }
    result = subprocess.run(
        [shutil.which("bash") or "bash", "-c", step["run"]],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout + result.stderr, uv_log


def test_the_floor_is_declared_once_on_the_install_step() -> None:
    step = _verifier_step()
    assert step["id"] == "verifier"
    assert step["env"]["VERIFIER_VERSION"] == "${{ inputs.verifier-version }}"
    floor = str(step["env"]["VERIFIER_FLOOR"])
    assert _version(floor) >= REFUSAL_RELEASE
    # One place: no other line of the workflow spells the floor's name.
    lines = [
        line
        for line in WORKFLOW_PATH.read_text().splitlines()
        if "VERIFIER_FLOOR:" in line
    ]
    assert len(lines) == 1, lines


def test_the_verifier_version_default_is_at_or_above_the_floor() -> None:
    workflow = _workflow()
    # PyYAML interprets the YAML 1.1 `on` key as True.
    trigger = workflow.get(True, workflow.get("on"))
    default = trigger["workflow_call"]["inputs"]["verifier-version"]["default"]
    assert _version(default) >= (0, 4, 305)
    assert _version(default) >= _version(str(_verifier_step()["env"]["VERIFIER_FLOOR"]))


@pytest.mark.parametrize("version", ["0.4.294", "0.4.280", "0.4.302", "0.3.999"])
def test_a_verifier_below_the_floor_is_refused_before_install(
    tmp_path: Path, version: str
) -> None:
    returncode, output, uv_log = _run_step(tmp_path, version)
    assert returncode == 1, output
    assert (f"::error::verifier-version {version} is below the floor 0.4.303") in output
    assert not uv_log.exists(), "nothing may be installed below the floor"


@pytest.mark.parametrize("version", ["0.4.303", "0.4.305", "0.4.1000", "1.0.0"])
def test_a_verifier_at_or_above_the_floor_is_installed(
    tmp_path: Path, version: str
) -> None:
    returncode, output, uv_log = _run_step(tmp_path, version)
    assert returncode == 0, output
    assert f"omnimarket=={version}" in uv_log.read_text()


@pytest.mark.parametrize("version", ["0.4", "v0.4.305", "0.4.305rc1", ""])
def test_a_non_numeric_version_is_still_refused(tmp_path: Path, version: str) -> None:
    returncode, output, uv_log = _run_step(tmp_path, version)
    assert returncode == 1, output
    assert "::error::verifier-version must match numeric MAJOR.MINOR.PATCH" in output
    assert not uv_log.exists()
