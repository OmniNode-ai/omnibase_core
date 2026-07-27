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

Two assertion classes:

1. Static wiring -- `guard_full_suite_host` is defined and is the first
   statement inside EVERY `IS_FULL` (full-suite) branch, so a future edit
   cannot silently drop the call site while leaving the branch intact.
2. Behavioral -- actually invoking the hook with the full-suite escalation
   forced (`PREPUSH_FULL_SUITE=1`) and a guaranteed-non-matching
   `PREPUSH_200_HOSTNAME` override exits non-zero WITHOUT ever reaching the
   real pytest invocation. The override makes this host-independent: it must
   hold true no matter which host runs the test suite (including `.200`
   itself), so the test does not rely on the ambient hostname.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

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
