# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-23527: the imperative contract guard names its validator ref and retries the fetch.

Measured 2026-11-10 10:50Z to 10:56Z: GitHub answered "API rate limit exceeded for
installation" to the validator checkout of six pull requests. The guard step never ran,
and the required check went red as if the caller's code were wrong. Two defects:

* the ref the checkout was given, ``github.job_workflow_sha``, is not a context that
  exists, so it evaluated empty and actions/checkout made a REST default-branch lookup
  on every run (the quota the burst then ran out of);
* nothing retried the fetch, and nothing said in the job summary that the red was a
  rate limit and not a finding.

These tests drive the steps' own ``run:`` text under bash with a fake ``git`` and a fake
``uv`` first on PATH, so a faked rate-limit answer, a faked server error, a refusal that
is neither, and a real guard violation are each exercised through the script the
workflow runs.
"""

from __future__ import annotations

import re
import stat
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "imperative-contract-guard.yml"
_CORE_REPOSITORY = "OmniNode-ai/omnibase_core"
_GOOD_SHA = "ab" * 20
_EMPTY_SPELLING = "github.job_workflow_sha"

_FAKE_GIT = """#!/usr/bin/env bash
# Fake git: logs every call; `fetch` behaves by FAKE_GIT_FETCH_MODE.
echo "$*" >> "$FAKE_GIT_LOG"
args=("$@")
sub=""
for ((i = 0; i < ${#args[@]}; i++)); do
  case "${args[$i]}" in
    fetch|rev-parse|checkout|init|remote|config) sub="${args[$i]}"; break ;;
  esac
done
case "$sub" in
  fetch)
    count_file="$FAKE_GIT_LOG.fetchcount"
    count=$(( $(cat "$count_file" 2>/dev/null || echo 0) + 1 ))
    echo "$count" > "$count_file"
    case "${FAKE_GIT_FETCH_MODE:-ok}" in
      ok) exit 0 ;;
      ratelimit)
        echo "remote: API rate limit exceeded for installation." >&2
        exit 128 ;;
      server)
        echo "fatal: unable to access 'https://github.com/x/': The requested URL returned error: 503" >&2
        exit 128 ;;
      notfound)
        echo "fatal: couldn't find remote ref deadbeef" >&2
        exit 128 ;;
      flaky)
        if [ "$count" -le 1 ]; then
          echo "remote: API rate limit exceeded for installation." >&2
          exit 128
        fi
        exit 0 ;;
    esac ;;
  rev-parse) echo "${FAKE_GIT_HEAD:-}" ;;
esac
exit 0
"""

_FAKE_UV = """#!/usr/bin/env bash
# Fake uv: `sync` succeeds; `run` (the guard command) exits FAKE_UV_RUN_EXIT.
echo "$*" >> "$FAKE_UV_LOG"
case "$1" in
  sync) exit 0 ;;
  run) exit "${FAKE_UV_RUN_EXIT:-0}" ;;
