# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Regression guard for the pre-push hook's `.200`-default host-identity
guard (OMN-15059).

Root cause this prevents regressing: root CLAUDE.md documents that the heavy
(full-suite, fail-closed escalation) branch of the pre-push hook defaults to
running on the `.200` execution host, not the local Mac -- but a rule stated
only in a doc/prompt has zero enforcement force without a call-site mechanism
(memory `feedback_a_rule_is_not_a_mechanism`). Evidence this was load-bearing:
a 2026-07-24 session drove the local Mac to load ~55 with 93% swap running
this exact escalation for 115+ minutes before `.200` was invoked as a rescue
rather than having been the execution target from the start.

Three assertion classes:

1. Static wiring -- `guard_full_suite_host` is defined and is the first
   statement inside EVERY `IS_FULL` (full-suite) branch, so a future edit
   cannot silently drop the call site while leaving the branch intact.
2. Behavioral -- actually invoking the hook with the full-suite escalation
   forced (`PREPUSH_FULL_SUITE=1`) and a guaranteed-non-matching
   `PREPUSH_200_HOSTNAME` override exits non-zero WITHOUT ever reaching the
   real pytest invocation. The override makes this host-independent: it must
   hold true no matter which host runs the test suite (including `.200`
   itself), so the test does not rely on the ambient hostname.
3. Heavyweight-SELECTION (OMN-15408) -- the guard must key on the work the
   selector actually picked, not on the `is_full_suite` flag. The selector
   routinely emits `is_full_suite=False` with `selected_paths=["tests/"]`, and
   before OMN-15408 those runs bypassed the guard outright: 13,898 tests /
   506s in omnimarket and 2,429 tests / 245s in omnibase_infra, executed on
   `omnibook` through real `git push` runs on 2026-07-29 with the guard never
   invoked -- while the identical selected work forced via
   `PREPUSH_FULL_SUITE=1` WAS refused. Assertion classes 1 and 2 above were
   green that entire time, because both only ever drove the flag-true path.
