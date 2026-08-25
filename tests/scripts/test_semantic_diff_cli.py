# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for scripts/analysis/semantic_diff.py CLI (OMN-10375)."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI = REPO_ROOT / "scripts" / "analysis" / "semantic_diff.py"

# Every test here shells out to the CLI, which builds the repo-wide consumer
# graph. Pinning the module to one xdist group makes --dist=loadgroup run them
# on a single worker, so the first pays the cold-cache build once and the rest
# reuse it. Fanning them across workers is what drove four simultaneous cold
# builds past the 60s per-test timeout and killed the run (OMN-15431).
pytestmark = pytest.mark.xdist_group("semantic_diff_cli")

# Ensure the worktree src takes precedence when running subprocess CLI calls.
# The editable .pth install may resolve to the canonical clone if it appears
# earlier on sys.path, which lacks not-yet-merged subpackages from stacked branches.
_WORKTREE_SRC = str(REPO_ROOT / "src")
_SUBPROCESS_ENV = {
    **os.environ,
    "PYTHONPATH": _WORKTREE_SRC + os.pathsep + os.environ.get("PYTHONPATH", ""),
}


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: PLW1510
        [sys.executable, str(CLI), *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=_SUBPROCESS_ENV,
    )


def _git(repo: Path, *args: str) -> None:
    """Run one git command in repo with the location overrides scrubbed.

    GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE are exported into every hook process
    and override both cwd= and -C, so an unscrubbed call here would retarget the
    real invoking worktree instead of repo (OMN-14891).
    """
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        env={
            **scrub_git_location_env(os.environ),
            "GIT_AUTHOR_NAME": "test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        },
    )


def _load_cli_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("semantic_diff_cli", CLI)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def cli_json_run() -> subprocess.CompletedProcess[str]:
    """One real CLI run over the branch's real diff, shared by the assertions below.

    Four tests previously issued this identical invocation, so the CLI analysed
    the same (large) diff four times over. They assert different properties of
    one run, not four different runs, so running it once is the same coverage at
    a quarter of the cost -- and the run is still a real subprocess against the
    real non-empty diff, so nothing here becomes a no-op (OMN-15431).
    """
    return _run_cli("--base", "origin/main", "--head", "HEAD", "--json")


@pytest.mark.unit
def test_cli_exits_0_with_json_flag(
    cli_json_run: subprocess.CompletedProcess[str],
) -> None:
    """CLI exits 0 even when critical changes are detected (advisory mode)."""
    assert cli_json_run.returncode == 0, f"stderr: {cli_json_run.stderr}"


@pytest.mark.unit
def test_cli_json_output_validates_against_model(
    cli_json_run: subprocess.CompletedProcess[str],
) -> None:
    """JSON output validates against ModelSemanticDiffReport via a subprocess round-trip."""
    # Validate via subprocess so the worktree src path takes precedence cleanly.
    # In-process import resolves to the editable-installed canonical clone which
    # lacks not-yet-merged subpackages from stacked branches.
    assert cli_json_run.returncode == 0, f"stderr: {cli_json_run.stderr}"

    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        f.write(cli_json_run.stdout)
        tmp_path = f.name

    validate_script = (
        "import sys, json;"
        f"sys.path.insert(0, {_WORKTREE_SRC!r});"
        "from omnibase_core.models.analysis.model_semantic_diff_report import ModelSemanticDiffReport;"
        f"data = json.load(open({tmp_path!r}));"
        "r = ModelSemanticDiffReport.model_validate(data);"
        "assert isinstance(r.changes, tuple);"
        "assert isinstance(r.total_consumers_affected, int);"
        "print('ok')"
    )
    val_result = subprocess.run(  # noqa: PLW1510
        [sys.executable, "-c", validate_script],
        capture_output=True,
        text=True,
        env=_SUBPROCESS_ENV,
    )
    Path(tmp_path).unlink(missing_ok=True)
    assert val_result.returncode == 0, f"Validation failed: {val_result.stderr}"
    assert val_result.stdout.strip() == "ok"


