# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Guards for lab-wide pre-push distribution (OMN-16991).

Three things are pinned here, because all three were structural defects rather
than bugs in a computation:

1. **The host table is the identity authority, read from the COMMITTED tree.**
   The guard used to test two hard-coded hostnames -- a literal ``||`` that was
   the entire reason ``.101``/``.105`` could not be used. The full table
   contents are asserted, so adding or promoting a host requires a reviewed
   commit *and* a deliberate edit here.

2. **Placement reads SLOT state before load.** Measured 2026-08-30: ``.201``
   showed the fittest load ratio in the lab (14.08/32 = 0.44x) while running
   three concurrent pre-push suites behind a 10-deep queue. A load-only picker
   routes a fourth run onto the most jammed host in the fleet.

3. **Nothing here may make the gate accept less work.** The precedence tests
   pin the GitHub-hosted sha-pinned run ahead of the lab leg, and pin that a
   remote RED refuses instead of falling through to the override grant.

The bash helpers are extract-and-executed (the pattern already used for this
hook's other pure shell functions) so the assertions run THE code that ships,
never a Python re-implementation that could pass while the shipped picker is
broken.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
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


# Every `git` subprocess below passes `env=scrub_git_location_env(os.environ)`.
# That is not ceremony: GIT_DIR / GIT_WORK_TREE / GIT_INDEX_FILE are exported
# into every process a git hook spawns, and they OVERRIDE both `cwd=` and `-C`.
# These tests build throwaway repos under tmp_path, so an unscrubbed call would
# silently retarget the REAL invoking worktree instead (OMN-14891) -- which is
# how a test that reads green can have been operating on the wrong repository
# the whole time. The scrub is spelled out at each call site rather than hidden
# behind a local helper so the guard can verify it statically.


# =============================================================================
# The table itself
# =============================================================================


def _rows() -> list[list[str]]:
    rows = []
    for line in TABLE.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0]
        if not line.strip():
            continue
        rows.append(line.split("\t"))
    return rows


def test_table_exists_and_every_row_has_the_full_column_set() -> None:
    assert TABLE.is_file(), f"expected the host table at {TABLE}"
    rows = _rows()
    assert rows, "expected at least one data row"
    for row in rows:
        assert len(row) == 13, (
            f"row {row[0] if row else row!r} has {len(row)} columns, expected 13 "
            "(label role hostname ssh_target cores uv_abs_path uv_min_version "
            "workroot slot_mode slots repos_denied mode note)"
        )


def test_table_contents_are_pinned() -> None:
    """The exact designated set, asserted.

    This is the point of the file: the table decides which machines may
    authorize a heavy gate run, so a row addition or a `mode` promotion must be
    a reviewed, deliberate change and not a quiet edit.
    """
    got = {r[0]: (r[1], r[2], r[11]) for r in _rows()}
    assert got == {
        "h200": ("capacity", "stickybeatz-studio", "authorizing"),
        "h201": ("capacity", "omninode-pc", "authorizing"),
        "h201c": ("identity", "gate-runner-201", "authorizing"),
        "h101": ("capacity", "stickybeatz", "authorizing"),
        "h105": ("capacity", "omnibook", "authorizing"),
        "hcloud": ("capacity", "onex-prepush-cloud1", "authorizing"),
    }


def test_201_host_is_designated_by_its_real_hostname() -> None:
    """`.201`'s real `hostname -s` is `omninode-pc`; `gate-runner-201` is only
    the CONTAINER's. Before OMN-16991 only the container name was designated,
    so every push on the host itself needed an env override that the pytest
    child's env scrub then stripped."""
    hosts = {r[0]: r[2] for r in _rows()}
    assert hosts["h201"] == "omninode-pc"
    assert hosts["h201c"] == "gate-runner-201"


def test_201_denies_no_repo_since_omn16989_closed() -> None:
    """OMN-16989 recorded 15 "host-coupled" `omnibase_infra` failures and denied
    the repo on `h201` because of them. Every one of those 15 was measured in
    the `.201` **gate-runner container** -- a different execution environment
    from the one this table addresses, which is the `.201` HOST over the
    OMN-16991 remote leg (bundle transplant, `uv sync` in a fresh tree, the
    wrapper's developer-shell PATH). Re-measured on the host over that real leg
    the full `tests/unit/` selection is green, so the denial was pinning a
    verdict from an environment the table never routes work to.

    Denial is per-repo capacity policy, so lifting it is a reviewed table edit
    plus a deliberate edit here -- the same two-step that guards a promotion."""
    denied = {r[0]: r[10] for r in _rows()}
    assert denied["h201"] == "-", (
        "h201 must deny no repo: the OMN-16989 denial was lifted after a green "
        "full tests/unit/ run on the host over the real remote leg"
    )
    assert all(v == "-" for v in denied.values()), (
        f"no row should deny a repo today; got {denied}"
    )


def test_h105_is_authorizing_because_shadow_could_never_add_capacity() -> None:
    """h105 (omnibook) is the only net-new host, and while it was `shadow` it
    could not add a single unit of pre-push capacity -- by construction, not by
    accident. A shadow row never authorizes, and the transplanted tree carries
    this repo's own conftest guard, which refuses a full-suite target on any
    host outside the authorizing set. So every heavy dispatch to a shadow h105
    exited nonzero at `pytest_configure` and wrote a receipt whose
    `pytest_exit != 0` is indistinguishable from a genuine red.

    Promotion is the fix, and it is a reviewed table edit plus a deliberate
    edit here -- exactly the two-step this file exists to force."""
    modes = {r[0]: r[11] for r in _rows()}
    assert modes["h105"] == "authorizing"


def test_h101_is_authorizing_because_shadow_could_never_add_capacity() -> None:
    """h101 (stickybeatz) was the last row stuck `disabled` (uv 0.8.3, below
    the 0.11.0 floor). OMN-17161 upgraded uv to 0.12.7 and re-probed
    non-interactively; the same shadow-can-never-authorize reasoning as h105
    applies, so promotion is proven by a real full-suite dispatch to h101
    rather than a preceding shadow day (see OMN-16991's own SUPERSEDED DoD
    item)."""
    modes = {r[0]: r[11] for r in _rows()}
    assert modes["h101"] == "authorizing"


def test_h101_hostname_is_what_hostname_s_actually_prints() -> None:
    """`ssh jonah@192.168.86.101 'hostname -s'` prints `Stickybeatz`, not
    `stickybeatz.local`. The old value could never have matched an identity
    check, so the row would have failed silently the moment it was promoted."""
    hosts = {r[0]: r[2] for r in _rows()}
    assert hosts["h101"] == "stickybeatz"
    assert "." not in hosts["h101"], (
        "the column holds `hostname -s` output, which is never dotted"
    )


def test_every_capacity_row_carries_an_absolute_uv_path_and_a_floor() -> None:
    """uv is on no host's non-interactive PATH, and the live fleet spread is
    0.8.3 -> 0.11.32 against a lockfile at revision 3. Presence is not enough;
    the version floor is what makes a stale host skip rather than fail weirdly
    mid-`uv sync`."""
    for row in _rows():
        if row[1] != "capacity":
            continue
        assert row[5].startswith("/"), (
            f"{row[0]}: uv path must be absolute, got {row[5]!r}"
        )
        assert row[6][0].isdigit(), (
            f"{row[0]}: expected a uv_min_version, got {row[6]!r}"
        )


def test_101_workroot_avoids_the_tcc_protected_tree() -> None:
    """`ssh jonah@.101 'ls ~/Code'` returns `Operation not permitted`, so the
    workroot must live outside it -- the bundle design never needs `~/Code` on
    a remote host, which is what removes the out-of-band GUI grant step."""
    workroots = {r[0]: r[7] for r in _rows()}
    assert not workroots["h101"].startswith(
        "/Users/jonah/Code"  # local-path-ok: the literal IS the assertion
    )
    assert (
        workroots["h101"]
        == "/Users/Shared/onex-prepush"  # local-path-ok: pins the table value
    )


# =============================================================================
# Extract-and-execute harness
# =============================================================================