4. Heavyweight-selection TARGET SET (OMN-15408 round 2) -- class 3 measured the
   selection against `FULL_SUITE_TARGET` (`tests/`) alone, which made it INERT
   for THIS repo's own dominant heavyweight shape. This repo's selector fails
   closed to the single-entry sentinel `["tests/unit/"]` -- a DESCENDANT of
   `tests/`, so a `tests/`-only target set can never trip on it. Measured on
   `omnibook` 2026-07-29 against the SHIPPED round-1 hook at merged commit
   c5b0a9e1, real selector, on round-1's own two-file diff: `is_full_suite=False
   reason=None paths=[ tests/unit/ ]` -> `running impacted subset` -> guard never
   invoked, exit 0, push allowed. That sentinel is 1452 of the 1520 test files
   the escalation itself runs (95.5%). Class 3's tests were green that entire
   time, because they only ever drove the `tests/` shape -- the one shape this
   repo's selector reaches via the FLAG branch, which was already guarded.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from scripts.ci.test_selection_closure import TEST_UNIT_PREFIX

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_SCRIPT = REPO_ROOT / "scripts" / "hooks" / "prepush_smart_tests.sh"

_GUARANTEED_NON_MATCHING_HOSTNAME = "definitely-not-the-200-host-omn15059"

_FULL_SUITE_BRANCH_RE = re.compile(
    r'if \[ "\$IS_FULL" = "True" \].*?\n(.*?\n)(?=elif|else|fi)',
    re.DOTALL,
)


def test_hook_script_exists() -> None:
    assert HOOK_SCRIPT.is_file(), f"expected pre-push hook at {HOOK_SCRIPT}"


def test_guard_function_is_defined() -> None:
    script_text = HOOK_SCRIPT.read_text(encoding="utf-8")
    assert "guard_full_suite_host()" in script_text, (
        "expected a guard_full_suite_host() function guarding the heavy "
        f"full-suite escalation in {HOOK_SCRIPT}"
    )


def test_guard_is_called_before_every_full_suite_pytest_invocation() -> None:
    """Every `if [ "$IS_FULL" = ... ]; then` branch must call
    guard_full_suite_host as its first statement, so the heavy escalation can
    never run without the host check firing first."""
    script_text = HOOK_SCRIPT.read_text(encoding="utf-8")
    full_suite_branches = _FULL_SUITE_BRANCH_RE.findall(script_text)
    assert full_suite_branches, "expected at least one IS_FULL branch in the hook"
    for branch_body in full_suite_branches:
        first_stmt = next(
            (line.strip() for line in branch_body.splitlines() if line.strip()),
            "",
        )
        assert first_stmt == "guard_full_suite_host", (
            "expected guard_full_suite_host to be the first statement in the "
            f"full-suite branch, found {first_stmt!r} instead"
        )


def test_guard_fails_open_when_hostname_cannot_be_determined() -> None:
    script_text = HOOK_SCRIPT.read_text(encoding="utf-8")
    assert 'if [ -z "$host" ]; then' in script_text, (
        "expected the guard to check for an unresolvable hostname"
    )
    assert "this guard is a routing optimization, not a security gate" in script_text, (
        "expected the fail-open comment explaining why an unresolvable host "
        "must not block the push"
    )


def test_guard_has_a_visible_degraded_host_override() -> None:
    script_text = HOOK_SCRIPT.read_text(encoding="utf-8")
    assert "PREPUSH_ALLOW_LOCAL_FULL_SUITE" in script_text, (
        "expected a documented PREPUSH_ALLOW_LOCAL_FULL_SUITE escape hatch"
    )
    assert "DEGRADED-HOST OVERRIDE" in script_text, (
        "expected the override to print a loud, visible warning naming the "
        "degraded evidence -- a silent bypass reproduces the incident this "
        "guard exists to prevent"
    )


def test_guard_refuses_full_suite_escalation_on_non_200_host() -> None:
    """Behavioral proof: force the full-suite escalation and a
    guaranteed-non-matching host; the hook must exit non-zero and must NEVER
    reach the actual pytest invocation."""
    env = dict(os.environ)
    env["PREPUSH_FULL_SUITE"] = "1"
    env["PREPUSH_BASE_REF"] = "HEAD"
    env["PREPUSH_200_HOSTNAME"] = _GUARANTEED_NON_MATCHING_HOSTNAME
    result = subprocess.run(
        ["bash", str(HOOK_SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode != 0, (
        "expected the host guard to refuse the full-suite escalation on a "
        f"non-.200 host; got exit {result.returncode}. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "not the designated .200 build host" in result.stderr, (
        f"expected the refusal message in stderr, got: {result.stderr!r}"
    )
    assert "collected" not in result.stdout, (
        "the guard must refuse BEFORE pytest ever collects tests -- found a "
        f"pytest collection banner in stdout: {result.stdout!r}"
    )


# =============================================================================
# OMN-15408: the guard must key on the SELECTED WORK, not the is_full_suite flag
# =============================================================================
# The OMN-15059 guard above was called ONLY from inside the `IS_FULL` branch, so
# it fired on the selector's `is_full_suite` FLAG. The selector routinely emits
# `is_full_suite=False` with `selected_paths=["tests/"]` -- the whole suite
# arriving as an "impacted subset" -- and those runs bypassed the guard
# entirely. Measured on host `omnibook` through real `git push` runs on
# 2026-07-29: omnimarket ran 13,898 tests in 506s and omnibase_infra 2,429 tests
# in 245s, locally, with the guard never invoked; the SAME selected work forced
# via `PREPUSH_FULL_SUITE=1` was refused. Identical cost, opposite outcome,
# decided by a flag. The tests below drive the flag-FALSE path, which is the one
# that reaches production behavior -- the pre-existing tests in this file only
# ever exercised the flag-TRUE path, and were green while the hole was open.
#
# `test_guard_refuses_whole_suite_equivalent_selection_when_flag_is_false` is
# RED against the pre-fix hook (it proceeds to pytest, exit 0) and GREEN after.
# `test_guard_allows_a_genuinely_narrow_selection` is the anti-overreach pin:
# the fix must not brick every push from this Mac.

_FULL_SUITE_TARGET = "tests/"
# The selector's own fail-closed whole-tree sentinel (OMN-15408 round 2) -- the
# shape this repo ACTUALLY reaches with is_full_suite=False. Asserted below to
# still equal scripts/ci/test_selection_closure.py::TEST_UNIT_PREFIX.
_SELECTOR_WHOLE_TREE_SENTINEL = "tests/unit/"
# The full heavy-target set the shipped predicate must be evaluated against.
_HEAVY_SELECTION_TARGETS = f"{_FULL_SUITE_TARGET} {_SELECTOR_WHOLE_TREE_SENTINEL}"
# The literal production shape from the OMN-15408 evidence table.
_WHOLE_SUITE_SELECTION = "tests/"
# Real, genuinely-narrow subdirectories of this repo's suite. `tests/scripts/`
# is 10 of 1520 files; `tests/unit/scripts/` is a strict descendant of the
# sentinel, so widening the target set must not swallow it.
_NARROW_SELECTION = "tests/scripts/"
_NARROW_SELECTION_UNDER_SENTINEL = "tests/unit/scripts/"
# Minimum share of the escalation target the sentinel must cover for listing it
# as a heavy target to be justified rather than overreach. Measured 95.5%
# (1452/1520) on 2026-07-29; the floor is deliberately slack so ordinary tree
# growth does not trip it, but a real restructuring that turned tests/unit/ into
# a minority of the suite (as it is in omnimarket, 33%) would.
_SENTINEL_COVERAGE_FLOOR = 0.75

_PREDICATE_RE = re.compile(
    r"^selection_is_whole_suite\(\) \{.*?^\}",
    re.DOTALL | re.MULTILINE,
)
_WHOLE_SUITE_GUARD_CALL_RE = re.compile(
    r"if selection_is_whole_suite .*?\n(.*?)\n\s*fi",
    re.DOTALL,
)


def _extract_predicate_source() -> str:
    """Return the literal `selection_is_whole_suite` bash function from the hook.

    Extract-and-execute (the pattern already used for the hook's other pure
    shell helpers) so these assertions run THE function that ships, never a
    Python re-implementation of it -- a re-implementation would pass happily
    while the shipped predicate was broken.
    """
    match = _PREDICATE_RE.search(HOOK_SCRIPT.read_text(encoding="utf-8"))
    assert match is not None, (
        "expected a selection_is_whole_suite() function in "
        f"{HOOK_SCRIPT} -- the OMN-15408 heavyweight-selection predicate"
    )
    return match.group(0)


def _predicate_says_whole_suite(target: str, *paths: str) -> bool:
    """Execute the real bash predicate; True == 'this selection is heavyweight'."""
    script = f'{_extract_predicate_source()}\nselection_is_whole_suite "$@"\n'
    completed = subprocess.run(
        ["bash", "-c", script, "selection_is_whole_suite", target, *paths],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode in (0, 1), (
        "predicate exited abnormally "
        f"({completed.returncode}): stderr={completed.stderr!r}"
    )
    return completed.returncode == 0


def _run_hook_with_stubbed_selection(
    tmp_path: Path,
    *,
    is_full_suite: bool,
    selected_paths: list[str],
) -> subprocess.CompletedProcess[str]:
    """Run the REAL hook end-to-end with a stubbed selector + stubbed pytest.

    A shim `uv` earlier on PATH answers the selector invocation with a chosen
    selection JSON and turns the pytest invocation into an observable sentinel,
    so the test can assert both `did the guard refuse` and `did execution ever
    reach pytest` against the actual script rather than a surrogate. Everything
    else (`uv run python - <heredoc>` for JSON parsing) is delegated to the
    real interpreter.

    `PREPUSH_BASE_REF=HEAD` keeps the pre-selector preamble deterministic and
    offline: it always resolves, `merge-base HEAD HEAD` is HEAD, and the diff is
    empty -- the stub supplies the selection regardless.
    """
    selection_file = tmp_path / "selection.json"
    selection_file.write_text(
        json.dumps(
            {
                "is_full_suite": is_full_suite,
                "full_suite_reason": None,
                "selected_paths": selected_paths,
            }
        ),
        encoding="utf-8",
    )

    stub_bin = tmp_path / "stub-bin"
    stub_bin.mkdir(parents=True, exist_ok=True)
    uv_stub = stub_bin / "uv"
    uv_stub.write_text(
        "#!/usr/bin/env bash\n"
        'args="$*"\n'
        'case "$args" in\n'
        "  *detect_test_paths*)\n"
        '    cat "$PREPUSH_TEST_SELECTION_JSON"\n'
        "    exit 0\n"
        "    ;;\n"
        "  *pytest*)\n"
        '    echo "STUB-PYTEST-INVOKED $args"\n'
        "    exit 0\n"
        "    ;;\n"
        "esac\n"
        "shift\n"
        'if [ "$1" = "python" ]; then\n'
        "  shift\n"
        '  exec python3 "$@"\n'
        "fi\n"
        'exec "$@"\n',
        encoding="utf-8",
    )
    uv_stub.chmod(0o755)

    env = dict(os.environ)
    env["PATH"] = f"{stub_bin}{os.pathsep}{env['PATH']}"
    env["PREPUSH_TEST_SELECTION_JSON"] = str(selection_file)
    env["PREPUSH_BASE_REF"] = "HEAD"
    env["PREPUSH_200_HOSTNAME"] = _GUARANTEED_NON_MATCHING_HOSTNAME
    for leaky in (
        "PREPUSH_FULL_SUITE",
        "PREPUSH_ALLOW_LOCAL_FULL_SUITE",
        "ENABLE_SMART_TESTS",
        "PREPUSH_ADJACENCY",
        "PREPUSH_PYTEST_ARGS",
    ):
        env.pop(leaky, None)

    return subprocess.run(
        ["bash", str(HOOK_SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


def test_heavyweight_selection_predicate_is_defined() -> None:
    assert "selection_is_whole_suite()" in HOOK_SCRIPT.read_text(encoding="utf-8"), (
        "expected a selection_is_whole_suite() predicate so the guard can key "
        "on the selected work rather than the is_full_suite flag (OMN-15408)"
    )


def test_full_suite_target_is_single_sourced() -> None:
    """The predicate and the escalation must read the SAME target.

    If the guard hard-coded its own notion of 'the whole suite' it would drift
    from whatever the escalation actually runs -- a second cost model, which is
    the thing this fix explicitly avoids.
    """
    script_text = HOOK_SCRIPT.read_text(encoding="utf-8")
    assert f'FULL_SUITE_TARGET="{_FULL_SUITE_TARGET}"' in script_text, (
        f"expected FULL_SUITE_TARGET to be set to {_FULL_SUITE_TARGET!r} in "
        f"{HOOK_SCRIPT}"
    )
    assert 'uv run pytest "${FULL_SUITE_TARGET}"' in script_text, (
        "expected the fail-closed escalation to run ${FULL_SUITE_TARGET} "
        "itself, so the guard predicate cannot drift from the run it guards"
    )
    assert (
        'HEAVY_SELECTION_TARGETS="${FULL_SUITE_TARGET} ${SELECTOR_WHOLE_TREE_SENTINEL}"'
        in script_text
    ), (
        "expected the heavy-target set to be DERIVED from FULL_SUITE_TARGET (the "
        "run it guards) plus the selector's own whole-tree sentinel, not "
        "hard-coded independently of either"
    )
    assert 'selection_is_whole_suite "$HEAVY_SELECTION_TARGETS"' in script_text, (
        "expected the predicate to be evaluated against the full "
        "HEAVY_SELECTION_TARGETS set -- evaluating it against FULL_SUITE_TARGET "
        "alone is the OMN-15408 round-1 inertness defect (the selector's "
        "tests/unit/ sentinel is a DESCENDANT of tests/ and can never trip it)"
    )


# -----------------------------------------------------------------------------
# OMN-15408 round 2: the target SET, not just the escalation target
# -----------------------------------------------------------------------------
# Round 1 measured the selection against `FULL_SUITE_TARGET` (`tests/`) only.
# This repo's selector reaches `tests/` only on the FLAG branch (`_full_suite()`
# returns `selected_paths=["tests/"]` with `is_full_suite=True`), which was
# already guarded. Its `is_full_suite=False` heavyweight answer is the closure
# sentinel `["tests/unit/"]` -- a DESCENDANT of `tests/`, so the round-1
# predicate provably never fired on it. Executed proof (host `omnibook`,
# 2026-07-29, SHIPPED hook at merged c5b0a9e1, real selector, round-1's own
# two-file diff as the input): `is_full_suite=False reason=None
# paths=[ tests/unit/ ]` -> `running impacted subset` -> guard never invoked,
# exit 0. The tests below pin both halves of the justification: the sentinel
# LITERAL still matches the selector's constant, and the sentinel still COVERS a
# supermajority of the escalation target (i.e. listing it as heavy is warranted,
# not overreach).


