# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The remote execution leg must carry the same pytest EXECUTION POLICY the
local leg runs under, and it must be liveness-bounded (OMN-17603).

This is the omnibase_core port of the omnibase_infra fix landed as OMN-17564
(``abc144fe6``). It is kept deliberately diffable against that file: same
constant names, same fit-record field, same ``min(row cores, cap)`` rule.

WHY THIS REPO NEEDED IT TOO -- and why the naive reading of the defect is
WRONG here. In omnibase_infra the story was "the remote leg has no parallelism
config anywhere". In omnibase_core that is false on its face:
``pyproject.toml``'s ``[tool.pytest.ini_options] addopts`` ALREADY declares
``-n4 --dist=loadgroup --timeout=60 --timeout-method=signal``. The remote leg
ran single-threaded anyway, because THAT BLOCK IS NEVER READ.

The mechanism is the one ``test_prepush_hook_has_bounded_timeout.py``
(OMN-14967) already documents for the LOCAL leg: ``tests/pytest.ini`` is a real
committed file whose own ``addopts`` is ``-v --tb=short --strict-markers
--disable-warnings --color=yes`` -- no ``-n``, no ``--timeout``, no ``--dist``.
Both legs invoke pytest with ``tests/`` as the argument, so pytest's
rootdir/inifile discovery starts there, finds ``tests/pytest.ini``, and stops:
``pytest.ini`` outranks ``pyproject.toml`` outright and the two do NOT merge.

OMN-14967 closed that hole for the local leg by asserting both ``uv run
pytest`` lines in ``prepush_smart_tests.sh`` pass ``-n``/``--timeout``
EXPLICITLY on the command line, where no ini file can shadow them. The remote
leg's pytest invocation does not live in that script -- it lives in the
heredoc'd wrapper inside ``prepush_dispatch.sh`` -- so it was never covered by
that guard, and it shipped ``"$UV" run pytest "${ARGV[@]}"
--ignore=tests/integration --tb=short`` with ARGV holding PATHS ONLY. This
module is the missing half of OMN-14967's invariant, at the dispatch seam.

MEASURED, read-only probe of h105 (192.168.86.105) at 2026-09-02T19:24Z, on
the live run ``omnibase_core-e69568dd5e02-80404``:

* ``ps -Ao pid,ppid,pcpu,rss,etime,command`` showed pid 87006 as the ONLY
  python process beneath the wrapper -- no ``execnet``/``gw*`` workers at all
  -- 759,888 KB RSS, 1h49m elapsed.
* that run's own ``suite.log`` header read ``rootdir:
  .../tree/tests`` / ``configfile: pytest.ini`` / ``collected 44720 items``,
  naming the shadowing file directly.

So this change is PARITY, not a new parallelism policy: after it the remote
leg runs under exactly the flags ``PREPUSH_TIMEOUT_FLAGS`` has always given
the local leg, on an identical rootdir and an identical selection.

The second face of the same seam, ported unchanged from OMN-17564: the
execution ssh carried ``ConnectTimeout=6`` and nothing else, while EVERY probe
ssh in the same file is ``timeout(1)``-wrapped. ``ConnectTimeout`` governs the
handshake only, so a host that wedges AFTER connect holds the lane forever.

What is pinned here:

* The argv file shipped to the remote host carries the execution policy --
  ``--dist=loadgroup --timeout=60 --timeout-method=signal`` and an ``-n<N>``.
* ``N`` is resolved from the SELECTED ROW's ``cores`` column, capped, never a
  hardcoded 4: a 2-core row gets ``-n2``, not four workers on two cores.
* The policy flags never make an EMPTY selection look non-empty -- the
  "no paths" refusal is decided on paths alone.
* The execution ssh carries ``ServerAliveInterval``/``ServerAliveCountMax``
  and is wrapped in the same ``timeout`` guard the probe legs already use.
* Expiry is not a new code path: a leg that returns no MARKER is classified
  NO EVIDENCE and the ranked walk ADVANCES to the next fit host, exactly as it
  did for an unreachable host before this change.
* The shadowing is pinned as a FACT, so if someone later deletes
  ``tests/pytest.ini`` and assumes the repo-root addopts now applies, the
  explicit flags are still proven present.