def _run_driver(repo_root: Path, body: str) -> subprocess.CompletedProcess[str]:
    """Run BODY with the real library sourced and the hook's own dependencies
    stubbed, against a throwaway git repo whose HEAD carries the real table.

    ``stdin`` is /dev/null on purpose. The row-scan defect these tests pin is
    "a probe ate the loop's stdin", and the tests that reproduce it stub a probe
    that DRAINS stdin; inheriting this pytest process's stdin would make such a
    stub block forever instead of returning at EOF.
    """
    script = f"""
set -uo pipefail
REPO_ROOT={repo_root}
PREPUSH_LOAD_THRESHOLD=1.0
log() {{ printf '[t] %s\\n' "$1" >&2; }}
die() {{ printf 'DIE: %s\\n' "$1" >&2; exit 1; }}
_prepush_timeout_cmd() {{ printf ''; }}
host_load_ratio() {{ return 1; }}
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
        },
    )


def _driver(repo_root: Path, body: str) -> str:
    return _run_driver(repo_root, body).stdout


def _driver_both(repo_root: Path, body: str) -> str:
    completed = _run_driver(repo_root, body)
    return completed.stdout + completed.stderr


#: A table whose rows exist only to exercise the RULES, independent of whichever
#: machines the lab happens to hold today. Two authorizing rows plus a shadow
#: row is the exact shape the placement bug needed: the shadow host is the
#: idlest, so a load-only picker chooses it and then throws its verdict away.
_SYNTHETIC_TABLE = (
    "#label\trole\thostname\tssh_target\tcores\tuv_abs_path\tuv_min_version"
    "\tworkroot\tslot_mode\tslots\trepos_denied\tmode\tnote\n"
    "ha\tcapacity\thosta\tjonah@hosta\t24\t/bin/uv\t0.1.0\t/tmp/wa\tlockdir\t1\t-\tauthorizing\tbusier\n"
    "hb\tcapacity\thostb\tjonah@hostb\t24\t/bin/uv\t0.1.0\t/tmp/wb\tlockdir\t1\t-\tauthorizing\tidler\n"
    "hs\tcapacity\thosts\tjonah@hosts\t24\t/bin/uv\t0.1.0\t/tmp/ws\tlockdir\t1\t-\tshadow\tidlest of all\n"
)

#: A single disabled row, so the shipped table's promotion of h101 (its last
#: disabled row, OMN-17161) does not strand the "a disabled host is never
#: probed" rule without a fixture to exercise it.
_SYNTHETIC_TABLE_DISABLED_ONLY = (
    "#label\trole\thostname\tssh_target\tcores\tuv_abs_path\tuv_min_version"
    "\tworkroot\tslot_mode\tslots\trepos_denied\tmode\tnote\n"
    "hd\tcapacity\thostd\tjonah@hostd\t24\t/bin/uv\t0.1.0\t/tmp/wd\tlockdir\t1\t-\tdisabled\tstill unfit\n"
)


def _repo_with_table(tmp_path: Path, table_text: str, name: str = "synth") -> Path:
    """A throwaway git repo whose HEAD carries TABLE_TEXT as the host table."""
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


@pytest.fixture
def table_repo(tmp_path: Path) -> Path:
    """A throwaway repo whose HEAD carries the real table, so the tests
    exercise the real `git show HEAD:` read path rather than a stub."""
    repo = tmp_path / "repo"
    (repo / "scripts" / "hooks").mkdir(parents=True)
    (repo / "scripts" / "hooks" / "prepush_hosts.tsv").write_text(
        TABLE.read_text(encoding="utf-8"), encoding="utf-8"
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


# =============================================================================
# Identity
# =============================================================================


def test_identity_accepts_the_real_201_hostname(table_repo: Path) -> None:
    out = _driver(table_repo, "prepush_identity_label omninode-pc || echo NONE")
    assert out.strip() == "h201"


def test_identity_accepts_the_201_container_hostname(table_repo: Path) -> None:
    out = _driver(table_repo, "prepush_identity_label gate-runner-201 || echo NONE")
    assert out.strip() == "h201c"


def test_a_shadow_host_is_not_a_designated_identity(tmp_path: Path) -> None:
    """A shadow host is a placement target whose verdict may not satisfy the
    escalation, so it must not confer identity either -- otherwise the identity
    guard would start PASSING on a host still in shadow, inverting the guard.

    Driven off a synthetic table because the shipped one no longer carries a
    shadow row (h105 was promoted); the RULE still has to hold for the next row
    that starts in shadow."""
    repo = _repo_with_table(tmp_path, _SYNTHETIC_TABLE)
    out = _driver(repo, "prepush_identity_label hosts || echo NONE")
    assert out.strip() == "NONE"


def test_a_disabled_host_is_not_a_designated_identity(table_repo: Path) -> None:
    out = _driver(table_repo, "prepush_identity_label stickybeatz.local || echo NONE")
    assert out.strip() == "NONE"


def test_an_override_replaces_its_row_rather_than_adding_a_name(
    table_repo: Path,
) -> None:
    """OMN-15059's guard is proven by forcing a nonsense `PREPUSH_200_HOSTNAME`
    and asserting refusal. That only holds while the override REPLACES the .200
    row: an override that merely appended a name could no longer de-designate
    this machine, silently inverting the guard."""
    out = _driver(
        table_repo,
        "PREPUSH_200_HOSTNAME=nope prepush_identity_label stickybeatz-studio || echo NONE",
    )
    assert out.strip() == "NONE"


def test_the_per_row_override_can_de_designate_any_row(table_repo: Path) -> None:
    out = _driver(
        table_repo,
        "PREPUSH_HOST_OVERRIDE_H201=nope prepush_identity_label omninode-pc || echo NONE",
    )
    assert out.strip() == "NONE"


def test_an_uncommitted_table_edit_cannot_designate_a_host(table_repo: Path) -> None:
    """The table is read from HEAD and the working copy must agree. Otherwise a
    one-line uncommitted edit naming your laptop would self-authorize a heavy
    gate run with no review and no receipt -- the forgeable-artifact surface
    OMN-16688 deliberately avoided."""
    tsv = table_repo / "scripts" / "hooks" / "prepush_hosts.tsv"
    tsv.write_text(
        tsv.read_text(encoding="utf-8")
        + "hevil\tcapacity\tmy-laptop\t-\t8\t/bin/uv\t0.1.0\t/tmp/w\tlockdir\t1\t-\tauthorizing\tforged\n",
        encoding="utf-8",
    )
    out = _driver(table_repo, "prepush_identity_label my-laptop || echo NONE")
    assert out.strip() == "NONE"


# =============================================================================
# The picker
# =============================================================================

_ALL_FREE = "h200=free,h201=free,h101=free,h105=free"


def _pick(
    repo: Path, *, load: str, slot: str, uv: str, repo_name: str = "omnibase_core"
) -> str:
    body = (
        f'export PREPUSH_LOAD_OVERRIDE_MAP="{load}"\n'
        f'export PREPUSH_SLOT_OVERRIDE_MAP="{slot}"\n'
        f'export PREPUSH_UV_OVERRIDE_MAP="{uv}"\n'
        f"if pick_capacity_host stickybeatz-studio {repo_name}; then\n"
        '  echo "PICK=$PREPUSH_PICK_LABEL"\n'
        "else\n"
        '  echo "PICK=none"\n'
        "fi\n"
        'echo "PROBE=$PREPUSH_PROBE_LOG"\n'
    )
    return _driver(repo, body)


_GOOD_UV = "h200=0.11.32,h201=0.11.5,h101=0.8.3,h105=0.11.8"


def test_picker_chooses_the_least_loaded_fit_host(table_repo: Path) -> None:
    out = _pick(
        table_repo,
        load="h200=0.90,h201=0.44,h105=0.21",
        slot=_ALL_FREE,
        uv=_GOOD_UV,
    )
    assert "PICK=h105" in out


def test_a_busy_host_is_unfit_even_when_it_is_the_least_loaded(
    table_repo: Path,
) -> None:
    """The measured case, not a hypothetical: `.201` read 0.44x -- the fittest
    ratio in the lab -- while running three concurrent pre-push suites behind a
    10-deep queue. load1 is a CPU-time proxy; the scarce resource is an
    exclusive heavy-suite slot."""
    out = _pick(
        table_repo,
        load="h200=0.90,h201=0.10,h105=0.80",
        slot="h200=free,h201=busy,h105=free",
        uv=_GOOD_UV,
    )
    assert "PICK=h105" in out, out
    assert "h201=busy" in out


def test_an_unreachable_host_is_skipped_never_assumed_free(
    table_repo: Path,
) -> None:
    """Silence is not headroom. A host we cannot read is skipped exactly like
    one we measured as over capacity -- the fail-closed posture the load probe
    already had."""
    out = _pick(
        table_repo,
        load="h200=0.90,h105=0.21",
        slot=_ALL_FREE,
        uv=_GOOD_UV,
    )
    assert "PICK=h105" in out
    assert "h201=unreachable" in out


def test_a_host_whose_slot_state_is_unknown_is_skipped(table_repo: Path) -> None:
    out = _pick(
        table_repo,
        load="h200=0.90,h201=0.10,h105=0.21",
        slot="h200=free,h201=unknown,h105=free",
        uv=_GOOD_UV,
    )
    assert "h201=slot-unknown" in out
    assert "PICK=h105" in out


def test_a_host_below_the_uv_floor_is_skipped(table_repo: Path) -> None:
    out = _pick(
        table_repo,
        load="h200=2.09,h201=2.0,h105=0.21",
        slot=_ALL_FREE,
        uv="h200=0.11.32,h201=0.11.5,h105=0.8.3",
    )
    assert "PICK=none" in out
    assert "h105=uv-unfit(0.8.3<0.11.0)" in out


def test_a_repo_denied_host_is_never_chosen(tmp_path: Path) -> None:
    """Driven off a synthetic table because the shipped one no longer denies any
    repo on any row (OMN-16989 lifted h201's `omnibase_infra` denial after the
    full `tests/unit/` suite ran green on that host over the real remote leg).

    The RULE still has to hold for the next row that needs a denial, and pinning
    it to whichever repo the lab happens to deny today made a capacity-policy
    edit look like a mechanism regression -- exactly the failure this run hit."""
    denied_table = _SYNTHETIC_TABLE.replace(
        "ha\tcapacity\thosta\tjonah@hosta\t24\t/bin/uv\t0.1.0\t/tmp/wa\tlockdir\t1\t-\t",
        "ha\tcapacity\thosta\tjonah@hosta\t24\t/bin/uv\t0.1.0\t/tmp/wa\tlockdir\t1\tsomerepo\t",
    )
    assert "\tsomerepo\t" in denied_table, "fixture edit did not take"
    repo = _repo_with_table(tmp_path, denied_table, name="denied")
    out = _pick(
        repo,
        load="ha=0.10,hb=0.21",
        slot="ha=free,hb=free,hs=free",
        uv="ha=9.9.9,hb=9.9.9,hs=9.9.9",
        repo_name="somerepo",
    )
    assert "ha=repo-denied" in out, out
    assert "PICK=hb" in out, out


def test_no_row_denies_a_repo_today_so_the_rule_needs_a_synthetic_fixture() -> None:
    """Guards the fixture choice above: the moment a real row denies a repo
    again, this fails and tells the next author they may pin the live table."""
    denied = {r[0]: r[10] for r in _rows()}
    assert all(v == "-" for v in denied.values()), (
        f"a row denies a repo again ({denied}) -- "
        "test_a_repo_denied_host_is_never_chosen may pin the live table again"
    )


def test_a_disabled_host_is_never_probed(tmp_path: Path) -> None:
    """Driven off a synthetic table because the shipped one no longer carries
    a disabled row (h101 was promoted, OMN-17161); the RULE still has to hold
    for the next row that starts disabled. The only row is disabled, so a fit
    pick is impossible if -- and only if -- it was actually skipped rather
    than probed."""
    repo = _repo_with_table(tmp_path, _SYNTHETIC_TABLE_DISABLED_ONLY)
    out = _pick(repo, load="hd=0.01", slot="hd=free", uv="hd=9.9.9")
    assert "hd=disabled" in out
    assert "PICK=none" in out


def test_picker_returns_no_host_when_nothing_is_fit(table_repo: Path) -> None:
    """The fallback path. When no host is fit the picker must fail rather than
    return a least-bad guess -- the caller then falls through to the existing
    precedence (GitHub-hosted verify -> grant -> die), which is unchanged."""
    out = _pick(
        table_repo,
        load="h200=2.09,h201=3.10,h105=1.90",
        slot=_ALL_FREE,
        uv=_GOOD_UV,
    )
    assert "PICK=none" in out


def test_every_probed_host_is_recorded_for_the_receipt(table_repo: Path) -> None:
    """A refusal has to be auditable rather than believed, so every probed host
    lands in the trail that the receipt and the die() message both carry."""
    out = _pick(
        table_repo,
        load="h200=2.09,h201=3.10,h105=1.90",
        slot=_ALL_FREE,
        uv=_GOOD_UV,
    )
    for label in ("h200", "h201", "h101", "h105"):
        assert label in out


# =============================================================================
# Per-host slot CAPACITY (OMN-17269): a row may declare slots > 1
# =============================================================================
#
# OMN-16991 gave every capacity row exactly one exclusive slot. Operator
# direction 2026-08-30 ("it looks like .105 can take more load") plus the same
# day's live evidence (h105: load1 2.74/10 = 0.27x, slot FREE) showed the
# binding constraint was the one-slot-per-host model, not host fitness. A row
# with `slots=N` is N independently placeable candidates -- slot 1 keeps the
# bare LABEL (byte-identical to every pre-OMN-17269 row), slot k>=2 is
# `LABEL.k`, its own override-map key -- each re-qualified on LIVE state at
# pick time, never assumed fit because a sibling slot on the same row is free.

_SYNTHETIC_TABLE_MULTISLOT = (
    "#label\trole\thostname\tssh_target\tcores\tuv_abs_path\tuv_min_version"
    "\tworkroot\tslot_mode\tslots\trepos_denied\tmode\tnote\n"
    "hm\tcapacity\thostm\tjonah@hostm\t10\t/bin/uv\t0.1.0\t/tmp/wm\tlockdir\t2\t-\tauthorizing\ttwo-slot test host\n"
)


def test_the_shipped_slots_column_is_pinned(table_repo: Path) -> None:
    """h101 and h105 carry slots=2; every other row stays slots=1.

    OMN-17159 pinned every row here at slots=1 and refused to inherit
    omnibase_infra's widening, on an explicit premise: that this repo's
    escalation is the whole `tests/` tree, so "two concurrent core suites on
    h105's ten cores would make both slower than one serialized pair while
    degrading the load signal every other row is ranked on." That premise was
    a projection, and it is now falsified by direct measurement of the thing
    it projected about -- a REAL core escalation on the remote leg.

    Measured 2026-09-02T19:22Z by read-only `ps`/`uptime` over ssh, on two
    hosts each carrying exactly one live governed core full-suite leg:

    * h101 (12 cores, 32 GiB), run `omnibase_core-4e116501fd0a-37091`,
      1h13m43s elapsed: the ENTIRE suite is ONE pytest process at 100.0% of
      ONE core, RSS 670 MB (whole process tree: cpu_sum 100.0%, rss_sum
      671 MB, 2 processes). load1 2.96/12 = 0.25x.
    * h105 (10 cores, 32 GiB), run `omnibase_core-e69568dd5e02-80404`,
      1h49m49s elapsed: same shape, one process, RSS 700 MB. load1 at
      19:22:08Z 4.07/10 = 0.41x while that host was carrying TWO concurrent
      core pytest invocations (the single-threaded leg plus a second `-n4`
      one) -- an accidental but on-point datapoint that a 10-core M4 is
      nowhere near saturated by two concurrent core suites.

    A core lane costs one core and ~0.7 GB, not the machine. Two of them cost
    two cores of ten (0.2x) and ~1.4 GB of 32 GiB -- so the serialization the
    old pin bought was not protecting the host from saturation, it was
    idling 8-11 cores per host while six lanes queued for a placement target.
    The load1 signal is not degraded either: it is re-measured per slot at
    pick time and 2/10 stays an order of magnitude under the 1.0x threshold.

    The widening survives OMN-17603 restoring `-n4` on the remote leg: two
    4-way suites is 8 of h105's 10 cores (0.8x, still under threshold) and 8
    of h101's 12 (0.67x), at ~2.8 GB per suite by the per-worker RSS measured
    above -- 5.6 GB of 32 GiB. It does NOT survive a widening past 2, which
    would put h105 over the threshold under `-n4`; slots=3 needs its own
    measurement, exactly as this one did.

    h200 and h201 are deliberately NOT widened: h200 is the local/default
    identity host rather than a distribution target, and h201 runs the
    separate `~/push-lanes/QUEUE` serializer (slot_mode=queue), a different
    concurrency mechanism this column does not govern. h201c never executes.

    `hcloud` -- the AWS overflow row this same PR adds (OMN-16634) -- also
    stays slots=1, and NOT by inheriting the old blanket pin. The h101/h105
    widening above is earned by a measurement of those two hosts; no such
    measurement of the EC2 host exists, and the row is an overflow target that
    is only reached once the lab is saturated anyway. Widening it is a separate,
    measured change, exactly as this one was.

    Widening a row's capacity stays the kind of change this file exists to
    force through a reviewed, deliberate test edit (same reasoning as the
    mode-promotion pins above)."""
    slots = {r[0]: r[9] for r in _rows()}
    assert slots == {
        "h200": "1",
        "h201": "1",
        "h201c": "1",
        "h101": "2",
        "h105": "2",
        "hcloud": "1",
    }


def test_a_widened_shipped_row_places_a_second_lane_when_slot_one_is_held(
    table_repo: Path,
) -> None:
    """The point of the widening, asserted against the REAL shipped table.

    Before OMN-17602 this behaviour was only ever exercised on the synthetic
    `hm` fixture below, because no shipped row declared slots>1 -- so the
    table could have been widened wrongly (a typo, a column shift) and every
    slot test would still have passed. Measured live 2026-09-02T19:11Z:
    across h105 (121 run dirs) and h101 (73), `LOCK.2` has never once been
    created and no `slots/` directory exists, i.e. the fleet has never taken
    a second slot for ANY repo -- which is what an unexercised path looks
    like from the outside.

    With slot 1 held and slot 2 re-qualified on its own live load, the picker
    must offer `h105.2` rather than reporting a placement miss."""
    out = _pick(
        table_repo,
        load="h200=2.09,h201=3.10,h101=2.50,h105.2=0.25",
        slot="h200=busy,h201=busy,h101=busy,h101.2=busy,h105=busy,h105.2=free",
        uv="h105.2=0.11.8",
    )
    assert "PICK=h105.2" in out, out
    assert "h105=busy" in out, out


def test_slot_one_keeps_the_bare_label_not_a_dot_one_suffix(
    table_repo: Path,
) -> None:
    """Slot 1 of every row -- including h105's slots=2 -- must place under the
    pre-existing bare LABEL, so every slots=1 row on the shipped table is
    byte-identical in placement to before this change."""
    out = _pick(
        table_repo,
        load="h200=0.90,h201=0.44,h105=0.21",
        slot=_ALL_FREE,
        uv=_GOOD_UV,
    )
    assert "PICK=h105" in out, out
    assert "PICK=h105.1" not in out, out


def test_both_slots_busy_is_a_placement_miss(tmp_path: Path) -> None:
    """A two-slot row with both slots held offers no placement at all."""
    repo = _repo_with_table(tmp_path, _SYNTHETIC_TABLE_MULTISLOT, name="multislot-a")
    out = _pick(
        repo,
        load="hm=0.10",
        slot="hm=busy,hm.2=busy",
        uv="hm=9.9.9",
        repo_name="omnibase_core",
    )
    assert "PICK=none" in out, out
    assert "hm=busy" in out, out
    assert "hm.2=busy" in out, out


def test_a_second_slot_is_accepted_when_it_re_qualifies_on_measured_load(
    tmp_path: Path,
) -> None:
    """Slot 1 held does not disqualify slot 2 -- slot 2 is probed on ITS OWN
    live state and, measured under threshold, is placeable."""
    repo = _repo_with_table(tmp_path, _SYNTHETIC_TABLE_MULTISLOT, name="multislot-b")
    out = _pick(
        repo,
        load="hm.2=0.30",
        slot="hm=busy,hm.2=free",
        uv="hm.2=9.9.9",
        repo_name="omnibase_core",
    )
    assert "PICK=hm.2" in out, out
    assert "hm=busy" in out, out


def test_a_second_slot_is_refused_when_measured_load_is_high(
    tmp_path: Path,
) -> None:
    """Free slot is necessary but not sufficient -- a free second slot on a
    host whose LIVE load is already over threshold must still refuse. Fitness
    is re-measured at pick time, never assumed from slot availability alone."""
    repo = _repo_with_table(tmp_path, _SYNTHETIC_TABLE_MULTISLOT, name="multislot-c")
    out = _pick(
        repo,
        load="hm.2=2.50",
        slot="hm=busy,hm.2=free",
        uv="hm.2=9.9.9",
        repo_name="omnibase_core",
    )
    assert "PICK=none" in out, out
    assert "hm.2=over(2.50)" in out, out


def test_prepush_select_candidate_exposes_the_slot_index(tmp_path: Path) -> None:
    """The slot a candidate was ranked into must be readable by the caller so
    the remote leg can lock the right LOCK.<k> and the receipt can record it
    (OMN-17269 DoD: receipts record which slot a run held)."""
    repo = _repo_with_table(tmp_path, _SYNTHETIC_TABLE_MULTISLOT, name="multislot-d")
    out = _driver(
        repo,
        'export PREPUSH_LOAD_OVERRIDE_MAP="hm.2=0.10"\n'
        'export PREPUSH_SLOT_OVERRIDE_MAP="hm=busy,hm.2=free"\n'
        'export PREPUSH_UV_OVERRIDE_MAP="hm.2=9.9.9"\n'
        "pick_capacity_host somewhere-else omnibase_core > /dev/null 2>&1\n"
        'echo "LABEL=$PREPUSH_PICK_LABEL SLOT=$PREPUSH_PICK_SLOT"\n',
    )
    assert "LABEL=hm.2 SLOT=2" in out, out


def test_prepush_select_candidate_defaults_slot_to_one(table_repo: Path) -> None:
    """A slot-1 candidate (every pre-OMN-17269 row) reports SLOT=1 explicitly,
    not an empty/unset value that a caller might mishandle."""
    out = _driver(
        table_repo,
        'export PREPUSH_LOAD_OVERRIDE_MAP="h105=0.21"\n'
        f'export PREPUSH_SLOT_OVERRIDE_MAP="{_ALL_FREE}"\n'
        f'export PREPUSH_UV_OVERRIDE_MAP="{_GOOD_UV}"\n'
        "pick_capacity_host somewhere-else omnibase_core > /dev/null 2>&1\n"
        'echo "LABEL=$PREPUSH_PICK_LABEL SLOT=$PREPUSH_PICK_SLOT"\n',
    )
    assert "LABEL=h105 SLOT=1" in out, out


# =============================================================================
# The slot PROBE itself (OMN-17602): why slots>1 was unreachable in practice
# =============================================================================
#
# OMN-17269 shipped the slot MECHANISM and OMN-17159 pinned this repo at
# slots=1, so the probe's multi-slot arithmetic had never run against a real
# remote host until OMN-17602 widened h101/h105. It did not work. Measured
# read-only 2026-09-02T19:11-20:20Z: `LOCK.2` had never been created ONCE
# anywhere in the fleet -- h105 121 run dirs, h101 73, bare `LOCK` only, no
# `slots/` directory -- even though omnibase_infra had carried h105 slots=2
# since 2026-08-30. Three defects in `_PREPUSH_SLOT_PROBE_SH` explain it, and
# the tests below pin each one. Every fix makes the predicate LESS strict, so
# each is pinned by the exact arithmetic it restores rather than by "it now
# returns free": an untracked heavy process with no lock to explain it must
# still read BUSY, and `test_an_unexplained_heavy_process_is_still_busy`
# asserts exactly that.


def _probe_line(out: str) -> list[str]:
    """The probe's last stdout line, split into fields."""
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    assert lines, f"probe produced no output: {out!r}"
    return lines[-1].split()


