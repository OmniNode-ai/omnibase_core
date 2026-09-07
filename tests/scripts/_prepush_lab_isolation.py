# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Keep hook-subprocess tests from spending a real lab host's cores (OMN-16991).

Several tests in this directory run the REAL pre-push hook with the heavy
escalation forced (``PREPUSH_FULL_SUITE=1``) and every designated host
de-designated, to prove the refusal. Until OMN-16991 that was harmless: the
hook's host scan was truncated after its first ssh probe, so the picker only
ever saw ``h200`` and never had a remote host to dispatch to.

Fixing the scan removed that accidental containment. Observed live on
2026-08-30, minutes after the fix: `pytest tests/scripts/` shipped a real git bundle
to ``omnibook``, took that host's exclusive slot, and started the full
``tests/unit/`` suite there -- ORIGIN on the remote wrapper named this very test
process. That is the OMN-16425/OMN-16489 F-01 recursion in its distributed form,
reached from a unit test instead of a push, and it burns a lab host for an hour
per test run.

The isolation below uses the picker's OWN deterministic override surface rather
than a new knob. ``PREPUSH_SLOT_OVERRIDE_MAP`` is consulted before any network
call, and a label absent from the map resolves to "slot unknown", which the
picker treats as unfit and skips -- the same fail-closed posture it applies to
an unreachable host. A map naming no real label therefore makes EVERY row unfit
with zero ssh, and stays correct when a row is added.

It can only make the gate stricter. With no host placeable the lab leg produces
no evidence and the hook falls through to its pre-existing precedence
(GitHub-hosted verify -> grant -> die), which is exactly what these tests assert.
"""

from __future__ import annotations

import functools
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOST_TABLE = _REPO_ROOT / "scripts" / "hooks" / "prepush_hosts.tsv"
_OVERLAY_DIRECTIVE = "#!placement-overlay"

#: OMN-18025. The placement columns live in a PRIVATE overlay outside this repo,
#: so whether a given machine can resolve them is a property of the machine, not
#: of the change under test. Unresolved, every capacity row loses its transport
#: and the picker classifies the whole table as unreachable-for-this-account --
#: a different branch of the hook from the one these tests assert. Measured
#: 2026-09-07 on the lab host omnibook, where the remote leg runs inside a
#: synthetic registry root that has no overlay: two refusal tests returned 0
#: instead of refusing, while the same tests passed on a workstation that has
#: the overlay. So the isolation pins its own SYNTHETIC overlay and the tests
#: read the same complete table everywhere.
#:
#: Reserved-for-documentation values only (RFC 6761 `.example`, a /tmp-shaped
#: workroot). Nothing here is dialled: PREPUSH_SLOT_OVERRIDE_MAP below already
#: makes every row unfit before any network call.
_SYNTHETIC_UV_ABS_PATH = "/opt/synthetic/bin/uv"
_SYNTHETIC_WORKROOT = "/tmp/onex-prepush-synthetic"

#: Deliberately names no real row label. See the module docstring.
#:
#: ``PREPUSH_REACH_OVERRIDE_MAP`` (OMN-17280) closes the second network surface
#: this module exists to close. The same-host route probes lab reachability
#: with a real ``ssh ... true`` before it may fire, and a hook-subprocess test
#: that reached a designated row would otherwise open real connections from
#: pytest. ``default=up`` reports EVERY row -- including rows added later --
#: as reachable, which makes the same-host route DECLINE. That is the strict
#: direction: the leg produces no evidence and the hook falls through to its
#: pre-existing precedence, which is exactly what these tests assert.
LAB_ISOLATION_ENV = {
    "PREPUSH_SLOT_OVERRIDE_MAP": "no-such-host=unknown",
    "PREPUSH_REACH_OVERRIDE_MAP": "default=up",
}


def _table_lines() -> list[str]:
    return _HOST_TABLE.read_text(encoding="utf-8").splitlines()


def _overlay_rel() -> str:
    """The overlay path the SHIPPED table declares, never a copy of it.

    Reading the directive rather than restating the filename is what keeps this
    fixture from silently drifting: if the overlay moves and this module still
    wrote the old path, the synthetic overlay would be absent again and the
    tests would go back to depending on the machine.
    """
    for line in _table_lines():
        if line.startswith(_OVERLAY_DIRECTIVE):
            rel = line[len(_OVERLAY_DIRECTIVE) :].strip()
            if rel:
                return rel
    raise AssertionError(
        f"{_HOST_TABLE} declares no {_OVERLAY_DIRECTIVE} directive; the hook "
        "resolves the private placement overlay from it, so a fixture that "
        "guessed the path would prove nothing"
    )


def _synthetic_overlay_text() -> str:
    """One overlay row per row of the shipped table, keyed on its own labels.

    Derived from the table so a newly added row is covered without editing this
    file. A row whose committed ssh_target is `-` is an identity-only row and
    stays `-`: the overlay may fill placement in, never invent a transport.
    """
    rows = ["#label\tssh_target\tuv_abs_path\tworkroot"]
    for line in _table_lines():
        if not line.strip() or line.startswith("#"):
            continue
        cols = line.split("\t")
        label, ssh_target = cols[0], cols[3]
        if ssh_target == "-":
            rows.append(f"{label}\t-\t-\t-")
            continue
        rows.append(
            f"{label}\thost-{label}.example"
            f"\t{_SYNTHETIC_UV_ABS_PATH}\t{_SYNTHETIC_WORKROOT}"
        )
    return "\n".join(rows) + "\n"


@functools.lru_cache(maxsize=1)
def _synthetic_overlay_home() -> Path:
    """A throwaway $OMNI_HOME carrying the synthetic placement overlay."""
    home = Path(tempfile.mkdtemp(prefix="prepush-lab-isolation-"))
    overlay = home / _overlay_rel()
    overlay.parent.mkdir(parents=True, exist_ok=True)
    overlay.write_text(_synthetic_overlay_text(), encoding="utf-8")
    return home


def network_free_lab_env() -> dict[str, str]:
    """Env fragment that makes the lab-dispatch leg network-free.

    Also pins ``OMNI_HOME`` to the synthetic overlay above, so placement
    resolves identically on a workstation that has the private overlay and on a
    lab host that does not.
    """
    return {**LAB_ISOLATION_ENV, "OMNI_HOME": str(_synthetic_overlay_home())}