def test_selector_whole_tree_sentinel_matches_the_selector_constant() -> None:
    """Anti-drift: the hook's sentinel literal must equal the selector's own.

    The hook cannot import Python, so the sentinel is a bash literal. That
    literal is only correct as long as the selector still fails closed to the
    same path. Bind the two here: if `compute_closure_selection`'s sentinel ever
    moves, this test fails instead of the guard silently going inert again --
    which is exactly the failure round 1 shipped.
    """
    assert _SELECTOR_WHOLE_TREE_SENTINEL == TEST_UNIT_PREFIX, (
        "this test's expected sentinel drifted from the selector's "
        f"TEST_UNIT_PREFIX ({TEST_UNIT_PREFIX!r})"
    )
    script_text = HOOK_SCRIPT.read_text(encoding="utf-8")
    assert f'SELECTOR_WHOLE_TREE_SENTINEL="{TEST_UNIT_PREFIX}"' in script_text, (
        "expected the hook to declare SELECTOR_WHOLE_TREE_SENTINEL as the "
        f"selector's own fail-closed sentinel {TEST_UNIT_PREFIX!r}; "
        f"{HOOK_SCRIPT} is out of sync with "
        "scripts/ci/test_selection_closure.py::TEST_UNIT_PREFIX"
    )


def test_sentinel_covers_a_supermajority_of_the_escalation_target() -> None:
    """The measured justification for treating the sentinel as heavyweight.

    A heavy-target list is a per-repo MEASURED claim, not a constant to copy
    between repos: in omnimarket the same `tests/unit/` path is 33% of the suite
    and listing it would be overreach. Here it is 95.5% (1452/1520 on
    2026-07-29) of exactly what the escalation runs -- `tests/` minus the
    always-ignored `tests/integration`. If a restructuring ever made it a
    minority, the guard would start refusing genuine narrowings and this test
    fails first.
    """
    escalation_root = REPO_ROOT / _FULL_SUITE_TARGET
    sentinel_root = REPO_ROOT / _SELECTOR_WHOLE_TREE_SENTINEL
    assert sentinel_root.is_dir(), f"expected the sentinel tree at {sentinel_root}"

    ignored = REPO_ROOT / "tests" / "integration"
    escalation_files = {
        p for p in escalation_root.rglob("test_*.py") if not p.is_relative_to(ignored)
    }
    sentinel_files = set(sentinel_root.rglob("test_*.py"))

    assert escalation_files, f"found no test files under {escalation_root}"
    assert sentinel_files <= escalation_files, (
        "the sentinel tree must be a subset of what the escalation runs"
    )
    share = len(sentinel_files) / len(escalation_files)
    assert share >= _SENTINEL_COVERAGE_FLOOR, (
        f"{_SELECTOR_WHOLE_TREE_SENTINEL} now covers only {share:.1%} "
        f"({len(sentinel_files)}/{len(escalation_files)}) of the escalation "
        f"target, below the {_SENTINEL_COVERAGE_FLOOR:.0%} floor. It is no "
        "longer whole-suite-equivalent, so listing it in "
        "HEAVY_SELECTION_TARGETS has become overreach -- drop it from the set "
        "rather than lowering this floor."
    )