def _fake_ps(bin_dir: Path, *lines: str) -> None:
    """A `ps` stub on PATH that prints LINES for any argv.

    The real signal cannot be produced from a test -- it needs a live remote
    leg -- so the stub reproduces the exact two argv lines a single leg puts
    in `ps`, captured verbatim from h105 at 2026-09-02T20:14Z.
    """
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = "#!/bin/sh\n" + "".join(f"printf '%s\\n' {line!r}\n" for line in lines)
    ps = bin_dir / "ps"
    ps.write_text(script, encoding="utf-8")
    ps.chmod(0o755)


#: The two argv lines ONE remote leg contributes to `ps ax -o args=`, copied
#: from h105 (run omnibase_core-e69568dd5e02-80404). The first is the ssh
#: wrapper shell, the second is the leg. A count that returns 2 here is
#: counting the shell that spawned the leg as a second leg. The `/Users/Shared`
#: paths are annotated rather than parameterised on purpose: this is a VERBATIM
#: transcript of what `ps` printed on a lab Mac, and the workroot the lab Macs
#: actually use is part of the evidence. Rewriting it to a tmp path would make
#: the fixture agree with the code instead of with the machine.
_ONE_LEG_PS = (
    "zsh -c cd '/Users/Shared/onex-prepush/runs/omnibase_core-e69568dd5e02-80404'"  # local-path-ok
    " || exit 96; chmod +x prepush_smart_tests.sh || exit 97;"
    " ./prepush_smart_tests.sh '/Users/Shared/onex-prepush/runs/x' '/uv' 'sha' '1'",  # local-path-ok
    "bash ./prepush_smart_tests.sh /Users/Shared/onex-prepush/runs/x /uv sha 1",  # local-path-ok
)


def test_the_slot_probe_counts_held_locks_under_a_shell_that_rejects_globs(
    table_repo: Path, tmp_path: Path
) -> None:
    """`held` must not depend on the shell expanding an unmatched glob.

    The lab Macs' login shell is zsh (measured 2026-09-02:
    `ssh <h101|h105> 'echo $SHELL'` -> /bin/zsh), and zsh's default `nomatch`
    makes an unmatched glob a FATAL error that aborts the command line before
    it runs -- so the old `ls -d "$W"/LOCK "$W"/LOCK.*` printed nothing, and
    its `2>/dev/null` could not suppress the message because the redirection
    belonged to a command that never executed. `held` therefore read 0 on
    every remote Mac probe in exactly the state slot 2 exists for: slot 1
    locked, slot 2 free. Reproduced portably with bash's `failglob`, which
    has the same semantics; a real-zsh twin runs below where zsh exists."""
    wr = tmp_path / "wr"
    (wr / "LOCK").mkdir(parents=True)
    home = tmp_path / "home"
    home.mkdir()
    out = _driver(
        table_repo,
        f'export HOME="{home}"\n'
        f'export PREPUSH_WORKROOT="{wr}"\n'
        "export PREPUSH_SLOT_INDEX=2\n"
        'bash -O failglob -c "$_PREPUSH_SLOT_PROBE_SH"\n',
    )
    fields = _probe_line(out)
    assert len(fields) == 4, fields
    assert fields[2] == "0", f"LOCK.2 does not exist, so l must be 0: {fields}"
    assert fields[3] == "1", f"one held lock dir (LOCK) must be counted: {fields}"


@pytest.mark.skipif(shutil.which("zsh") is None, reason="zsh not installed")
def test_the_slot_probe_counts_held_locks_under_real_zsh(
    table_repo: Path, tmp_path: Path
) -> None:
    """The same property against the ACTUAL shell the lab Macs run, so the
    portable `failglob` stand-in above can never drift away from the thing it
    stands in for."""
    wr = tmp_path / "wr"
    (wr / "LOCK").mkdir(parents=True)
    home = tmp_path / "home"
    home.mkdir()
    out = _driver(
        table_repo,
        f'export HOME="{home}"\n'
        f'export PREPUSH_WORKROOT="{wr}"\n'
        "export PREPUSH_SLOT_INDEX=2\n"
        'zsh -c "$_PREPUSH_SLOT_PROBE_SH"\n',
    )
    fields = _probe_line(out)
    assert len(fields) == 4, fields
    assert fields[3] == "1", f"one held lock dir (LOCK) must be counted: {fields}"


def test_the_slot_probe_counts_one_process_per_leg_not_the_ssh_wrapper(
    table_repo: Path, tmp_path: Path
) -> None:
    """A single remote leg must count as ONE heavy process, not two.

    The leg is launched as `zsh -c '...; ./prepush_smart_tests.sh ...'`, so
    the wrapper shell AND the script both carry the script name in their
    argv. Measured on h101, h105 and h201 at 2026-09-02T20:14Z: exactly one
    leg was running on each and the old count returned 2 on all three. That
    doubling is what defeats `p <= self + held` -- one lock can never explain
    two processes, so a correctly-locked host reads BUSY on every slot."""
    wr = tmp_path / "wr"
    wr.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    _fake_ps(tmp_path / "bin", *_ONE_LEG_PS)
    out = _driver(
        table_repo,
        f'export HOME="{home}"\n'
        f'export PATH="{tmp_path / "bin"}:$PATH"\n'
        f'export PREPUSH_WORKROOT="{wr}"\n'
        'sh -c "$_PREPUSH_SLOT_PROBE_SH"\n',
    )
    fields = _probe_line(out)
    assert fields[1] == "1", f"one leg must count once, got p={fields[1]}: {fields}"


def test_the_slot_probe_emits_four_fields_when_the_queue_file_is_empty(
    table_repo: Path, tmp_path: Path
) -> None:
    """`grep -c .` on an EXISTING BUT EMPTY file prints 0 and exits 1, so the
    old `|| echo 0` fired as well and `q` became two lines. Every later field
    then shifted left by one and `l` was read out of `p`.

    This was live on h201, whose `~/push-lanes/QUEUE` exists and is empty: the
    2026-09-02T20:07Z refusal trail printed `h201=busy(queue=0 heavy_pids=0
    lock=2 held=1)` -- and `l` is assigned only 0 or 1, so `lock=2` is a value
    the code cannot produce except by shifting."""
    wr = tmp_path / "wr"
    wr.mkdir()
    home = tmp_path / "home"
    (home / "push-lanes").mkdir(parents=True)
    (home / "push-lanes" / "QUEUE").write_text("", encoding="utf-8")
    out = _driver(
        table_repo,
        f'export HOME="{home}"\n'
        f'export PREPUSH_WORKROOT="{wr}"\n'
        'sh -c "$_PREPUSH_SLOT_PROBE_SH"\n',
    )
    # The WHOLE probe output, not just its last line: the defect emitted the
    # extra `0` on a line of its own, which a last-line read would hide while
    # `set -- $raw` in the caller still word-splits across the newline and
    # shifts every field.
    words = out.split()
    assert len(words) == 4, f"an empty QUEUE must not add a field: {out!r}"
    assert words[0] == "0", words


def test_a_probe_with_the_wrong_field_count_is_unknown_not_shifted(
    table_repo: Path,
) -> None:
    """Fail closed on a malformed probe instead of reading it shifted.

    The old parse took `${1..4}` positionally with defaults, so the five-word
    output above was accepted and silently misread rather than rejected.
    Unknown is skipped exactly like unreachable, which is the rule the whole
    probe is built on -- so a future field change degrades to a placement
    miss, never to a wrong verdict."""
    out = _driver(
        table_repo,
        'PREPUSH_SLOT_OVERRIDE="0 0 0 0 1" prepush_slot_state "" /nonexistent 0 1\n'
        'echo "RC=$?"\n',
    )
    assert "RC=2" in out, out


def test_a_second_slot_is_free_when_one_locked_leg_explains_the_heavy_process(
    table_repo: Path, tmp_path: Path
) -> None:
    """The whole point, end to end, against the real probe.

    State: slot 1 locked (`LOCK` present), slot 2 unlocked (no `LOCK.2`), and
    exactly one live leg -- the state every lab Mac was in for hours on
    2026-09-02 while six lanes queued for a placement target. Slot 1 must read
    BUSY and slot 2 must read FREE. Before OMN-17602 both read BUSY."""
    wr = tmp_path / "wr"
    (wr / "LOCK").mkdir(parents=True)
    home = tmp_path / "home"
    home.mkdir()
    _fake_ps(tmp_path / "bin", *_ONE_LEG_PS)
    out = _driver(
        table_repo,
        f'export HOME="{home}"\n'
        f'export PATH="{tmp_path / "bin"}:$PATH"\n'
        f'prepush_slot_state "" "{wr}" 0 1; echo "SLOT1=$?"\n'
        f'prepush_slot_state "" "{wr}" 0 2; echo "SLOT2=$?"\n',
    )
    assert "SLOT1=3" in out, out
    assert "SLOT2=0" in out, out


def test_an_unexplained_heavy_process_is_still_busy(
    table_repo: Path, tmp_path: Path
) -> None:
    """The fixes must not turn the probe permissive.

    Two independent legs (two wrapper+script pairs, so p=2) with only ONE
    held lock is a host running an untracked heavy process this table cannot
    account for. That must stay BUSY on the free slot -- the `p <= self +
    held` predicate is what makes the probe fail closed, and OMN-17602 only
    restored its inputs, it did not relax it."""
    wr = tmp_path / "wr"
    (wr / "LOCK").mkdir(parents=True)
    home = tmp_path / "home"
    home.mkdir()
    _fake_ps(tmp_path / "bin", *(_ONE_LEG_PS + _ONE_LEG_PS))
    out = _driver(
        table_repo,
        f'export HOME="{home}"\n'
        f'export PATH="{tmp_path / "bin"}:$PATH"\n'
        f'prepush_slot_state "" "{wr}" 0 2; echo "SLOT2=$?"\n',
    )
    assert "SLOT2=3" in out, out


# =============================================================================
# The lock
# =============================================================================


def test_lock_is_exclusive(table_repo: Path, tmp_path: Path) -> None:
    wr = tmp_path / "wr"
    out = _driver(
        table_repo,
        f"prepush_lock_acquire {wr} && echo FIRST=ok\n"
        f'( PREPUSH_HELD_LOCK=""; prepush_lock_acquire {wr} && echo SECOND=ok || echo SECOND=blocked )\n',
    )
    assert "FIRST=ok" in out
    assert "SECOND=blocked" in out


def test_lock_is_reusable_after_release(table_repo: Path, tmp_path: Path) -> None:
    wr = tmp_path / "wr"
    out = _driver(
        table_repo,
        f"prepush_lock_acquire {wr} && echo FIRST=ok\n"
        "prepush_lock_release\n"
        f'( PREPUSH_HELD_LOCK=""; prepush_lock_acquire {wr} && echo SECOND=ok || echo SECOND=blocked )\n',
    )
    assert "FIRST=ok" in out
    assert "SECOND=ok" in out


def test_a_lock_whose_holder_is_dead_on_this_machine_is_reclaimed(
    table_repo: Path, tmp_path: Path
) -> None:
    """mkdir(2) is the lock primitive because flock(1) is absent on both Macs
    and its fd idiom needs `exec {fd}<>`, which bash 3.2 cannot parse. What
    mkdir lacks is auto-release on death, so a lock whose holder is provably
    gone is reclaimed -- without this one externally-SIGTERMed run (OMN-16713)
    wedges a host permanently."""
    wr = tmp_path / "wr"
    lockdir = wr / "LOCK"
    lockdir.mkdir(parents=True)
    host = subprocess.run(
        ["hostname", "-s"], capture_output=True, text=True, check=False
    ).stdout.strip()
    # pid 2^22 is above every default pid_max and is reliably absent.
    (lockdir / "holder").write_text(f"4194303 {host} 2026-01-01T00:00:00Z\n")
    out = _driver(
        table_repo,
        f"prepush_lock_acquire {wr} && echo RECLAIM=ok || echo RECLAIM=blocked",
    )
    assert "RECLAIM=ok" in out


def test_a_lock_held_by_a_live_process_is_not_reclaimed(
    table_repo: Path, tmp_path: Path
) -> None:
    wr = tmp_path / "wr"
    lockdir = wr / "LOCK"
    lockdir.mkdir(parents=True)
    host = subprocess.run(
        ["hostname", "-s"], capture_output=True, text=True, check=False
    ).stdout.strip()
    (lockdir / "holder").write_text(f"{os.getpid()} {host} 2026-01-01T00:00:00Z\n")
    out = _driver(
        table_repo,
        f"prepush_lock_acquire {wr} && echo RECLAIM=ok || echo RECLAIM=blocked",
    )
    assert "RECLAIM=blocked" in out


def test_a_lock_held_by_another_machine_is_never_reclaimed(
    table_repo: Path, tmp_path: Path
) -> None:
    """A pid from another host says nothing about whether a process here is
    alive, so a foreign holder is never reaped on a liveness check."""
    wr = tmp_path / "wr"
    lockdir = wr / "LOCK"
    lockdir.mkdir(parents=True)
    (lockdir / "holder").write_text("4194303 some-other-host 2026-01-01T00:00:00Z\n")
    out = _driver(
        table_repo,
        f"prepush_lock_acquire {wr} && echo RECLAIM=ok || echo RECLAIM=blocked",
    )
    assert "RECLAIM=blocked" in out


