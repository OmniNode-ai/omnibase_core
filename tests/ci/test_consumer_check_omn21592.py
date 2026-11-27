# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-21592: an omnibase_core pull request head is tried in omnimarket dev and omnibase_infra dev.

``consumer-check-reusable.yml`` installs the head into each consumer's locked environment (no deps, no config, run
from outside the consumer's project so its override cannot keep the old core) and runs the consumer's smoke and test
files. Its step is run here by bash against fake ``git``/``uv``/interpreter binaries that answer from the environment:
every step that did not run to an answer fails the job (unread is never a pass), a failing smoke or test fails it,
and only a head that is the installed one with green files passes.
"""

from __future__ import annotations

import json
import stat
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
SHA = "a" * 40

FAKE_GIT = """#!/bin/bash
echo "git $*" >> "$FAKE_LOG"
case " $* " in *" $FAKE_FAIL "*) echo "fatal: $FAKE_FAIL" >&2; exit 128;; esac
if [ "$1" = clone ] || [[ " $* " == *" clone "* ]]; then
  for last; do :; done
  mkdir -p "$last"
fi
exit 0
"""

FAKE_UV = """#!/bin/bash
echo "uv (cwd=$PWD) $*" >> "$FAKE_LOG"
case " $* " in *" $FAKE_FAIL "*) echo "uv: $FAKE_FAIL" >&2; exit 2;; esac
if [ "$1" = sync ]; then
  mkdir -p .venv/bin
  cp "$FAKE_PY" .venv/bin/python
fi
exit 0
"""

FAKE_PY = """#!/bin/bash
echo "py $*" >> "$FAKE_LOG"
if [ "$1" = -I ]; then echo "$FAKE_INSTALLED"; exit 0; fi
if [ "$1" = -m ]; then exit "${FAKE_PYTEST_RC:-0}"; fi
if [[ "$1" == *latest_core_smoke.py ]]; then
  echo "$FAKE_SMOKE_OUT"; exit "${FAKE_SMOKE_RC:-0}"
fi
exit 0
"""


def _workflow() -> dict[str, Any]:
    data = yaml.safe_load((WORKFLOWS / "consumer-check-reusable.yml").read_text())
    assert isinstance(data, dict)
    return data


def _step(name: str) -> str:
    steps = _workflow()["jobs"]["consumer"]["steps"]
    return next(s["run"] for s in steps if s["name"] == name)


def _matrix(consumer: str) -> dict[str, str]:
    include = _workflow()["jobs"]["consumer"]["strategy"]["matrix"]["include"]
    return next(m for m in include if m["consumer"] == consumer)


def _run(consumer: str, tmp_path: Path, **env: str) -> tuple[int, str, str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in (("git", FAKE_GIT), ("uv", FAKE_UV), ("fakepy", FAKE_PY)):
        path = bin_dir / name
        path.write_text(body)
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / "log"
    log.write_text("")
    matrix = _matrix(consumer)
    base = {
        "PATH": f"{bin_dir}:/usr/local/bin:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "FAKE_LOG": str(log),
        "FAKE_PY": str(bin_dir / "fakepy"),
        "FAKE_FAIL": "none-of-these",
        "FAKE_INSTALLED": SHA,
        "FAKE_SMOKE_OUT": "LATEST-CORE-SMOKE packages=3 modules_tried=40 failed=0",
        "GITHUB_SERVER_URL": "https://example.invalid",
        "CORE_SHA": SHA,
        "CORE_REPO": str(tmp_path / "core"),
        "CONSUMER": consumer,
        "SMOKE": matrix["smoke"],
        "TESTS": matrix["tests"],
        "WORK_DIR": str(tmp_path / "work"),
    }
    done = subprocess.run(
        ["bash", "-c", _step("Try the head in the consumer")],
        env={**base, **env},
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    return done.returncode, done.stdout, log.read_text()


def test_the_matrix_names_both_consumers_and_their_files() -> None:
    om, infra = _matrix("omnimarket"), _matrix("omnibase_infra")
    assert om["smoke"] == "tests/ci/latest_core_smoke.py"
    assert len(om["tests"].split()) == 3
    assert infra["tests"].split() == [
        "tests/integration/cli/test_onex_command_group_without_occ_omn20074.py",
        "tests/unit/test_smoke.py",
    ]


@pytest.mark.parametrize("consumer", ["omnimarket", "omnibase_infra"])
def test_head_installed_and_files_green_passes(consumer: str, tmp_path: Path) -> None:
    rc, out, _ = _run(consumer, tmp_path)
    assert rc == 0
    assert f"verdict=pass head={SHA}" in out


def test_install_is_locked_outside_the_project_with_no_config(tmp_path: Path) -> None:
    rc, _, log = _run("omnimarket", tmp_path)
    assert rc == 0
    assert "uv (cwd=" + str(tmp_path / "work" / "omnimarket") + ") sync --frozen" in log
    install = next(line for line in log.splitlines() if "--reinstall-package" in line)
    assert "--no-config" in install and "--no-deps" in install
    assert f"(cwd={tmp_path / 'work'})" in install
    assert f"@{SHA}" in install


def test_a_failing_consumer_test_fails_as_break(tmp_path: Path) -> None:
    rc, out, _ = _run("omnibase_infra", tmp_path, FAKE_PYTEST_RC="1")
    assert rc != 0
    assert "verdict=break step=tests" in out


def test_a_failing_smoke_fails_as_break(tmp_path: Path) -> None:
    rc, out, _ = _run("omnimarket", tmp_path, FAKE_SMOKE_RC="1")
    assert rc != 0
    assert "verdict=break step=smoke" in out


def test_a_smoke_that_imported_nothing_is_unread(tmp_path: Path) -> None:
    rc, out, _ = _run("omnimarket", tmp_path, FAKE_SMOKE_OUT="")
    assert rc != 0
    assert "verdict=unread reason=smoke-imported-nothing" in out


@pytest.mark.parametrize("failing", ["clone", "sync", "--reinstall-package"])
def test_a_step_that_did_not_run_fails_the_job(failing: str, tmp_path: Path) -> None:
    rc, out, _ = _run("omnimarket", tmp_path, FAKE_FAIL=failing)
    assert rc != 0
    assert "verdict=pass" not in out


def test_a_head_that_is_not_the_installed_one_is_unread(tmp_path: Path) -> None:
    rc, out, _ = _run("omnimarket", tmp_path, FAKE_INSTALLED="b" * 40)
    assert rc != 0
    assert "verdict=unread reason=head-not-installed" in out


def test_ci_calls_the_reusable_and_is_report_only() -> None:
    ci = yaml.safe_load((WORKFLOWS / "ci.yml").read_text())
    job = ci["jobs"]["consumer-check"]
    assert job["uses"] == "./.github/workflows/consumer-check-reusable.yml"
    assert job["with"]["core_sha"] == "${{ github.event.pull_request.head.sha }}"
    assert "pull_request" in job["if"]
    exclusions = json.loads(
        (REPO_ROOT / "scripts/ci/ci_summary_sweep_exclusions.json").read_text()
    )
    for name in ("omnimarket", "omnibase_infra"):
        entry = exclusions[f"Consumer Check / Consumer Check ({name})"]
        assert entry["ticket"] == "OMN-21592"