The bash is extract-and-executed against fake ``ssh``/``scp``/``timeout``
binaries that record their argv, so the assertions run THE code that ships
rather than grepping for it.
"""

from __future__ import annotations

import configparser
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "scripts" / "hooks" / "prepush_smart_tests.sh"
LIB = REPO_ROOT / "scripts" / "hooks" / "prepush_dispatch.sh"

pytestmark = pytest.mark.unit

#: The execution policy the remote leg must carry. Held here as literals so a
#: silent drop of any one of them turns this module red rather than costing
#: another 4-5x slot-occupancy multiplier nobody measures for a week.
POLICY_FLAGS = ("--dist=loadgroup", "--timeout=60", "--timeout-method=signal")

#: The cap. It is the worker count this repo's LOCAL heavy leg already runs
#: (``PREPUSH_TIMEOUT_FLAGS="-n4 --dist=loadgroup --timeout=60
#: --timeout-method=signal"``, ``prepush_smart_tests.sh``), and the same value
#: ``pyproject.toml``'s shadowed ``addopts`` declares -- i.e. this change is
#: PARITY with the policy this repo has always intended, not a new one.
XDIST_CAP = 4

# A two-row synthetic table in THIS repo's column shape: 13 columns, with no
# heavy_local/placement_tier (omnibase_infra carries those; omnibase_core has
# not ported them -- OMN-17392/OMN-17485). The two rows differ only in `cores`,
# which is the field under test.
_TABLE = (
    "#label\trole\thostname\tssh_target\tcores\tuv_abs_path\tuv_min_version"
    "\tworkroot\tslot_mode\tslots\trepos_denied\tmode\tnote\n"
    "hbig\tcapacity\thostbig\thostbig.lan\t32\t/bin/uv\t0.1.0\t/tmp/wbig"
    "\tlockdir\t1\t-\tauthorizing\tthirty-two cores\n"
    "hsmall\tcapacity\thostsmall\thostsmall.lan\t2\t/bin/uv\t0.1.0\t/tmp/wsmall"
    "\tlockdir\t1\t-\tauthorizing\ttwo cores\n"
)

_FAKE_SSH = """#!/usr/bin/env bash
printf 'SSH %s\\n' "$*" >> "$PREPUSH_TEST_LOG"
exit 0
"""

# Records its argv and copies every LOCAL source file into the capture dir, so
# the test can read the exact argv.txt that would have been shipped.
_FAKE_SCP = """#!/usr/bin/env bash
printf 'SCP %s\\n' "$*" >> "$PREPUSH_TEST_LOG"
skip_next=0
for a in "$@"; do
  if [ "$skip_next" = "1" ]; then skip_next=0; continue; fi
  case "$a" in
    -o) skip_next=1; continue ;;
    -*) continue ;;
    *:*) continue ;;
  esac
  [ -f "$a" ] && cp "$a" "$PREPUSH_TEST_CAPTURE/" 2>/dev/null
done
exit 0
"""

# Records the budget it was handed, then runs the wrapped command, so wrapping
# is proven without making every test wait on a real timeout(1).
_FAKE_TIMEOUT = """#!/usr/bin/env bash
printf 'TIMEOUT %s\\n' "$*" >> "$PREPUSH_TEST_LOG"
shift
exec "$@"
"""


def _extract_function(source: str, name: str) -> str:
    lines = source.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.startswith(f"{name}() {{")),
        None,
    )
    assert start is not None, f"{name}() not found"
    end = next((i for i in range(start + 1, len(lines)) if lines[i] == "}"), None)
    assert end is not None, f"unterminated {name}()"
    return "\n".join(lines[start : end + 1])


def _synth_repo(tmp_path: Path, name: str = "synth") -> Path:
    """A throwaway git repo whose HEAD carries the two-row table above.

    The library reads the host table from HEAD, never the working tree, so the
    repo has to be real and committed.
    """
    repo = tmp_path / name
    (repo / "scripts" / "hooks").mkdir(parents=True)
    (repo / "scripts" / "hooks" / "prepush_hosts.tsv").write_text(
        _TABLE, encoding="utf-8"
    )
    (repo / "README.md").write_text("synthetic tree\n", encoding="utf-8")
    # Every `git` call here passes env=scrub_git_location_env(os.environ)
    # (OMN-14891). GIT_DIR / GIT_WORK_TREE / GIT_INDEX_FILE are exported into
    # every process a git hook spawns and OVERRIDE both `cwd=` and `-C`, and
    # this module runs under the pre-push hook -- so an unscrubbed call would
    # `git init` and COMMIT into the real invoking worktree rather than
    # tmp_path. Spelled out at each call site so the guard can verify it
    # statically.
    subprocess.run(
        ["git", "init", "-q", "."],
        cwd=repo,
        check=True,
        env=scrub_git_location_env(os.environ),
    )
    subprocess.run(
        ["git", "add", "-A"],
        cwd=repo,
        check=True,
        env=scrub_git_location_env(os.environ),
    )
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "table"],
        cwd=repo,
        check=True,
        env=scrub_git_location_env(os.environ),
    )
    return repo


def _fake_bin(tmp_path: Path) -> Path:
    binbase = tmp_path / "fakebin"
    binbase.mkdir()
    for name, body in (
        ("ssh", _FAKE_SSH),
        ("scp", _FAKE_SCP),
        ("timeout", _FAKE_TIMEOUT),
    ):
        p = binbase / name
        p.write_text(body, encoding="utf-8")
        p.chmod(0o755)
    return binbase


def _run(
    repo_root: Path,
    body: str,
    env: dict[str, str] | None = None,
    extra_prelude: str = "",
) -> subprocess.CompletedProcess[str]:
    """Run BODY with the real library sourced and the hook's own callbacks stubbed."""
    bash = shutil.which("bash")
    assert bash is not None, "bash not available"
    script = f"""
set -uo pipefail
REPO_ROOT={repo_root}
PREPUSH_LOAD_THRESHOLD=1.0
log() {{ printf '[t] %s\\n' "$1" >&2; }}
die() {{ printf 'DIE: %s\\n' "$1" >&2; exit 1; }}
host_load_ratio() {{ printf '2.40 12 0.20\\n'; }}
# The real resolver, copied from the hook that sources this library. It picks
# the fake `timeout` this harness puts first on PATH.
_prepush_timeout_cmd() {{
  if command -v timeout > /dev/null 2>&1; then printf 'timeout'
  elif command -v gtimeout > /dev/null 2>&1; then printf 'gtimeout'
  fi
}}
. {LIB}
{extra_prelude}
{body}
"""
    return subprocess.run(
        [bash, "-c", script],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
        stdin=subprocess.DEVNULL,
        env={
            **os.environ,
            "PREPUSH_LOAD_OVERRIDE_MAP": "",
            "PREPUSH_SLOT_OVERRIDE_MAP": "",
            "PREPUSH_UV_OVERRIDE_MAP": "",
            **(env or {}),
        },
    )


