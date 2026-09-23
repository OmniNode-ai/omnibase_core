# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Mechanical enforcement of the OMN-18176 pre-push test-leg retirement.

OMN-18176 removed the governed impacted-test selector (``prepush-smart-tests``)
from the pre-push stage in this repository. Hosted CI is the enforced merge
gate and runs the identical selection: collected both directions on
2026-09-11, ``pytest tests/ --ignore=tests/integration`` yields 45,136 tests on
the pre-push side and 45,136 on CI's full-suite side, with zero rows in either
difference. Neither side applies a marker expression, so no test lost its only
execution path.

This module is the *mechanism* for that end state rather than a note about it.
A comment in a configuration file is not enforcement; the next lane to touch
these hooks reads this test, or fails it.

Two hooks that reach a test runner are RETAINED deliberately, as the named
exceptions of ``OmniNode-ai/knowledge-base-internal#328`` section 2.8, and both
live only in this repository:

``pytest-protocol-uuid-enforcement``
    Retained on COVERAGE. 2.02 s of runner time, 4.4 s wall, one module, 45
    tests, unconditional. ``ENABLE_SMART_TESTS`` is true here, so an ordinary
    pull request runs the selector's output rather than the full suite, and no
    workflow names this module or a marker unique to it -- CI's coverage of the
    property is conditional on the diff while the hook's is unconditional.

``verify-flip-bundle``
    Retained on COST, not on coverage. 0.51 s at steady state behind a path
    filter, reaching the runner only when a push carries a newly canonicalised
    node. CI runs the identical gate on every non-docs-only pull request, so
    retiring it would lose no property.

Precedents: ``OmniNode-ai/omnibase_infra#3415`` (repo 1) and
``OmniNode-ai/omnimarket#2463`` (repo 2).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PRECOMMIT_CONFIG = REPO_ROOT / ".pre-commit-config.yaml"
SELECTOR_SCRIPT = REPO_ROOT / "scripts" / "hooks" / "prepush_smart_tests.sh"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"

RETIRED_HOOK_ID = "prepush-smart-tests"

#: The hooks that reach a test runner and are kept anyway. This set is the
#: whole exception list; a third entry is a decision, never a cleanup.
NAMED_TEST_EXCEPTIONS = frozenset(
    {
        "pytest-protocol-uuid-enforcement",
        "verify-flip-bundle",
    }
)

#: Every hook that must survive at the pre-push stage, in configuration order.
EXPECTED_PREPUSH_HOOKS: tuple[str, ...] = (
    "mypy-type-check",
    "pyright-type-check",
    "check-evidence-shape",
    "verify-flip-bundle",
    "validate-naming-conventions",
    "validate-file-naming-conventions",
    "pytest-protocol-uuid-enforcement",
    "check-enum-governance",
    "check-node-purity",
)

#: Tokens that mean "a test runner is being launched here".
TEST_RUNNER_TOKENS: tuple[str, ...] = ("pytest", "unittest", "nose2")


