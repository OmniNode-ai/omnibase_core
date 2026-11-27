# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-26616 AC4 end to end: the installed package on an empty customer machine.

Builds the wheel from the source tree, installs it into a fresh virtual
environment and runs the installed ``onex doctor`` and ``onex health`` with an
empty home directory and a minimal environment. Both must exit 0 and print no
raw error text and no environment variable name.

Slow and network-bound (it builds and installs), so it only runs when
``OMN_26616_INSTALLED_E2E=1``. A lab run or CI job invokes it with::

    OMN_26616_INSTALLED_E2E=1 OMN_26616_E2E_EVIDENCE_DIR=<dir> \\
        uv run pytest tests/integration/test_omn26616_installed_package_e2e.py \\
        -n 0 --reruns 0 --no-cov -p no:cacheprovider

``OMN_26616_E2E_SOURCE`` names another source tree to build instead of this
one (used to show the run red on an earlier head). The run writes its repeatable
artifact, ``omn26616_installed_e2e.txt``, into the evidence directory.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from omnibase_core.models.bootstrap.model_environment_bootstrap import (
    ModelEnvironmentBootstrap,
)

pytestmark = [pytest.mark.integration, pytest.mark.slow]

_SETTINGS = ModelEnvironmentBootstrap.capture_process_environment(
    declared_keys=(
        "OMN_26616_INSTALLED_E2E",
        "OMN_26616_E2E_SOURCE",
        "OMN_26616_E2E_EVIDENCE_DIR",
    )
).environment
_ENABLED = _SETTINGS.optional("OMN_26616_INSTALLED_E2E") == "1"
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ALL_CAPS_NAME = re.compile(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b")
_FIX_EXPORT = re.compile(r"Fix: export [A-Z0-9_]+=")
_RAW_MARKERS = ("Error: '", "[Errno", "Traceback", "Import error")


def _run(
    argv: list[str], *, env: dict[str, str] | None, cwd: Path, timeout: int
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        env=env,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


@pytest.mark.skipif(not _ENABLED, reason="set OMN_26616_INSTALLED_E2E=1 to run")
@pytest.mark.timeout(1200)
def test_installed_onex_doctor_and_health_exit_zero_on_a_customer_machine(
    tmp_path: Path,
) -> None:
    uv = shutil.which("uv")
    assert uv is not None, "uv is required to build and install the wheel"
    source = Path(_SETTINGS.optional("OMN_26616_E2E_SOURCE") or _REPO_ROOT)
    dist = tmp_path / "dist"
    venv = tmp_path / "venv"
    home = tmp_path / "home"
    home.mkdir()

    built = _run(
        [uv, "build", "--wheel", "--out-dir", str(dist), str(source)],
        env=None,
        cwd=tmp_path,
        timeout=900,
    )
    assert built.returncode == 0, built.stderr
    wheel = next(dist.glob("omnibase_core-*.whl"))
    made = _run(
        [uv, "venv", "--python", "3.12", str(venv)],
        env=None,
        cwd=tmp_path,
        timeout=300,
    )
    assert made.returncode == 0, made.stderr
    installed = _run(
        [uv, "pip", "install", "--python", str(venv / "bin" / "python"), str(wheel)],
        env=None,
        cwd=tmp_path,
        timeout=900,
    )
    assert installed.returncode == 0, installed.stderr

    customer_env = {"HOME": str(home), "PATH": f"{venv / 'bin'}:/usr/bin:/bin"}
    onex = str(venv / "bin" / "onex")
    lines: list[str] = [f"source: {source}", f"wheel: {wheel.name}"]
    failures: list[str] = []
    for command in (["doctor"], ["health"]):
        proc = _run([onex, *command], env=customer_env, cwd=home, timeout=120)
        text = proc.stdout + proc.stderr
        lines += [f"$ onex {' '.join(command)}", text, f"exit: {proc.returncode}"]
        if proc.returncode != 0:
            failures.append(f"onex {command[0]} exited {proc.returncode}")
        for marker in _RAW_MARKERS:
            if marker in text:
                failures.append(f"onex {command[0]} printed {marker!r}")
        if _ALL_CAPS_NAME.search(_FIX_EXPORT.sub("Fix: export ", text)):
            failures.append(f"onex {command[0]} named an environment variable")

    evidence_dir = Path(_SETTINGS.optional("OMN_26616_E2E_EVIDENCE_DIR") or tmp_path)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "omn26616_installed_e2e.txt").write_text("\n".join(lines) + "\n")
    assert not failures, "\n".join(failures) + "\n" + "\n".join(lines)