def _leg_env(tmp_path: Path, **extra: str) -> dict[str, str]:
    binbase = _fake_bin(tmp_path)
    capture = tmp_path / "capture"
    capture.mkdir()
    log = tmp_path / "calls.log"
    log.write_text("", encoding="utf-8")
    base = {
        "PATH": f"{binbase}{os.pathsep}{os.environ.get('PATH', '')}",
        "PREPUSH_TEST_LOG": str(log),
        "PREPUSH_TEST_CAPTURE": str(capture),
        "PREPUSH_LOAD_OVERRIDE_MAP": "hbig=0.20,hsmall=0.20",
        "PREPUSH_UV_OVERRIDE_MAP": "hbig=9.9.9,hsmall=9.9.9",
        "PREPUSH_SLOT_OVERRIDE_MAP": "hbig=free,hsmall=free",
    }
    base.update(extra)
    return base


# =============================================================================
# 0. The root cause this port exists to close: the repo-root addopts is SHADOWED
# =============================================================================


def test_the_repo_root_addopts_declares_the_policy_the_remote_leg_needs() -> None:
    """``pyproject.toml`` is not the problem -- it already declares the policy.

    Pinned so the next reader does not "fix" this by adding flags to a block
    that is already correct and already ignored.
    """
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    addopts = data["tool"]["pytest"]["ini_options"]["addopts"]
    assert f"-n{XDIST_CAP}" in addopts, addopts
    for flag in POLICY_FLAGS:
        assert flag in addopts, f"{flag} missing from repo-root addopts: {addopts}"


def test_tests_pytest_ini_shadows_that_addopts_and_declares_none_of_it() -> None:
    """The mechanism, asserted rather than described (OMN-14967's root cause).

    Both legs invoke pytest with ``tests/`` as the argument, so config
    discovery starts in ``tests/`` and stops at this file -- ``pytest.ini``
    outranks ``pyproject.toml`` and the two do NOT merge. Live confirmation
    from h105 on 2026-09-02: the dispatched suite's own log header read
    ``rootdir: .../tree/tests`` / ``configfile: pytest.ini``.

    If this file is ever deleted the assertion below flips and this test says
    so plainly -- the explicit-flag guarantee further down does not depend on
    it either way, which is the point of passing the flags on the argv.
    """
    ini_path = REPO_ROOT / "tests" / "pytest.ini"
    assert ini_path.is_file(), (
        "tests/pytest.ini is gone -- re-read this module's docstring: the "
        "remote leg's flags are on the argv precisely so config discovery "
        "cannot decide the policy either way"
    )
    parser = configparser.ConfigParser()
    parser.read(ini_path, encoding="utf-8")
    shadowing_addopts = parser["pytest"].get("addopts", "")
    assert "-n" not in shadowing_addopts, shadowing_addopts
    for flag in POLICY_FLAGS:
        assert flag not in shadowing_addopts, (
            f"{flag} is in tests/pytest.ini now; this module's premise moved"
        )