# =============================================================================
# Precedence and non-bypass invariants (static wiring)
# =============================================================================


def test_the_lab_leg_is_tried_before_the_degraded_grant() -> None:
    """Precedence is by EVIDENCE STRENGTH, not convenience.

    The lab leg runs a real suite on hardware this repo designates, bound to
    the pushed sha by a completion marker carrying {head_sha, argv_sha, exit,
    collected, log_sha256}. The grant runs a CONTENDED suite on a host the
    guard just measured as unfit and merely says so in a receipt. Ordering the
    grant first would spend the weakest evidence available while an idle lab
    host went unprobed -- which is the stalled state OMN-17159 was opened
    against.

    omnibase_infra additionally consults a sha-pinned GitHub-hosted full-suite
    run AHEAD of the lab leg (OMN-16688). That leg is deliberately NOT ported
    here yet -- it needs this repo's own sharded-CI shape wired into
    prepush_remote_verify.py -- so this test pins the two legs this repo
    actually has. Its absence can only make this gate STRICTER: one fewer
    evidence source above the grant, never a new pass. See
    test_no_evidence_source_was_ported_without_its_entry_rejection below for
    the ordering constraint that governed what did land."""
    text = HOOK.read_text(encoding="utf-8")
    start = text.index("guard_full_suite_host() {")
    guard = text[start:]
    assert "remote_full_suite_verified" not in guard, (
        "the GitHub-hosted verify leg appears in the guard but was not ported "
        "with its script; wire prepush_remote_verify.py and pin its order here"
    )
    for path_name, segment in (
        ("designated-host", guard[: guard.index("# Not a designated host")]),
        ("undesignated-host", guard[guard.index("# Not a designated host") :]),
    ):
        i_lab = segment.index("dispatch_to_lab_host")
        i_grant = segment.index("consume_override_grant")
        assert i_lab < i_grant, (
            f"{path_name} path: expected the lab leg BEFORE the degraded "
            "grant, got a different order"
        )


def test_no_evidence_source_was_ported_without_its_entry_rejection() -> None:
    """OMN-17159's DoD ordering, asserted rather than trusted.

    The ticket's own words: porting the picker first "would add a PASS path
    with no entry rejection behind it". The picker IS a new PASS path, so the
    OMN-16480 entry rejection must be reachable before it -- in the same file,
    at hook entry, not merely present somewhere.

    `reject_inherited_env_overrides` is CALLED at top level (not just defined),
    and that call must sit above the guard that can dispatch to a lab host. A
    future edit that moves the picker earlier, or drops the call to a lazily
    invoked branch, fails here."""
    text = HOOK.read_text(encoding="utf-8")
    call_sites = [
        i
        for i, line in enumerate(text.splitlines())
        if line.strip() == "reject_inherited_env_overrides"
    ]
    assert call_sites, (
        "reject_inherited_env_overrides is never CALLED at top level -- "
        "defining it is not enforcing it (OMN-16480)"
    )
    lines = text.splitlines()
    guard_line = next(
        i
        for i, line in enumerate(lines)
        if line.startswith("guard_full_suite_host() {")
    )
    assert call_sites[0] < guard_line, (
        "the entry rejection must be reachable before the guard that can "
        "dispatch a new PASS path (OMN-17159 DoD ordering)"
    )


def test_a_remote_red_refuses_and_never_falls_through_to_a_grant() -> None:
    """A suite that genuinely failed on a designated host is a red gate, not a
    capacity problem. Letting it fall through to `consume_override_grant` would
    be a bypass wearing the word "fallback"."""
    text = HOOK.read_text(encoding="utf-8")
    start = text.index("dispatch_to_lab_host() {")
    body = text[start : text.index("guard_full_suite_host() {")]
    assert "3)" in body and "die " in body, (
        "expected the rc=3 (remote RED) branch of dispatch_to_lab_host to die"
    )
    red_branch = body[body.index("    3)") :]
    assert "die " in red_branch.split("esac")[0], (
        "the remote-RED branch must refuse, not return and fall through"
    )


def test_the_hook_introduces_no_new_bypass_env_knob() -> None:
    """Every knob added by OMN-16991 either routes work or makes the gate run
    MORE of it. None can make it accept less: the entry rejection of
    PREPUSH_ALLOW_* and the recursion sentinel are untouched."""
    text = HOOK.read_text(encoding="utf-8")
    assert "reject_inherited_env_overrides" in text
    assert 'if [ -n "${ONEX_PREPUSH_HOOK_ACTIVE:-}" ]; then' in text
    lib = LIB.read_text(encoding="utf-8")
    assert "PREPUSH_ALLOW" not in lib, (
        "the distribution library must not read any PREPUSH_ALLOW_* variable"
    )


def test_the_remote_command_rearms_both_guards() -> None:
    """ssh forwards neither the recursion sentinel nor the env scrub. Without
    re-arming, the remote repo's own suite -- which subprocesses this hook --
    takes FIRST-entry behavior there, resolves the selector, picks a host and
    ships another bundle: an unbounded DISTRIBUTED variant of the
    OMN-16425/OMN-16489 F-01 recursion (~9h03m, 44,064 tests)."""
    lib = LIB.read_text(encoding="utf-8")
    remote = lib[lib.index("cat > \"$runner\" <<'REMOTE'") : lib.index("\nREMOTE\n")]
    assert "export ONEX_PREPUSH_HOOK_ACTIVE=" in remote
    assert "PREPUSH_[A-Za-z0-9_]*" in remote, (
        "expected every PREPUSH_* name to be unset"
    )
    assert "unset ENABLE_SMART_TESTS" in remote


def test_the_verdict_is_read_from_a_marker_not_the_ssh_exit_code() -> None:
    """ssh returns 255 on transport failure (indistinguishable from a test
    failure) and any backgrounding wrapper returns 0 with nothing having run --
    a fail-OPEN shape. The marker binds the verdict to this tree and this argv;
    absence or mismatch is NO evidence."""
    lib = LIB.read_text(encoding="utf-8")
    assert 'readback="$(ssh' in lib, (
        "the verdict must be READ BACK from the target host, not inferred here"
    )
    assert 'marker="$(printf \'%s\\n\' "$readback"' in lib
    assert '"$m_head" != "$head_sha"' in lib
    assert '"$m_argv" != "$argv_sha"' in lib
    assert "NO EVIDENCE" in lib
    # The streaming pipeline's status belongs to sed(1), and `|| true` follows
    # it, so nothing about the verdict can come from that command's exit code.
    #
    # OMN-17603 lifted the wrapper invocation into `$remote_cmd` (it is now
    # issued twice -- once timeout-wrapped, once not, depending on whether
    # timeout(1) exists on the pusher), so the invocation and the pipeline that
    # streams it are no longer adjacent and a fixed window after the invocation
    # would pin nothing. Assert the property directly instead, on EVERY
    # streaming branch: a branch added later without the discard would
    # reintroduce exactly the fail-open shape this test exists for.
    assert "./prepush_smart_tests.sh '${rundir}'" in lib, (
        "the remote command no longer invokes the wrapper"
    )
    streams = [m.start() for m in re.finditer(r'"\$remote_cmd" 2>&1 \|', lib)]
    assert streams, "no streaming invocation of $remote_cmd found"
    for idx in streams:
        window = lib[idx : idx + 200]
        assert 'sed "s/^/[${label}] /" >&2 || true' in window, window


def test_a_shadow_host_verdict_never_authorizes() -> None:
    lib = LIB.read_text(encoding="utf-8")
    idx = lib.index('if [ "$PREPUSH_PICK_MODE" = "shadow" ]')
    branch = lib[idx : idx + 500]
    assert "return 1" in branch, (
        "a shadow host must fall through to the normal precedence, never authorize"
    )


def test_the_remote_wrapper_is_visible_to_the_201_queue_gate() -> None:
    """`.201`'s queue runner gates every lane on
    `ps ax | grep prepush_smart_tests.sh` ("covers foreign runs not launched
    through this queue"). Naming the remote wrapper to match makes a
    distributed run share that one mutex instead of becoming another foreign
    detached run -- the defect class OMN-16968 is open against."""
    lib = LIB.read_text(encoding="utf-8")
    assert 'runner="${localdir}/prepush_smart_tests.sh"' in lib
    assert "prepush_smart_tests.sh" in lib[lib.index("_PREPUSH_SLOT_PROBE_SH") :][:600]


def test_the_local_heavy_path_takes_the_host_lock() -> None:
    """OMN-16174: the local path took no lock of any kind, which is why five
    concurrent full suites once ran on one host with one taking 97+ minutes. It
    was the busiest path in the hook and the only unserialized one."""
    text = HOOK.read_text(encoding="utf-8")
    start = text.index("guard_full_suite_host() {")
    guard = text[start:]
    fit = guard[guard.index('if host_is_fit ""; then') :][:900]
    assert "prepush_lock_acquire" in fit
    assert "prepush_local_workroot" in fit


def test_the_escalation_argv_stays_a_superset_of_the_narrow_selection() -> None:
    """OMN-16825: the heavy call site runs $FULL_SUITE_TARGET **plus** the
    allowlisted service-free integration paths. Shipping only tests/unit/ to a
    remote host would silently drop tests/integration/chains/, a required Event
    Chain Gate surface, with no test firing."""
    lib = LIB.read_text(encoding="utf-8")
    argv = lib[lib.index("prepush_remote_argv() {") :]
    argv = argv[: argv.index("\n}\n")]
    assert "FULL_SUITE_TARGET" in argv
    assert "RUNNABLE_INTEGRATION_PATHS" in argv
    assert "PATHS" in argv


def test_the_dangling_runbook_pointer_is_gone() -> None:
    """The die() text cited docs/runbooks/200-build-lane-execution-pattern.md
    for months; that file has never existed in this repo (OMN-16446).

    The replacement pointer is this TABLE, not a new markdown file: the
    add-a-host procedure lives in its header, so the instructions and the rows
    they describe cannot drift apart, and there is no second document to leave
    stale. That also keeps the fix inside the KB doc gate (OMN-16589), which
    blocks new local markdown outside the exemption set."""
    for path in (
        HOOK,
        LIB,
        REPO_ROOT / "scripts" / "hooks" / "pytest_full_suite_host_guard.py",
    ):
        assert "200-build-lane-execution-pattern" not in path.read_text(
            encoding="utf-8"
        ), f"{path} still cites a runbook that does not exist"
    hook_text = HOOK.read_text(encoding="utf-8")
    assert "${PREPUSH_HOST_TABLE_REL}" in hook_text, (
        "every refusal must point somewhere real; the table is that pointer"
    )
    assert "ADDING A HOST" in TABLE.read_text(encoding="utf-8"), (
        "the table header must carry the add-a-host procedure the refusals "
        "point at -- a pointer to a file with no procedure in it is the same "
        "dangling pointer under a new name"
    )


def test_an_unusable_workroot_is_reported_as_infrastructural_not_contention(
    table_repo: Path, tmp_path: Path
) -> None:
    """rc 2 (workroot unusable) must stay distinguishable from rc 1
    (contended). Conflating them would make a permissions problem look like a
    busy host and start refusing heavy pushes that passed before this lock
    existed -- inventing a refusal out of an infrastructural failure."""
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("i am a file")
    out = _driver(
        table_repo,
        f'rc=0; prepush_lock_acquire {blocker}/wr || rc=$?; echo "RC=$rc"',
    )
    assert "RC=2" in out


def test_the_local_fit_path_proceeds_when_the_workroot_is_unusable() -> None:
    """An unusable workroot says nothing about capacity, so the hook must fall
    through to the governed actor route rather than refuse."""
    text = HOOK.read_text(encoding="utf-8")
    start = text.index("guard_full_suite_host() {")
    fit = text[start:]
    fit = fit[fit.index('if host_is_fit ""; then') :][:2400]
    assert '[ "$lock_rc" -eq 2 ]' in fit
    assert "prepush_local_actor_route" in fit


# =============================================================================
# The row scan must reach every host (OMN-16991 verify finding 1)
# =============================================================================


def test_the_picker_scans_every_row_even_when_a_probe_consumes_stdin(
    table_repo: Path,
) -> None:
    """The whole lab must be evaluated, not just whichever row sorts first.

    The picker's loop body invokes ssh(1) three times per row, and ssh reads
    its parent's stdin unless given ``-n``. While the row list WAS the loop's
    stdin, the first probe swallowed every remaining row: the real picker on
    the real network emitted ``PROBE=[h200=fit(0.9,authorizing)]`` and never
    evaluated h201/h101/h105, so a lab with three idle hosts refused the push
    and the feature added exactly zero capacity.

    Reproduced here without a network by stubbing the three probes to DRAIN
    stdin, which is precisely what ssh does. Under the old here-doc-fed loop
    this test sees one label; under the array scan it sees all four.
    """
    body = (
        'host_load_ratio() { while IFS= read -r _junk; do :; done; printf "1.0 10 0.10\\n"; }\n'
        "prepush_slot_state() { while IFS= read -r _junk; do :; done; PREPUSH_SLOT_DETAIL=stub; return 0; }\n"
        "prepush_uv_version_ok() { while IFS= read -r _junk; do :; done; PREPUSH_UV_VERSION_SEEN=9.9.9; return 0; }\n"
        "pick_capacity_host stickybeatz-studio omnibase_core > /dev/null 2>&1 || true\n"
        'echo "PROBE=$PREPUSH_PROBE_LOG"\n'
    )
    out = _driver(table_repo, body)
    for label in ("h200", "h201", "h101", "h105"):
        assert label in out, (
            f"{label} was never evaluated -- the row scan was truncated: {out!r}"
        )


def test_every_ssh_invocation_carries_dash_n(table_repo: Path) -> None:
    """Belt and braces for the same defect, from the other side.

    The array scan alone would fix it, but a stdin-eating probe inside ANY
    future loop reintroduces it silently -- a truncated scan looks exactly like
    a small lab. ``-n`` makes ssh structurally incapable of it.
    """
    invocation = re.compile(r"(?<![\w./-])ssh\s+(-\S+)")
    for path in (LIB, HOOK):
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if line.lstrip().startswith("#"):
                continue
            for match in invocation.finditer(line):
                assert match.group(1) == "-n", (
                    f"{path.name}:{lineno} invokes ssh without -n; inside a row "
                    f"loop that eats the remaining rows: {line.strip()!r}"
                )


# =============================================================================
# A shadow host must never win placement (OMN-16991 verify finding 3)
# =============================================================================


