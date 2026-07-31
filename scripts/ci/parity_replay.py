# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Executed-parity engine for the canonical-shape flip gate (OMN-15340).

"RED to GREEN for the right reason" was prose until this module existed: nothing in
CI ever executed a candidate test against the PRE-change tree. The hand-flip proof
path (``canonical_handler_shape.verify_handflip_proof``) read a self-authored
``parity.status == "pass"`` string and counted ``parity.test_ids`` without ever
running them — on either tree. Two failure modes were therefore invisible:

1. the declared parity tests are not green on HEAD (the string is fabricated); and
2. the declared parity tests are ALREADY GREEN on the pre-change tree — they do not
   discriminate the flip at all, so their green run proves nothing about the
   def-A -> def-B behavior transfer.

This module executes them. Two entry points:

* :func:`run_on_head` — run the declared ids against the working tree; every id must
  PASS. Consumed by ``canonical_handler_shape``'s default parity executor, which is
  what replaces the credited-but-unexecuted ``status`` string.
* :func:`red_on_base` — materialize the receipt's OWN ``base_ref`` as a detached git
  worktree, overlay the HEAD copies of the declared test files onto that pre-change
  tree, and require every declared id to be RED **on its own assertion**.

Exit reasons are distinguished, never collapsed into "non-zero" (see
:class:`EnumParityOutcome`). A test that cannot even import on the base tree proves
nothing — an ``ImportError`` at collection is the same evidence as no test at all, so
it is rejected with its own reason rather than counted as RED. Likewise a call-phase
``AttributeError`` is NOT an assertion: it is indistinguishable from a test that is
merely incompatible with the base tree, so the discriminating claim must be asserted
(``AssertionError``/``pytest.fail``) to count.

Non-vacuity (the load-bearing part): the base-tree run only means something if the
BASE source is the source actually imported. A canonical clone's editable install
resolves the package to the HEAD tree, so a base run that silently imports HEAD
source is a vacuous RED/GREEN either way. :func:`red_on_base` prepends the base
worktree's source root to ``PYTHONPATH`` and then PROBES the legacy handler module's
resolved ``__file__``, failing closed unless it lives under the base worktree.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Sequence
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict

#: A failure whose junit ``message`` starts with one of these is the test's OWN
#: assertion (``pytest.fail`` raises ``Failed``, which is an explicit assertion).
#: Anything else that reaches the ``<failure>`` element (AttributeError, TypeError,
#: ...) is a non-assertion exception and is reported as its own outcome class.
ASSERTION_MESSAGE_PREFIXES: tuple[str, ...] = ("AssertionError", "Failed:", "Failed\n")

#: Per-test subprocess ceiling. A hung parity test must fail the gate, not hang CI.
DEFAULT_TEST_TIMEOUT_S = 300

#: Git env keys that silently retarget a subprocess at another repository
#: (memory ``reference_git_env_vars_override_c_and_cwd``); pre-commit exports several
#: of these, so every git call here runs with them stripped.
_GIT_ENV_BLOCKLIST: tuple[str, ...] = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_COMMON_DIR",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
)


class EnumParityOutcome(str, Enum):
    """What actually happened when one declared parity test id was executed."""

    PASSED = "passed"
    RED_ASSERTION = "red_assertion"  # ran; failed on its OWN assertion
    RED_EXCEPTION = "red_exception"  # ran; failed on a non-assertion exception
    SKIPPED = "skipped"
    COLLECTION_ERROR = "collection_error"  # could not import/collect (proves nothing)
    NOT_COLLECTED = "not_collected"  # the id does not exist in that tree
    RUNNER_ERROR = "runner_error"  # pytest could not be launched / timed out


class ModelParityTestResult(BaseModel):
    """One declared parity test id's executed outcome on one tree."""

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    # A pytest node id ("path::test[param]") is pytest's own identifier format, not
    # an ONEX entity id — a UUID here would name nothing runnable.
    # string-id-ok: external (pytest) identifier format
    test_id: str
    outcome: EnumParityOutcome
    detail: str


class ModelParityRun(BaseModel):
    """The executed verdict over a receipt's declared ``parity.test_ids``."""

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    tree: str
    executed: bool
    results: tuple[ModelParityTestResult, ...]
    detail: str

    @property
    def all_passed(self) -> bool:
        return bool(self.results) and all(
            r.outcome is EnumParityOutcome.PASSED for r in self.results
        )

    @property
    def all_red_on_assertion(self) -> bool:
        return bool(self.results) and all(
            r.outcome is EnumParityOutcome.RED_ASSERTION for r in self.results
        )

    def offenders(
        self, accepted: EnumParityOutcome
    ) -> tuple[ModelParityTestResult, ...]:
        return tuple(r for r in self.results if r.outcome is not accepted)