# =============================================================================
# 1. Worker count is resolved from the selected row, capped, never hardcoded
# =============================================================================


@pytest.mark.parametrize(
    ("cores", "expected"),
    [
        ("2", 2),  # a small row is NEVER oversubscribed to the cap
        ("4", 4),
        ("10", XDIST_CAP),
        ("12", XDIST_CAP),
        ("32", XDIST_CAP),
        ("", 1),  # unresolvable -> today's single-worker behavior, never the cap
        ("-", 1),
        ("many", 1),
        ("0", 1),
    ],
)
def test_worker_count_is_min_of_the_rows_cores_and_the_cap(
    tmp_path: Path, cores: str, expected: int
) -> None:
    """``-n`` follows the TARGET host, not the pushing host.

    A fixed ``-n4`` would under-use a 32-core row and oversubscribe a 2-core
    one; an unresolvable ``cores`` field degrades to one worker (exactly what
    shipped before this change) rather than guessing headroom -- the same
    fail-closed posture the load and slot probes already carry.
    """
    repo = _synth_repo(tmp_path)
    out = _run(
        repo,
        f'PREPUSH_PICK_CORES="{cores}"\nprepush_remote_xdist_workers',
    )
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.strip() == str(expected), out.stdout + out.stderr


def test_the_flag_block_carries_the_whole_execution_policy(tmp_path: Path) -> None:
    repo = _synth_repo(tmp_path)
    out = _run(repo, 'PREPUSH_PICK_CORES="32"\nprepush_remote_pytest_flags')
    assert out.returncode == 0, out.stdout + out.stderr
    emitted = [line for line in out.stdout.splitlines() if line]
    for flag in POLICY_FLAGS:
        assert flag in emitted, f"{flag} missing from {emitted}"
    assert f"-n{XDIST_CAP}" in emitted, emitted


def test_the_picker_publishes_the_selected_rows_core_count(tmp_path: Path) -> None:
    """``PREPUSH_PICK_CORES`` is what the worker count is resolved from, so the
    picker has to publish it alongside every other ``PREPUSH_PICK_*`` field."""
    repo = _synth_repo(tmp_path)
    out = _run(
        repo,
        "pick_capacity_host somewhereelse synth authorizing\n"
        'echo "PICK=${PREPUSH_PICK_LABEL} CORES=${PREPUSH_PICK_CORES}"',
        env=_leg_env(tmp_path),
    )
    match = re.search(r"PICK=(\w+)", out.stdout)
    assert match, out.stdout + out.stderr
    label = match.group(1)
    expected = "32" if label == "hbig" else "2"
    assert f"CORES={expected}" in out.stdout, out.stdout + out.stderr


def test_the_cores_field_does_not_disturb_the_ranking_key(tmp_path: Path) -> None:
    """``cores`` is APPENDED, behind every field the ranking reads.

    Index divergence from omnibase_infra is deliberate: infra reads ``cores``
    at f11 because its record carries a ``tier_rank`` at f10
    (OMN-17392/OMN-17485), which this repo has not ported -- so here the record
    is nine fields and ``cores`` lands at f10. The coupling the remote leg
    actually has is to the NAME ``PREPUSH_PICK_CORES``, which is identical in
    both.

    The records are sorted on field 1 (the load ratio) alone in this repo, so
    appending must not change which host wins. Both synthetic rows are pinned
    to the same ratio here, which means the ONLY way a specific host could be
    selected is the append order -- i.e. the sort is proven not to have started
    keying on the new column.
    """
    repo = _synth_repo(tmp_path)
    out = _run(
        repo,
        "pick_capacity_host somewhereelse synth authorizing\n"
        'printf "%s\\n" "$PREPUSH_FIT_RECORDS"',
        env=_leg_env(tmp_path),
    )
    records = [line for line in out.stdout.splitlines() if "|" in line]
    assert len(records) == 2, out.stdout + out.stderr
    for record in records:
        fields = record.split("|")
        assert len(fields) == 10, record
        assert fields[9] in {"32", "2"}, record


# =============================================================================
# 2. The argv FILE that is shipped carries the policy
# =============================================================================