def test_a_shadow_row_never_wins_placement_over_an_authorizing_host(
    tmp_path: Path,
) -> None:
    """Ranking on load alone let the idlest host win regardless of its mode.

    Live dry-run against the shipped picker before this fix:
    ``h200=fit(0.90,authorizing) h201=fit(0.30,authorizing)
    h105=fit(0.20,shadow) -> PICK=h105``. A shadow verdict cannot satisfy the
    escalation, so the run was dispatched, a bundle + scp + `uv sync` + a full
    suite were paid for, and the answer was then discarded -- while the
    authorizing host that could have answered was passed over. Mode is now an
    eligibility filter applied BEFORE the probe, not a post-hoc veto.
    """
    repo = _repo_with_table(tmp_path, _SYNTHETIC_TABLE)
    out = _driver(
        repo,
        'export PREPUSH_LOAD_OVERRIDE_MAP="ha=0.90,hb=0.30,hs=0.05"\n'
        'export PREPUSH_SLOT_OVERRIDE_MAP="ha=free,hb=free,hs=free"\n'
        'export PREPUSH_UV_OVERRIDE_MAP="ha=1.0.0,hb=1.0.0,hs=1.0.0"\n'
        "if pick_capacity_host somewhere-else omnibase_core; then\n"
        '  echo "PICK=$PREPUSH_PICK_LABEL"\n'
        "else\n"
        '  echo "PICK=none"\n'
        "fi\n"
        'echo "PROBE=$PREPUSH_PROBE_LOG"\n',
    )
    assert "PICK=hb" in out, out
    assert "hs=mode-shadow-not-eligible" in out, out
    assert "hs=fit" not in out, "a shadow row must not even be probed for placement"


def test_the_eligible_mode_is_a_parameter_not_a_hardcoded_authorizing(
    tmp_path: Path,
) -> None:
    """Shadow is still a supported mode -- it is just not a candidate for a
    verdict-bearing run. Pinning the parameter keeps a future shadow-day tool
    from having to re-implement the picker to get at those rows."""
    repo = _repo_with_table(tmp_path, _SYNTHETIC_TABLE)
    out = _driver(
        repo,
        'export PREPUSH_LOAD_OVERRIDE_MAP="ha=0.90,hb=0.30,hs=0.05"\n'
        'export PREPUSH_SLOT_OVERRIDE_MAP="ha=free,hb=free,hs=free"\n'
        'export PREPUSH_UV_OVERRIDE_MAP="ha=1.0.0,hb=1.0.0,hs=1.0.0"\n'
        "pick_capacity_host somewhere-else omnibase_core shadow > /dev/null 2>&1\n"
        'echo "PICK=$PREPUSH_PICK_LABEL"\n',
    )
    assert "PICK=hs" in out, out


def test_the_picker_ranks_every_fit_host_not_just_the_winner(
    tmp_path: Path,
) -> None:
    """Placement is a ranked list so a candidate that fails to answer costs the
    next-best host, not the whole escalation."""
    repo = _repo_with_table(tmp_path, _SYNTHETIC_TABLE)
    out = _driver(
        repo,
        'export PREPUSH_LOAD_OVERRIDE_MAP="ha=0.90,hb=0.30,hs=0.05"\n'
        'export PREPUSH_SLOT_OVERRIDE_MAP="ha=free,hb=free,hs=free"\n'
        'export PREPUSH_UV_OVERRIDE_MAP="ha=1.0.0,hb=1.0.0,hs=1.0.0"\n'
        "pick_capacity_host somewhere-else omnibase_core > /dev/null 2>&1\n"
        'echo "COUNT=$(prepush_candidate_count)"\n'
        'prepush_select_candidate 1 && echo "FIRST=$PREPUSH_PICK_LABEL"\n'
        'prepush_select_candidate 2 && echo "SECOND=$PREPUSH_PICK_LABEL"\n'
        'prepush_select_candidate 3 || echo "THIRD=none"\n',
    )
    assert "COUNT=2" in out, out
    assert "FIRST=hb" in out, out
    assert "SECOND=ha" in out, out
    assert "THIRD=none" in out, out


# =============================================================================
# A failed pick must try the next fit host (OMN-16991 verify finding 3)
# =============================================================================


def _extract_shell_function(path: Path, name: str) -> str:
    """The SHIPPED text of one shell function, so these assertions drive the
    code that runs on a push rather than a Python restatement of it."""
    text = path.read_text(encoding="utf-8")
    start = text.index(f"{name}() {{")
    end = text.index("\n}\n", start) + len("\n}\n")
    return text[start:end]


def _dispatch_driver(repo: Path, remote_run_stub: str) -> str:
    body = (
        'export PREPUSH_LOAD_OVERRIDE_MAP="ha=0.90,hb=0.30,hs=0.05"\n'
        'export PREPUSH_SLOT_OVERRIDE_MAP="ha=free,hb=free,hs=free"\n'
        'export PREPUSH_UV_OVERRIDE_MAP="ha=1.0.0,hb=1.0.0,hs=1.0.0"\n'
        "PREPUSH_LC_HOST=somewhere-else\n"
        "REMOTE_LAB_RUN_VERDICT=0\n"
        + _extract_shell_function(HOOK, "dispatch_to_lab_host")
        + remote_run_stub
        + 'if dispatch_to_lab_host "heavy thing"; then\n'
        '  echo "RESULT=satisfied verdict=$REMOTE_LAB_RUN_VERDICT host=$PREPUSH_PICK_LABEL"\n'
        "else\n"
        '  echo "RESULT=no-evidence"\n'
        "fi\n"
    )
    return _driver_both(repo, body)


def test_dispatch_tries_the_next_ranked_host_when_the_first_yields_no_evidence(
    tmp_path: Path,
) -> None:
    """ "No completion marker" says nothing about the tree -- it is a placement
    miss. Before this fix the whole escalation was staked on one host: a single
    unreachable-on-arrival candidate refused a push that the second-ranked
    host, idle and reachable, would have cleared."""
    repo = _repo_with_table(tmp_path, _SYNTHETIC_TABLE)
    out = _dispatch_driver(
        repo,
        'prepush_remote_run() { echo "TRIED=$PREPUSH_PICK_LABEL";'
        ' [ "$PREPUSH_PICK_LABEL" = "hb" ] && return 1; return 0; }\n',
    )
    assert "TRIED=hb" in out, out
    assert "TRIED=ha" in out, out
    assert "RESULT=satisfied verdict=1 host=ha" in out, out


def test_dispatch_tries_the_next_ranked_host_when_the_slot_is_taken_on_arrival(
    tmp_path: Path,
) -> None:
    """rc 4 = the target's heavy-suite slot was held when the wrapper landed,
    so NO suite ran there. That is a placement miss too, and refusing on it
    would turn a race with another dispatcher into a failed push."""
    repo = _repo_with_table(tmp_path, _SYNTHETIC_TABLE)
    out = _dispatch_driver(
        repo,
        'prepush_remote_run() { echo "TRIED=$PREPUSH_PICK_LABEL";'
        ' [ "$PREPUSH_PICK_LABEL" = "hb" ] && return 4; return 0; }\n',
    )
    assert "TRIED=hb" in out
    assert "TRIED=ha" in out
    assert "RESULT=satisfied verdict=1 host=ha" in out, out


def test_dispatch_refuses_on_a_remote_red_without_shopping_for_a_greener_host(
    tmp_path: Path,
) -> None:
    """The retry loop must not become verdict shopping. A RED is a verdict --
    the suite genuinely failed on a host we designated -- so it refuses right
    there and never asks a second host for a nicer answer."""
    repo = _repo_with_table(tmp_path, _SYNTHETIC_TABLE)
    out = _dispatch_driver(
        repo,
        'prepush_remote_run() { echo "TRIED=$PREPUSH_PICK_LABEL";'
        ' [ "$PREPUSH_PICK_LABEL" = "hb" ] && return 3; return 0; }\n',
    )
    assert "TRIED=hb" in out
    assert "TRIED=ha" not in out, "a remote RED must not fall through to another host"
    assert "DIE:" in out, out
    assert "RESULT=" not in out


def test_dispatch_reports_no_evidence_when_no_ranked_host_answers(
    tmp_path: Path,
) -> None:
    repo = _repo_with_table(tmp_path, _SYNTHETIC_TABLE)
    out = _dispatch_driver(repo, "prepush_remote_run() { return 1; }\n")
    assert "RESULT=no-evidence" in out, out


def test_dispatch_asks_the_picker_for_authorizing_rows_explicitly() -> None:
    """The verdict-bearing path names the mode it needs at the call site, so a
    later default change cannot quietly make shadow hosts placeable again."""
    body = _extract_shell_function(HOOK, "dispatch_to_lab_host")
    assert 'pick_capacity_host "$PREPUSH_LC_HOST" "$repo" authorizing' in body


# =============================================================================
# The remote leg must take the TARGET host's slot (OMN-16991 verify finding 2)
# =============================================================================


def _remote_wrapper_text() -> str:
    """The wrapper exactly as it is shipped to the target host."""
    lib = LIB.read_text(encoding="utf-8")
    opener = "cat > \"$runner\" <<'REMOTE'\n"
    start = lib.index(opener) + len(opener)
    return lib[start : lib.index("\nREMOTE\n", start)] + "\n"


def _self_hostname() -> str:
    return subprocess.run(
        ["hostname", "-s"], capture_output=True, text=True, check=False
    ).stdout.strip()


@pytest.fixture
def remote_run_env(tmp_path: Path) -> dict[str, Path]:
    """A materialized remote-side run: workroot, rundir, a real git bundle, an
    argv file, the shipped wrapper, and a fake `uv` that records whether the
    host lock was held WHILE the suite ran."""
    src = tmp_path / "src"
    (src / "tests").mkdir(parents=True)
    (src / "tests" / "test_a.py").write_text("def test_a():\n    assert True\n")
    subprocess.run(
        ["git", "init", "-q", "."],
        cwd=src,
        check=True,
        env=scrub_git_location_env(os.environ),
    )
    subprocess.run(
        ["git", "add", "-A"],
        cwd=src,
        check=True,
        env=scrub_git_location_env(os.environ),
    )
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "t"],
        cwd=src,
        check=True,
        env=scrub_git_location_env(os.environ),
    )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=src,
        capture_output=True,
        text=True,
        check=True,
        env=scrub_git_location_env(os.environ),
    ).stdout.strip()

    workroot = tmp_path / "workroot"
    rundir = workroot / "runs" / "r1"
    rundir.mkdir(parents=True)
    subprocess.run(
        ["git", "bundle", "create", str(rundir / "tree.bundle"), "HEAD"],
        cwd=src,
        check=True,
        capture_output=True,
        env=scrub_git_location_env(os.environ),
    )
    (rundir / "argv.txt").write_text("tests\n")

    wrapper = rundir / "prepush_smart_tests.sh"
    wrapper.write_text(_remote_wrapper_text())
    wrapper.chmod(0o755)

    witness = tmp_path / "lock_witness"
    fake_uv = tmp_path / "uv"
    fake_uv.write_text(
        "#!/bin/sh\n"
        # OMN-17741: record the workspace root the wrapper handed us. Written
        # on BOTH the `sync` and the pytest invocation, so a wrapper that
        # establishes the registry too late (after `uv sync`) is still caught.
        'printf "%s\\n" "${OMNI_HOME:-<unset>}" > "$OMNI_HOME_WITNESS"\n'
        'if [ "$1" = "sync" ]; then exit 0; fi\n'
        # Proof that the target-host slot is held for the DURATION of the run,
        # not merely acquired and dropped before the expensive part.
        'if [ -d "$LOCK_PROBE" ]; then echo held > "$LOCK_WITNESS"; '
        'else echo free > "$LOCK_WITNESS"; fi\n'
        'echo "collected 3 items"\n'
        'exit "${FAKE_UV_EXIT:-0}"\n'
    )
    fake_uv.chmod(0o755)

    return {
        "workroot": workroot,
        "rundir": rundir,
        "uv": fake_uv,
        "witness": witness,
        "omni_home_witness": tmp_path / "omni_home_witness",
        "head": head,  # type: ignore[dict-item]
    }


def _run_wrapper(
    env_info: dict[str, Path],
    *,
    extra_env: dict[str, str] | None = None,
    extra_argv: list[str] | None = None,
    repo: str = "omnibase_core",
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "LOCK_PROBE": str(env_info["workroot"] / "LOCK"),
        "LOCK_WITNESS": str(env_info["witness"]),
        "OMNI_HOME_WITNESS": str(env_info["omni_home_witness"]),
    }
    # FIDELITY, not tidiness (OMN-17741): `ssh` forwards no environment, so on
    # a real target host the wrapper starts with OMNI_HOME UNSET. This pytest
    # process inherits a developer shell where it IS set, and leaking that in
    # would let a wrapper that establishes nothing pass the registry assertions
    # on the launcher's value.
    env.pop("OMNI_HOME", None)
    env.update(extra_env or {})
    # The wrapper's trailing positionals are optional on the remote side but
    # POSITIONAL, so they are padded here rather than appended: a caller that
    # passes only BASE_REF/BASE_SHA must still land the repo name in slot 10.
    tail = list(extra_argv or [])
    base_ref = tail[0] if len(tail) > 0 else ""
    base_sha = tail[1] if len(tail) > 1 else ""
    slot = tail[2] if len(tail) > 2 and tail[2] else "1"
    return subprocess.run(
        [
            "bash",
            str(env_info["rundir"] / "prepush_smart_tests.sh"),
            str(env_info["rundir"]),
            str(env_info["uv"]),
            str(env_info["head"]),
            "argvsha",
            "origin-host:1",
            str(env_info["workroot"]),
            base_ref,
            base_sha,
            slot,
            repo,
        ],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
        stdin=subprocess.DEVNULL,
        env=env,
    )


def test_the_remote_leg_holds_the_target_hosts_lock_for_the_whole_run(
    remote_run_env: dict[str, Path],
) -> None:
    """The remote leg took NO lock on the target before this fix.

    Polled live during a real 25s dispatch to omnibook: ``LOCK=no`` throughout,
    and afterwards the workroot held only ``runs/`` -- after two real
    dispatches. So the local heavy path (which DOES take the lock) and a
    transplanted suite could run on the same host at the same time: OMN-16174's
    overlap, reopened across the local/remote boundary. Remote exclusion rested
    entirely on ``ps ax | grep prepush_smart_tests.sh``, which has a
    probe -> scp -> exec race window.
    """
    result = _run_wrapper(remote_run_env)
    assert result.returncode == 0, result.stderr
    assert remote_run_env["witness"].read_text().strip() == "held", (
        "the target host's LOCK was not held while the suite was executing"
    )
    marker = (remote_run_env["rundir"] / "MARKER").read_text()
    assert "exit=0" in marker
    assert "collected=3" in marker
    assert not (remote_run_env["workroot"] / "LOCK").exists(), (
        "the lock must be released when the wrapper exits"
    )


# =============================================================================
# The transplanted tree needs a registry root (OMN-17741)
# =============================================================================
# Ported from omnibase_infra (OMN-17741, merge 4053dc3c065b0bc94e98001a28ea9415
# ffd782cb, PR #3161) under OMN-17754, and re-run here against THIS repo's copy
# of the library. `ssh` forwards no environment, so the wrapper starts with
# OMNI_HOME unset on every target host. Code the suite runs that resolves a
# workspace then either fails, or -- the case actually measured upstream --
# falls back to a home-relative default that EXISTS on the lab Macs and is
# TCC-denied to `sshd`. OMN-17459 recorded that shape: a real full suite on
# h101, 17,883 tests in 13m58s, 12 failures, all 12 green locally, one root
# cause.
#
# A false red here HARD-BLOCKS a push (`dispatch_to_lab_host` rc=3 -> `die`,
# "a remote red is never satisfied by minting an override grant"), so this is
# part of the verdict meaning anything -- the same standing the PATH-parity
# block already has.


