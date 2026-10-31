# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A canonical-file-shape refusal ends a consumer's pre-commit run (OMN-21648).

The check itself takes seconds; the hook suite behind it takes minutes. A consumer
repository runs the hook from this repository's ``.pre-commit-hooks.yaml``, so the
manifest decides whether the suite keeps running after the check refuses. Each test
builds a consumer repository whose config names the real manifest through a local
hooks repository and overrides only the entry and language, so the manifest's own
``fail_fast`` is what the run obeys. A sentinel hook behind the check shows whether
the suite kept running.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)
from tests.unit.nodes.node_canonical_file_shape_check_compute.support import (
    git,
    init_repo,
    stage,
    write,
)

pytestmark = pytest.mark.unit

MANIFEST = Path(__file__).resolve().parents[4] / ".pre-commit-hooks.yaml"
HOOK_ID = "canonical-file-shape"
ENTRY = (
    f"{sys.executable} -m omnibase_core.nodes.node_canonical_file_shape_check_compute"
    ".runtime_canonical_file_shape_check"
)
SENTINEL = "sentinel_hook_ran"
LEGACY_HOOK = "plugins/p/hooks/lib/legacy_hook.py"
LEGACY_HOOK_TEXT = "# legacy hook\nA = 1\nB = 2\n\nC = 3\n"
REFUSED_RULE = "[baselined-file-growth]"


def _consumer(tmp_path: Path, fail_fast: bool | None) -> tuple[Path, dict[str, str]]:
    """A consumer repository with the real manifest, the check and a sentinel hook behind it."""
    hooks = tmp_path / "hooks_repo"
    hooks.mkdir(parents=True)
    (hooks / ".pre-commit-hooks.yaml").write_text(
        MANIFEST.read_text(encoding="utf-8"), encoding="utf-8"
    )
    git(hooks, "init", "-q", "-b", "dev")
    git(hooks, "add", "-A")
    git(hooks, "commit", "-q", "-m", "hooks")
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=hooks,
        env=scrub_git_location_env(),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    consumer = tmp_path / "consumer"
    consumer.mkdir(parents=True)
    write(consumer, LEGACY_HOOK, LEGACY_HOOK_TEXT)
    check_hook: dict[str, object] = {
        "id": HOOK_ID,
        "language": "system",
        "entry": ENTRY,
    }
    if fail_fast is not None:
        check_hook["fail_fast"] = fail_fast
    config = {
        "repos": [
            {"repo": str(hooks), "rev": revision, "hooks": [check_hook]},
            {
                "repo": "local",
                "hooks": [
                    {
                        "id": "sentinel",
                        "name": "sentinel",
                        "language": "system",
                        "entry": f"{sys.executable} -c \"open('{SENTINEL}', 'w').close()\"",
                        "pass_filenames": False,
                        "always_run": True,
                    }
                ],
            },
        ]
    }
    write(consumer, ".pre-commit-config.yaml", yaml.safe_dump(config, sort_keys=False))
    init_repo(consumer, baselined=[LEGACY_HOOK])
    env = scrub_git_location_env()
    env["PRE_COMMIT_HOME"] = str(tmp_path / "pre_commit_home")
    return consumer, env


def _run_hooks(consumer: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pre_commit", "run", "--color=never"],
        cwd=consumer,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _finding_lines(output: str) -> list[str]:
    return sorted(line.strip() for line in output.splitlines() if REFUSED_RULE in line)


def _grow_baselined_hook(consumer: Path) -> None:
    write(consumer, LEGACY_HOOK, LEGACY_HOOK_TEXT + "D = 4\n")
    stage(consumer)


def test_refusal_stops_later_hooks(tmp_path: Path) -> None:
    """A refused growth of a baselined script ends the run before the sentinel hook."""
    consumer, env = _consumer(tmp_path, fail_fast=None)
    _grow_baselined_hook(consumer)
    result = _run_hooks(consumer, env)
    assert result.returncode == 1, result.stdout + result.stderr
    assert not (consumer / SENTINEL).exists()


def test_refusal_result_unchanged(tmp_path: Path) -> None:
    """The exit status and the finding lines match a run that lets the suite continue."""
    stopped, stopped_env = _consumer(tmp_path / "stops", fail_fast=None)
    continued, continued_env = _consumer(tmp_path / "continues", fail_fast=False)
    for consumer in (stopped, continued):
        _grow_baselined_hook(consumer)
    stopped_run = _run_hooks(stopped, stopped_env)
    continued_run = _run_hooks(continued, continued_env)
    assert (continued / SENTINEL).exists()
    assert stopped_run.returncode == continued_run.returncode == 1
    findings = _finding_lines(stopped_run.stdout + stopped_run.stderr)
    assert findings
    assert findings == _finding_lines(continued_run.stdout + continued_run.stderr)


def test_admitted_change_runs_later_hooks(tmp_path: Path) -> None:
    """A change the check admits (a shrink) still runs the hooks behind it."""
    consumer, env = _consumer(tmp_path, fail_fast=None)
    write(consumer, LEGACY_HOOK, "# legacy hook\nA = 1\n")
    stage(consumer)
    result = _run_hooks(consumer, env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (consumer / SENTINEL).exists()