def test_predicate_flags_the_selector_whole_tree_sentinel() -> None:
    """THE ROUND-1 INERTNESS, at predicate grain.

    RED against the round-1 hook: `selection_is_whole_suite "tests/"
    "tests/unit/"` returns false, because `tests/unit/` is a descendant of the
    target and the predicate only matches the target itself or an ancestor.
    """
    assert _predicate_says_whole_suite(
        _HEAVY_SELECTION_TARGETS, _SELECTOR_WHOLE_TREE_SENTINEL
    ), (
        "the selector's fail-closed whole-tree sentinel is the heaviest "
        "is_full_suite=False selection this repo produces; it must be treated "
        "as heavyweight"
    )
    assert _predicate_says_whole_suite(
        _HEAVY_SELECTION_TARGETS, _SELECTOR_WHOLE_TREE_SENTINEL.rstrip("/")
    ), "a trailing-slash-less sentinel must normalize to the same target"
    assert _predicate_says_whole_suite(
        _HEAVY_SELECTION_TARGETS, _NARROW_SELECTION, _SELECTOR_WHOLE_TREE_SENTINEL
    ), "one heavyweight path anywhere in the selection makes it heavyweight"
    # The round-1 target set is preserved, not replaced.
    assert _predicate_says_whole_suite(_HEAVY_SELECTION_TARGETS, _FULL_SUITE_TARGET)


