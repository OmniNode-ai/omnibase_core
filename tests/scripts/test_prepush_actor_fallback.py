# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The governed pre-push dispatcher must work for an actor who is not the lab's
owner (OMN-17280).

THE DEFECT, reproduced live before any of this was written. Every
``ssh_target`` in ``scripts/hooks/prepush_hosts.tsv`` hardcoded one operator's
login, so for any other actor every remote row answered
``Permission denied (publickey,password)``. Re-measured 2026-09-02 against
THIS repo's own committed table, one ssh per capacity row, non-owner login::

    h200  ...tail75df5e.ts.net   rc=255  0s  Permission denied (publickey,password,keyboard-interactive).
    h201  192.168.86.201         rc=255  0s  Permission denied (publickey,password).
    h101  192.168.86.101         rc=255  0s  Permission denied (publickey,password,keyboard-interactive).
    h105  192.168.86.105         rc=255  1s  Permission denied (publickey,password,keyboard-interactive).

The actor's OWN host still probed ``fit``, but ``dispatch_to_lab_host`` skips a
self candidate (it carries no ssh target), so the ranked walk executed nothing
and the refusal ladder fell through to ``die()``. That trace was captured
2026-09-01 by driving the SHARED picker library from omnibase_infra, whose copy
of this file is the upstream this repo vendors -- the ``tier=`` field is that
repo's OMN-17485 column, which this repo's table does not yet carry::

    PROBE_LOG=h200=slot-unknown h201=fit(0.10,authorizing,40000MiB,tier=last_resort)
    WALK idx=1 label=h201 -> SKIPPED (self candidate, no ssh target)
    CANDIDATE_COUNT=1  REMOTE_LEG_EXECUTED=0

The self-skip is not inherited by assumption: it is pinned here against the
copy THIS repo ships, by
``test_the_same_host_route_fires_when_no_lab_host_is_reachable_for_the_actor``
and ``test_one_reachable_lab_host_closes_the_same_host_route``.

A second, independent defect fed the same refusal: ``prepush_lock_acquire``
reported EACCES on a workroot the actor cannot write as rc=1 (CONTENDED), so
the caller printed "this host is fit but its heavy-suite slot is already held"
-- measurably false, and the exact shape every non-owner hits on every push.

What is pinned here:

1. No capacity row may hardcode an ssh login, and the picker must parse a row
   whose ``ssh_target`` carries no user field.
2. Reachability is measured for THIS actor, not assumed from the table.
3. The same-host route fires only when NO capacity row is reachable, so one
   reachable lab host keeps the OMN-17392 / OMN-17485 off-box preference
   exactly as it shipped.
4. It refuses itself on identity (a host absent from the table) and on genuine
   slot contention (OMN-16174 serialization wins).
5. It writes a receipt naming the reason, so a same-host run is auditable
   rather than believed.
6. It sits ABOVE the override grant in the ladder -- it produces a real full
   suite on a designated host, which is stronger evidence than a grant, and it
   burns no grant to get there.

The bash is extract-and-executed, the pattern this hook's other shell tests
already use, so the assertions run THE code that ships.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from omnibase_core.validators.no_unguarded_git_subprocess import (
    scrub_git_location_env,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "scripts" / "hooks" / "prepush_smart_tests.sh"
LIB = REPO_ROOT / "scripts" / "hooks" / "prepush_dispatch.sh"
TABLE = REPO_ROOT / "scripts" / "hooks" / "prepush_hosts.tsv"

pytestmark = pytest.mark.unit


def _rows() -> list[list[str]]:
    rows = []
    for line in TABLE.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0]
        if not line.strip():
            continue
        rows.append(line.split("\t"))
    return rows


# =============================================================================
# 1. The table carries a HOST, never a login
# =============================================================================


def test_no_capacity_row_hardcodes_an_ssh_login() -> None:
    """``ssh_target`` is a host. ssh(1) resolves the login from ``~/.ssh/config``
    or the invoking account, so each actor reaches the lab as themselves.

    A ``user@`` here is not a style question: it pins every execution target to
    one person's credentials, and the picker then reports the whole lab
    unreachable for everybody else while their own fit host goes unused. This
    assertion is what stops the next row from quietly reintroducing it."""
    for row in _rows():
        if row[1] != "capacity":
            continue
        assert "@" not in row[3], (
            f"{row[0]}: ssh_target {row[3]!r} hardcodes a login. Use the bare "
            "host and let ssh(1) resolve the user from ~/.ssh/config or the "
            "invoking account (OMN-17280)."
        )