def _load_config() -> dict:
    with PRECOMMIT_CONFIG.open(encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    assert isinstance(loaded, dict), "pre-commit config did not parse to a mapping"
    return loaded


def _all_hooks() -> list[dict]:
    return [hook for repo in _load_config()["repos"] for hook in repo.get("hooks", [])]


def _prepush_hooks() -> list[dict]:
    out: list[dict] = []
    for hook in _all_hooks():
        stages = hook.get("stages")
        if stages and any("pre-push" in str(stage) for stage in stages):
            out.append(hook)
    return out


def _strip_shell_comments(text: str) -> str:
    """Drop whole-line and trailing ``#`` comments from shell source.

    Deliberately conservative: a ``#`` inside a quoted string would be stripped
    too. That direction is safe here -- it can only make the scan see LESS, and
    every place this module relies on the scan seeing less is covered by the
    positive control below.
    """
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.split("#", 1)[0]
        out.append(stripped)
    return "\n".join(out)


def _strip_python_comments_and_docstrings(source: str) -> str:
    """Drop ``#`` comments and triple-quoted blocks from Python source.

    String LITERALS are deliberately preserved. The first revision of this
    scan in repo 1 stripped every string literal and therefore could not see
    ``subprocess.run(["pytest", ...])`` -- a fail-open hole that reported a
    clean scan over a module which launches the test runner on every call. The
    positive control below exists to keep that hole shut.
    """
    without_docstrings = re.sub(r'""".*?"""', "", source, flags=re.DOTALL)
    without_docstrings = re.sub(r"'''.*?'''", "", without_docstrings, flags=re.DOTALL)
    out: list[str] = []
    for line in without_docstrings.splitlines():
        out.append(line.split("#", 1)[0])
    return "\n".join(out)


def _scan_source_for_runner(path: Path) -> bool:
    """True when ``path``'s executable source launches a test runner."""
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".py":
        text = _strip_python_comments_and_docstrings(text)
    else:
        text = _strip_shell_comments(text)
    return any(token in text for token in TEST_RUNNER_TOKENS)


def _entry_paths(entry: str) -> list[Path]:
    """Repository-relative files an ``entry:`` string actually executes."""
    found: list[Path] = []
    for token in entry.split():
        cleaned = token.strip("'\"")
        if "/" not in cleaned:
            continue
        candidate = REPO_ROOT / cleaned
        if candidate.is_file():
            found.append(candidate)
    return found


def _local_imports(path: Path) -> list[Path]:
    """Repository-local modules a Python entry script imports, one level deep.

    Both spellings matter and the second one is the one that bites. This
    module's first revision handled only ``from scripts.ci.foo import bar`` and
    therefore resolved ``from scripts.ci import parity_replay`` to
    ``scripts/ci.py``, which does not exist -- so it concluded that
    ``verify-flip-bundle`` does not reach a test runner, when in fact
    ``parity_replay`` launches one via ``subprocess``. The named exception
    would have been silently demoted to an ordinary hook.
    """
    if path.suffix != ".py" or not path.is_file():
        return []
    source = path.read_text(encoding="utf-8", errors="replace")
    candidates: list[Path] = []

    def _module_path(dotted: str) -> Path:
        return REPO_ROOT / (dotted.replace(".", "/") + ".py")

    for package, names in re.findall(
        r"^\s*from\s+(scripts[\w.]*)\s+import\s+([\w,\s]+)", source, re.M
    ):
        # `from scripts.ci.parity_replay import X` -> the package IS the module.
        candidates.append(_module_path(package))
        # `from scripts.ci import parity_replay` -> each name is a submodule.
        for name in names.split(","):
            bare = name.strip().split(" as ")[0].strip()
            if bare:
                candidates.append(_module_path(f"{package}.{bare}"))
    for module in re.findall(r"^\s*import\s+(scripts[\w.]*)", source, re.M):
        candidates.append(_module_path(module))
    return [candidate for candidate in candidates if candidate.is_file()]


def _hook_reaches_test_runner(hook: dict) -> bool:
    entry = str(hook.get("entry", ""))
    if any(token in entry for token in TEST_RUNNER_TOKENS):
        return True
    for path in _entry_paths(entry):
        if _scan_source_for_runner(path):
            return True
        for imported in _local_imports(path):
            if _scan_source_for_runner(imported):
                return True
    return False


# ---------------------------------------------------------------------------
# 1. The retired hook is gone, at every stage, not merely moved off pre-push.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_retired_hook_id_appears_at_no_stage() -> None:
    ids = [hook["id"] for hook in _all_hooks()]
    assert RETIRED_HOOK_ID not in ids, (
        f"{RETIRED_HOOK_ID!r} is configured again. OMN-18176 retired the "
        "governed impacted-test selector from this repository's hooks "
        "entirely, not just from the pre-push stage. Restoring it is a revert "
        "of that decision, not a fix."
    )


# ---------------------------------------------------------------------------
# 2. Nothing at pre-push runs tests except the two named exceptions.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_only_the_named_exceptions_reach_a_test_runner_at_prepush() -> None:
    offenders = {
        hook["id"] for hook in _prepush_hooks() if _hook_reaches_test_runner(hook)
    }
    unexpected = offenders - NAMED_TEST_EXCEPTIONS
    assert not unexpected, (
        f"pre-push hook(s) {sorted(unexpected)} launch a test runner. OMN-18176 "
        "made pre-push policy, type and lint only, plus exactly the two named "
        f"exceptions {sorted(NAMED_TEST_EXCEPTIONS)}. A third test hook at this "
        "stage re-opens the load this change removed."
    )


@pytest.mark.unit
def test_both_named_exceptions_are_still_present_and_still_reach_the_runner() -> None:
    by_id = {hook["id"]: hook for hook in _prepush_hooks()}
    for hook_id in sorted(NAMED_TEST_EXCEPTIONS):
        assert hook_id in by_id, (
            f"{hook_id!r} is missing from the pre-push stage. It is a RETAINED "
            "exception under OMN-18176 / kb-internal#328 section 2.8, kept "
            "deliberately. Removing it for consistency with the retirement is "
            "the specific mistake the annotations in the configuration exist "
            "to prevent."
        )
        assert _hook_reaches_test_runner(by_id[hook_id]), (
            f"{hook_id!r} no longer reaches a test runner. If that is "
            "intentional it is no longer an exception and belongs out of "
            "NAMED_TEST_EXCEPTIONS; if it is accidental the gate has been "
            "hollowed out."
        )


# ---------------------------------------------------------------------------
# 3. The other nine survive, by id and in order.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_the_surviving_prepush_hooks_are_exactly_these_nine_in_order() -> None:
    actual = tuple(hook["id"] for hook in _prepush_hooks())
    assert actual == EXPECTED_PREPUSH_HOOKS, (
        "the pre-push hook set changed. OMN-18176 removes exactly one hook and "
        "reorders nothing; AC1 forbids removing, reordering, or changing the "
        f"behaviour of any other pre-push hook.\n  expected: "
        f"{EXPECTED_PREPUSH_HOOKS}\n  actual:   {actual}"
    )


# ---------------------------------------------------------------------------
# 4. Both exceptions carry the annotation that explains why they stayed.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_each_named_exception_carries_its_retention_annotation() -> None:
    text = PRECOMMIT_CONFIG.read_text(encoding="utf-8")
    for hook_id, marker in (
        ("pytest-protocol-uuid-enforcement", "RETAINED TEST EXCEPTION #1"),
        ("verify-flip-bundle", "RETAINED TEST EXCEPTION #2"),
    ):
        assert marker in text, (
            f"the annotation {marker!r} for {hook_id!r} is gone. AC1a of "
            "OMN-18176 requires each retained exception to carry, in the "
            "configuration, its measured cost and the reason it is kept, so a "
            "later reader does not remove it as an oversight."
        )
    assert "Kept ON COVERAGE" in text, (
        "the protocol identifier hook's retention GROUND is missing. It is "
        "kept because CI's coverage of the property is conditional on the diff."
    )
    assert "Kept ON COST, NOT ON COVERAGE" in text, (
        "the flip-bundle gate's retention GROUND is missing. It is kept on "
        "cost -- CI runs the identical gate -- and blurring that into the "
        "coverage argument would misstate why it survives."
    )


# ---------------------------------------------------------------------------
# 5. The selector script stays, and says what it is.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_selector_script_is_retained_and_declares_itself_manual_only() -> None:
    assert SELECTOR_SCRIPT.is_file(), (
        f"{SELECTOR_SCRIPT.relative_to(REPO_ROOT)} was deleted. It is retained "
        "deliberately: the remote lab dispatcher, the full-suite host guard "
        "and seven modules under tests/scripts/ depend on it."
    )
    header = SELECTOR_SCRIPT.read_text(encoding="utf-8")[:4000]
    assert "MANUAL INVOCATION ONLY" in header, (
        "the selector script's header no longer states it is manual-invocation "
        "only (AC7). A reader who finds an unannotated pre-push selector in "
        "the tree reasonably assumes it is wired to a hook."
    )
    assert "OMN-18176" in header, (
        "the selector script's header does not cite the retirement, so a "
        "reader cannot find the measurement or the rollback."
    )


@pytest.mark.unit
def test_the_dispatcher_still_references_the_retained_script() -> None:
    """The reason the script is kept must remain true, not merely asserted."""
    dispatcher = REPO_ROOT / "scripts" / "hooks" / "prepush_dispatch.sh"
    assert dispatcher.is_file(), "the remote dispatcher is missing"
    assert "prepush_smart_tests.sh" in dispatcher.read_text(encoding="utf-8"), (
        "the dispatcher no longer references the selector script. If nothing "
        "calls it any more, AC6 of the plan permits deleting it -- but that is "
        "a deliberate follow-up, and this test is the place to record it."
    )


# ---------------------------------------------------------------------------
# 6. No environment knob brings the leg back.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_no_environment_knob_restores_the_retired_leg() -> None:
    text = PRECOMMIT_CONFIG.read_text(encoding="utf-8")
    executable_lines = [
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    ]
    executable = "\n".join(executable_lines)
    for knob in ("PREPUSH_FULL_SUITE", "ENABLE_SMART_TESTS", "PREPUSH_PYTEST_ARGS"):
        assert knob not in executable, (
            f"{knob} appears in executable configuration. OMN-18176 leaves no "
            "dual path: the leg is retired, and restoring it is a revert of "
            "the squash commit, not an environment variable. A knob that "
            "re-enables it would make the retirement unobservable from the "
            "configuration alone."
        )


# ---------------------------------------------------------------------------
# 7. CI's selection stays the one this subset finding was measured against.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ci_full_suite_step_still_runs_the_selection_that_was_measured() -> None:
    """The zero-gap finding is only true while CI's own selection holds.

    Measured 2026-09-11: the pre-push maximal selection and CI's full-suite
    selection are the same command and collect the same 45,136 tests, with
    zero rows in either direction. If CI narrows its filter later, that
    finding stops being true and this test is where it is noticed.
    """
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    assert "pytest tests/ \\" in workflow, (
        "ci.yml no longer runs a whole-tests/ full-suite step. The OMN-18176 "
        "zero-gap measurement assumed it does."
    )
    assert "--ignore=tests/integration" in workflow, (
        "ci.yml no longer ignores tests/integration in the same way the "
        "retired pre-push leg did, so the two selections are no longer the "
        "same set and the subset finding must be re-measured."
    )


@pytest.mark.unit
def test_neither_side_applies_a_marker_expression() -> None:
    """No marker diff exists because no marker expression exists.

    This is the load-bearing half of the zero-gap claim: a difference in
    ``-m`` filters is how repo 1 lost 39 tests to a silent coverage gap. Here
    there is no ``-m`` on either side, so there is nothing to diff and nothing
    to re-home.
    """
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    # `-m` is overloaded: `python -m omnibase_core...` is a module invocation,
    # not a marker expression. Only a `-m` whose argument is quoted or begins
    # `not ` is pytest's marker flag in this workflow's idiom.
    marker_flags = re.findall(r"(?:^|\s)-m\s+(?:[\"']|not\s)", workflow)
    assert not marker_flags, (
        "ci.yml has grown a pytest marker expression. The OMN-18176 finding "
        "that no test lost its only execution path rests on neither side "
        "applying one. Re-measure the collection diff before changing this."
    )
    selector = (REPO_ROOT / "scripts" / "hooks" / "prepush_smart_tests.sh").read_text(
        encoding="utf-8"
    )
    selector_markers = re.findall(r"(?:^|\s)-m\s+(?:[\"']|not\s)", selector)
    assert not selector_markers, (
        "the selector script has grown a marker expression, so the two "
        "selections are no longer the same set."
    )


# ---------------------------------------------------------------------------
# 8. Positive control. Without this the scan can pass by being blind.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_positive_control_the_scan_sees_real_invocations_and_ignores_prose(
    tmp_path: Path,
) -> None:
    """The control that earned its place in repo 1.

    An earlier revision of this scan stripped every string literal from Python
    sources and so could not see ``subprocess.run(["pytest", ...])``. It
    reported a clean result over a module that launches the test runner on
    every call -- fail-open, and indistinguishable from a correct pass.
    """
    shell_real = tmp_path / "real.sh"
    shell_real.write_text("#!/bin/bash\nexec uv run pytest tests/\n", encoding="utf-8")
    assert _scan_source_for_runner(shell_real), (
        "the scan cannot see a test runner invoked from shell. Every 'no hook "
        "runs tests' assertion above would pass vacuously."
    )

    python_real = tmp_path / "real.py"
    python_real.write_text(
        "import subprocess\n\n\ndef go():\n"
        '    subprocess.run(["pytest", "tests/unit"], check=True)\n',
        encoding="utf-8",
    )
    assert _scan_source_for_runner(python_real), (
        "the scan cannot see a test runner passed as a string argument to "
        "subprocess. This is the exact fail-open hole the repo 1 control "
        "caught before it shipped."
    )

    shell_prose = tmp_path / "prose.sh"
    shell_prose.write_text(
        "#!/bin/bash\n# this script does not run pytest, it only mentions it\n"
        "echo done\n",
        encoding="utf-8",
    )
    assert not _scan_source_for_runner(shell_prose), (
        "the scan reports a test runner that exists only in a shell comment, "
        "so it cannot distinguish a real invocation from a description of one."
    )

    python_prose = tmp_path / "prose.py"
    python_prose.write_text(
        '"""This module describes pytest but never launches it."""\n\n\n'
        "def go() -> None:\n    return None\n",
        encoding="utf-8",
    )
    assert not _scan_source_for_runner(python_prose), (
        "the scan reports a test runner named only in a docstring."
    )