def test_predicate_still_allows_narrowings_under_the_widened_target_set() -> None:
    """Anti-overreach pin against the WIDENED set.

    Adding a second, deeper heavy target is the change most likely to start
    swallowing genuine narrowings. `tests/scripts/` (10 files) and
    `tests/unit/scripts/` (a strict descendant of the sentinel) must both stay
    ALLOWED, or the guard becomes a blanket push block.
    """
    assert not _predicate_says_whole_suite(_HEAVY_SELECTION_TARGETS, _NARROW_SELECTION)
    assert not _predicate_says_whole_suite(
        _HEAVY_SELECTION_TARGETS, _NARROW_SELECTION_UNDER_SENTINEL
    )
    assert not _predicate_says_whole_suite(
        _HEAVY_SELECTION_TARGETS, f"{_NARROW_SELECTION_UNDER_SENTINEL}test_thing.py"
    )
    assert not _predicate_says_whole_suite(
        _HEAVY_SELECTION_TARGETS, "tests/unit/models/", "tests/unit/cli/"
    ), "several real subdirectories are still a proper narrowing"
    assert not _predicate_says_whole_suite(_HEAVY_SELECTION_TARGETS)


def test_guard_refuses_selector_whole_tree_sentinel_when_flag_is_false(
    tmp_path: Path,
) -> None:
    """THE OMN-15408 ROUND-2 REGRESSION, end-to-end through the real hook.

    `is_full_suite=False` + `selected_paths=["tests/unit/"]` on a non-`.200`
    host is the shape the SHIPPED round-1 hook allowed through to pytest at
    merged commit c5b0a9e1 (verified against the real selector on that commit's
    own diff, not stubbed). RED against round 1; GREEN after.
    """
    result = _run_hook_with_stubbed_selection(
        tmp_path,
        is_full_suite=False,
        selected_paths=[_SELECTOR_WHOLE_TREE_SENTINEL],
    )
    assert result.returncode != 0, (
        "expected the host guard to refuse the selector's fail-closed "
        "whole-tree sentinel selection even though is_full_suite=False; got "
        f"exit {result.returncode}. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "not the designated .200 build host" in result.stderr, (
        f"expected the refusal message in stderr, got: {result.stderr!r}"
    )
    assert "STUB-PYTEST-INVOKED" not in result.stdout, (
        "the guard must refuse BEFORE pytest is invoked -- found a pytest "
        f"invocation in stdout: {result.stdout!r}"
    )


