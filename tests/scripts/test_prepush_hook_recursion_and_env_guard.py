# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""S0 tactical defect patch for the pre-push hook (OMN-16489).

Three defects, each proven live in the 2026-08-23/24 window
(`docs/tracking/2026-08-24-system-friction-report.md` F-01/F-04, plan
`docs/plans/2026-08-24-blocker-decoupling-redesign-plan.md` §4 S0 items 1-3):

1. NO recursion guard — this hook spawns pytest, and the spawned suite
   contains tests that exec this same hook script. A re-entering child can
   launch nested full suites: the OMN-16425 class cost ~9h03m across 5 failed
   ~1h45m runs. OMN-16425's fix scrubbed the *test sites*; the hook itself
   still accepted re-entry. Fix: an exported `ONEX_PREPUSH_HOOK_ACTIVE=<pid>`
   sentinel; a nested invocation refuses fail-closed before any selector or
   pytest work.

2. Override env vars inherit downward — the hook handed its FULL environment
   (including `PREPUSH_ALLOW_LOCAL_FULL_SUITE` and every `PREPUSH_*` override)
   to the pytest subprocess tree, so a bypass granted to the outer push was
   silently honored by every descendant (F-04: "permission to bypass once"
   became "permission for every descendant process, forever"). Fix: the hook
   strips exported `PREPUSH_*` (+`ENABLE_SMART_TESTS`) from the spawned
   pytest env. OMN-16480 (landed) independently rejects `PREPUSH_ALLOW_*` at
   hook entry; this scrub covers the whole `PREPUSH_*` prefix class one layer
   deeper, at the child boundary.