@pytest.mark.unit
def test_cli_json_has_required_fields(
    cli_json_run: subprocess.CompletedProcess[str],
) -> None:
    """JSON output has changes list and total_consumers_affected."""
    assert cli_json_run.returncode == 0, f"stderr: {cli_json_run.stderr}"
    payload = json.loads(cli_json_run.stdout)
    assert "changes" in payload
    assert "total_consumers_affected" in payload
    assert isinstance(payload["changes"], list)
    assert isinstance(payload["total_consumers_affected"], int)


@pytest.mark.unit
def test_cli_missing_required_args_exits_nonzero() -> None:
    """CLI exits non-zero when required --base / --head args are absent."""
    result = _run_cli("--json")
    assert result.returncode != 0


@pytest.mark.unit
def test_compute_report_skips_consumer_graph_when_no_changed_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No-diff runs should not build the expensive full-repo consumer graph."""
    module = _load_cli_module()

    monkeypatch.setattr(
        module,
        "_git_changed_py_files",
        lambda _base, _head, _repo_root: [],
    )

    def fail_build_consumer_graph(_repo_root: Path) -> dict[str, int]:
        raise AssertionError("consumer graph should not be built for an empty diff")

    monkeypatch.setattr(module, "build_consumer_graph", fail_build_consumer_graph)

    report = module._compute_report("origin/main", "HEAD", REPO_ROOT)

    assert report.changes == ()
    assert report.total_consumers_affected == 0


@pytest.mark.unit
def test_cli_unavailable_base_ref_emits_empty_advisory_report() -> None:
    """CLI stays advisory when a shallow checkout lacks the requested base ref."""
    result = _run_cli(
        "--base", "refs/heads/omn-missing-base", "--head", "HEAD", "--json"
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "base ref" in result.stderr
    payload = json.loads(result.stdout)
    assert payload == {"changes": [], "total_consumers_affected": 0}


@pytest.mark.unit
def test_cli_json_change_fields(
    cli_json_run: subprocess.CompletedProcess[str],
) -> None:
    """Each change entry has the required fields."""
    assert cli_json_run.returncode == 0
    payload = json.loads(cli_json_run.stdout)
    for change in payload["changes"]:
        assert "kind" in change
        assert "severity" in change
        assert "symbol_name" in change
        assert "file_path" in change
        assert "consumers_count" in change


@pytest.mark.unit
def test_compute_report_detects_changes_for_a_non_empty_python_diff(
    tmp_path: Path,
) -> None:
    """A non-empty Python diff must still reach the consumer graph and report changes.

    Counterpart to the empty-diff skip test above, and the guard that keeps this
    suite fix-discriminating: the cold-cache crash (OMN-15431) would also "go
    away" if the CLI stopped analysing real diffs or stopped building the graph,
    so both must be asserted, not just that the run finished.
    """
    module = _load_cli_module()

    target = tmp_path / "mod.py"
    target.write_text(
        "def kept() -> int:\n    return 1\n\n\ndef dropped() -> int:\n    return 2\n",
        encoding="utf-8",
    )
    (tmp_path / "consumer.py").write_text("import mod\n", encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "base", "--no-gpg-sign")
    _git(tmp_path, "branch", "-f", "base-ref")

    target.write_text("def kept() -> int:\n    return 1\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "drop a function", "--no-gpg-sign")

    graph_calls: list[Path] = []
    real_build = module.build_consumer_graph

    def recording_build(repo_root: Path) -> dict[str, int]:
        graph_calls.append(repo_root)
        return real_build(repo_root)

    module.build_consumer_graph = recording_build

    report = module._compute_report("base-ref", "HEAD", tmp_path)

    # The expensive path is exercised, not short-circuited...
    assert graph_calls == [tmp_path]
    # ...and the deleted symbol is actually surfaced.
    assert report.changes, "non-empty diff produced no changes"
    assert "dropped" in {change.symbol_name for change in report.changes}
    # consumer.py imports mod.py, so the affected-consumer count is real.
    assert report.total_consumers_affected == 1


@pytest.mark.unit
def test_git_files_at_batches_reads_and_reports_missing_blobs(tmp_path: Path) -> None:
    """One batched git process must return exactly what per-file reads returned.

    Content has to survive the batch framing intact (header, payload, trailing
    newline), and a path absent at a ref must still come back as "" rather than
    shifting every later blob in the stream.
    """
    module = _load_cli_module()

    first = "def one() -> int:\n    return 1\n"
    second = "x = 'héllo'\n\n\ndef two() -> int:\n    return 2\n"
    (tmp_path / "one.py").write_text(first, encoding="utf-8")
    (tmp_path / "two.py").write_text(second, encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "seed", "--no-gpg-sign")

    sources = module._git_files_at(
        tmp_path,
        [
            ("HEAD", "one.py"),
            ("HEAD", "absent.py"),
            ("HEAD", "two.py"),
        ],
    )

    assert sources[("HEAD", "one.py")] == first
    # A missing blob must not desynchronise the blobs that follow it.
    assert sources[("HEAD", "absent.py")] == ""
    assert sources[("HEAD", "two.py")] == second


@pytest.mark.unit
def test_git_files_at_survives_a_newline_inside_a_tracked_path(tmp_path: Path) -> None:
    """A newline in a path must not split one request into two and desync the stream.

    git permits a newline inside a path. A newline-framed ``git cat-file
    --batch`` request stream turns such a path into two requests, so every
    response after it is read against the wrong header and unrelated files come
    back corrupted or empty -- a regression the per-file ``git show`` shape this
    batching replaced could not have. The batch reader must be NUL-framed.

    This covers the PRESENT-blob half only: ``-z`` frames stdin, which is what
    this case needs. The absent-blob half re-injects the newline on git's
    LF-framed STDOUT and is a separate defect, pinned by the sibling test
    :func:`test_git_files_at_survives_a_newline_inside_a_missing_path`.
    """
    module = _load_cli_module()

    weird_rel = "we\nird.py"
    after = "AFTER = 2\n"
    (tmp_path / weird_rel).write_text("WEIRD = 1\n", encoding="utf-8")
    (tmp_path / "after.py").write_text(after, encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "seed", "--no-gpg-sign")

    sources = module._git_files_at(
        tmp_path,
        [("HEAD", weird_rel), ("HEAD", "after.py")],
    )

    assert sources[("HEAD", weird_rel)] == "WEIRD = 1\n"
    # The real regression: the blob AFTER the newline-bearing path.
    assert sources[("HEAD", "after.py")] == after


@pytest.mark.unit
def test_git_files_at_survives_a_newline_inside_a_missing_path(tmp_path: Path) -> None:
    """A newline in an ABSENT path must not desync the blobs that follow it either.

    ``-z`` frames stdin only; git's stdout stays LF-framed (``-Z`` needs git
    >= 2.42, the fleet runs 2.39). git answers an unresolvable name by echoing
    the request VERBATIM plus " missing", so a newline-bearing absent path puts
    its own newline back into the response stream. Scanning for the next LF
    splits that echo, burns an extra response slot, and silently loses the
    FOLLOWING blob -- the response must be matched against the request instead.

    Not exotic: ``_compute_report`` requests every changed path at both base and
    head, so every added or deleted file is a missing-blob request.
    """
    module = _load_cli_module()

    weird_rel = "we\nird.py"
    after = "AFTER = 2\n"
    # Only after.py is committed, so weird_rel is MISSING at HEAD.
    (tmp_path / "after.py").write_text(after, encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "seed", "--no-gpg-sign")

    sources = module._git_files_at(
        tmp_path,
        [("HEAD", weird_rel), ("HEAD", "after.py")],
    )

    assert sources[("HEAD", weird_rel)] == ""
    # The regression: the blob after a MISSING newline-bearing path.
    assert sources[("HEAD", "after.py")] == after


@pytest.mark.unit
def test_git_files_at_warns_instead_of_silently_emptying_the_whole_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed git process must say so, not masquerade as a clean diff.

    One non-zero exit resolves EVERY blob to "", so ``compute_diff`` reports no
    semantic changes for the whole diff -- byte-identical to a genuinely clean
    result. The per-file ``git show`` shape this batching replaced could only
    lose one file at a time, so batching made a silent failure global.
    """
    module = _load_cli_module()

    # GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE are exported into hook processes and
    # override cwd=, which would retarget this call at a REAL repo and make it
    # succeed (OMN-14891).
    for var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(var, raising=False)

    # Not a git repository, so no git process can resolve anything: a real
    # process-level failure, not a simulated one.
    sources = module._git_files_at(tmp_path, [("HEAD", "one.py")])

    assert sources == {}
    assert "failed; emitting empty advisory report" in capsys.readouterr().err