def test_the_remote_wrapper_gives_the_transplanted_tree_a_registry_root(
    remote_run_env: dict[str, Path],
) -> None:
    """The value must be a REAL registry the remote process can write, holding
    the transplanted repo under its own name -- not an unset variable and not a
    bare rundir, which contains no directory named for the repo at all."""
    result = _run_wrapper(remote_run_env, repo="omnibase_core")
    assert result.returncode == 0, result.stderr

    recorded = remote_run_env["omni_home_witness"].read_text().strip()
    assert recorded != "<unset>", (
        "the suite ran with no OMNI_HOME: every workspace-resolving call site "
        "in the transplanted tree is left to guess, and the lab Macs have a "
        "TCC-denied ~/Code/omni_home for it to guess wrong onto"
    )
    registry = Path(recorded)
    assert registry == remote_run_env["rundir"] / "omni_home", recorded
    assert registry.is_dir()

    linked = registry / "omnibase_core"
    assert linked.is_symlink(), "the repo must be reachable under its own name"
    assert linked.resolve() == (remote_run_env["rundir"] / "tree").resolve()
    assert (linked / "tests" / "test_a.py").is_file(), (
        "the registry entry must resolve to the tree that was actually cloned"
    )

    # Writability is the whole point: the measured failure was PermissionError
    # on mkdir, not a missing path.
    (registry / ".onex_state" / "probe").mkdir(parents=True)


def test_the_registry_root_is_established_on_target_never_inherited(
    remote_run_env: dict[str, Path],
) -> None:
    """Forwarding the LAUNCHER's OMNI_HOME is strictly worse than leaving it
    unset: the launcher's workspace path exists on every lab Mac and is
    TCC-denied to `sshd`, so forwarding converts a fail-fast into a
    PermissionError deep inside a test. Pin that an inherited value loses."""
    launcher_value = "/nonexistent/launcher/Code/omni_home"
    result = _run_wrapper(
        remote_run_env,
        repo="omnibase_core",
        extra_env={"OMNI_HOME": launcher_value},
    )
    assert result.returncode == 0, result.stderr
    recorded = remote_run_env["omni_home_witness"].read_text().strip()
    assert recorded != launcher_value, (
        "the wrapper forwarded the launcher's workspace path to the target host"
    )
    assert recorded == str(remote_run_env["rundir"] / "omni_home")
    assert (Path(recorded) / "omnibase_core").is_symlink()


def test_the_registry_root_is_named_by_the_dispatch_not_hardcoded(
    remote_run_env: dict[str, Path],
) -> None:
    """One wrapper serves omnibase_infra, omnibase_core and omnimarket, so the
    repo name has to travel with the dispatch. `prepush_remote_run` already
    computes it as `basename "$REPO_ROOT"`; assert it is passed through as the
    tenth positional, and that a dispatch naming a different repo gets a
    registry entry under THAT name."""
    lib = LIB.read_text(encoding="utf-8")
    idx = lib.index('remote_cmd="cd ')
    invocation = lib[idx : lib.index("\n", idx)]
    assert "'${repo}'" in invocation, (
        "the remote command does not pass the repo name to the wrapper: " + invocation
    )
    remote = _remote_wrapper_text()
    assert "REPO_NAME=" in remote, "the wrapper does not bind a repo name positional"
    for hardcoded in ("omni_home/omnibase_core", "omni_home/omnimarket"):
        assert hardcoded not in remote

    result = _run_wrapper(remote_run_env, repo="some-other-repo")
    assert result.returncode == 0, result.stderr
    registry = Path(remote_run_env["omni_home_witness"].read_text().strip())
    assert (registry / "some-other-repo").is_symlink()
    assert not (registry / "omnibase_core").exists()


def test_the_registry_root_lives_under_the_gc_swept_workroot() -> None:
    """It must not become a new class of stranded state. `prepush_remote_gc`
    sweeps `<workroot>/runs`, so the registry belongs inside the rundir."""
    remote = _remote_wrapper_text()
    idx = remote.index("OMNI_HOME=")
    assignment = remote[idx : remote.index("\n", idx)]
    assert "$RUNDIR/" in assignment, assignment


def test_a_dispatch_that_names_no_repo_is_no_evidence_not_a_verdict(
    remote_run_env: dict[str, Path],
) -> None:
    """A registry that cannot be built on the TARGET says nothing about the
    tree under test. The wrapper exits 98 before the suite runs, which produces
    no MARKER -- the classification the dispatcher already walks past."""
    result = _run_wrapper(remote_run_env, repo="")
    assert result.returncode == 98, (result.returncode, result.stderr)
    assert "NO_REPO_NAME_FOR_REGISTRY_ROOT" in result.stderr
    assert not (remote_run_env["rundir"] / "MARKER").exists()
    assert not (remote_run_env["workroot"] / "LOCK").exists(), (
        "the slot must be released even when the registry cannot be built"
    )


def test_the_remote_leg_releases_the_lock_even_when_the_suite_fails(
    remote_run_env: dict[str, Path],
) -> None:
    """A red suite must not wedge the host. Release is an EXIT trap, not a
    line after the happy path."""
    result = _run_wrapper(remote_run_env, extra_env={"FAKE_UV_EXIT": "1"})
    assert result.returncode == 1
    assert "exit=1" in (remote_run_env["rundir"] / "MARKER").read_text()
    assert not (remote_run_env["workroot"] / "LOCK").exists()


def test_the_remote_wrapper_locks_a_numbered_lockdir_for_slot_two(
    remote_run_env: dict[str, Path],
) -> None:
    """OMN-17269: SLOT_INDEX (positional arg 9) selects WHICH lockdir this
    dispatch holds. Slot 1 (the default, exercised by every other test in this
    file) keeps the bare `LOCK` path; slot 2 must hold `LOCK.2` instead -- a
    DIFFERENT directory, not merely a different witness of the same one, so a
    second concurrent lane can hold its own exclusive lock on the same host
    without contending slot 1's."""
    workroot = remote_run_env["workroot"]
    slot2_probe = workroot / "LOCK.2"
    env = {
        **os.environ,
        "LOCK_PROBE": str(slot2_probe),
        "LOCK_WITNESS": str(remote_run_env["witness"]),
        "OMNI_HOME_WITNESS": str(remote_run_env["omni_home_witness"]),
    }
    env.pop("OMNI_HOME", None)
    result = subprocess.run(
        [
            "bash",
            str(remote_run_env["rundir"] / "prepush_smart_tests.sh"),
            str(remote_run_env["rundir"]),
            str(remote_run_env["uv"]),
            str(remote_run_env["head"]),
            "argvsha",
            "origin-host:1",
            str(workroot),
            "",
            "",
            "2",
            "omnibase_core",
        ],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
        stdin=subprocess.DEVNULL,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert remote_run_env["witness"].read_text().strip() == "held", (
        "slot 2 must hold LOCK.2 while the suite runs, not the bare LOCK dir "
        "slot 1 uses"
    )
    assert not slot2_probe.exists(), "LOCK.2 must be released when the wrapper exits"
    assert not (workroot / "LOCK").exists(), (
        "a slot-2 dispatch must never touch slot 1's bare LOCK dir"
    )


def test_the_remote_leg_refuses_when_the_target_slot_is_already_held(
    remote_run_env: dict[str, Path],
) -> None:
    """Exit 94 is "no suite ran here", which the caller turns into "try the
    next ranked host" -- never into a verdict about the tree."""
    lockdir = remote_run_env["workroot"] / "LOCK"
    lockdir.mkdir(parents=True)
    (lockdir / "holder").write_text(
        f"{os.getpid()} {_self_hostname()} 2026-01-01T00:00:00Z\n"
    )
    result = _run_wrapper(remote_run_env)
    assert result.returncode == 94, result.stderr
    assert "REMOTE_LOCK_CONTENDED" in result.stderr
    assert not (remote_run_env["rundir"] / "MARKER").exists(), (
        "a contended slot must produce no marker -- a marker is a verdict"
    )
    assert lockdir.exists(), "the live holder's lock must survive the refusal"


def test_the_remote_leg_reclaims_a_lock_whose_holder_died_on_that_host(
    remote_run_env: dict[str, Path],
) -> None:
    """mkdir(2) does not auto-release on death, so one externally-SIGTERMed run
    (OMN-16713) would wedge the host forever without this."""
    lockdir = remote_run_env["workroot"] / "LOCK"
    lockdir.mkdir(parents=True)
    (lockdir / "holder").write_text(
        f"4194303 {_self_hostname()} 2026-01-01T00:00:00Z\n"
    )
    result = _run_wrapper(remote_run_env)
    assert result.returncode == 0, result.stderr
    assert remote_run_env["witness"].read_text().strip() == "held"


def test_the_remote_leg_never_reclaims_a_lock_held_from_another_machine(
    remote_run_env: dict[str, Path],
) -> None:
    """A pid from another host says nothing about whether a process HERE is
    alive, so a foreign holder is never reaped on a liveness check."""
    lockdir = remote_run_env["workroot"] / "LOCK"
    lockdir.mkdir(parents=True)
    (lockdir / "holder").write_text("4194303 some-other-host 2026-01-01T00:00:00Z\n")
    result = _run_wrapper(remote_run_env)
    assert result.returncode == 94, result.stderr


def test_the_remote_command_carries_no_set_e_that_would_eat_the_wrapper_exit() -> None:
    """Under ``set -e`` a failing (or slot-contended, exit 94) wrapper aborts
    the remote shell BEFORE ``rc=$?`` runs, so the one fact this leg needs --
    why the wrapper stopped -- is the fact that never gets written."""
    lib = LIB.read_text(encoding="utf-8")
    cmd = lib[lib.index("./prepush_smart_tests.sh '${rundir}'") - 400 :][:900]
    assert "set -e;" not in cmd, cmd
    assert "WRAPPER_EXIT" in cmd
    assert 'wrapper_exit:-}" = "94"' in lib, (
        "the contended-slot code must be routed to a try-the-next-host result"
    )


# =============================================================================
# Housekeeping invariants
# =============================================================================


def test_the_lock_release_and_the_tempfile_cleanup_share_one_exit_trap() -> None:
    """bash keeps exactly ONE EXIT trap per shell. The guard used to install
    ``trap prepush_lock_release EXIT`` after the hook had already installed the
    mktemp cleanup, silently replacing it and leaking three temp files on every
    heavy run that took the host slot."""
    text = HOOK.read_text(encoding="utf-8")
    traps = re.findall(r"^\s*trap\s+\S+\s+EXIT", text, flags=re.MULTILINE)
    assert len(traps) == 1, f"expected exactly one EXIT trap, found {traps}"
    cleanup = _extract_shell_function(HOOK, "prepush_hook_cleanup")
    assert "CHANGED_FILE" in cleanup
    assert "prepush_lock_release" in cleanup


def test_the_remote_leg_reclaims_the_transplanted_tree() -> None:
    """A clone plus ``uv sync --all-extras`` is ~0.5 GB per run and nothing
    pruned it: two dispatches left 1.0 GB on omnibook, the host the picker
    prefers, which fills a laptop disk in a few hundred pushes and then fails
    runs for a reason that looks nothing like its cause."""
    lib = LIB.read_text(encoding="utf-8")
    gc = _extract_shell_function(LIB, "prepush_remote_gc")
    assert "rm -rf '${2}/tree'" in gc
    assert "-mtime +3" in gc
    run = lib[lib.index("prepush_remote_run() {") :]
    assert run.count("prepush_remote_gc ") >= 4, (
        "every terminal path of the remote leg must reclaim the tree"
    )


def test_a_remote_red_fetches_the_suite_log_it_tells_you_to_read() -> None:
    """The refusal instructs the developer to read the streamed output, but the
    wrapper redirects pytest into ``$RUNDIR/suite.log`` on the REMOTE host --
    so before this there was nothing above to read and a remote RED, which
    hard-blocks the push, was undiagnosable without a manual ssh."""
    lib = LIB.read_text(encoding="utf-8")
    assert "tail -n 200 '${rundir}/suite.log'" in lib
    red = lib[lib.index('if [ "$m_exit" -ne 0 ]; then') :][:900]
    assert "suite.log" in red


# =============================================================================
# The pytest-side guard reads the SAME table (OMN-16991 verify finding 4)
# =============================================================================
#
# This is the coupling that made the shadow mode useless. A dispatched run is
# executed by a TRANSPLANTED copy of this repo, and that copy carries this
# repo's own conftest.py -> scripts/hooks/pytest_full_suite_host_guard.enforce,
# which refuses a full-suite target on any host outside the authorizing set.
# So while omnibook was `shadow`, every heavy dispatch to it exited nonzero at
# pytest_configure and wrote a receipt whose pytest_exit != 0 is
# indistinguishable from a genuine red. The "shadow day, then promote" plan was
# unreachable by construction: the shadow host could never record a green.

_GIT_SCOPING_ENV_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_COMMON_DIR",
    "GIT_PREFIX",
)