esac
exit 0
"""


def _load() -> dict[str, Any]:
    data = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _steps(data: dict[str, Any]) -> list[dict[str, Any]]:
    return data["jobs"]["imperative-contract-guard"]["steps"]


def _step_by_id(data: dict[str, Any], step_id: str) -> dict[str, Any]:
    (step,) = [s for s in _steps(data) if s.get("id") == step_id]
    return step


def _guard_step(data: dict[str, Any]) -> dict[str, Any]:
    (step,) = [
        s for s in _steps(data) if "check-imperative-contracts" in s.get("run", "")
    ]
    return step


def _non_comment_text(text: str) -> str:
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )


def _empty_spelling_present(text: str) -> bool:
    return _EMPTY_SPELLING in _non_comment_text(text)


def _install(directory: Path, name: str, body: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _run_step(
    tmp_path: Path,
    step: dict[str, Any],
    env: dict[str, str],
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    _install(bin_dir, "git", _FAKE_GIT)
    _install(bin_dir, "uv", _FAKE_UV)
    _install(bin_dir, "sleep", '#!/usr/bin/env bash\necho "$*" >> "$FAKE_SLEEP_LOG"\n')
    script = tmp_path / "step.sh"
    script.write_text(step["run"], encoding="utf-8")
    full_env = {
        "PATH": f"{bin_dir}:/usr/local/bin:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "FAKE_GIT_LOG": str(tmp_path / "git.log"),
        "FAKE_UV_LOG": str(tmp_path / "uv.log"),
        "FAKE_SLEEP_LOG": str(tmp_path / "sleep.log"),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary.md"),
        "GITHUB_OUTPUT": str(tmp_path / "output.txt"),
        "GITHUB_WORKSPACE": str(tmp_path),
        **env,
    }
    return subprocess.run(
        ["bash", str(script)],
        cwd=cwd or tmp_path,
        env=full_env,
        capture_output=True,
        text=True,
        check=False,
    )


def _fetch_env(tmp_path: Path, mode: str) -> dict[str, str]:
    return {
        "GH_TOKEN": "dummy",
        "GITHUB_SERVER_URL": "https://github.com",
        "VALIDATOR_REF": _GOOD_SHA,
        "VALIDATOR_REPOSITORY": _CORE_REPOSITORY,
        "VALIDATOR_DEST": str(tmp_path / "omnibase_core"),
        "FETCH_ATTEMPTS": "3",
        "FETCH_BACKOFF_SECONDS": "7",
        "FAKE_GIT_FETCH_MODE": mode,
        "FAKE_GIT_HEAD": _GOOD_SHA,
    }


def _fetch_calls(tmp_path: Path) -> int:
    count_file = tmp_path / "git.log.fetchcount"
    return int(count_file.read_text()) if count_file.exists() else 0


def _summary(tmp_path: Path) -> str:
    path = tmp_path / "summary.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


# --- the pin step -------------------------------------------------------------------


def _pin_env(sha: str, repository: str, override: str = "") -> dict[str, str]:
    return {
        "WORKFLOW_SHA": sha,
        "WORKFLOW_REPOSITORY": repository,
        "REF_OVERRIDE": override,
    }


def test_pin_step_refuses_an_empty_ref(tmp_path: Path) -> None:
    result = _run_step(
        tmp_path, _step_by_id(_load(), "pin"), _pin_env("", _CORE_REPOSITORY)
    )
    assert result.returncode == 1
    assert "THE GATE DID NOT RUN" in result.stdout


def test_pin_step_refuses_a_ref_that_is_not_40_hex(tmp_path: Path) -> None:
    result = _run_step(
        tmp_path, _step_by_id(_load(), "pin"), _pin_env("dev", _CORE_REPOSITORY)
    )
    assert result.returncode == 1
    assert "THE GATE DID NOT RUN" in result.stdout


def test_pin_step_refuses_a_workflow_from_another_repository(tmp_path: Path) -> None:
    result = _run_step(
        tmp_path, _step_by_id(_load(), "pin"), _pin_env(_GOOD_SHA, "OmniNode-ai/other")
    )
    assert result.returncode == 1


def test_pin_step_outputs_the_job_workflow_sha(tmp_path: Path) -> None:
    result = _run_step(
        tmp_path, _step_by_id(_load(), "pin"), _pin_env(_GOOD_SHA, _CORE_REPOSITORY)
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "output.txt").read_text().strip() == f"ref={_GOOD_SHA}"


def test_pin_step_explicit_override_wins(tmp_path: Path) -> None:
    result = _run_step(
        tmp_path,
        _step_by_id(_load(), "pin"),
        _pin_env("", _CORE_REPOSITORY, override="dev-20261018024445-b6ee996befa1"),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "output.txt").read_text().strip() == (
        "ref=dev-20261018024445-b6ee996befa1"
    )


# --- the fetch step -----------------------------------------------------------------


def test_fetch_succeeds_first_time_with_one_fetch(tmp_path: Path) -> None:
    result = _run_step(
        tmp_path, _step_by_id(_load(), "fetch"), _fetch_env(tmp_path, "ok")
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert _fetch_calls(tmp_path) == 1
    assert _summary(tmp_path) == ""


def test_fetch_rate_limit_is_retried_then_fails_and_says_so(tmp_path: Path) -> None:
    result = _run_step(
        tmp_path, _step_by_id(_load(), "fetch"), _fetch_env(tmp_path, "ratelimit")
    )
    assert result.returncode == 1
    assert _fetch_calls(tmp_path) == 3
    sleeps = (tmp_path / "sleep.log").read_text().split()
    assert sleeps == ["7", "14"], "exponential backoff between the three attempts"
    summary = _summary(tmp_path)
    assert "rate limit" in summary
    assert "did not run" in summary
    assert "NOT a finding" in summary


def test_fetch_server_error_is_retried_then_fails_and_says_so(tmp_path: Path) -> None:
    result = _run_step(
        tmp_path, _step_by_id(_load(), "fetch"), _fetch_env(tmp_path, "server")
    )
    assert result.returncode == 1
    assert _fetch_calls(tmp_path) == 3
    assert "did not run" in _summary(tmp_path)


def test_fetch_that_recovers_passes_after_a_retry(tmp_path: Path) -> None:
    result = _run_step(
        tmp_path, _step_by_id(_load(), "fetch"), _fetch_env(tmp_path, "flaky")
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert _fetch_calls(tmp_path) == 2


def test_fetch_failure_that_is_not_a_rate_limit_fails_at_once_without_a_retry(
    tmp_path: Path,
) -> None:
    result = _run_step(
        tmp_path, _step_by_id(_load(), "fetch"), _fetch_env(tmp_path, "notfound")
    )
    assert result.returncode == 1
    assert _fetch_calls(tmp_path) == 1
    assert not (tmp_path / "sleep.log").exists()
    assert "rate limit" not in _summary(tmp_path)
    assert "THE GATE DID NOT RUN" in result.stdout


def test_fetch_checked_out_at_the_wrong_commit_fails(tmp_path: Path) -> None:
    env = _fetch_env(tmp_path, "ok")
    env["FAKE_GIT_HEAD"] = "f" * 40
    result = _run_step(tmp_path, _step_by_id(_load(), "fetch"), env)
    assert result.returncode == 1
    assert "expected" in result.stdout


# --- a real violation still fails exactly as before -----------------------------------


def _guard_env(run_exit: int) -> dict[str, str]:
    return {
        "UV_SYNC_ATTEMPTS": "1",
        "UV_SYNC_RETRY_DELAY_SECONDS": "0",
        "ALLOWLIST_PATH": "imperative-contract-allowlist.yaml",
        "RATCHET_BASE_REF": "",
        "SCAN_FREESTANDING": "true",
        "FAKE_UV_RUN_EXIT": str(run_exit),
    }


def test_guard_step_fails_when_the_guard_reports_a_violation(tmp_path: Path) -> None:
    (tmp_path / "omnibase_core").mkdir()
    (tmp_path / "target").mkdir()
    result = _run_step(
        tmp_path,
        _guard_step(_load()),
        _guard_env(1),
        cwd=tmp_path / "omnibase_core",
    )
    assert result.returncode == 1
    assert "check-imperative-contracts" in (tmp_path / "uv.log").read_text()


def test_guard_step_passes_when_the_guard_is_clean(tmp_path: Path) -> None:
    (tmp_path / "omnibase_core").mkdir()
    (tmp_path / "target").mkdir()
    result = _run_step(
        tmp_path,
        _guard_step(_load()),
        _guard_env(0),
        cwd=tmp_path / "omnibase_core",
    )
    assert result.returncode == 0, result.stdout + result.stderr


# --- structure --------------------------------------------------------------------------


def test_workflow_no_longer_uses_the_empty_context_spelling() -> None:
    assert not _empty_spelling_present(WORKFLOW_PATH.read_text(encoding="utf-8"))


def test_empty_spelling_check_has_a_positive_control() -> None:
    mutated = WORKFLOW_PATH.read_text(encoding="utf-8").replace(
        "${{ steps.pin.outputs.ref }}",
        "${{ inputs['omnibase-core-ref'] || github.job_workflow_sha }}",
        1,
    )
    assert _empty_spelling_present(mutated)


def test_validator_is_fetched_only_by_the_retried_step() -> None:
    steps = _steps(_load())
    checkouts = [
        s for s in steps if str(s.get("uses", "")).startswith("actions/checkout@")
    ]
    assert [c.get("with", {}).get("repository") for c in checkouts] == [None]
    assert _step_by_id(_load(), "fetch")["env"]["VALIDATOR_REPOSITORY"] == (
        _CORE_REPOSITORY
    )


def test_no_step_may_soften_a_failure() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "continue-on-error" not in text
    assert not re.search(r"\|\|\s*true", _non_comment_text(text))


def test_step_order_resolves_the_pin_before_the_fetch_before_the_guard() -> None:
    names = [s.get("name", "") for s in _steps(_load())]
    pin = names.index("Resolve the omnibase_core validator pin")
    fetch = names.index(
        "Fetch the omnibase_core validator (retried on a rate limit or 5xx)"
    )
    guard = names.index("Run imperative contract guard")
    assert names.index("Checkout target repository") < pin < fetch < guard