@pytest.mark.unit
def test_git_files_at_needs_no_cat_file_switch_newer_than_the_runner_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The batched read must work on the git 2.34.1 the self-hosted runners ship.

    The OMN-15431 batching passed ``cat-file --batch -z`` to NUL-frame its
    requests. That switch does not exist on git 2.34.1, so on every dev push
    run ``cat-file`` exited 129 with ``error: unknown switch `z'``, every blob
    resolved to "", and ``_compute_report`` reported "no semantic changes" for
    genuinely non-empty diffs (OMN-16347: five failures in this module, one of
    them a false negative in a change-analysis surface). Developer machines run
    a newer git, so the plain suite cannot see this; the fake below refuses the
    NUL-framing switches exactly as the runner's git does, and the read must
    still succeed -- newline-bearing path included, since that path is the
    whole reason ``-z`` was reached for.
    """
    module = _load_cli_module()

    weird_rel = "we\nird.py"
    after = "AFTER = 2\n"
    (tmp_path / weird_rel).write_text("WEIRD = 1\n", encoding="utf-8")
    (tmp_path / "after.py").write_text(after, encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "seed", "--no-gpg-sign")

    real_run = subprocess.run
    cat_file_calls: list[list[str]] = []

    def git_2_34_run(
        argv: list[str], **kwargs: Any
    ) -> subprocess.CompletedProcess[bytes]:
        if argv[:2] == ["git", "cat-file"]:
            cat_file_calls.append(argv)
            if {"-z", "-Z", "--batch-command"} & set(argv):
                return subprocess.CompletedProcess(
                    argv, 129, b"", b"error: unknown switch `z'\n"
                )
        return real_run(argv, **kwargs)

    monkeypatch.setattr(module.subprocess, "run", git_2_34_run)

    sources = module._git_files_at(
        tmp_path,
        [("HEAD", weird_rel), ("HEAD", "absent.py"), ("HEAD", "after.py")],
    )

    assert cat_file_calls, "the batched read no longer reads blobs through cat-file"
    assert sources[("HEAD", weird_rel)] == "WEIRD = 1\n"
    assert sources[("HEAD", "absent.py")] == ""
    assert sources[("HEAD", "after.py")] == after