def test_identity_rows_carry_no_execution_target() -> None:
    """An ``identity`` row is never an execution target, so it must not carry
    one -- the same rule as before OMN-17280, re-pinned because the column
    changed shape."""
    for row in _rows():
        if row[1] != "identity":
            continue
        assert row[3] == "-", f"{row[0]}: identity rows carry '-', got {row[3]!r}"


# =============================================================================
# Extract-and-execute harness
# =============================================================================

#: Bare-host ``ssh_target`` values on purpose: the parsing this fixture proves
#: is the post-OMN-17280 shape, where no row names a user.
_TABLE_NO_USER_FIELD = (
    "#label\trole\thostname\tssh_target\tcores\tuv_abs_path\tuv_min_version"
    "\tworkroot\tslot_mode\tslots\trepos_denied\tmode\tnote\n"
    "hme\tcapacity\thostme\thostme.lan\t24\t/bin/uv\t0.1.0\t{workroot}"
    "\tlockdir\t1\t-\tauthorizing\tthe actor is on this one\n"
    "hfar\tcapacity\thostfar\thostfar.lan\t24\t/bin/uv\t0.1.0\t/tmp/wfar"
    "\tlockdir\t1\t-\tauthorizing\tsomewhere else in the lab\n"
)


def _repo_with_table(tmp_path: Path, table_text: str, name: str = "synth") -> Path:
    repo = tmp_path / name
    (repo / "scripts" / "hooks").mkdir(parents=True)
    (repo / "scripts" / "hooks" / "prepush_hosts.tsv").write_text(
        table_text, encoding="utf-8"
    )
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