# --------------------------------------------------------------------------- #
# Process primitives
# --------------------------------------------------------------------------- #


def _git_env() -> dict[str, str]:
    env = dict(os.environ)
    for key in _GIT_ENV_BLOCKLIST:
        env.pop(key, None)
    return env


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=False,
        env=_git_env(),
    )


def resolve_interpreter(repo_root: Path) -> Path:
    """The target repo's own venv python when present, else this interpreter.

    The BASE tree carries no installed environment of its own, so dependencies come
    from the target repo's venv while the SOURCE comes from the base worktree via
    ``PYTHONPATH`` (proven by the residency probe). The assertion is about the source
    transition, not about dependency pinning.
    """
    candidate = repo_root / ".venv" / "bin" / "python"
    if candidate.exists():
        return candidate
    return Path(sys.executable)


#: Inherited env that would silently reconfigure the inner pytest run. ``PYTEST_ADDOPTS``
#: is the dangerous one: an ambient ``--reruns`` can turn the RED being measured into a
#: PASS, and ``PYTHONPATH`` leftovers can shadow the tree under test.
_RUN_ENV_BLOCKLIST: tuple[str, ...] = (
    "PYTHONPATH",
    "PYTHONHOME",
    "PYTEST_ADDOPTS",
    "PYTEST_PLUGINS",
    "PYTEST_CURRENT_TEST",
    "PYTEST_XDIST_WORKER",
    "PYTEST_XDIST_WORKER_COUNT",
)


def _run_env(source_root: Path) -> dict[str, str]:
    blocked = set(_RUN_ENV_BLOCKLIST) | set(_GIT_ENV_BLOCKLIST)
    env = {k: v for k, v in os.environ.items() if k not in blocked}
    env["PYTHONPATH"] = str(source_root)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


# --------------------------------------------------------------------------- #
# One test id -> one typed outcome
# --------------------------------------------------------------------------- #


def _classify_junit(
    xml_path: Path, test_id: str, returncode: int
) -> ModelParityTestResult:
    """Map one single-id pytest run to a typed outcome.

    Single-id invocation is deliberate: a collection error aborts a whole pytest
    session (``Interrupted``), so batching ids would let one broken file mask every
    other id's real outcome. One id per process makes each verdict independent.
    """
    if not xml_path.exists():
        return ModelParityTestResult(
            test_id=test_id,
            outcome=EnumParityOutcome.NOT_COLLECTED,
            detail=(
                f"pytest produced no report for {test_id!r} (rc={returncode}) — the id "
                f"does not exist in that tree"
            ),
        )
    try:
        # Suppression rationale mirrors scripts/ci/test_selection_shadow.py: the
        # document is the junit report the pytest process launched two frames up just
        # wrote into a private temp dir — it is not untrusted input.
        root = ET.parse(xml_path).getroot()  # noqa: S314 (self-produced junit report)
    except ET.ParseError as exc:
        return ModelParityTestResult(
            test_id=test_id,
            outcome=EnumParityOutcome.RUNNER_ERROR,
            detail=f"unparseable junit report: {exc}",
        )
    cases = list(root.iter("testcase"))
    if not cases:
        return ModelParityTestResult(
            test_id=test_id,
            outcome=EnumParityOutcome.NOT_COLLECTED,
            detail=f"no testcase recorded for {test_id!r} (rc={returncode})",
        )
    case = cases[0]
    for child in case:
        message = (child.get("message") or "").strip()
        if child.tag == "error":
            return ModelParityTestResult(
                test_id=test_id,
                outcome=EnumParityOutcome.COLLECTION_ERROR,
                detail=f"collection/setup error: {message[:200]}",
            )
        if child.tag == "skipped":
            return ModelParityTestResult(
                test_id=test_id,
                outcome=EnumParityOutcome.SKIPPED,
                detail=f"skipped: {message[:200]}",
            )
        if child.tag == "failure":
            if message.startswith(ASSERTION_MESSAGE_PREFIXES):
                return ModelParityTestResult(
                    test_id=test_id,
                    outcome=EnumParityOutcome.RED_ASSERTION,
                    detail=f"failed on its own assertion: {message[:200]}",
                )
            return ModelParityTestResult(
                test_id=test_id,
                outcome=EnumParityOutcome.RED_EXCEPTION,
                detail=(
                    f"failed on a NON-assertion exception: {message[:200]} — an "
                    f"exception is not a discriminating claim; assert it"
                ),
            )
    return ModelParityTestResult(
        test_id=test_id,
        outcome=EnumParityOutcome.PASSED,
        detail="passed",
    )