def _dispatch_one_leg(
    tmp_path: Path, cores: str = "32", body_extra: str = ""
) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
    """Drive the real ``prepush_remote_run`` against fake ssh/scp/timeout.

    Nothing writes a MARKER, so the leg lands on the NO-EVIDENCE branch -- the
    branch an expired or wedged host also lands on.
    """
    repo = _synth_repo(tmp_path)
    env = _leg_env(tmp_path)
    out = _run(
        repo,
        "IS_FULL=True\n"
        'FULL_SUITE_TARGET="tests/"\n'
        "RUNNABLE_INTEGRATION_PATHS=()\n"
        "PATHS=()\n"
        'PREPUSH_PICK_LABEL="hbig"\n'
        'PREPUSH_PICK_HOSTNAME="hostbig"\n'
        'PREPUSH_PICK_SSH="hostbig.lan"\n'
        'PREPUSH_PICK_UV="/bin/uv"\n'
        'PREPUSH_PICK_WORKROOT="/tmp/wbig"\n'
        'PREPUSH_PICK_SLOTMODE="lockdir"\n'
        'PREPUSH_PICK_MODE="authorizing"\n'
        'PREPUSH_PICK_SLOT="1"\n'
        'PREPUSH_PICK_RATIO="0.20"\n'
        'PREPUSH_PROBE_LOG="hbig=fit"\n'
        f'PREPUSH_PICK_CORES="{cores}"\n'
        f"{body_extra}"
        'rc=0; prepush_remote_run "full-suite escalation" || rc=$?\n'
        'echo "RC=${rc}"',
        env=env,
    )
    return out, Path(env["PREPUSH_TEST_CAPTURE"]), Path(env["PREPUSH_TEST_LOG"])


def test_the_shipped_argv_file_carries_paths_then_the_execution_policy(
    tmp_path: Path,
) -> None:
    out, capture, _ = _dispatch_one_leg(tmp_path, cores="32")
    argv = (capture / "argv.txt").read_text(encoding="utf-8").splitlines()
    assert argv, out.stdout + out.stderr
    # The selection still leads, byte-identical to what it always was: the
    # policy is APPENDED, so it can never displace or reorder a test path.
    assert argv[0] == "tests/", argv
    for flag in POLICY_FLAGS:
        assert flag in argv, f"{flag} missing from shipped argv {argv}"
    assert f"-n{XDIST_CAP}" in argv, argv


def test_the_shipped_worker_count_follows_a_small_row_down(tmp_path: Path) -> None:
    """End-to-end, not just at the helper: a 2-core row ships ``-n2``."""
    _, capture, _ = _dispatch_one_leg(tmp_path, cores="2")
    argv = (capture / "argv.txt").read_text(encoding="utf-8").splitlines()
    assert "-n2" in argv, argv
    assert f"-n{XDIST_CAP}" not in argv, argv


def test_the_selection_paths_receipt_field_stays_paths_only(tmp_path: Path) -> None:
    """``prepush_remote_argv`` is the SELECTION, and the receipt records it under
    ``selection_paths``. Folding execution flags into it would make an audit of
    "what did that host actually run" read flags as coverage."""
    repo = _synth_repo(tmp_path)
    out = _run(
        repo,
        "IS_FULL=True\n"
        'FULL_SUITE_TARGET="tests/"\n'
        "RUNNABLE_INTEGRATION_PATHS=()\n"
        "PATHS=()\n"
        'PREPUSH_PICK_CORES="32"\n'
        "prepush_remote_argv",
    )
    assert out.stdout.splitlines() == ["tests/"], out.stdout + out.stderr


def test_the_policy_flags_cannot_make_an_empty_selection_look_runnable(
    tmp_path: Path,
) -> None:
    """The "nothing selected" refusal is decided on PATHS alone.

    If the flags were written before the emptiness check, a selection that
    resolved to zero paths would ship an argv file of pure flags -- pytest
    would then collect ``testpaths`` from the transplanted tree's own config
    (``tests/pytest.ini`` declares ``testpaths = unit integration``), silently
    running something nobody selected and reporting it as this push's evidence.
    """
    out, capture, log = _dispatch_one_leg(
        tmp_path,
        cores="32",
        body_extra='IS_FULL=False\nPATHS=()\nFULL_SUITE_TARGET="tests/"\n',
    )
    assert "RC=1" in out.stdout, out.stdout + out.stderr
    assert not (capture / "argv.txt").exists(), "an empty selection was shipped"
    assert "SCP" not in log.read_text(encoding="utf-8")


# =============================================================================
# 3. The execution ssh is liveness-bounded
# =============================================================================