def _run(
    repo_root: Path, body: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run BODY with the real library sourced and the hook's own dependencies
    stubbed.

    ``stdin`` is /dev/null for the same reason the sibling harness does it: the
    probes this file drives must never be able to eat a caller's stdin.
    """
    script = f"""
set -uo pipefail
REPO_ROOT={repo_root}
PREPUSH_LOAD_THRESHOLD=1.0
PREPUSH_MIN_FREE_MEM_MB=4096
log() {{ printf '[t] %s\\n' "$1" >&2; }}
die() {{ printf 'DIE: %s\\n' "$1" >&2; exit 1; }}
_prepush_timeout_cmd() {{ printf ''; }}
host_load_ratio() {{ printf '2.40 12 0.20 40960\n'; }}
. {LIB}
{body}
"""
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        stdin=subprocess.DEVNULL,
        env={
            **os.environ,
            "PREPUSH_LOAD_OVERRIDE_MAP": "",
            "PREPUSH_SLOT_OVERRIDE_MAP": "",
            "PREPUSH_MEM_OVERRIDE_MAP": "",
            "PREPUSH_REACH_OVERRIDE_MAP": "",
            **(env or {}),
        },
    )


def _actor_env(**extra: str) -> dict[str, str]:
    """The env an actor-route driver needs: a measurement for the local row and
    no real network anywhere."""
    base = {
        "PREPUSH_LOAD_OVERRIDE_MAP": "hme=0.20,hfar=0.20",
        "PREPUSH_MEM_OVERRIDE_MAP": "hme=40000,hfar=40000",
        "PREPUSH_UV_OVERRIDE_MAP": "hme=9.9.9,hfar=9.9.9",
        "PREPUSH_SLOT_OVERRIDE_MAP": "hme=free,hfar=free",
    }
    base.update(extra)
    return base


@pytest.fixture
def actor_repo(tmp_path: Path) -> Path:
    """A throwaway repo whose HEAD carries a two-row table with bare hosts and a
    workroot this test owns."""
    workroot = tmp_path / "workroot"
    workroot.mkdir()
    return _repo_with_table(
        tmp_path, _TABLE_NO_USER_FIELD.format(workroot=workroot), name="actor"
    )


# =============================================================================
# 2. Table parsing with no user field
# =============================================================================


def test_the_picker_ranks_a_row_whose_ssh_target_has_no_user_field(
    actor_repo: Path,
) -> None:
    """The bare host must survive parsing and reach ``PREPUSH_PICK_SSH``
    verbatim -- that string is what ssh(1) is handed, and ssh is what resolves
    the login."""
    out = _run(
        actor_repo,
        "pick_capacity_host hostme somerepo authorizing\n"
        'echo "PICK=${PREPUSH_PICK_LABEL} SSH=${PREPUSH_PICK_SSH}"',
        env=_actor_env(),
    )
    assert "PICK=hfar SSH=hostfar.lan" in out.stdout, out.stdout + out.stderr


# =============================================================================
# 3. Reachability is measured for THIS actor
# =============================================================================


def test_reachability_excludes_this_host_and_counts_only_reachable_rows(
    actor_repo: Path,
) -> None:
    out = _run(
        actor_repo,
        "prepush_remote_reachability hostme somerepo\n"
        'echo "N=${PREPUSH_REACHABLE_COUNT} LOG=${PREPUSH_REACHABILITY_LOG}"',
        env=_actor_env(PREPUSH_REACH_OVERRIDE_MAP="hfar=up"),
    )
    assert "N=1" in out.stdout, out.stdout + out.stderr
    # This host is reported, never counted: it is not a REMOTE target.
    assert "hme=self" in out.stdout
    assert "hfar=up" in out.stdout


def test_reachability_reports_zero_when_no_row_answers_for_this_actor(
    actor_repo: Path,
) -> None:
    out = _run(
        actor_repo,
        "prepush_remote_reachability hostme somerepo\n"
        'echo "N=${PREPUSH_REACHABLE_COUNT} LOG=${PREPUSH_REACHABILITY_LOG}"',
        env=_actor_env(PREPUSH_REACH_OVERRIDE_MAP="hfar=down"),
    )
    assert "N=0" in out.stdout, out.stdout + out.stderr
    assert "hfar=down" in out.stdout


def test_a_default_key_covers_rows_the_map_does_not_name(actor_repo: Path) -> None:
    """The test-isolation fragment relies on this: a per-label map silently
    stops covering a row that is ADDED to the table, and the failure mode of
    that gap is a unit test opening a real ssh connection to a lab host."""
    out = _run(
        actor_repo,
        "prepush_remote_reachability hostme somerepo\n"
        'echo "N=${PREPUSH_REACHABLE_COUNT}"',
        env=_actor_env(PREPUSH_REACH_OVERRIDE_MAP="default=up"),
    )
    assert "N=1" in out.stdout, out.stdout + out.stderr


# =============================================================================
# 4. The same-host route
# =============================================================================


def test_the_same_host_route_fires_when_no_lab_host_is_reachable_for_the_actor(
    actor_repo: Path,
) -> None:
    """The defect this ticket exists for: an actor on a designated host, with
    no reachable lab target, must get a governed run rather than a refusal."""
    out = _run(
        actor_repo,
        "PREPUSH_LC_HOST=hostme\n"
        'rc=0; prepush_local_actor_route "full-suite escalation" hme || rc=$?\n'
        'echo "RC=${rc}"',
        env=_actor_env(PREPUSH_REACH_OVERRIDE_MAP="hfar=down"),
    )
    assert "RC=0" in out.stdout, out.stdout + out.stderr
    assert "SAME-HOST ROUTE IN EFFECT" in out.stderr
    assert "reason=no_remote_target_reachable_for_actor" in out.stderr


def test_one_reachable_lab_host_closes_the_same_host_route(
    actor_repo: Path,
) -> None:
    """The OMN-17392 / OMN-17485 off-box preference is untouched for anyone who
    can reach the lab. This is the branch every one of the lab owner's own
    pushes takes, and it must stay a refusal so the existing ladder answers."""
    out = _run(
        actor_repo,
        "PREPUSH_LC_HOST=hostme\n"
        'rc=0; prepush_local_actor_route "full-suite escalation" hme || rc=$?\n'
        'echo "RC=${rc}"',
        env=_actor_env(PREPUSH_REACH_OVERRIDE_MAP="hfar=up"),
    )
    assert "RC=1" in out.stdout, out.stdout + out.stderr
    assert "SAME-HOST ROUTE IN EFFECT" not in out.stderr


def test_the_same_host_route_still_requires_a_designated_row(
    actor_repo: Path,
) -> None:
    """Identity is unchanged: a machine the COMMITTED table does not designate
    is exactly as unable to authorize a heavy run as it was before."""
    out = _run(
        actor_repo,
        "PREPUSH_LC_HOST=some-random-laptop\n"  # pragma: allowlist secret
        'rc=0; prepush_local_actor_route "full-suite escalation" "" || rc=$?\n'
        'echo "RC=${rc}"',
        env=_actor_env(PREPUSH_REACH_OVERRIDE_MAP="hfar=down"),
    )
    assert "RC=1" in out.stdout, out.stdout + out.stderr


def test_genuine_slot_contention_still_refuses(tmp_path: Path) -> None:
    """Contention is not a reachability problem. A slot held by a LIVE run on
    this host keeps OMN-16174 serialization: the route declines and the
    caller's existing ladder answers."""
    workroot = tmp_path / "workroot"
    (workroot / "LOCK").mkdir(parents=True)
    # A holder this process can prove is alive, so the reclaim path cannot take
    # the lock back.
    (workroot / "LOCK" / "holder").write_text(
        f"{os.getpid()} {os.uname().nodename.split('.')[0]} 2026-09-01T00:00:00Z\n",
        encoding="utf-8",
    )
    repo = _repo_with_table(
        tmp_path, _TABLE_NO_USER_FIELD.format(workroot=workroot), name="contended"
    )
    out = _run(
        repo,
        "PREPUSH_LC_HOST=hostme\n"
        'rc=0; prepush_local_actor_route "full-suite escalation" hme || rc=$?\n'
        'echo "RC=${rc}"',
        env=_actor_env(PREPUSH_REACH_OVERRIDE_MAP="hfar=down"),
    )
    assert "RC=1" in out.stdout, out.stdout + out.stderr
    assert "SAME-HOST ROUTE declined" in out.stderr


# =============================================================================
# 5. The receipt
# =============================================================================


def test_the_same_host_route_writes_a_receipt_naming_the_reason(
    actor_repo: Path,
) -> None:
    """A same-host run must be auditable rather than believed: who ran it,
    where, on what measurement, and which lab rows refused them."""
    _run(
        actor_repo,
        'PREPUSH_LC_HOST=hostme\nprepush_local_actor_route "full-suite escalation" hme',
        env=_actor_env(PREPUSH_REACH_OVERRIDE_MAP="hfar=down"),
    )
    receipts = actor_repo / ".onex_state" / "prepush_distribution" / "receipts.jsonl"
    assert receipts.is_file(), "the route must leave a receipt"
    record = json.loads(receipts.read_text(encoding="utf-8").splitlines()[-1])
    assert record["route"] == "local_actor_fallback"
    assert record["reason"] == "no_remote_target_reachable_for_actor"
    assert record["row"] == "hme"
    assert record["host"] == "hostme"
    assert record["actor"], "the receipt must name the actor it ran as"
    assert "hfar=down" in record["reachability"]
    assert record["serialization"].startswith("serialized at ")
    # The measurement must come from THIS host's reading, not from whatever the
    # placement probe left in a global (see prepush_local_actor_route).
    assert record["measured"] == "load 0.20x, mem 40960MiB"


# =============================================================================
# 6. An unwritable workroot is infrastructural, not contention
# =============================================================================


@pytest.mark.skipif(
    os.geteuid() == 0, reason="root ignores the mode bits this test depends on"
)
def test_an_unwritable_workroot_is_infrastructural_not_contention(
    tmp_path: Path, actor_repo: Path
) -> None:
    """Measured before the fix: rc=1 (CONTENDED), which made the caller print
    "this host is fit but its heavy-suite slot is already held" about a lock
    that does not exist. It is EACCES, not EEXIST -- rc=2, which the callers
    already know how to degrade through."""
    ro = tmp_path / "ro-workroot"
    ro.mkdir()
    ro.chmod(0o555)
    try:
        out = _run(
            actor_repo,
            f'rc=0; prepush_lock_acquire {ro} || rc=$?\necho "RC=${{rc}}"',
        )
        assert "RC=2" in out.stdout, out.stdout + out.stderr
    finally:
        ro.chmod(0o755)


@pytest.mark.skipif(
    os.geteuid() == 0, reason="root ignores the mode bits this test depends on"
)
def test_an_unwritable_row_workroot_falls_back_to_a_per_actor_slot(
    tmp_path: Path,
) -> None:
    """The row's workroot belongs to whoever provisioned the host. An actor
    without write access gets a per-actor workroot rather than an unserialized
    run -- strictly better than the pre-existing rc=2 behavior, which warned
    and ran with no lock at all."""
    ro = tmp_path / "row-workroot"
    ro.mkdir()
    ro.chmod(0o555)
    home = tmp_path / "actor-home"
    home.mkdir()
    repo = _repo_with_table(
        tmp_path, _TABLE_NO_USER_FIELD.format(workroot=ro), name="rowro"
    )
    try:
        out = _run(
            repo,
            "PREPUSH_LC_HOST=hostme\n"
            'rc=0; prepush_local_actor_route "full-suite escalation" hme || rc=$?\n'
            'echo "RC=${rc}"',
            env=_actor_env(PREPUSH_REACH_OVERRIDE_MAP="hfar=down", HOME=str(home)),
        )
        assert "RC=0" in out.stdout, out.stdout + out.stderr
        assert (home / ".onex-prepush" / "LOCK").is_dir(), (
            "expected a per-actor slot lock under $HOME"
        )
    finally:
        ro.chmod(0o755)


# =============================================================================
# 7. Ladder placement
# =============================================================================


def test_the_route_sits_above_the_override_grant_and_below_lab_dispatch() -> None:
    """Ordering is evidence strength, not convenience. The route must be
    reachable only after the lab produced nothing, and must be tried before a
    grant is consumed -- it produces a real full suite on a designated
    authorizing host, which is stronger than a receipted degraded-capacity
    grant, and it burns no grant to get there."""
    text = HOOK.read_text(encoding="utf-8")
    route = text.index('prepush_local_actor_route "$heavy_what" "$label"')
    dispatch = text.index('if dispatch_to_lab_host "$heavy_what"; then')
    grant = text.index('consume_override_grant "degraded-capacity:')
    assert dispatch < route < grant, (
        "the same-host route must sit between lab dispatch and the override "
        "grant in guard_full_suite_host"
    )


def test_the_route_is_opened_by_no_prepush_override() -> None:
    """The only inputs are the COMMITTED table, the actor's own ssh
    reachability, and the local slot. Nothing a pusher can export opens it."""
    text = LIB.read_text(encoding="utf-8")
    start = text.index("prepush_local_actor_route() {")
    end = text.index("\n}\n", start)
    body = text[start:end]
    for forbidden in (
        "PREPUSH_FULL_SUITE",
        "PREPUSH_ALLOW_LOCAL_FULL_SUITE",
        "ENABLE_SMART_TESTS",
        "--no-verify",
    ):
        assert forbidden not in body, (
            f"prepush_local_actor_route must not consult {forbidden}"
        )


def test_the_unserialized_degradation_consults_the_route_first() -> None:
    """The path a non-owner actually lands on.

    A workroot this process cannot write is the signature of running as
    someone other than whoever provisioned the host. Before OMN-17280 that
    read as CONTENDED and refused; with the rc=2 fix alone it would read as
    "run unserialized" and produce no receipt at all. The route is consulted
    first so the run is serialized under a per-actor slot AND carries the
    receipt naming why it ran here. It declines whenever a lab host is
    reachable, so an owner whose workroot is genuinely broken still gets the
    unserialized warning unchanged.
    """
    text = HOOK.read_text(encoding="utf-8")
    warn = text.index("could not create the heavy-suite slot lock under")
    route = text.rindex("prepush_local_actor_route", 0, warn)
    # Same `if [ "$lock_rc" -eq 2 ]` block, not somewhere far above it.
    assert "lock_rc" in text[text.rindex("lock_rc", 0, route) : warn]
    assert warn - route < 900, (
        "the route call must sit immediately before the unserialized warning"
    )
