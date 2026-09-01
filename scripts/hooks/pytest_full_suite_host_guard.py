#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Direct-invocation .200-default host guard for pytest (OMN-15977 Hole 1).

The OMN-15059 guard (``scripts/hooks/prepush_smart_tests.sh``) refuses/redirects
the heavy full-suite path when it runs -- but ONLY when pytest is launched via
that hook, i.e. via ``git push``. It hooks the push path, not pytest itself.

Build agents routinely run the full suite DIRECTLY as a "prove nothing else
broke" verification step:

    uv run pytest tests/ -q > .gate_logs/full_suite3.log

No pre-push hook fires for that invocation, so the ``.200``-default host-check
is never consulted. Observed 3x in one lane (full_suite1/2/3) on 2026-08-12,
and confirmed as a live coverage hole in OMN-15977.

This module is the SAME host-identity check the bash hook performs
(``guard_full_suite_host`` in ``prepush_smart_tests.sh``), reimplemented so it
can also fire for a bare/direct ``pytest`` invocation via
``pytest_configure`` -- registered from the repo-root ``conftest.py`` so it
is loaded for every collection, regardless of which testpath is targeted.

Design mirrors the bash guard's documented posture exactly (see
``prepush_smart_tests.sh`` OMN-15059 section):

  * ROUTING OPTIMIZATION, NOT a security control. If host identity cannot be
    determined, FAIL OPEN -- proceed locally rather than lock a developer out
    of their own repo on an ambiguous read.
  * CI runners are never gated -- this guard exists to keep a contended local
    Mac from being driven to a load spike by a runaway full suite; a
    short-lived, isolated CI runner is not that failure mode.
  * The escape hatch is the same one the bash hook uses -- one mechanism for
    both entry points, not two. As of OMN-16480 that mechanism is a single-use,
    repo+HEAD-scoped, TTL-bounded, receipted grant token
    (``scripts/hooks/prepush_override_grant.py``), NOT an environment variable.
    Any ``PREPUSH_ALLOW_*`` variable present in the environment is now a HARD
    REFUSAL here, exactly as it is in the bash hook: an env var is inherited by
    every descendant process, so honoring one let a single leak disarm the gate
    for a whole process tree and recursively spawn a second 44,064-test suite
    (~9h03m lost, friction report F-01/F-04). See that module's docstring.
  * Only fires on an UNNARROWED collection targeting the full-suite root (or
    an ancestor of it) -- a targeted/narrow run (a single test file, a
    ``-k``/``-m`` filter) always stays runnable locally. Gating every
    invocation would get this guard disabled within a week, which is worse
    than no guard (verbatim rationale carried over from the bash hook).

