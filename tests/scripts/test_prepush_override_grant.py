# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Unit proof for the single-use pre-push override grant (OMN-16480).

What is being pinned, and why it matters more than the usual "does the helper
work" question:

The gate this token guards had a *correct-usage* failure mode. In the
2026-08-23/24 window there were zero ``[skip-*`` tokens and zero
``--no-verify`` -- compliance was perfect -- and the sanctioned escape hatch
(``PREPUSH_ALLOW_LOCAL_FULL_SUITE=1``) still produced the worst outage of the
night: it leaked into a subprocess env copy, the hook took its override branch,
and a second full 44,064-test suite spawned recursively. ~9h03m, ~72% of all
serialized suite wall-clock in the window (friction report F-01/F-04).

So the properties under test are the ones an environment variable structurally
cannot have, and each one maps to a leg of that incident:

  * **single-use**   -- a spent grant cannot re-arm a nested invocation
                        (this is what makes the recursion terminate)
  * **repo-bound**   -- a grant does not authorize a different checkout
  * **commit-bound** -- an amend/rebase voids it
  * **TTL-bound**    -- it stops being permission after minutes
  * **rejecting**    -- the old env var is a REFUSAL, not a bypass
  * **receipted**    -- an override is never invisible
  * **pid-scoped**   -- the hook->child-pytest hand-off does not become an
                        ambient permission for unrelated processes
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from scripts.hooks import prepush_override_grant as grant_mod

pytestmark = pytest.mark.unit


_HEAD = "a" * 40
_OTHER_HEAD = "b" * 40


def _mint(
    repo_root: Path,
    *,
    head_sha: str = _HEAD,
    reason: str = "both venues saturated, gate evidence needed now",
    ttl_minutes: float = 10,
    now: float = 1000.0,
) -> dict[str, object]:
    grant = grant_mod.build_grant(
        repo_root=repo_root,
        head_sha=head_sha,
        reason=reason,
        ttl_minutes=ttl_minutes,
        now=now,
        pid=4242,
        host="test-host",
    )
    grant_mod.write_grant(repo_root, grant)
    return grant


def _receipts(repo_root: Path) -> list[dict[str, object]]:
    path = grant_mod.receipts_path(repo_root)
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


# =============================================================================
# Env-var rejection -- the defect itself
# =============================================================================


def test_inherited_override_env_vars_detects_the_whole_prefix_class() -> None:
    """Enforcement is by PREFIX, not by one blessed name.

    Pinning only ``PREPUSH_ALLOW_LOCAL_FULL_SUITE`` would leave the *class*
    open: the next inheritable override would just be spelled differently and
    reproduce the same incident.
    """
    env = {
        "PREPUSH_ALLOW_LOCAL_FULL_SUITE": "1",
        "PREPUSH_ALLOW_SOMETHING_NOT_YET_INVENTED": "yes",
        "PREPUSH_FULL_SUITE": "1",
        "PATH": "/usr/bin",
    }
    assert grant_mod.inherited_override_env_vars(env) == [
        "PREPUSH_ALLOW_LOCAL_FULL_SUITE",
        "PREPUSH_ALLOW_SOMETHING_NOT_YET_INVENTED",
    ]


def test_empty_valued_override_var_is_not_an_arming_signal() -> None:
    """Matches the shell's ``[ -n "$VAR" ]`` semantics the hook always used, so
    an exported-but-empty variable is neither armed nor a spurious refusal."""
    assert (
        grant_mod.inherited_override_env_vars(
            {"PREPUSH_ALLOW_LOCAL_FULL_SUITE": "", "PREPUSH_ALLOW_OTHER": "   "}
        )
        == []
    )


def test_env_rejection_message_names_the_variable_and_the_supported_path() -> None:
    message = grant_mod.env_rejection_message(["PREPUSH_ALLOW_LOCAL_FULL_SUITE"])
    assert "PREPUSH_ALLOW_LOCAL_FULL_SUITE" in message
    assert "unset PREPUSH_ALLOW_LOCAL_FULL_SUITE" in message
    assert "prepush_override_grant.py mint" in message


def test_consume_refuses_when_an_override_env_var_is_present(tmp_path: Path) -> None:
    """The exact OMN-16425 shape: a valid grant exists AND a leaked var is in
    the environment. The leak must lose -- otherwise the env var is still a
    live arming path and nothing has actually changed."""
    _mint(tmp_path)
    result = grant_mod.consume(
        repo_root=tmp_path,
        head_sha=_HEAD,
        context="test",
        now=1001.0,
        pid=1,
        host="h",
        env={"PREPUSH_ALLOW_LOCAL_FULL_SUITE": "1"},
    )
    assert not result.accepted
    assert result.code == "inheritable_env_override_present"
    assert grant_mod.grant_path(tmp_path).is_file(), (
        "a leaked env var must not consume the outstanding grant as a side "
        "effect -- the operator should be able to unset and retry"
    )


# =============================================================================
# Single-use -- the recursion breaker
# =============================================================================


def test_grant_is_consumed_exactly_once(tmp_path: Path) -> None:
    """This single property is what makes the OMN-16425 recursion structurally
    impossible rather than patched at one call site: the nested invocation
    finds no grant and refuses."""
    _mint(tmp_path)
    first = grant_mod.consume(
        repo_root=tmp_path,
        head_sha=_HEAD,
        context="outer",
        now=1001.0,
        pid=1,
        host="h",
        env={},
    )
    second = grant_mod.consume(
        repo_root=tmp_path,
        head_sha=_HEAD,
        context="nested",
        now=1002.0,
        pid=2,
        host="h",
        env={},
    )
    assert first.accepted
    assert not second.accepted
    assert second.code == "no_grant"
    assert not grant_mod.grant_path(tmp_path).is_file()


def test_consume_with_no_grant_reports_how_to_mint_one(tmp_path: Path) -> None:
    result = grant_mod.consume(
        repo_root=tmp_path,
        head_sha=_HEAD,
        context="c",
        now=1.0,
        pid=1,
        host="h",
        env={},
    )
    assert not result.accepted
    assert result.code == "no_grant"
    assert "mint" in result.detail


# =============================================================================
# Scope bindings
# =============================================================================


def test_grant_does_not_survive_a_head_change(tmp_path: Path) -> None:
    """An amend or rebase voids the grant. Authorization was for a specific
    tree, not for "whatever this branch happens to be later"."""
    _mint(tmp_path, head_sha=_HEAD)
    result = grant_mod.consume(
        repo_root=tmp_path,
        head_sha=_OTHER_HEAD,
        context="c",
        now=1001.0,
        pid=1,
        host="h",
        env={},
    )
    assert not result.accepted
    assert result.code == "head_sha_mismatch"


def test_grant_does_not_authorize_a_different_repo(tmp_path: Path) -> None:
    other_repo = tmp_path / "other"
    other_repo.mkdir()
    grant = grant_mod.build_grant(
        repo_root=other_repo,
        head_sha=_HEAD,
        reason="minted elsewhere",
        ttl_minutes=10,
        now=1000.0,
        pid=1,
        host="h",
    )
    # Physically place the foreign grant in THIS repo's state dir -- proving
    # the binding is validated, not merely implied by file location.
    grant_mod.write_grant(tmp_path, grant)
    result = grant_mod.consume(
        repo_root=tmp_path,
        head_sha=_HEAD,
        context="c",
        now=1001.0,
        pid=1,
        host="h",
        env={},
    )
    assert not result.accepted
    assert result.code == "repo_mismatch"


def test_grant_expires(tmp_path: Path) -> None:
    _mint(tmp_path, ttl_minutes=10, now=1000.0)
    result = grant_mod.consume(
        repo_root=tmp_path,
        head_sha=_HEAD,
        context="c",
        now=1000.0 + (10 * 60) + 1,
        pid=1,
        host="h",
        env={},
    )
    assert not result.accepted
    assert result.code == "expired"


def test_a_failed_presentation_still_spends_the_grant(tmp_path: Path) -> None:
    """Deliberate: claim-before-validate. A grant is one authorization for one
    run; presenting it against the wrong sha spends it rather than leaving it
    on disk to be retried until something lines up."""
    _mint(tmp_path, head_sha=_HEAD)
    grant_mod.consume(
        repo_root=tmp_path,
        head_sha=_OTHER_HEAD,
        context="c",
        now=1001.0,
        pid=1,
        host="h",
        env={},
    )
    assert not grant_mod.grant_path(tmp_path).is_file()


def test_malformed_grant_is_rejected_not_honored(tmp_path: Path) -> None:
    target = grant_mod.grant_path(tmp_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("not json at all", encoding="utf-8")
    result = grant_mod.consume(
        repo_root=tmp_path,
        head_sha=_HEAD,
        context="c",
        now=1.0,
        pid=1,
        host="h",
        env={},
    )
    assert not result.accepted
    assert result.code == "malformed_grant"


# =============================================================================
# Mint-time constraints
# =============================================================================


def test_mint_requires_a_reason(tmp_path: Path) -> None:
    with pytest.raises(grant_mod.GrantError):
        grant_mod.build_grant(
            repo_root=tmp_path,
            head_sha=_HEAD,
            reason="   ",
            ttl_minutes=10,
            now=0.0,
            pid=1,
            host="h",
        )


def test_ttl_is_hard_capped(tmp_path: Path) -> None:
    """A long-lived grant is an environment variable wearing a different file
    extension -- the cap is what keeps the token from decaying back into the
    thing it replaced."""
    with pytest.raises(grant_mod.GrantError):
        grant_mod.build_grant(
            repo_root=tmp_path,
            head_sha=_HEAD,
            reason="valid",
            ttl_minutes=grant_mod.MAX_TTL_MINUTES + 1,
            now=0.0,
            pid=1,
            host="h",
        )


@pytest.mark.parametrize("bad_ttl", [0, -5])
def test_ttl_must_be_positive(tmp_path: Path, bad_ttl: float) -> None:
    with pytest.raises(grant_mod.GrantError):
        grant_mod.build_grant(
            repo_root=tmp_path,
            head_sha=_HEAD,
            reason="valid",
            ttl_minutes=bad_ttl,
            now=0.0,
            pid=1,
            host="h",
        )


def test_reason_is_sanitized_and_capped() -> None:
    cleaned = grant_mod.sanitize_reason("a\nb\t\x00c" + ("x" * 500))
    assert "\n" not in cleaned and "\x00" not in cleaned
    assert len(cleaned) <= grant_mod.MAX_REASON_CHARS


# =============================================================================
# Receipts -- an override is never invisible
# =============================================================================


def test_accepted_consume_writes_a_receipt(tmp_path: Path) -> None:
    _mint(tmp_path, reason="both venues saturated")
    grant_mod.consume(
        repo_root=tmp_path,
        head_sha=_HEAD,
        context="degraded-host escalation",
        now=1001.0,
        pid=77,
        host="test-host",
        env={},
    )
    consumed = [
        r for r in _receipts(tmp_path) if r["event"] == "prepush_override_consumed"
    ]
    assert len(consumed) == 1
    record = consumed[0]
    assert record["reason"] == "both venues saturated"
    assert record["context"] == "degraded-host escalation"
    assert record["head_sha"] == _HEAD
    assert record["pid"] == 77


def test_rejected_consume_also_writes_a_receipt(tmp_path: Path) -> None:
    """Refusals are recorded too. A window full of rejected presentations is
    itself a signal -- it means the gate is being fought, which is exactly the
    thing F-04 could only reconstruct from ledger prose after the fact."""
    _mint(tmp_path, head_sha=_HEAD)
    grant_mod.consume(
        repo_root=tmp_path,
        head_sha=_OTHER_HEAD,
        context="c",
        now=1001.0,
        pid=1,
        host="h",
        env={},
    )
    rejected = [
        r for r in _receipts(tmp_path) if r["event"] == "prepush_override_rejected"
    ]
    assert len(rejected) == 1
    assert rejected[0]["code"] == "head_sha_mismatch"


# =============================================================================
# Activation record -- the hook -> child pytest hand-off
# =============================================================================


def test_activation_covers_the_consuming_process_and_its_children(
    tmp_path: Path,
) -> None:
    """The bash hook consumes the grant, then spawns pytest, which hits the same
    guard. Without this the authorized run could never execute -- but the
    coverage must stop at the process tree, or the record is just an ambient
    permission again."""
    _mint(tmp_path)
    assert grant_mod.consume(
        repo_root=tmp_path,
        head_sha=_HEAD,
        context="hook",
        now=1001.0,
        pid=100,
        host="h",
        env={},
    ).accepted

    tree = {200: 100, 300: 200}  # 200's parent is 100 (the hook); 300's is 200

    def resolver(pid: int) -> int | None:
        return tree.get(pid)

    for pid in (100, 200, 300):
        assert grant_mod.has_active_override(
            repo_root=tmp_path,
            head_sha=_HEAD,
            now=1002.0,
            pid=pid,
            ppid_resolver=resolver,
        ), f"pid {pid} is the consumer or its descendant and must be covered"


def test_activation_does_not_cover_an_unrelated_process(tmp_path: Path) -> None:
    _mint(tmp_path)
    grant_mod.consume(
        repo_root=tmp_path,
        head_sha=_HEAD,
        context="hook",
        now=1001.0,
        pid=100,
        host="h",
        env={},
    )
    assert not grant_mod.has_active_override(
        repo_root=tmp_path,
        head_sha=_HEAD,
        now=1002.0,
        pid=999,
        ppid_resolver=lambda pid: 1,
    ), (
        "a sibling process that merely runs during the TTL must NOT inherit the "
        "override -- that is the ambient-permission failure this replaces"
    )


def test_activation_expires_and_is_head_bound(tmp_path: Path) -> None:
    _mint(tmp_path, ttl_minutes=10, now=1000.0)
    grant_mod.consume(
        repo_root=tmp_path,
        head_sha=_HEAD,
        context="hook",
        now=1001.0,
        pid=100,
        host="h",
        env={},
    )
    assert not grant_mod.has_active_override(
        repo_root=tmp_path,
        head_sha=_HEAD,
        now=1000.0 + (10 * 60) + 1,
        pid=100,
        ppid_resolver=lambda pid: None,
    )
    assert not grant_mod.has_active_override(
        repo_root=tmp_path,
        head_sha=_OTHER_HEAD,
        now=1002.0,
        pid=100,
        ppid_resolver=lambda pid: None,
    )


def test_ancestor_walk_terminates_on_an_unresolvable_tree(tmp_path: Path) -> None:
    """Fail CLOSED, and never hang pytest startup: an unresolvable or cyclic
    process tree ends the walk rather than looping."""
    assert not grant_mod.is_self_or_ancestor(100, 200, lambda pid: None)
    assert not grant_mod.is_self_or_ancestor(100, 200, lambda pid: pid)
    assert not grant_mod.is_self_or_ancestor(999, 200, lambda pid: 200)


def test_default_ppid_resolver_finds_the_real_parent() -> None:
    """Anti-mock pin: the injected resolver above must correspond to something
    that actually works on this platform."""
    assert grant_mod.default_ppid_resolver(os.getpid()) == os.getppid()