3. Empty-hostname fail-open — `guard_full_suite_host()` warned and
   `return 0`ed when `hostname -s` produced nothing, so the heavy escalation
   proceeded on a host that could not be identified, contradicting the hook's
   own fail-loud doctrine ("a gate that cannot run must be indistinguishable
   from a failing gate"). Fix: fail CLOSED with a remediation message.

All behavioral tests below run THE real hook script end-to-end with the same
stubbed-`uv` harness `tests/scripts/test_prepush_hook_host_identity_guard.py`
established for OMN-15408, never a Python re-implementation of it.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from tests.scripts._prepush_lab_isolation import network_free_lab_env

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_SCRIPT = REPO_ROOT / "scripts" / "hooks" / "prepush_smart_tests.sh"

# Matches the guaranteed-non-matching override used by the OMN-15059 tests, so
# host-identity never accidentally matches while these tests run on .200 itself.
_NON_MATCHING_HOSTNAME = "definitely-not-the-200-host-omn16489"
_NARROW_SELECTION = "tests/scripts/"

# Every env var the hook honors at entry that must NOT leak into its pytest
# children. Mirrors the leaky-var scrub list in the OMN-15408 harness plus the
# recursion sentinel this ticket introduces.
_LEAKY_VARS = (
    "PREPUSH_FULL_SUITE",
    "PREPUSH_ALLOW_LOCAL_FULL_SUITE",
    "ENABLE_SMART_TESTS",
    "PREPUSH_ADJACENCY",
    "PREPUSH_PYTEST_ARGS",
    "ONEX_PREPUSH_HOOK_ACTIVE",
)

_UV_STUB = """#!/usr/bin/env bash
args="$*"
case "$args" in
  *detect_test_paths*)
    cat "$PREPUSH_TEST_SELECTION_JSON"
    exit 0
    ;;
  *pytest*)
    echo "STUB-PYTEST-INVOKED $args"
    echo "STUB-PYTEST-ENV ALLOW=${PREPUSH_ALLOW_LOCAL_FULL_SUITE:-UNSET} \
CANARY=${PREPUSH_CANARY_LEAK_PROBE:-UNSET} \
SMART=${ENABLE_SMART_TESTS:-UNSET} \
SENTINEL=${ONEX_PREPUSH_HOOK_ACTIVE:-UNSET}"
    exit 0
    ;;
esac
shift
if [ "$1" = "python" ]; then
  shift
  exec python3 "$@"
fi
exec "$@"
"""


def _run_hook(
    tmp_path: Path,
    *,
    is_full_suite: bool,
    selected_paths: list[str],
    extra_env: dict[str, str] | None = None,
    empty_hostname: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run the REAL hook with a stubbed selector + observable stubbed pytest.

    The pytest stub echoes the override vars it received, so assertions can
    see exactly what the hook's subprocess env carried. `empty_hostname=True`
    additionally shadows `hostname` with a stub that produces nothing, driving
    the guard's unresolvable-hostname branch deterministically on any host.
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
    uv_stub.write_text(_UV_STUB, encoding="utf-8")
    uv_stub.chmod(0o755)
    if empty_hostname:
        hostname_stub = stub_bin / "hostname"
        hostname_stub.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
        hostname_stub.chmod(0o755)

    env = dict(os.environ)
    for leaky in _LEAKY_VARS:
        env.pop(leaky, None)
    env["PATH"] = f"{stub_bin}{os.pathsep}{env['PATH']}"
    env["PREPUSH_TEST_SELECTION_JSON"] = str(selection_file)
    env["PREPUSH_BASE_REF"] = "HEAD"
    env["PREPUSH_200_HOSTNAME"] = _NON_MATCHING_HOSTNAME
    # OMN-16991: this harness forces first-entry behavior on a de-designated
    # host, which now reaches the lab-dispatch leg. Keep it network-free -- a
    # unit test must not take a lab host's exclusive slot for an hour.
    env.update(network_free_lab_env())
    if extra_env:
        env.update(extra_env)

    return subprocess.run(
        ["bash", str(HOOK_SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


def _stub_pytest_env(stdout: str) -> dict[str, str]:
    for line in stdout.splitlines():
        if line.startswith("STUB-PYTEST-ENV "):
            return dict(pair.split("=", 1) for pair in line.split(" ", 1)[1].split())
    raise AssertionError(f"no STUB-PYTEST-ENV line in stdout: {stdout!r}")


# =============================================================================
# Defect 1 — nested invocation must refuse
# =============================================================================


def test_recursion_sentinel_is_exported() -> None:
    script_text = HOOK_SCRIPT.read_text(encoding="utf-8")
    assert 'export ONEX_PREPUSH_HOOK_ACTIVE="$$"' in script_text, (
        "expected the hook to export the ONEX_PREPUSH_HOOK_ACTIVE=<pid> "
        "recursion sentinel at entry (OMN-16489 defect 1)"
    )


def test_nested_invocation_refuses(tmp_path: Path) -> None:
    """A hook invoked while an ancestor hook is active must refuse fail-closed.

    RED against the pre-fix hook (it proceeded all the way to pytest, exit 0).
    """
    result = _run_hook(
        tmp_path,
        is_full_suite=False,
        selected_paths=[_NARROW_SELECTION],
        extra_env={"ONEX_PREPUSH_HOOK_ACTIVE": "99999"},
    )
    assert result.returncode != 0, (
        "expected a nested hook invocation to refuse; got exit "
        f"{result.returncode}. stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "nested invocation refused" in result.stderr, (
        f"expected the nested-invocation refusal in stderr: {result.stderr!r}"
    )
    assert "STUB-PYTEST-INVOKED" not in result.stdout, (
        "a nested invocation must refuse BEFORE any pytest is spawned; "
        f"stdout: {result.stdout!r}"
    )


def test_nested_full_suite_escalation_refuses(tmp_path: Path) -> None:
    """The exact OMN-16425 shape: a nested invocation that would escalate to
    the full suite (leaked override included) must still refuse at entry —
    even the degraded-host override cannot arm a nested run."""
    result = _run_hook(
        tmp_path,
        is_full_suite=True,
        selected_paths=[],
        extra_env={
            "ONEX_PREPUSH_HOOK_ACTIVE": "99999",
            "PREPUSH_FULL_SUITE": "1",
            "PREPUSH_ALLOW_LOCAL_FULL_SUITE": "1",
        },
    )
    assert result.returncode != 0, (
        "expected the nested escalation to refuse; got exit "
        f"{result.returncode}. stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "nested invocation refused" in result.stderr
    assert "STUB-PYTEST-INVOKED" not in result.stdout


# =============================================================================
# Defect 2 — overrides must not inherit into the pytest subprocess
# =============================================================================


def test_scrub_helper_is_defined_and_called_before_every_pytest() -> None:
    script_text = HOOK_SCRIPT.read_text(encoding="utf-8")
    assert "scrub_prepush_override_env()" in script_text, (
        "expected a scrub_prepush_override_env helper stripping PREPUSH_* "
        "overrides from the pytest subprocess env (OMN-16489 defect 2)"
    )
    pytest_invocations = script_text.count("uv run pytest")
    scrub_calls = script_text.count("scrub_prepush_override_env\n")
    assert scrub_calls >= 2, (
        "expected scrub_prepush_override_env to be invoked ahead of both "
        f"pytest invocation sites; found {scrub_calls} call(s) for "
        f"{pytest_invocations} documented invocation(s)"
    )


def test_overrides_do_not_inherit_into_pytest_child(tmp_path: Path) -> None:
    """The F-04 mechanism: an override honored by THIS hook run must be
    invisible to the pytest tree it spawns, while the recursion sentinel must
    inherit (children need it for the recursion guard to hold).

    RED against the pre-fix hook (exported overrides leaked straight through).
    `PREPUSH_ALLOW_*` is deliberately absent from extra_env: since OMN-16480
    landed, its presence is a hard refusal at hook entry (its own tests pin
    that), so it can never survive to the scrub this test exercises. The
    probe uses vars the hook still honors at entry (`ENABLE_SMART_TESTS`) plus
    a generic `PREPUSH_*` canary covering the whole prefix class.
    """
    result = _run_hook(
        tmp_path,
        is_full_suite=False,
        selected_paths=[_NARROW_SELECTION],
        extra_env={
            "PREPUSH_CANARY_LEAK_PROBE": "leaked",
            # Deliberately a value the hook's FLAG parsing ignores, so the
            # selection stays the narrow subset; only inheritance is probed.
            "ENABLE_SMART_TESTS": "true",
        },
    )
    assert result.returncode == 0, (
        "narrow selection must still run; got exit "
        f"{result.returncode}. stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    child_env = _stub_pytest_env(result.stdout)
    assert child_env["ALLOW"] == "UNSET", (
        "PREPUSH_ALLOW_LOCAL_FULL_SUITE reached the pytest child env — it is "
        "rejected at hook entry (OMN-16480) and scrubbed by prefix here, so "
        f"any path for it to appear is a regression: {child_env!r}"
    )
    assert child_env["CANARY"] == "UNSET", (
        f"a generic PREPUSH_* var leaked into the pytest child env: {child_env!r}"
    )
    assert child_env["SMART"] == "UNSET", (
        f"ENABLE_SMART_TESTS leaked into the pytest child env: {child_env!r}"
    )
    assert child_env["SENTINEL"] != "UNSET", (
        "the ONEX_PREPUSH_HOOK_ACTIVE sentinel must inherit into the pytest "
        f"tree (the recursion guard depends on it): {child_env!r}"
    )
    assert child_env["SENTINEL"].isdigit(), (
        f"the sentinel must carry the exporting hook's pid: {child_env!r}"
    )


# =============================================================================
# Defect 3 — unresolvable hostname must fail CLOSED
# =============================================================================


def test_empty_hostname_refuses_heavy_escalation(tmp_path: Path) -> None:
    """A host that cannot be identified cannot be routed; the heavy escalation
    must refuse with remediation, never proceed on silence.

    RED against the pre-fix hook (it warned, returned 0, and ran pytest).
    """
    result = _run_hook(
        tmp_path,
        is_full_suite=True,
        selected_paths=[],
        empty_hostname=True,
    )
    assert result.returncode != 0, (
        "expected the guard to refuse the heavy escalation when the hostname "
        f"cannot be determined; got exit {result.returncode}. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "could not determine the local hostname" in result.stderr, (
        f"expected the fail-closed refusal in stderr: {result.stderr!r}"
    )
    assert "REMEDIATION" in result.stderr, (
        f"a fail-closed refusal must name its remediation: {result.stderr!r}"
    )
    assert "STUB-PYTEST-INVOKED" not in result.stdout, (
        f"the guard must refuse BEFORE pytest is spawned; stdout: {result.stdout!r}"
    )


def test_fail_open_hostname_branch_is_gone() -> None:
    """The old branch logged a WARNING and returned 0; neither the log line
    nor the fail-open rationale string may survive."""
    script_text = HOOK_SCRIPT.read_text(encoding="utf-8")
    assert "proceeding locally (fail-open" not in script_text, (
        "the empty-hostname fail-open branch must be gone (OMN-16489 defect 3)"
    )
    assert "this guard is a routing optimization, not a security gate" not in (
        script_text
    ), (
        "the fail-open rationale is superseded by the S0 fail-closed ruling "
        "(plan §4 S0 item 3); remove it so it cannot be cited to re-open "
        "the branch"
    )