def _designated_from(repo: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[str, ...]:
    """`designated_hostnames()` resolved against REPO's committed table.

    A live `git push` exports GIT_DIR/GIT_WORK_TREE into hook children and they
    override both `-C` and cwd for every descendant git call, so they are
    cleared here -- otherwise this would silently read THIS worktree.
    """
    from scripts.hooks.pytest_full_suite_host_guard import designated_hostnames

    for var in _GIT_SCOPING_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(repo)
    return designated_hostnames(env={})


def test_the_conftest_guard_reads_the_same_committed_table_as_the_bash_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo_with_table(tmp_path, TABLE.read_text(encoding="utf-8"), name="shipped")
    assert _designated_from(repo, monkeypatch) == (
        "stickybeatz-studio",
        "omninode-pc",
        "gate-runner-201",
        "stickybeatz",
        "omnibook",
        "onex-prepush-cloud1",
    )


def test_omnibook_can_now_produce_a_green_full_suite_verdict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The end of finding 4, asserted on the exact decision function that
    refused: with h105 authorizing, a full-suite target transplanted to
    omnibook is no longer rejected at pytest_configure, so a dispatch there can
    return a verdict that means something."""
    from scripts.hooks.pytest_full_suite_host_guard import (
        full_suite_host_violation_message,
    )

    repo = _repo_with_table(
        tmp_path, TABLE.read_text(encoding="utf-8"), name="shipped2"
    )
    names = _designated_from(repo, monkeypatch)
    assert (
        full_suite_host_violation_message(
            host="omnibook",
            target_hostname=names[0],
            additional_target_hostnames=names[1:],
            override_authorized=False,
        )
        is None
    )


def test_a_shadow_row_is_still_refused_by_the_conftest_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Promotion is what changed for h105 -- not the rule. A row in `shadow`
    confers no identity on either guard, which is exactly why a shadow host can
    never self-certify its way to `authorizing`."""
    from scripts.hooks.pytest_full_suite_host_guard import (
        full_suite_host_violation_message,
    )

    repo = _repo_with_table(tmp_path, _SYNTHETIC_TABLE, name="synthguard")
    names = _designated_from(repo, monkeypatch)
    assert names == ("hosta", "hostb")
    message = full_suite_host_violation_message(
        host="hosts",
        target_hostname=names[0],
        additional_target_hostnames=names[1:],
        override_authorized=False,
    )
    assert message is not None
    assert "hosts" in message


def test_the_remote_wrapper_restores_a_developer_shell_path() -> None:
    """A non-interactive ssh session gets a minimal PATH -- measured on omnibook
    it is literally ``/usr/bin:/bin:/usr/sbin:/sbin``, with neither the Homebrew
    prefix nor ``~/.local/bin`` on it. The suite shells out to tools by BARE
    NAME (``uv``, ``shellcheck``), so the first full-suite dispatch there
    returned 8 reds, every one a FileNotFoundError for a tool that WAS installed
    on the host. A remote red hard-blocks the push, so PATH parity is what makes
    the verdict mean anything."""
    remote = _remote_wrapper_text()
    assert 'PATH="$(dirname "$UV")' in remote
    assert "/opt/homebrew/bin" in remote
    assert "/usr/local/bin" in remote
    assert "export PATH" in remote
    argv_line = remote.index('"$UV" run pytest')
    assert remote.index("export PATH") < argv_line, (
        "PATH must be set before the suite runs, not after"
    )


def test_the_remote_wrapper_path_covers_linux_hosts_too() -> None:
    """The shipped prefix was macOS-only by construction (OMN-16989):
    ``/opt/homebrew/bin`` has no meaning on a Linux row, and h201 is the fleet's
    only Linux capacity row. Its measured non-interactive PATH omits
    ``~/.local/bin``, where BOTH ``uv`` and ``shellcheck`` live there.

    The Linux analogues are appended AFTER every measured entry, so they can
    only add resolution -- a tool that already resolves keeps resolving to the
    same binary."""
    remote = _remote_wrapper_text()
    line = next(
        ln for ln in remote.splitlines() if ln.startswith('PATH="$(dirname "$UV")')
    )
    for entry in (
        "/home/linuxbrew/.linuxbrew/bin",  # local-path-ok: pins a remote PATH entry
        "/snap/bin",
    ):
        assert entry in line, f"expected {entry} on the remote PATH"
    assert line.index("${HOME:-}/.local/bin") < line.index(
        "/home/linuxbrew/.linuxbrew/bin"  # local-path-ok: see above
    ), "the measured entries must keep precedence over the added ones"


def test_the_remote_leg_ships_the_base_ref_so_the_transplant_can_resolve_it() -> None:
    """``git bundle create <b> HEAD`` carries one ref, so the transplanted clone
    has no ``origin/dev`` -- and this suite SUBPROCESSES the hook, which
    resolves ``${PREPUSH_BASE_REF:-origin/dev}`` before anything else. Measured
    on h201 (OMN-16989): the whole
    ``tests/scripts/test_prepush_hook_host_identity_guard.py`` behavioral proof
    reduced to ``base ref 'origin/dev' could not be resolved`` -- a red about the
    transplant, not about the tree under test."""
    lib = LIB.read_text(encoding="utf-8")
    cmd = lib[lib.index("./prepush_smart_tests.sh '${rundir}'") :][:400]
    assert "'${base_ref}' '${base_sha}'" in cmd, (
        "the remote command must hand the wrapper the base ref and its sha"
    )
    assert 'base_ref="${BASE_REF:-}"' in lib
    assert 'base_sha="${BASE_SHA:-}"' in lib


def test_the_wrapper_materializes_the_base_ref_in_the_transplanted_tree(
    remote_run_env: dict[str, Path],
) -> None:
    """Behavioral: run the shipped wrapper with a base ref and assert the clone
    resolves it afterwards. BASE_SHA is a merge-base on the origin side, so it
    is always an ancestor of HEAD and its objects are already in the bundle --
    only the ref is missing, and creating it is a local ``update-ref``."""
    head = str(remote_run_env["head"])
    result = _run_wrapper(remote_run_env, extra_argv=["origin/dev", head])
    assert result.returncode == 0, result.stderr
    tree = remote_run_env["rundir"] / "tree"
    resolved = subprocess.run(
        ["git", "rev-parse", "origin/dev"],
        cwd=tree,
        capture_output=True,
        text=True,
        check=False,
        env=scrub_git_location_env(os.environ),
    )
    assert resolved.returncode == 0, (
        f"the transplanted tree must resolve origin/dev; got {resolved.stderr!r}"
    )
    assert resolved.stdout.strip() == head


def test_the_wrapper_runs_normally_when_no_base_ref_is_supplied(
    remote_run_env: dict[str, Path],
) -> None:
    """Absent or unresolvable, the base ref is skipped SILENTLY. It may only add
    resolution -- it must never be able to refuse a run, which would turn a
    convenience into a new way to hard-block a push."""
    result = _run_wrapper(remote_run_env, extra_argv=["origin/dev", "0" * 40])
    assert result.returncode == 0, result.stderr
    assert (remote_run_env["rundir"] / "MARKER").is_file()


# =============================================================================
# Cross-repo parity of the picker library (OMN-17159 DoD item 3)
# =============================================================================


# =============================================================================
# Vendored-file provenance: digest + upstream commit (OMN-17754)
# =============================================================================
# Three repos are meant to run one picker, not three that drifted. The obvious
# assertion -- "all three copies are identical" -- is NOT implementable from a
# repo-local harness: this suite cannot read a sibling checkout, and a test
# that reaches for `$OMNI_HOME/omnibase_infra` would pass or fail on whether an
# unrelated clone happens to exist. So each repo pins the sha256 of the copy IT
# ships, and a local edit is a deliberate, reviewed digest bump rather than a
# silent fork.
#
# Until OMN-17754 this repo pinned that digest as a literal inside this test,
# which detects a LOCAL edit but says nothing about whether the copy is STALE
# -- measured 2026-09-01, core's copy sat a whole feature (OMN-17392) behind
# upstream before its own PR merged, and nothing here could say so. The record
# now lives in scripts/hooks/prepush_vendored.tsv, the same shape omnimarket
# adopted under OMN-17435: each row carries the upstream COMMIT alongside the
# digest, so "has upstream moved?" is answerable by anyone with network access
# without this repo needing that access at push time. The header of that file
# records where and why this repo's copy diverges from a verbatim take.

VENDORED = REPO_ROOT / "scripts" / "hooks" / "prepush_vendored.tsv"


def _vendored_rows() -> list[list[str]]:
    rows = []
    for line in VENDORED.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0]
        if not line.strip():
            continue
        rows.append(line.split("\t"))
    return rows


def test_every_vendored_file_matches_its_recorded_digest() -> None:
    """The shipped bytes and the provenance record cannot disagree.

    Updating a vendored file is a legitimate, expected operation -- re-copy (or
    re-port) from the named upstream path, update BOTH the sha256 and the
    upstream_commit in the same commit, and name the upstream revision in the
    PR body. Editing the file WITHOUT touching the record is the thing that
    cannot happen quietly.
    """
    rows = _vendored_rows()
    assert rows, f"expected at least one provenance row in {VENDORED}"
    for row in rows:
        assert len(row) == 7, f"malformed provenance row: {row!r}"
        rel, _repo, _upath, commit, _branch, digest, _copied = row
        target = REPO_ROOT / rel
        assert target.is_file(), f"provenance names a missing file: {rel}"
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        assert actual == digest, (
            f"{rel} has diverged from its recorded copy "
            f"({_repo}@{commit}:{_upath}). If the change is intentional, update "
            f"the sha256 in {VENDORED.name} in the same commit and say which "
            "upstream revision it now tracks; if it is not, restore the file"
        )
        assert len(commit) == 40, (
            f"upstream_commit for {rel} is not a full 40-char sha: {commit!r}"
        )
        assert all(c in "0123456789abcdef" for c in commit), (
            f"upstream_commit for {rel} is not lowercase hex: {commit!r}"
        )


def test_the_picker_library_is_covered_by_the_provenance_record() -> None:
    """The picker specifically -- not merely "some file" -- must be pinned.

    A provenance file that happened to list only the two Python helpers would
    leave the fail-closed placement logic itself unguarded, which is the one
    file whose silent fork actually changes where a suite runs.
    """
    covered = {row[0] for row in _vendored_rows()}
    assert "scripts/hooks/prepush_dispatch.sh" in covered
    assert "scripts/hooks/prepush_override_grant.py" in covered
    assert "scripts/hooks/pytest_full_suite_host_guard.py" in covered


def test_the_picker_library_is_not_edited_into_a_repo_specific_fork() -> None:
    """The copied library must carry no repo-local branching.

    A conditional on the repo name inside the shared picker is how "one
    mechanism, three repos" becomes three mechanisms wearing one filename. The
    supported seam for per-repo behavior is the host TABLE (repos_denied, mode,
    slots) and the CALLER's argv, both of which are data this library reads --
    never a branch compiled into the library itself.
    """
    text = LIB.read_text(encoding="utf-8")
    for token in ("omnibase_core", "omnimarket"):
        assert token not in text, (
            f"the shared picker library names {token!r}; per-repo behavior "
            "belongs in prepush_hosts.tsv or the caller's argv, not in a "
            "branch inside the shared file"
        )


# =============================================================================
# The collected count must be REAL, and acceptance must gate on it (OMN-17787)
# =============================================================================
# Ported from omnibase_infra (OMN-17787, merge 812d0b5451c1b157dd764cc26a83b9c
# 7e12bcf71, PR #3179) under OMN-17754. The port is NOT mechanical: this repo
# reproduces the defect through a THIRD mechanism the upstream copy does not
# have, pinned separately below.
#
# `collected=` in the completion marker is the only number in the whole
# dispatch that can distinguish "the remote host ran the selection green" from
# "the remote host ran NOTHING and exited 0". Two things were wrong: the number
# was structurally zero, and nothing compared it to anything.
#
# WHAT WAS MEASURED IN THIS REPO, read-only out of the lab run dirs on
# 2026-09-04. Not a sample -- EVERY remote run dir for this repo present on
# either host records `collected=0`, serial and parallel alike:
#
#   h105 .../runs/<repo>-378075e85050-2669   SERIAL, 3:57:27
#     suite.log:9   ESC[1mcollecting ... ESC[0mcollected 44730 items / 4 skipped
#     MARKER        exit=0  collected=0
#   h105 .../runs/<repo>-d839c27cb88a-83571  -n4 --dist=loadgroup, 1:34:58
#     suite.log:13  4 workers [44741 items]
#     MARKER        exit=0  collected=0     (44683 passed)
#   h101 .../runs/<repo>-cef00a3fa597-37250  SERIAL, 4:46:38
#     MARKER        exit=0  collected=0     (44664 passed)
#
# TWO INDEPENDENT CAUSES, and upstream only has one of them:
#
# 1. `pytest-xdist` 3.8.0 REPLACES the collector banner with `N workers [M
#    items]`, so `^collected N items` matches nothing under the OMN-17603
#    execution policy. That is upstream's cause, and it is live here too --
#    OMN-17603 (#1643) made `-n4 --dist=loadgroup` the remote policy in this
#    repo on 2026-09-03, so the note that this repo's remote leg "still runs
#    serial" was already stale when this port was briefed.
#
# 2. THIS REPO ONLY: the serial banner does not match either, and never has.
#    `tests/pytest.ini` addopts carries `--color=yes`, and the remote leg's
#    rootdir resolves to `tests/` so that file is the one pytest reads. The
#    banner therefore arrives as
#    `ESC[1mcollecting ... ESC[0mcollected 44730 items / 4 skipped` -- the line
#    does not BEGIN with `collected`, so the `^` anchor fails. Upstream has no
#    `tests/pytest.ini` at all and so has an uncolored banner; a verbatim copy
#    of the upstream fallback chain would ship a dead fallback here.
#
# The consequence of (1)+(2) together is that in this repo the marker count was
# not intermittently wrong, it was ALWAYS zero -- and with exit-code-only
# acceptance, every green remote run in this repo's history was accepted as
# "ran 0 tests green".
#
# Why the existing wrapper fixture never caught it: `remote_run_env`'s fake
# `uv` echoes `collected 3 items` -- an uncolored SERIAL banner, i.e. the one
# form this repo's remote leg can never actually produce.


def _sh_quote(value: str) -> str:
    """POSIX single-quote VALUE for embedding in the stub shell script.

    Upstream interpolates the banner with Python ``!r``. That is wrong here:
    the colorized banner this repo actually produces contains ESC bytes, and
    ``repr`` renders those as the four characters ``\\x1b`` -- a stub built
    that way would emit a banner that no real pytest ever writes and the ANSI
    case would be untested. For the plain ASCII banners the two forms agree.
    """
    return "'" + value.replace("'", "'\\''") + "'"


def _junit_xml(tests: int) -> str:
    """A minimal JUnit document in the shape pytest writes it."""
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<testsuites>"
        f'<testsuite name="pytest" errors="0" failures="0" skipped="0" '
        f'tests="{tests}" time="1.234" timestamp="2026-09-04T10:00:00" '
        f'hostname="stub"></testsuite>'
        "</testsuites>\n"
    )


def _uv_stub_emitting(*, banner: str, junit_tests: int | None) -> str:
    """A fake `uv` that reproduces a REAL remote pytest invocation: it prints
    BANNER on stdout and, when asked for a JUnit report, writes one at exactly
    the path the wrapper handed it.

    The junit path is recovered from the stub's OWN argv rather than from an
    env var, so a wrapper that stops passing ``--junitxml`` cannot pass these
    tests by having the fixture write the file for it.
    """
    write_junit = ""
    if junit_tests is not None:
        write_junit = (
            'for a in "$@"; do\n'
            '  case "$a" in\n'
            "    --junitxml=*)\n"
            "      printf '%s' "
            f"{_sh_quote(_junit_xml(junit_tests))}"
            ' > "${a#--junitxml=}" ;;\n'
            "  esac\n"
            "done\n"
        )
    return (
        "#!/bin/sh\n"
        'if [ "$1" = "sync" ]; then exit 0; fi\n'
        'printf "%s\\n" "$*" > "$PYTEST_ARGV_WITNESS"\n'
        'if [ -d "$LOCK_PROBE" ]; then echo held > "$LOCK_WITNESS"; '
        'else echo free > "$LOCK_WITNESS"; fi\n'
        + write_junit
        + f'printf "%s\\n" {_sh_quote(banner)}\n'
        'exit "${FAKE_UV_EXIT:-0}"\n'
    )


def _marker_field(rundir: Path, field: str) -> str:
    for line in (rundir / "MARKER").read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{field}="):
            return line.split("=", 1)[1]
    raise AssertionError(
        f"MARKER carries no {field}=: {(rundir / 'MARKER').read_text()}"
    )