def run_test_id(
    test_id: str,
    *,
    interpreter: Path,
    cwd: Path,
    env: dict[str, str],
    timeout: int = DEFAULT_TEST_TIMEOUT_S,
) -> ModelParityTestResult:
    """Execute exactly one pytest id and classify its outcome.

    ``-o addopts=`` neutralizes the repo's ini addopts (xdist / reruns / coverage),
    which would otherwise make a single-id verdict non-deterministic — a ``--reruns``
    retry can turn a RED into a PASS, and that is the exact signal being measured.
    """
    report_dir = Path(tempfile.mkdtemp(prefix="parity-junit-"))
    xml_path = report_dir / "report.xml"
    argv = [
        str(interpreter),
        "-m",
        "pytest",
        test_id,
        "-o",
        "addopts=",
        "-p",
        "no:cacheprovider",
        "-p",
        "no:randomly",
        "--continue-on-collection-errors",
        f"--junitxml={xml_path}",
        "-q",
    ]
    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
            env=env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        shutil.rmtree(report_dir, ignore_errors=True)
        return ModelParityTestResult(
            test_id=test_id,
            outcome=EnumParityOutcome.RUNNER_ERROR,
            detail=f"timed out after {timeout}s",
        )
    except OSError as exc:
        shutil.rmtree(report_dir, ignore_errors=True)
        return ModelParityTestResult(
            test_id=test_id,
            outcome=EnumParityOutcome.RUNNER_ERROR,
            detail=f"pytest could not be launched: {exc}",
        )
    try:
        return _classify_junit(xml_path, test_id, proc.returncode)
    finally:
        shutil.rmtree(report_dir, ignore_errors=True)


def _run_ids(
    test_ids: Sequence[str],
    *,
    interpreter: Path,
    cwd: Path,
    source_root: Path,
    tree: str,
    timeout: int,
) -> ModelParityRun:
    env = _run_env(source_root)
    results = tuple(
        run_test_id(test_id, interpreter=interpreter, cwd=cwd, env=env, timeout=timeout)
        for test_id in test_ids
    )
    return ModelParityRun(
        tree=tree,
        executed=True,
        results=results,
        detail=f"{len(results)} declared parity id(s) executed against the {tree} tree",
    )


# --------------------------------------------------------------------------- #
# HEAD side — "run them or reject them"
# --------------------------------------------------------------------------- #


def run_on_head(
    repo_root: Path,
    source_root: Path,
    test_ids: Sequence[str],
    *,
    timeout: int = DEFAULT_TEST_TIMEOUT_S,
) -> ModelParityRun:
    """Execute the declared ids against the working tree; all must PASS.

    ``PYTHONPATH`` is pinned to ``source_root`` even here: inside a git worktree the
    canonical clone's editable ``.pth`` otherwise resolves the package to the
    CANONICAL checkout, so the run would grade a tree nobody edited
    (memory ``reference_pythonpath_shadows_worktree_source``).
    """
    if not test_ids:
        return ModelParityRun(
            tree="head",
            executed=False,
            results=(),
            detail="no parity test ids declared",
        )
    return _run_ids(
        test_ids,
        interpreter=resolve_interpreter(repo_root),
        cwd=repo_root,
        source_root=source_root,
        tree="head",
        timeout=timeout,
    )


# --------------------------------------------------------------------------- #
# BASE side — the RED-for-the-right-reason mechanism
# --------------------------------------------------------------------------- #


def _test_files(test_ids: Iterable[str]) -> list[str]:
    seen: list[str] = []
    for test_id in test_ids:
        rel = test_id.split("::", 1)[0].strip()
        if rel and rel not in seen:
            seen.append(rel)
    return seen


def _ensure_ref(repo_root: Path, base_ref: str) -> bool:
    if (
        _git(
            repo_root, "rev-parse", "--verify", "--quiet", f"{base_ref}^{{commit}}"
        ).returncode
        == 0
    ):
        return True
    # Shallow CI checkouts legitimately lack an older receipt base_ref; try once to
    # fetch exactly it before failing closed.
    _git(repo_root, "fetch", "--no-tags", "--depth=1", "origin", base_ref)
    return (
        _git(
            repo_root, "rev-parse", "--verify", "--quiet", f"{base_ref}^{{commit}}"
        ).returncode
        == 0
    )