def test_guard_allows_a_narrow_selection_under_the_sentinel_on_a_local_host(
    tmp_path: Path,
) -> None:
    """Anti-overreach pin, end-to-end, for the newly-added heavy target.

    `tests/unit/scripts/` sits UNDER the sentinel. It must still run locally --
    the widened target set must catch the sentinel itself, not everything
    beneath it.
    """
    result = _run_hook_with_stubbed_selection(
        tmp_path,
        is_full_suite=False,
        selected_paths=[_NARROW_SELECTION_UNDER_SENTINEL],
    )
    assert result.returncode == 0, (
        "expected a narrow selection under the sentinel to be allowed on a "
        f"non-.200 host; got exit {result.returncode}. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "not the designated .200 build host" not in result.stderr, (
        f"the guard must NOT refuse a proper narrowing; stderr: {result.stderr!r}"
    )
    assert "STUB-PYTEST-INVOKED" in result.stdout, (
        f"expected the narrow selection to reach pytest; stdout: {result.stdout!r}"
    )


def test_guard_is_called_when_the_selection_is_whole_suite_equivalent() -> None:
    """Static wiring: the impacted-subset branch must consult the guard.

    Pairs with the pre-existing IS_FULL-branch assertion above; together they
    pin BOTH call sites, so a future edit cannot silently drop either one.
    """
    script_text = HOOK_SCRIPT.read_text(encoding="utf-8")
    guarded_blocks = _WHOLE_SUITE_GUARD_CALL_RE.findall(script_text)
    assert guarded_blocks, (
        "expected an `if selection_is_whole_suite ...` block in the "
        "impacted-subset branch (OMN-15408)"
    )
    assert any("guard_full_suite_host" in block for block in guarded_blocks), (
        "expected guard_full_suite_host to be called when the selection is "
        f"whole-suite-equivalent; found blocks: {guarded_blocks!r}"
    )