def _run_wrapper_with_stub(
    env_info: dict[str, Path], *, banner: str, junit_tests: int | None
) -> subprocess.CompletedProcess[str]:
    env_info["uv"].write_text(_uv_stub_emitting(banner=banner, junit_tests=junit_tests))
    env_info["uv"].chmod(0o755)
    return _run_wrapper(
        env_info,
        extra_env={"PYTEST_ARGV_WITNESS": str(env_info["rundir"] / "pytest_argv.txt")},
    )


def test_the_wrapper_asks_pytest_for_a_machine_readable_report(
    remote_run_env: dict[str, Path],
) -> None:
    """The count must not be scraped out of a human-readable banner whose shape
    is decided by whichever plugins happen to be loaded and whether color is
    on. `--junitxml` is policy-independent: serial, `-n4 --dist=loadgroup`, and
    `--color=yes` all produce the same document."""
    result = _run_wrapper_with_stub(
        remote_run_env, banner="4 workers [11 items]", junit_tests=11
    )
    assert result.returncode == 0, result.stderr
    argv = (remote_run_env["rundir"] / "pytest_argv.txt").read_text()
    assert "--junitxml=" in argv, (
        "the wrapper does not ask pytest for a machine-readable report: " + argv
    )
    assert str(remote_run_env["rundir"]) in argv, (
        "the JUnit report must land inside the run dir, where the marker and "
        "suite.log already live and prepush_remote_gc already sweeps: " + argv
    )


def test_the_collected_count_comes_from_the_report_not_the_banner(
    remote_run_env: dict[str, Path],
) -> None:
    """Deliberate mismatch: the JUnit report says 7, the banner says 3. The
    marker must carry 7. If it carries 3 the count is still banner-derived and
    still hostage to the execution policy."""
    result = _run_wrapper_with_stub(
        remote_run_env, banner="4 workers [3 items]", junit_tests=7
    )
    assert result.returncode == 0, result.stderr
    assert _marker_field(remote_run_env["rundir"], "collected") == "7", (
        "the count is not read from the JUnit report"
    )


def test_the_collected_count_is_non_zero_under_the_real_parallel_policy(
    remote_run_env: dict[str, Path],
) -> None:
    """THE REGRESSION PIN for cause (1). No JUnit report at all, and only the
    banner `pytest-xdist` actually prints -- the exact bytes measured in h105's
    ``<repo>-d839c27cb88a-83571/suite.log`` line 13 on 2026-09-04. The shipped
    ``^collected N items`` sed cannot match this, so before the fix the marker
    read ``collected=0`` for a run of 44,683 passing tests."""
    result = _run_wrapper_with_stub(
        remote_run_env, banner="4 workers [44741 items]", junit_tests=None
    )
    assert result.returncode == 0, result.stderr
    assert _marker_field(remote_run_env["rundir"], "collected") == "44741", (
        "a real xdist run still reports a zero collected count"
    )


def test_the_colorized_serial_banner_this_repo_actually_emits_is_understood(
    remote_run_env: dict[str, Path],
) -> None:
    """THE REGRESSION PIN for cause (2), which upstream does not have.

    These are the literal bytes of line 9 of h105's
    ``<repo>-378075e85050-2669/suite.log``, a 3h57m SERIAL run whose MARKER
    reads ``collected=0`` against 44,672 passing tests. ``tests/pytest.ini``
    addopts carries ``--color=yes`` and the remote leg's rootdir resolves into
    ``tests/``, so pytest prefixes the collector banner with the ``collecting
    ...`` status line and its SGR codes. The line therefore does not BEGIN with
    ``collected`` and the ``^`` anchor never matched -- which is why the count
    was zero here even on runs with no xdist involved at all.

    A verbatim copy of the upstream fallback chain passes every other test in
    this block and still fails this one.
    """
    result = _run_wrapper_with_stub(
        remote_run_env,
        banner="\x1b[1mcollecting ... \x1b[0mcollected 44730 items / 4 skipped",
        junit_tests=None,
    )
    assert result.returncode == 0, result.stderr
    assert _marker_field(remote_run_env["rundir"], "collected") == "44730", (
        "this repo's own colorized serial banner is still unreadable"
    )


def test_the_plain_serial_collector_banner_is_still_understood(
    remote_run_env: dict[str, Path],
) -> None:
    """The uncolored form, which is what a run with ``--color=no`` or a
    different rootdir produces. Reading the report must not cost the
    pre-existing form."""
    result = _run_wrapper_with_stub(
        remote_run_env, banner="collected 18095 items / 2 skipped", junit_tests=None
    )
    assert result.returncode == 0, result.stderr
    assert _marker_field(remote_run_env["rundir"], "collected") == "18095"


def test_a_report_saying_zero_tests_is_carried_through_as_zero(
    remote_run_env: dict[str, Path],
) -> None:
    """A remote leg that EXITS 0 and writes a real JUnit document whose
    ``<testsuite>`` says ``tests="0"`` -- a genuinely empty run, the case the
    parsing defect made indistinguishable from a full one.

    The wrapper must carry that ``0`` into the marker unchanged. Specifically
    it must NOT treat a report of zero as "no report" and fall through to a
    banner: the fallback chain is keyed on the count being UNREADABLE, not on
    it being small, and a chain that re-reads a zero off some other line could
    invent a number for a run that executed nothing. The acceptance branch
    then refuses that marker as NO EVIDENCE -- proven in
    ``test_a_green_remote_run_that_collected_nothing_is_no_evidence_not_a_pass``,
    which is the other half of this chain.
    """
    result = _run_wrapper_with_stub(
        remote_run_env, banner="4 workers [0 items]", junit_tests=0
    )
    assert result.returncode == 0, result.stderr
    assert _marker_field(remote_run_env["rundir"], "exit") == "0"
    assert _marker_field(remote_run_env["rundir"], "collected") == "0", (
        "a report of zero tests must reach the marker as zero, not be treated "
        "as a missing report and replaced from a banner"
    )


def test_a_banner_only_host_that_ran_nothing_still_reports_zero(
    remote_run_env: dict[str, Path],
) -> None:
    """The degraded path: no JUnit report at all (a host that could not write
    one), exit 0, and a banner that itself says zero items. The ordered banner
    fallbacks must land on ``0`` rather than on an empty string that the
    ``|| COLLECTED=0`` tail would coincidentally also render as ``0`` -- the
    two are the same number here, which is exactly why the case needs its own
    pin: it is the one input where a broken fallback chain and a working one
    agree, so it cannot be inferred from the non-zero tests."""
    result = _run_wrapper_with_stub(
        remote_run_env, banner="4 workers [0 items]", junit_tests=None
    )
    assert result.returncode == 0, result.stderr
    assert _marker_field(remote_run_env["rundir"], "collected") == "0"


# -----------------------------------------------------------------------------
# Acceptance must GATE on the count (OMN-17787 defect 2)
# -----------------------------------------------------------------------------
# `prepush_remote_run`'s acceptance was exit-code-only. `m_collected` was
# logged, written into the durable receipt, and never compared to anything, so
# a remote run that collected genuinely ZERO tests and exited 0 was accepted as
# a PASS and satisfied the escalation. These drive the SHIPPED function with a
# stubbed transport, so the assertions run the real acceptance branch.


def _remote_run_driver(
    repo: Path,
    tmp_path: Path,
    *,
    marker_exit: str,
    marker_collected: str,
) -> subprocess.CompletedProcess[str]:
    """Run the shipped `prepush_remote_run` against a stub host that returns a
    completion marker carrying MARKER_EXIT / MARKER_COLLECTED verbatim."""
    stub_bin = tmp_path / "stubbin"
    stub_bin.mkdir(exist_ok=True)
    (stub_bin / "ssh").write_text(
        "#!/bin/sh\n"
        # The readback is the only ssh whose command mentions WRAPPER_EXIT.
        # Every other leg (mkdir, exec, suite.log tail, gc) is a quiet success.
        'for a in "$@"; do\n'
        '  case "$a" in\n'
        "    *WRAPPER_EXIT*)\n"
        '      echo "wrapper_exit=0"\n'
        '      echo "head_sha=$STUB_HEAD_SHA"\n'
        '      echo "argv_sha=stubargvsha"\n'
        '      echo "exit=$STUB_EXIT"\n'
        '      echo "collected=$STUB_COLLECTED"\n'
        '      echo "log_sha256=stublogsha"\n'
        '      echo "host=stubhost"\n'
        "      exit 0 ;;\n"
        "  esac\n"
        "done\n"
        "exit 0\n"
    )
    (stub_bin / "ssh").chmod(0o755)
    (stub_bin / "scp").write_text("#!/bin/sh\nexit 0\n")
    (stub_bin / "scp").chmod(0o755)

    body = (
        f'export PATH="{stub_bin}:$PATH"\n'
        f'export STUB_EXIT="{marker_exit}"\n'
        f'export STUB_COLLECTED="{marker_collected}"\n'
        'export STUB_HEAD_SHA="$(git -C "$REPO_ROOT" rev-parse HEAD)"\n'
        "PATHS=(tests)\n"
        "PREPUSH_PICK_LABEL=hb\n"
        "PREPUSH_PICK_SSH=jonah@hostb\n"
        "PREPUSH_PICK_UV=/bin/uv\n"
        f'PREPUSH_PICK_WORKROOT="{tmp_path}/wb"\n'
        "PREPUSH_PICK_SLOT=1\n"
        "PREPUSH_PICK_HOSTNAME=hostb\n"
        "PREPUSH_PICK_MODE=authorizing\n"  # pragma: allowlist secret
        "PREPUSH_PICK_RATIO=0.10\n"
        "PREPUSH_PICK_CORES=24\n"
        "PREPUSH_PROBE_LOG=stub\n"
        # Not under test here: the argv digest and the reclaim ssh. Pinning the
        # digest lets the stub host answer with a marker that BINDS, which is
        # the precondition for reaching the acceptance branch at all.
        "prepush_sha256_file() { printf 'stubargvsha'; }\n"
        "prepush_remote_gc() { :; }\n"
        "rc=0\n"
        'prepush_remote_run "heavy thing" || rc=$?\n'
        'echo "RC=$rc"\n'
    )
    return _run_driver(repo, body)


def _receipt_lines(repo: Path) -> list[str]:
    path = repo / ".onex_state" / "prepush_distribution" / "receipts.jsonl"
    if not path.exists():
        return []
    return [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def test_a_green_remote_run_that_collected_nothing_is_no_evidence_not_a_pass(
    tmp_path: Path,
) -> None:
    """THE FAIL-CLOSED PIN. exit=0 with collected=0 is indistinguishable from a
    run that executed nothing, so it cannot authorize a push. rc 1 is NO
    EVIDENCE: `dispatch_to_lab_host` walks to the next fit host, and if none
    answers it falls through to the local/grant/refusal ladder. It is
    deliberately NOT rc 3 -- an empty selection says nothing about the tree, so
    it must not hard-refuse the push either."""
    repo = _repo_with_table(tmp_path, _SYNTHETIC_TABLE)
    out = _remote_run_driver(repo, tmp_path, marker_exit="0", marker_collected="0")
    combined = out.stdout + out.stderr
    assert "RC=1" in combined, combined
    assert "PASS accepted" not in combined, (
        "a zero-collection remote run was accepted as a PASS: " + combined
    )
    assert "NO EVIDENCE" in combined, combined


def test_a_green_remote_run_that_collected_tests_is_still_accepted(
    tmp_path: Path,
) -> None:
    """NON-VACUITY. The gate must not have been bought by refusing everything:
    the same driver with the count h105 actually ran on 2026-09-04
    (``<repo>-d839c27cb88a-83571``, suite.log last line "44683 passed, 59
    skipped, 3 xpassed, 151 warnings in 5698.79s") is still a PASS, and the
    receipt now carries the real number instead of 0."""
    repo = _repo_with_table(tmp_path, _SYNTHETIC_TABLE)
    out = _remote_run_driver(repo, tmp_path, marker_exit="0", marker_collected="44683")
    combined = out.stdout + out.stderr
    assert "RC=0" in combined, combined
    assert "PASS accepted" in combined, combined
    assert "ran 44683 tests green" in combined, combined
    receipts = _receipt_lines(repo)
    assert receipts, "no durable receipt was written"
    assert '"collected":44683' in receipts[-1], receipts[-1]


def test_pytest_reporting_no_tests_collected_is_no_evidence_not_a_red(
    tmp_path: Path,
) -> None:
    """pytest exit 5 is EXIT_NOTESTSCOLLECTED -- nothing to run. That is the
    same statement about the tree as a missing marker (none), so it is a
    placement miss, not a failing gate. Before this it returned 3 and `die()`d
    the push on a selection that simply resolved to nothing on the target."""
    repo = _repo_with_table(tmp_path, _SYNTHETIC_TABLE)
    out = _remote_run_driver(repo, tmp_path, marker_exit="5", marker_collected="0")
    combined = out.stdout + out.stderr
    assert "RC=1" in combined, combined
    assert "NO EVIDENCE" in combined, combined
    assert "RC=3" not in combined


def test_a_non_numeric_collected_field_cannot_fall_through_to_a_pass(
    tmp_path: Path,
) -> None:
    """A marker is remote input. `[ "$m_collected" -eq 0 ]` on a non-numeric
    value is a bash ERROR whose status is 2 -- which reads as "not zero" and
    would sail straight into the PASS branch. The field is normalized before it
    is compared, so garbage is 0 and 0 is NO EVIDENCE."""
    repo = _repo_with_table(tmp_path, _SYNTHETIC_TABLE)
    out = _remote_run_driver(repo, tmp_path, marker_exit="0", marker_collected="lots")
    combined = out.stdout + out.stderr
    assert "RC=1" in combined, combined
    assert "PASS accepted" not in combined, combined
    receipts = _receipt_lines(repo)
    assert receipts, "no durable receipt was written"
    assert '"collected":0' in receipts[-1], (
        "a non-numeric count must be normalized before it reaches the receipt, "
        "or the receipt is not valid JSON: " + receipts[-1]
    )


def test_the_acceptance_branch_names_the_count_it_gates_on() -> None:
    """A later edit that reverts the comparison must not be able to leave the
    PASS log sentence intact and silently stop gating.

    THE ASSERTION IS MADE AGAINST COMMENT-STRIPPED SOURCE, and that is the
    whole point of it. Measured upstream on 2026-09-04: deleting the entire
    acceptance gate left the first draft of this test PASSING, because the
    normalization block immediately above it carries a COMMENT that quotes the
    very string being searched for (``[ "$m_collected" -eq 0 ]`` -- explaining
    why the value is normalized before it is compared). A guard that a comment
    can satisfy is the same defect class as the gate this ticket closes: it
    cannot tell the artifact from a description of the artifact. Executable
    lines only.
    """
    lib = LIB.read_text(encoding="utf-8")
    run = lib[lib.index("prepush_remote_run() {") :]
    code = "\n".join(
        line for line in run.splitlines() if not line.lstrip().startswith("#")
    )
    assert "OMN-17787" in run, "the acceptance branch carries no reference to the gate"
    assert "m_collected" in code
    assert '[ "$m_collected" -eq 0 ]' in code, (
        "acceptance no longer compares the collected count to zero on any "
        "EXECUTABLE line (a comment mentioning the comparison does not count)"
    )