def test_the_execution_ssh_carries_keepalives_and_a_timeout_guard(
    tmp_path: Path,
) -> None:
    """``ConnectTimeout`` governs the handshake only.

    The leg that sat 5h29m on a wedged h105 had connected successfully; what it
    lacked was any bound on SILENCE after that. Keepalives bound the transport
    and the ``timeout`` wrapper bounds the whole run, mirroring the probe legs
    in this same file which are all ``timeout``-wrapped already.
    """
    out, _, log = _dispatch_one_leg(tmp_path)
    calls = log.read_text(encoding="utf-8").splitlines()
    exec_calls = [
        c for c in calls if "prepush_smart_tests.sh" in c and c.startswith("SSH")
    ]
    assert exec_calls, f"no execution ssh recorded: {calls}\n{out.stderr}"
    execline = exec_calls[0]
    assert "ServerAliveInterval=" in execline, execline
    assert "ServerAliveCountMax=" in execline, execline

    wrapped = [c for c in calls if c.startswith("TIMEOUT") and "ssh" in c]
    assert wrapped, f"the execution ssh was not wrapped in the timeout guard: {calls}"
    budget = wrapped[0].split()[1]
    assert budget.isdigit() and int(budget) > 0, wrapped[0]


def test_the_execution_ssh_runs_unwrapped_when_no_timeout_binary_exists(
    tmp_path: Path,
) -> None:
    """``timeout(1)`` ships on neither Mac in the lab by default.

    Its absence must degrade to the keepalive bound alone -- which still closes
    the wedged-host case -- rather than refusing to dispatch at all.
    """
    repo = _synth_repo(tmp_path)
    env = _leg_env(tmp_path)
    out = _run(
        repo,
        "IS_FULL=True\n"
        'FULL_SUITE_TARGET="tests/"\n'
        "RUNNABLE_INTEGRATION_PATHS=()\n"
        "PATHS=()\n"
        'PREPUSH_PICK_LABEL="hbig"\n'
        'PREPUSH_PICK_HOSTNAME="hostbig"\n'
        'PREPUSH_PICK_SSH="hostbig.lan"\n'
        'PREPUSH_PICK_UV="/bin/uv"\n'
        'PREPUSH_PICK_WORKROOT="/tmp/wbig"\n'
        'PREPUSH_PICK_SLOTMODE="lockdir"\n'
        'PREPUSH_PICK_MODE="authorizing"\n'
        'PREPUSH_PICK_SLOT="1"\n'
        'PREPUSH_PICK_RATIO="0.20"\n'
        'PREPUSH_PROBE_LOG="hbig=fit"\n'
        'PREPUSH_PICK_CORES="32"\n'
        'rc=0; prepush_remote_run "full-suite escalation" || rc=$?\n'
        'echo "RC=${rc}"',
        env=env,
        extra_prelude="_prepush_timeout_cmd() { printf ''; }\n",
    )
    calls = Path(env["PREPUSH_TEST_LOG"]).read_text(encoding="utf-8").splitlines()
    exec_calls = [
        c for c in calls if "prepush_smart_tests.sh" in c and c.startswith("SSH")
    ]
    assert exec_calls, f"no execution ssh recorded: {calls}\n{out.stderr}"
    assert "ServerAliveInterval=" in exec_calls[0], exec_calls[0]
    assert not [c for c in calls if c.startswith("TIMEOUT")], calls


# =============================================================================
# 4. Expiry falls through to the EXISTING no-evidence classification
# =============================================================================


def test_a_leg_that_writes_no_marker_is_no_evidence_not_a_verdict(
    tmp_path: Path,
) -> None:
    out, _, _ = _dispatch_one_leg(tmp_path)
    assert "RC=1" in out.stdout, out.stdout + out.stderr
    assert "NO completion marker" in out.stderr, out.stderr
    assert "not a pass, not a failure" in out.stderr, out.stderr


def test_the_ranked_walk_advances_past_a_leg_that_produced_no_marker(
    tmp_path: Path,
) -> None:
    """Timing a host out must cost the NEXT host, not the whole escalation.

    This is the property that makes the ``timeout`` wrapper safe to add: it
    creates no new classification. An expired leg returns exactly what an
    unreachable-on-arrival leg has always returned, and ``dispatch_to_lab_host``
    already treats that as a PLACEMENT miss.
    """
    repo = _synth_repo(tmp_path)
    env = _leg_env(tmp_path)
    out = _run(
        repo,
        "IS_FULL=True\n"
        'FULL_SUITE_TARGET="tests/"\n'
        "RUNNABLE_INTEGRATION_PATHS=()\n"
        "PATHS=()\n"
        'PREPUSH_LC_HOST="somewhereelse"\n'
        'rc=0; dispatch_to_lab_host "full-suite escalation" || rc=$?\n'
        'echo "RC=${rc}"',
        env=env,
        extra_prelude=_extract_function(
            HOOK.read_text(encoding="utf-8"), "dispatch_to_lab_host"
        ),
    )
    assert "RC=1" in out.stdout, out.stdout + out.stderr
    # BOTH fit candidates were tried -- the walk did not stop at the first
    # silent host, and it did not forge a verdict from either.
    assert "hbig" in out.stderr and "hsmall" in out.stderr, out.stderr
    assert "no fit lab host produced a verdict" in out.stderr, out.stderr
    assert "REMOTE LAB RUN PASS" not in out.stderr, out.stderr