@pytest.mark.unit
def test_git_files_at_normalises_newlines_like_the_previous_per_file_read(
    tmp_path: Path,
) -> None:
    """CRLF/CR blobs must arrive LF-normalised, as universal-newline reads gave.

    The replaced ``git show`` call used ``text=True``, so callers have always
    seen LF. Reading raw bytes out of the batch stream would hand ``compute_diff``
    CRLF instead; this pins the translation rather than leaving it incidental.
    """
    module = _load_cli_module()

    (tmp_path / "crlf.py").write_bytes(b"a = 1\r\nb = 2\r\n")
    (tmp_path / "cr.py").write_bytes(b"a = 1\rb = 2\r")
    _git(tmp_path, "init", "-q")
    # -A with core.autocrlf unset stores the bytes verbatim; pin it so a global
    # ~/.gitconfig cannot normalise the fixture out from under the assertion.
    _git(tmp_path, "config", "core.autocrlf", "false")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "seed", "--no-gpg-sign")

    sources = module._git_files_at(
        tmp_path,
        [("HEAD", "crlf.py"), ("HEAD", "cr.py")],
    )

    assert sources[("HEAD", "crlf.py")] == "a = 1\nb = 2\n"
    assert sources[("HEAD", "cr.py")] == "a = 1\nb = 2\n"


@pytest.mark.unit
def test_git_files_at_returns_empty_for_no_requests(tmp_path: Path) -> None:
    """No requested blobs means no git process at all."""
    module = _load_cli_module()

    assert module._git_files_at(tmp_path, []) == {}
