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
``pytest_collection_modifyitems`` -- registered from the repo-root
``conftest.py`` so it is loaded for every collection, regardless of which
testpath is targeted.

Design mirrors the bash guard's documented posture exactly (see
``prepush_smart_tests.sh`` OMN-15059 section):

  * ROUTING OPTIMIZATION, NOT a security control. If host identity cannot be
    determined, FAIL OPEN -- proceed locally rather than lock a developer out
    of their own repo on an ambiguous read.
  * CI runners are never gated -- this guard exists to keep a contended local
    Mac from being driven to a load spike by a runaway full suite; a
    short-lived, isolated CI runner is not that failure mode.
  * ``PREPUSH_ALLOW_LOCAL_FULL_SUITE`` is the same escape hatch the bash hook
    honors -- a single override name for both entry points, not two.
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

DEFAULT_PREPUSH_200_HOSTNAME = "stickybeatz-studio"


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

    A genuinely narrow target (a single test file, ``tests/unit/scripts/``)
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
    allow_override: bool,
) -> str | None:
    """Return a refusal message, or None if this run may proceed.

    Pure decision function -- no I/O, no env reads -- so it is directly unit
    testable without subprocess/monkeypatch machinery. ``host`` "" means
    "could not be determined" and fails OPEN (returns None), matching the
    bash guard's documented routing-optimization posture verbatim.
    """
    if not host:
        return None
    if host.lower() == target_hostname.lower():
        return None
    if allow_override:
        return None
    return (
        f"direct full-suite pytest invocation refused on host '{host}', not the "
        f"designated .200 build host ('{target_hostname}'). This closes OMN-15977 "
        "Hole 1: agent-launched direct `pytest tests/` runs bypass the git-push "
        "guard (scripts/hooks/prepush_smart_tests.sh) entirely, so the .200-default "
        "host-check was never consulted. Run from .200 instead "
        "(ssh jonah@stickybeatz-studio.tail75df5e.ts.net; see "
        "docs/runbooks/200-build-lane-execution-pattern.md), OR set "
        "PREPUSH_ALLOW_LOCAL_FULL_SUITE=1 to run the full suite on this host anyway "
        "(visible, degraded-evidence override -- do not use as a routine bypass)."
    )


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
    allow_override = bool(os.environ.get("PREPUSH_ALLOW_LOCAL_FULL_SUITE"))
    option = config.option  # type: ignore[attr-defined]
    if not is_full_suite_target(
        args=list(config.args),  # type: ignore[attr-defined]
        testpaths=list(config.getini("testpaths") or []),  # type: ignore[attr-defined]
        keyword=option.keyword or "",
        markexpr=option.markexpr or "",
        full_suite_target=full_suite_target,
    ):
        return
    host = resolve_local_hostname()
    target_hostname = os.environ.get(
        "PREPUSH_200_HOSTNAME", DEFAULT_PREPUSH_200_HOSTNAME
    )
    message = full_suite_host_violation_message(
        host=host,
        target_hostname=target_hostname,
        allow_override=allow_override,
    )
    if message is None:
        return
    import pytest

    pytest.exit(message, returncode=1)