def _probe_source_residency(
    module: str,
    *,
    interpreter: Path,
    cwd: Path,
    env: dict[str, str],
    expected_root: Path,
) -> tuple[bool, str]:
    """Prove the module the tests will import resolves INSIDE ``expected_root``."""
    script = (
        "import importlib.util,sys\n"
        f"spec = importlib.util.find_spec({module!r})\n"
        "print(spec.origin if spec is not None else '')\n"
    )
    try:
        proc = subprocess.run(
            [str(interpreter), "-c", script],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
            env=env,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"residency probe could not run: {exc}"
    origin = proc.stdout.strip().splitlines()[-1].strip() if proc.stdout.strip() else ""
    if not origin:
        return (
            False,
            f"{module} does not resolve on the base tree "
            f"({(proc.stderr or '').strip()[:200]})",
        )
    try:
        Path(origin).resolve().relative_to(expected_root.resolve())
    except ValueError:
        return (
            False,
            f"VACUOUS BASE RUN — {module} resolved to {origin}, OUTSIDE the base "
            f"worktree {expected_root}; the base-tree run would have graded HEAD "
            f"source (editable install shadowing)",
        )
    return True, f"{module} resolves inside the base worktree ({origin})"


def red_on_base(
    node_id: str,
    test_ids: Sequence[str],
    base_ref: str,
    legacy_module: str,
    repo_root: Path,
    source_root: Path,
    *,
    timeout: int = DEFAULT_TEST_TIMEOUT_S,
) -> tuple[bool, str]:
    """Every declared parity test must fail ON ITS OWN ASSERTION at ``base_ref``.

    Fail-closed at every step: an unresolvable ref, an un-materializable worktree, a
    declared test file missing at HEAD, a failed residency probe, or ANY id that is
    not ``RED_ASSERTION`` returns ``(False, reason)``.
    """
    if not test_ids:
        return False, "hand-flip parity block declares no test_ids to execute"
    if not _ensure_ref(repo_root, base_ref):
        return False, f"receipt base_ref {base_ref!r} unresolvable in {repo_root}"
    try:
        rel_src = source_root.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return (
            False,
            f"source root {source_root} is outside the repo {repo_root}; cannot map it "
            f"onto the base worktree",
        )

    work_dir = Path(tempfile.mkdtemp(prefix=f"flipbase-{node_id.split('.')[-1]}-"))
    base_tree = work_dir / "base"
    try:
        add = _git(repo_root, "worktree", "add", "--detach", str(base_tree), base_ref)
        if add.returncode != 0:
            return (
                False,
                f"could not materialize base worktree at {base_ref}: "
                f"{(add.stderr or add.stdout).strip()[:300]}",
            )

        # Overlay the CANDIDATE tests onto the PRE-change tree. The tests are new in
        # the flip PR, so without the overlay there is nothing to run at base.
        for rel in _test_files(test_ids):
            head_file = repo_root / rel
            if not head_file.is_file():
                return False, f"declared parity test file absent at HEAD: {rel}"
            target = base_tree / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(head_file, target)

        base_src = base_tree / rel_src
        env = _run_env(base_src)
        interpreter = resolve_interpreter(repo_root)
        ok_probe, probe_detail = _probe_source_residency(
            legacy_module,
            interpreter=interpreter,
            cwd=base_tree,
            env=env,
            expected_root=base_tree,
        )
        if not ok_probe:
            return False, probe_detail

        run = _run_ids(
            test_ids,
            interpreter=interpreter,
            cwd=base_tree,
            source_root=base_src,
            tree=f"base({base_ref[:12]})",
            timeout=timeout,
        )
    finally:
        _git(repo_root, "worktree", "remove", "--force", str(base_tree))
        _git(repo_root, "worktree", "prune")
        shutil.rmtree(work_dir, ignore_errors=True)

    offenders = run.offenders(EnumParityOutcome.RED_ASSERTION)
    if offenders:
        rendered = "; ".join(
            f"{r.test_id} -> {r.outcome.value} ({r.detail[:120]})"
            for r in offenders[:5]
        )
        return (
            False,
            f"parity tests are NOT RED-for-the-right-reason at base_ref {base_ref[:12]}: "
            f"{len(offenders)}/{len(run.results)} id(s) did not fail on their own "
            f"assertion -> {rendered}",
        )
    return (
        True,
        f"all {len(run.results)} declared parity id(s) RED on their own assertion at "
        f"base_ref {base_ref[:12]} ({probe_detail})",
    )