Kept import-light and dependency-free (only ``os``/``socket``/``pytest``) so it
is trivial to unit test the pure decision function directly, and so the guard
itself can never be the thing that breaks pytest startup.
"""

from __future__ import annotations

import os
import socket
import subprocess

from scripts.hooks.prepush_override_grant import (
    consume,
    env_rejection_message,
    has_active_override,
    inherited_override_env_vars,
    resolve_head_sha,
    resolve_repo_root,
)

DEFAULT_PREPUSH_200_HOSTNAME = "stickybeatz-studio"
DEFAULT_PREPUSH_201_GATE_RUNNER_HOSTNAME = "gate-runner-201"

HOST_TABLE_REL = "scripts/hooks/prepush_hosts.tsv"

# Legacy env override -> host-table row label. An override REPLACES the row it
# names; it never ADDS a hostname to the designated set. That distinction is
# load-bearing: under a table listing several hosts, an override that merely
# appended a name could no longer DE-designate the local machine, silently
# inverting the OMN-15059 guard that
# `test_guard_refuses_full_suite_escalation_on_non_200_host` proves by forcing
# a nonsense hostname.
_LEGACY_OVERRIDE_BY_LABEL = {
    "h200": "PREPUSH_200_HOSTNAME",
    "h201c": "PREPUSH_201_GATE_RUNNER_HOSTNAME",
}


def _override_var(label: str) -> str:
    """Per-row override env var name, matching prepush_dispatch.sh."""
    sanitized = "".join(c if c.isalnum() else "_" for c in label.upper())
    return f"PREPUSH_HOST_OVERRIDE_{sanitized}"


def designated_hostnames(
    env: dict[str, str] | None = None,
) -> tuple[str, ...]:
    """Every hostname that may run a full suite, from the COMMITTED host table.

    OMN-16991. This guard used to read `.201`'s identity straight off
    ``PREPUSH_201_GATE_RUNNER_HOSTNAME`` -- and the bash hook's
    ``scrub_prepush_override_env`` deliberately unsets every ``PREPUSH_*`` name
    before ``exec uv run pytest``, so on the `.201` host (whose real
    ``hostname -s`` is ``omninode-pc``, not the container's
    ``gate-runner-201``) the sanctioned override never reached THIS guard. The
    push passed the bash guard and was then refused by its own pytest child.
    That is why full-suite escalations could not run on `.201` at all. In THIS
    repo (OMN-17159) the gap was wider still: there was no host table to read,
    so the guard recognized exactly one name -- `.200` -- and refused a
    transplanted suite on every other lab host by construction.

    The scrub is NOT the bug and is not weakened here -- an inheritable
    ``PREPUSH_*`` override crossing into the pytest tree is exactly what turned
    one sanctioned grant into a recursive 44,064-test launcher (OMN-16425 F-01,
    ~9h03m). The bug was sourcing host IDENTITY from an environment variable
    that must not cross a process boundary. Identity now comes from a committed
    file that needs no inheritance at all.

    Read from ``git show HEAD:`` rather than the working tree, and ignored
    outright if the working copy diverges, so an uncommitted row cannot
    self-designate this machine. An unreadable table falls back to the two
    code-embedded defaults -- the pre-OMN-16991 behavior exactly, so a checkout
    without the table is neither more nor less permissive than before.
    """
    active_env: dict[str, str] | os._Environ[str] = os.environ if env is None else env
    fallback = (
        active_env.get("PREPUSH_200_HOSTNAME", DEFAULT_PREPUSH_200_HOSTNAME),
        active_env.get(
            "PREPUSH_201_GATE_RUNNER_HOSTNAME",
            DEFAULT_PREPUSH_201_GATE_RUNNER_HOSTNAME,
        ),
    )
    try:
        repo_root = resolve_repo_root()
        committed = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"HEAD:{HOST_TABLE_REL}"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if committed.returncode != 0 or not committed.stdout.strip():
            return fallback
        working = repo_root / HOST_TABLE_REL
        if working.is_file() and working.read_text() != committed.stdout:
            return fallback
        names: list[str] = []
        for line in committed.stdout.splitlines():
            line = line.split("#", 1)[0]
            if not line.strip():
                continue
            fields = line.split("\t")
            if len(fields) < 12 or fields[11] != "authorizing":
                continue
            label, hostname = fields[0], fields[2]
            legacy = _LEGACY_OVERRIDE_BY_LABEL.get(label)
            if legacy and active_env.get(legacy):
                hostname = active_env[legacy]
            override = active_env.get(_override_var(label))
            if override:
                hostname = override
            names.append(hostname)
        return tuple(names) if names else fallback
    except Exception:  # noqa: BLE001 - deliberately total; see below
        # Deliberately broad. This runs in `pytest_configure`, where ANY escaping
        # exception becomes an INTERNALERROR that kills the whole session before a
        # single test is collected -- a far worse failure than falling back. The
        # fallback is the exact pre-OMN-16991 behavior (the two code-embedded
        # defaults), so degrading here is neither more nor less permissive than
        # before. `resolve_repo_root()` raising outside a git checkout is the
        # concrete case: it raises GrantError, not OSError.
        return fallback


def is_ci_environment(env: dict[str, str] | None = None) -> bool:
    """True when running under a CI runner -- this guard never gates CI."""
    active_env: dict[str, str] | os._Environ[str] = os.environ if env is None else env
    return bool(active_env.get("CI") or active_env.get("GITHUB_ACTIONS"))


def resolve_local_hostname() -> str:
    """Short hostname of the current machine, or "" if undetermined.

    Mirrors the bash guard's ``hostname -s`` call and its fail-open posture:
    an exception or empty result here is NOT distinguished from a legitimate
    "could not verify" read by any caller of this function.
    """
    try:
        return socket.gethostname().split(".", 1)[0]
    except OSError:
        return ""


def is_full_suite_target(
    *,
    args: list[str],
    testpaths: list[str],
    keyword: str,
    markexpr: str,
    full_suite_target: str,
) -> bool:
    """Whether this invocation is an unnarrowed collection of the full suite.

    Mirrors ``selection_is_whole_suite`` in ``prepush_smart_tests.sh``: true
    when some target path IS the full-suite root or a directory ANCESTOR of
    it (so a bare ``pytest`` with no args, which falls back to ``testpaths``,
    is caught too), AND neither ``-k`` nor ``-m`` narrowed the run.

    A genuinely narrow target (a single test file, ``tests/scripts/``)
    is strictly BELOW the full-suite root and never trips this -- only a
    target that covers the whole thing does.
    """
    if keyword or markexpr:
        return False
    targets = list(args) if args else list(testpaths)
    if not targets:
        return False
    normalized_full = full_suite_target.rstrip("/") + "/"
    for raw in targets:
        normalized = str(raw).rstrip("/") + "/"
        if normalized_full.startswith(normalized):
            return True
    return False


def full_suite_host_violation_message(
    *,
    host: str,
    target_hostname: str,
    additional_target_hostnames: tuple[str, ...] = (),
    override_authorized: bool,
) -> str | None:
    """Return a refusal message, or None if this run may proceed.

    Pure decision function -- no I/O, no env reads -- so it is directly unit
    testable without subprocess/monkeypatch machinery. ``host`` "" means
    "could not be determined" and fails OPEN (returns None), matching the
    bash guard's documented routing-optimization posture verbatim.

    ``override_authorized`` is resolved by the caller from a consumed grant
    token, never from the environment (OMN-16480). It used to be
    ``allow_override``, read straight off ``PREPUSH_ALLOW_LOCAL_FULL_SUITE``;
    the rename is the point, not cosmetic -- the input is now a spent,
    scope-checked authorization rather than an ambient, inheritable flag.
    """
    if not host:
        return None
    allowed_hostnames = (target_hostname, *additional_target_hostnames)
    if any(host.lower() == allowed.lower() for allowed in allowed_hostnames):
        return None
    if override_authorized:
        return None
    return (
        f"direct full-suite pytest invocation refused on host '{host}', not the "
        f"designated .200 build host ('{target_hostname}') nor any other host "
        f"carrying mode=authorizing in {HOST_TABLE_REL} "
        f"({', '.join(repr(allowed) for allowed in additional_target_hostnames)}). "
        "This closes OMN-15977 "
        "Hole 1: agent-launched direct `pytest tests/` runs bypass the git-push "
        "guard (scripts/hooks/prepush_smart_tests.sh) entirely, so the .200-default "
        "host-check was never consulted. Run from .200 instead "
        "(ssh jonah@stickybeatz-studio.tail75df5e.ts.net; see "
        f"{HOST_TABLE_REL}, whose header documents how to add one), OR mint "
        "a single-use "
        "override grant to run the full suite on this host anyway (visible, "
        "receipted, degraded-evidence -- do not use as a routine bypass): "
        "`uv run python scripts/hooks/prepush_override_grant.py mint "
        "--reason '<why>'`."
    )


def override_authorization(*, context: str) -> bool:
    """Whether a scoped override authorizes THIS full-suite run.

    Two ways in, in priority order:

    1. An **activation record** already covering this process -- the bash hook
       consumed a grant and then spawned this pytest as its child. Without this
       leg the hook would consume the one grant for itself and its own child
       pytest would then refuse, so the authorized run could never actually
       execute. It is checked first precisely so the hand-off does not burn a
       second grant.
    2. A **grant** minted for this repo and this HEAD, claimed here and spent.
       That is the direct-``pytest``-invocation path, where no hook ran at all.

    Fails CLOSED on anything indeterminate (not a git worktree, git
    unavailable, unreadable state): a guard that cannot prove authorization
    must behave exactly like one that was denied it.
    """
    try:
        repo_root = resolve_repo_root()
        head_sha = resolve_head_sha(repo_root)
    except Exception:  # noqa: BLE001 -- see fail-closed note below
        # Blanket by design, both here and below. This runs inside
        # pytest_configure on EVERY invocation: an unexpected exception must
        # become "not authorized", never a traceback that breaks collection for
        # everyone. Narrowing the clause would trade a fail-closed refusal for a
        # crash in the one path that must not crash.
        return False
    try:
        if has_active_override(repo_root=repo_root, head_sha=head_sha):
            return True
        return consume(repo_root=repo_root, head_sha=head_sha, context=context).accepted
    except Exception:  # noqa: BLE001 -- fail closed, never crash collection
        return False


def enforce(config: object, full_suite_target: str) -> None:
    """pytest_configure entry point -- call from conftest.py.

    Deliberately hooked at ``pytest_configure`` (before collection starts),
    not ``pytest_collection_modifyitems`` (after collection completes): the
    whole point is to refuse BEFORE paying collection cost on a full-suite
    target, which for a several-thousand-test tree is itself non-trivial
    wall-clock, not just before the CPU-bound test *execution* that follows.

    ``config`` is a ``pytest.Config``; typed as ``object`` here to keep this
    module importable (and unit-testable) without a hard ``pytest`` import
    dependency at module load time.
    """
    if is_ci_environment():
        return
    option = config.option  # type: ignore[attr-defined]
    if not is_full_suite_target(
        args=list(config.args),  # type: ignore[attr-defined]
        testpaths=list(config.getini("testpaths") or []),  # type: ignore[attr-defined]
        keyword=option.keyword or "",
        markexpr=option.markexpr or "",
        full_suite_target=full_suite_target,
    ):
        return

    import pytest

    # OMN-16480: a leaked PREPUSH_ALLOW_* variable is a REFUSAL, not a bypass.
    # Checked after the narrowing test (a targeted run is never gated) but
    # before the host check, so the leak is reported on the host where it
    # actually causes damage -- and so the OMN-16425 recursion terminates here
    # instead of spawning another full suite.
    leaked = inherited_override_env_vars(os.environ)
    if leaked:
        pytest.exit(env_rejection_message(leaked), returncode=1)

    host = resolve_local_hostname()
    # OMN-16991: identity comes from the committed host table, not from
    # PREPUSH_* env vars the bash hook's scrub deliberately strips before it
    # spawns this pytest. See designated_hostnames().
    all_designated = designated_hostnames()
    target_hostname = all_designated[0]
    additional_hostnames = tuple(all_designated[1:])
    if (
        full_suite_host_violation_message(
            host=host,
            target_hostname=target_hostname,
            additional_target_hostnames=additional_hostnames,
            override_authorized=False,
        )
        is None
    ):
        return
    # Host mismatch. Only NOW look for an override -- resolving one has side
    # effects (it spends a grant and writes a receipt), so it must never run on
    # a path that was going to be allowed anyway.
    if override_authorization(
        context=f"direct full-suite pytest invocation on host '{host}'"
    ):
        return
    message = full_suite_host_violation_message(
        host=host,
        target_hostname=target_hostname,
        additional_target_hostnames=additional_hostnames,
        override_authorized=False,
    )
    assert message is not None

    pytest.exit(message, returncode=1)