# =============================================================================
# 4b. The flags actually WIN against the config-discovery shadow
# =============================================================================


def test_argv_flags_beat_the_inifile_shadow_that_ate_the_repo_addopts(
    tmp_path: Path,
) -> None:
    """The bug lives one level below "did we append the flags".

    Everything above proves the flags reach ``argv.txt``. This proves they
    still WIN once pytest resolves its config on the remote host -- which is
    the exact step that silently discarded the repo-root ``addopts`` in the
    first place. Reproduced hermetically in a synthetic tree with the same
    shape as the transplanted one: a repo-root ``pyproject.toml`` declaring
    ``-n4``, and a ``tests/pytest.ini`` declaring an ``addopts`` without it.

    Both halves are asserted, because only the pair is evidence:

    * invoked the OLD way (paths only), pytest reports ``configfile:
      pytest.ini``, spins NO xdist workers and arms NO timeout -- the defect,
      reproduced.
    * invoked the NEW way (paths + this leg's policy flags), the same tree
      reports the same ``configfile`` and DOES spin workers and arm the
      signal-method timeout -- the shadow is still there, and the flags beat
      it anyway.

    That second point is why this fix is correct independently of whether
    ``tests/pytest.ini`` is ever merged away: argv outranks every ini file.
    """
    tree = tmp_path / "tree"
    (tree / "tests").mkdir(parents=True)
    (tree / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\naddopts = ["-n4"]\n', encoding="utf-8"
    )
    # The shadowing file, same shape as this repo's: an addopts with no -n.
    (tree / "tests" / "pytest.ini").write_text(
        "[pytest]\naddopts =\n    --tb=short\n    --strict-markers\n",
        encoding="utf-8",
    )
    (tree / "tests" / "test_synthetic.py").write_text(
        "def test_one() -> None:\n    assert True\n\n\n"
        "def test_two() -> None:\n    assert True\n",
        encoding="utf-8",
    )

    def _run_pytest(extra: list[str]) -> str:
        # `sys.executable -m pytest`, NOT `uv run pytest`. The synthetic tree
        # is deliberately not a uv project -- its pyproject.toml carries only
        # `[tool.pytest.ini_options]`, because a `[project]` table is exactly
        # what this fixture must NOT have to reproduce the shadow. `uv run`
        # refuses such a tree outright ("No `project` table found in ...") on
        # the uv that CI resolves, and worse, pointing UV_PROJECT_ENVIRONMENT
        # at the real repo venv invites `uv run` to sync a throwaway fixture
        # project INTO the venv running this suite. The interpreter already
        # executing this test has pytest, xdist and pytest-timeout available
        # by construction, so invoking it directly is both hermetic and
        # uv-version-independent.
        env = {k: v for k, v in os.environ.items() if not k.startswith("PYTEST_")}
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "--tb=short", *extra],
            cwd=tree,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
            env=env,
        )
        return completed.stdout + completed.stderr

    # The defect, reproduced: the repo-root -n4 is discarded outright. xdist
    # announces its pool as "N workers [...]" on the header line, so its
    # ABSENCE is the single-threaded run this ticket exists to end.
    before = _run_pytest([])
    assert "configfile: pytest.ini" in before, before
    assert "workers" not in before, (
        "the synthetic tree did not reproduce the shadow -- the repo-root "
        f"-n4 was honoured, so this test proves nothing:\n{before}"
    )
    assert "timeout method" not in before, before

    # The fix: the same shadow, the same tree, flags on the argv.
    after = _run_pytest([f"-n{XDIST_CAP}", *POLICY_FLAGS])
    assert "configfile: pytest.ini" in after, after
    assert f"created: {XDIST_CAP}/{XDIST_CAP} workers" in after, (
        "the -n did NOT survive config discovery -- putting the policy on the "
        f"argv is exactly what this change relies on:\n{after}"
    )
    # The watchdog half of the policy has to survive the same shadow, and it
    # is the half that silently does nothing when it does not.
    assert "timeout: 60.0s" in after, after
    assert "timeout method: signal" in after, after