def test_predicate_flags_a_whole_suite_selection() -> None:
    """A selection covering the entire escalation target is heavyweight."""
    assert _predicate_says_whole_suite(_FULL_SUITE_TARGET, _WHOLE_SUITE_SELECTION)
    assert _predicate_says_whole_suite(_FULL_SUITE_TARGET, _FULL_SUITE_TARGET)
    assert _predicate_says_whole_suite(
        _FULL_SUITE_TARGET, _FULL_SUITE_TARGET.rstrip("/")
    ), "a trailing-slash-less path must normalize to the same target"
    assert _predicate_says_whole_suite(
        _FULL_SUITE_TARGET, _NARROW_SELECTION, _WHOLE_SUITE_SELECTION
    ), "one whole-suite path anywhere in the selection makes it heavyweight"


def test_predicate_allows_a_genuinely_narrow_selection() -> None:
    """Real narrowing stays runnable -- the guard is not a blanket push block."""
    assert not _predicate_says_whole_suite(_FULL_SUITE_TARGET, _NARROW_SELECTION)
    assert not _predicate_says_whole_suite(
        _FULL_SUITE_TARGET, f"{_NARROW_SELECTION}test_something.py"
    )
    assert not _predicate_says_whole_suite(_FULL_SUITE_TARGET)


def test_guard_refuses_whole_suite_equivalent_selection_when_flag_is_false(
    tmp_path: Path,
) -> None:
    """THE OMN-15408 REGRESSION.

    `is_full_suite=False` + `selected_paths=["tests/"]` on a non-`.200` host is
    the exact shape that ran 13,898 tests locally with the guard never invoked.
    RED against the pre-fix hook (it reached pytest and exited 0); GREEN after.
    """
    result = _run_hook_with_stubbed_selection(
        tmp_path,
        is_full_suite=False,
        selected_paths=[_WHOLE_SUITE_SELECTION],
    )
    assert result.returncode != 0, (
        "expected the host guard to refuse a whole-suite-equivalent selection "
        "even though is_full_suite=False; got exit "
        f"{result.returncode}. stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "not the designated .200 build host" in result.stderr, (
        f"expected the refusal message in stderr, got: {result.stderr!r}"
    )
    assert "STUB-PYTEST-INVOKED" not in result.stdout, (
        "the guard must refuse BEFORE pytest is invoked -- found a pytest "
        f"invocation in stdout: {result.stdout!r}"
    )


def test_guard_allows_a_genuinely_narrow_selection_on_a_local_host(
    tmp_path: Path,
) -> None:
    """Anti-overreach pin.

    A real narrow selection must still run locally on a non-`.200` host. If
    this ever fails, the fix has become a blanket push block and will be
    disabled within a week -- which is worse than no guard at all.
    """
    result = _run_hook_with_stubbed_selection(
        tmp_path,
        is_full_suite=False,
        selected_paths=[_NARROW_SELECTION],
    )
    assert result.returncode == 0, (
        "expected a genuinely narrow selection to be allowed on a non-.200 "
        f"host; got exit {result.returncode}. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "not the designated .200 build host" not in result.stderr, (
        f"the guard must NOT refuse a proper narrowing; stderr: {result.stderr!r}"
    )
    assert "STUB-PYTEST-INVOKED" in result.stdout, (
        "expected the narrow selection to actually reach pytest; stdout: "
        f"{result.stdout!r}"
    )
    assert _NARROW_SELECTION in result.stdout, (
        "expected the narrow selection's own path to be handed to pytest; "
        f"stdout: {result.stdout!r}"
    )