# =============================================================================
# 5. The policy must be HONOURABLE on the transplanted tree
# =============================================================================


def test_the_shipped_flags_are_backed_by_declared_test_dependencies() -> None:
    """A flag the remote environment cannot honour is a FALSE RED, and a false
    red on this leg HARD-BLOCKS the push.

    The remote wrapper materializes the tree with ``uv sync --all-extras``,
    which installs this project's default dependency groups. ``-n``/``--dist``
    come from ``pytest-xdist`` and ``--timeout``/``--timeout-method`` from
    ``pytest-timeout``; if either is dropped from the declared groups, pytest
    exits on "unrecognized arguments" on EVERY dispatched suite and every
    escalation becomes a refusal. Pin the coupling rather than discover it on a
    host at 02:00.

    Live corroboration that the sync does install them: the h105 run's own
    suite.log header on 2026-09-02 listed ``xdist-3.8.0`` and ``timeout-2.4.0``
    among its loaded plugins -- the plugins were present, only the FLAGS were
    missing.
    """
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dev = data["dependency-groups"]["dev"]
    names = {re.split(r"[<>=!~\[ ]", spec, maxsplit=1)[0] for spec in dev}
    assert "pytest-xdist" in names, "-n/--dist are shipped to the remote leg"
    assert "pytest-timeout" in names, "--timeout/--timeout-method are shipped"


def test_the_remote_pytest_invocation_is_otherwise_unchanged() -> None:
    """The policy is ADDITIVE. The remote wrapper still ignores
    ``tests/integration`` (the leg deliberately excludes service-dependent
    suites) and still shortens tracebacks; nothing about the invocation moved
    except the argv it is handed."""
    lib = LIB.read_text(encoding="utf-8")
    assert (
        '"$UV" run pytest "${ARGV[@]}" --ignore=tests/integration --tb=short' in lib
    ), "the remote pytest invocation changed shape"


def test_the_policy_is_constants_not_env_indirection() -> None:
    """``PREPUSH_*`` env overrides are forbidden by the hook (OMN-16480), and
    the ``-n4`` local flags are already a bare constant for the same reason: an
    env indirection here would let ``PREPUSH_REMOTE_XDIST_WORKER_CAP=1`` restore
    the single-threaded defect in one word, silently."""
    lib = LIB.read_text(encoding="utf-8")
    for const in (
        "PREPUSH_REMOTE_POLICY_FLAGS",
        "PREPUSH_REMOTE_XDIST_WORKER_CAP",
        "PREPUSH_REMOTE_SSH_ALIVE_INTERVAL_SECONDS",
        "PREPUSH_REMOTE_SSH_ALIVE_COUNT_MAX",
        "PREPUSH_REMOTE_EXEC_TIMEOUT_SECONDS",
    ):
        assert re.search(rf"^{const}=[^$]", lib, re.MULTILINE), (
            f"{const} must be a bare constant, not a ${{VAR:-...}} indirection"
        )


def test_the_remote_policy_matches_the_local_legs_policy() -> None:
    """PARITY IS THE WHOLE CLAIM.

    The remote leg is not being given a new configuration -- it is being given
    the one ``PREPUSH_TIMEOUT_FLAGS`` has always given the local leg. If the
    local leg's policy is ever changed without the remote leg following, the
    two legs stop being interchangeable evidence for the same gate, and this
    test says so.
    """
    hook = HOOK.read_text(encoding="utf-8")
    match = re.search(r'^PREPUSH_TIMEOUT_FLAGS="([^"]*)"', hook, re.MULTILINE)
    assert match, "PREPUSH_TIMEOUT_FLAGS assignment not found in the hook"
    local_flags = match.group(1).split()
    lib = LIB.read_text(encoding="utf-8")
    remote_match = re.search(
        r'^PREPUSH_REMOTE_POLICY_FLAGS="([^"]*)"', lib, re.MULTILINE
    )
    assert remote_match, "PREPUSH_REMOTE_POLICY_FLAGS assignment not found"
    remote_flags = set(remote_match.group(1).split())
    for flag in local_flags:
        if flag.startswith("-n"):
            # The worker count is the ONE deliberate divergence: the local leg
            # sizes it for THIS machine, the remote leg for the target row.
            assert flag == f"-n{XDIST_CAP}", (
                "the local leg's worker count moved; re-derive "
                f"PREPUSH_REMOTE_XDIST_WORKER_CAP against it (local: {flag})"
            )
            continue
        assert flag in remote_flags, (
            f"the local leg runs {flag} and the remote leg does not -- the two "
            "legs are no longer interchangeable evidence for the same gate"
        )
