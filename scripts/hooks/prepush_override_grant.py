#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Single-use, scope-bound grant tokens for pre-push gate overrides (OMN-16480).

WHY THIS EXISTS
---------------
The ``.200``-default host/capacity guard (OMN-15059 / OMN-15408 / OMN-15977 /
OMN-16295) shipped its escape hatch as a plain environment variable,
``PREPUSH_ALLOW_LOCAL_FULL_SUITE``. An environment variable is:

  * **inherited** by every descendant process, forever,
  * **unscoped** -- not bound to a repo, a commit, or a run,
  * **unexpiring**, and
  * **unaudited** -- it leaves no record that an override was used.

So "permission to bypass the load gate once, for this push" was implemented as
"permission for every process this shell ever spawns to bypass this gate
silently". That is the same failure shape Rule 10 was hardened against for
``[skip-*`` tokens (OMN-9731 / OMN-13388), left open one layer down.

It is not hypothetical. In the 2026-08-23/24 window the variable leaked from an
operator shell into a guard test's ``env=dict(os.environ)`` subprocess copy; the
hook took its degraded-override branch and recursively launched another full
44,064-test suite, which reached the same test and recursed again. Measured cost
in `docs/tracking/2026-08-24-system-friction-report.md` (F-01/F-04): ~9h03m,
about 72% of all serialized suite wall-clock in that window. Crucially,
compliance was *perfect* -- zero ``[skip-*`` tokens, zero ``--no-verify``. The
damage came from the sanctioned escape path being correctly used. A design
defect, not a discipline defect.

THE REPLACEMENT
---------------
A grant is a file, not a variable:

  * **repo-bound** -- carries the absolute repo root it was minted in,
  * **commit-bound** -- carries the HEAD sha it was minted against, so an
    amend/rebase invalidates it,
  * **TTL-bound** -- minutes, not forever (default 10, hard cap 30),
  * **single-use** -- claimed by an atomic rename and deleted, so it is
    consumed exactly once even if two processes race for it,
  * **reasoned** -- a non-empty reason is mandatory at mint time,
  * **receipted** -- every consume, accepted OR rejected, appends a JSON line to
    ``.onex_state/prepush_override/receipts.jsonl``.

A child process cannot inherit a file that no longer exists. That is the whole
property the env var could not provide, and it is what makes the OMN-16425
recursion structurally impossible rather than merely patched at one call site:
the nested hook invocation looks for a grant, finds none, and refuses.

THE HAND-OFF (why an activation record exists)
----------------------------------------------
The bash hook consumes the grant, then runs ``uv run pytest tests/unit/`` -- and
that child pytest hits the SAME guard again via the repo-root ``conftest.py``
(OMN-15977 Hole 1). Passing authorization down through the environment would
reintroduce exactly the defect this module removes. Instead, a successful
consume writes a short-lived **activation record** naming the consuming
process's pid, and the pytest-side guard honors it only when that pid is the
current process or one of its live ANCESTORS. So the authorized run's own
children are covered; an unrelated sibling process that merely happens to run
during the TTL is not. This is the "bound to one pid" leg of the design.

Deliberately stdlib-only (no pydantic, no repo imports): this module is loaded
by the repo-root ``conftest.py`` on every single pytest invocation, so it must
never be the thing that breaks collection, and it must be trivially unit
testable as pure functions.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------
# Contract constants
# --------------------------------------------------------------------------

GRANT_SCHEMA_VERSION = 1

#: Any environment variable with this prefix is a REJECTED arming signal, never
#: an honored one. The prefix (not one exact name) is the unit of enforcement so
#: a future ``PREPUSH_ALLOW_SOMETHING_ELSE`` cannot quietly reopen the class.
OVERRIDE_ENV_PREFIX = "PREPUSH_ALLOW_"

DEFAULT_TTL_MINUTES = 10
MAX_TTL_MINUTES = 30

STATE_DIRNAME = ".onex_state"
OVERRIDE_SUBDIR = "prepush_override"
GRANT_FILENAME = "grant"
ACTIVATION_FILENAME = "active"
RECEIPTS_FILENAME = "receipts.jsonl"

MAX_REASON_CHARS = 200
_REASON_DISALLOWED_RE = re.compile(r"[^A-Za-z0-9 ._,:;/#()\[\]@+=-]")

#: Ancestor walks are bounded so a pid-cycle or a pathological process tree can
#: never hang a pytest startup.
ANCESTOR_WALK_MAX_DEPTH = 40


class GrantError(RuntimeError):
    """Raised for operator-facing misuse (bad TTL, empty reason, no repo)."""


# --------------------------------------------------------------------------
# Env-override rejection
# --------------------------------------------------------------------------


def inherited_override_env_vars(env: Mapping[str, str]) -> list[str]:
    """Names of set, non-empty ``PREPUSH_ALLOW_*`` variables in ``env``.

    Empty/whitespace values are not treated as set -- that matches the shell's
    ``[ -n "$VAR" ]`` semantics the hook has always used, so exporting an empty
    string is neither an arming signal nor a spurious refusal.
    """
    return sorted(
        name
        for name, value in env.items()
        if name.startswith(OVERRIDE_ENV_PREFIX) and str(value).strip()
    )


def env_rejection_message(names: list[str]) -> str:
    """Refusal text naming the leaked variables and the supported path."""
    joined = ", ".join(names)
    return (
        f"inheritable gate-override environment variable(s) present: {joined}. "
        "These are REJECTED, never honored (OMN-16480): an environment variable "
        "is inherited by every descendant process, has no expiry, is bound to no "
        "repo or commit, and leaves no receipt -- one leak into a subprocess "
        "recursively spawned a second full suite and burned ~9h03m on 2026-08-23 "
        "(friction report F-01/F-04). Unset it "
        f"(`unset {names[0]}`), then mint a scoped single-use grant instead: "
        "`uv run python scripts/hooks/prepush_override_grant.py mint "
        "--reason '<why this run must go ahead here>'`. The grant is bound to "
        "this repo and this HEAD sha, expires in minutes, is consumed on first "
        "read, and is recorded in .onex_state/prepush_override/receipts.jsonl."
    )


# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------


def override_dir(repo_root: Path) -> Path:
    return Path(repo_root) / STATE_DIRNAME / OVERRIDE_SUBDIR


def grant_path(repo_root: Path) -> Path:
    return override_dir(repo_root) / GRANT_FILENAME


def activation_path(repo_root: Path) -> Path:
    return override_dir(repo_root) / ACTIVATION_FILENAME


def receipts_path(repo_root: Path) -> Path:
    return override_dir(repo_root) / RECEIPTS_FILENAME


# --------------------------------------------------------------------------
# Repo / process facts
# --------------------------------------------------------------------------


def _git_output(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise GrantError(
            f"`git {' '.join(args)}` failed ({result.returncode}): "
            f"{result.stderr.strip() or 'no stderr'}"
        )
    return result.stdout.strip()


def resolve_repo_root(start: Path | None = None) -> Path:
    """Absolute repo root, resolved from git -- never from a caller argument.

    Caller-supplied scope would be forgeable: a process could claim a grant
    minted for another repository. The binding is only worth anything if both
    mint and consume derive it the same way, from the same authority.
    """
    return Path(_git_output(["rev-parse", "--show-toplevel"], cwd=start)).resolve()


def resolve_head_sha(repo_root: Path) -> str:
    return _git_output(["rev-parse", "HEAD"], cwd=repo_root)


def default_ppid_resolver(pid: int) -> int | None:
    """Parent pid of ``pid``, or None when it cannot be determined.

    Linux ``/proc`` first (free), macOS ``ps`` fallback. Returning None ends the
    ancestor walk, which makes an unresolvable tree fail CLOSED: the activation
    record is simply not honored and the guard refuses.
    """
    proc_stat = Path(f"/proc/{pid}/stat")
    try:
        if proc_stat.is_file():
            # comm can contain spaces/parens; ppid is the field after the
            # closing paren of comm.
            raw = proc_stat.read_text(encoding="utf-8", errors="replace")
            tail = raw.rsplit(")", 1)[-1].split()
            return int(tail[1])
    except (OSError, ValueError, IndexError):
        return None
    try:
        result = subprocess.run(
            ["ps", "-o", "ppid=", "-p", str(pid)],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    raw_out = result.stdout.strip()
    if result.returncode != 0 or not raw_out:
        return None
    try:
        return int(raw_out.split()[0])
    except (ValueError, IndexError):
        return None


def is_self_or_ancestor(
    candidate_pid: int,
    pid: int,
    ppid_resolver: Callable[[int], int | None] = default_ppid_resolver,
    max_depth: int = ANCESTOR_WALK_MAX_DEPTH,
) -> bool:
    """True when ``candidate_pid`` is ``pid`` itself or one of its ancestors."""
    if candidate_pid <= 0 or pid <= 0:
        return False
    current = pid
    for _ in range(max_depth):
        if current == candidate_pid:
            return True
        if current <= 1:
            return False
        parent = ppid_resolver(current)
        if parent is None or parent == current:
            return False
        current = parent
    return False


# --------------------------------------------------------------------------
# Mint
# --------------------------------------------------------------------------


def sanitize_reason(raw: str) -> str:
    """Collapse whitespace, drop exotic characters, cap length.

    The reason lands in a receipt line and in log output, so it is normalized
    at the boundary rather than trusted downstream.
    """
    collapsed = " ".join(str(raw).split())
    cleaned = _REASON_DISALLOWED_RE.sub("", collapsed).strip()
    return cleaned[:MAX_REASON_CHARS]


def build_grant(
    *,
    repo_root: Path,
    head_sha: str,
    reason: str,
    ttl_minutes: float,
    now: float,
    pid: int,
    host: str,
) -> dict[str, object]:
    cleaned_reason = sanitize_reason(reason)
    if not cleaned_reason:
        raise GrantError(
            "a grant requires a non-empty --reason (it is recorded in the "
            "receipt line; 'because the gate said no' is not a reason)"
        )
    if ttl_minutes <= 0:
        raise GrantError("--ttl-minutes must be greater than 0")
    if ttl_minutes > MAX_TTL_MINUTES:
        raise GrantError(
            f"--ttl-minutes {ttl_minutes:g} exceeds the {MAX_TTL_MINUTES}-minute "
            "hard cap. A long-lived override is an environment variable wearing "
            "a different file extension -- mint a fresh grant instead."
        )
    return {
        "version": GRANT_SCHEMA_VERSION,
        "nonce": secrets.token_hex(16),
        "repo_root": str(Path(repo_root).resolve()),
        "head_sha": head_sha,
        "reason": cleaned_reason,
        "ttl_minutes": ttl_minutes,
        "issued_at": now,
        "expires_at": now + (ttl_minutes * 60.0),
        "issued_by_pid": pid,
        "issued_on_host": host,
    }


def write_grant(repo_root: Path, grant: dict[str, object]) -> Path:
    target = grant_path(repo_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Written 0600 via a temp file + atomic rename so a half-written grant is
    # never observable by a concurrent consume.
    tmp = target.parent / f"{GRANT_FILENAME}.tmp.{os.getpid()}.{secrets.token_hex(4)}"
    tmp.write_text(json.dumps(grant, sort_keys=True) + "\n", encoding="utf-8")
    tmp.chmod(0o600)
    tmp.replace(target)
    return target


# --------------------------------------------------------------------------
# Receipts
# --------------------------------------------------------------------------


def append_receipt(repo_root: Path, record: dict[str, object]) -> None:
    """Append one JSON line. Never raises -- a receipt-write failure must not
    turn into a gate outcome, in either direction."""
    try:
        path = receipts_path(repo_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    except OSError:
        return


# --------------------------------------------------------------------------
# Consume
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ConsumeResult:
    accepted: bool
    code: str
    detail: str
    grant: dict[str, object] | None = None


def _reject(
    repo_root: Path,
    *,
    code: str,
    detail: str,
    context: str,
    now: float,
    pid: int,
    host: str,
    grant: dict[str, object] | None = None,
) -> ConsumeResult:
    append_receipt(
        repo_root,
        {
            "ts": now,
            "event": "prepush_override_rejected",
            "code": code,
            "detail": detail,
            "context": context,
            "pid": pid,
            "host": host,
            "repo_root": str(repo_root),
            "nonce": (grant or {}).get("nonce"),
        },
    )
    return ConsumeResult(accepted=False, code=code, detail=detail, grant=grant)


def consume(
    *,
    repo_root: Path,
    head_sha: str,
    context: str,
    now: float | None = None,
    pid: int | None = None,
    host: str | None = None,
    env: Mapping[str, str] | None = None,
) -> ConsumeResult:
    """Claim and validate the outstanding grant exactly once.

    Ordering is deliberate: the claim (atomic rename) happens BEFORE validation,
    so a grant presented against the wrong sha/repo/clock is destroyed rather
    than left on disk to be retried. A grant is a single authorization for a
    single run; a failed presentation spends it.
    """
    now = time.time() if now is None else now
    pid = os.getpid() if pid is None else pid
    host = socket.gethostname().split(".", 1)[0] if host is None else host
    env = os.environ if env is None else env
    repo_root = Path(repo_root)

    leaked = inherited_override_env_vars(env)
    if leaked:
        return _reject(
            repo_root,
            code="inheritable_env_override_present",
            detail=env_rejection_message(leaked),
            context=context,
            now=now,
            pid=pid,
            host=host,
        )

    source = grant_path(repo_root)
    claimed = override_dir(repo_root) / (
        f"{GRANT_FILENAME}.claimed.{pid}.{secrets.token_hex(4)}"
    )
    try:
        # Atomic claim: exactly one racer can win the rename, so "single-use"
        # holds even when two guards reach for the same grant concurrently.
        source.replace(claimed)
    except OSError:
        return ConsumeResult(
            accepted=False,
            code="no_grant",
            detail=(
                f"no pre-push override grant is outstanding at {source}. Mint one "
                "with: uv run python scripts/hooks/prepush_override_grant.py mint "
                "--reason '<why this run must go ahead here>' (it is bound to this "
                "repo and this HEAD sha, expires in minutes, and is consumed on "
                "first read)."
            ),
        )

    try:
        raw = claimed.read_text(encoding="utf-8")
    except OSError as exc:
        return _reject(
            repo_root,
            code="unreadable_grant",
            detail=f"grant could not be read: {exc}",
            context=context,
            now=now,
            pid=pid,
            host=host,
        )
    finally:
        try:
            claimed.unlink()
        except OSError:
            pass

    try:
        grant = json.loads(raw)
    except (ValueError, TypeError) as exc:
        return _reject(
            repo_root,
            code="malformed_grant",
            detail=f"grant is not valid JSON: {exc}",
            context=context,
            now=now,
            pid=pid,
            host=host,
        )
    if not isinstance(grant, dict):
        return _reject(
            repo_root,
            code="malformed_grant",
            detail="grant payload is not an object",
            context=context,
            now=now,
            pid=pid,
            host=host,
        )

    if grant.get("version") != GRANT_SCHEMA_VERSION:
        return _reject(
            repo_root,
            code="version_mismatch",
            detail=(
                f"grant schema version {grant.get('version')!r} != "
                f"{GRANT_SCHEMA_VERSION}"
            ),
            context=context,
            now=now,
            pid=pid,
            host=host,
            grant=grant,
        )
    if str(grant.get("repo_root")) != str(repo_root.resolve()):
        return _reject(
            repo_root,
            code="repo_mismatch",
            detail=(
                f"grant was minted for {grant.get('repo_root')!r}, not "
                f"{str(repo_root.resolve())!r}"
            ),
            context=context,
            now=now,
            pid=pid,
            host=host,
            grant=grant,
        )
    if str(grant.get("head_sha")) != str(head_sha):
        return _reject(
            repo_root,
            code="head_sha_mismatch",
            detail=(
                f"grant was minted against HEAD {str(grant.get('head_sha'))[:12]}, "
                f"but HEAD is now {str(head_sha)[:12]} -- an amend, rebase or new "
                "commit invalidates a grant. Mint a fresh one."
            ),
            context=context,
            now=now,
            pid=pid,
            host=host,
            grant=grant,
        )
    expires_at = grant.get("expires_at")
    if not isinstance(expires_at, (int, float)) or now > float(expires_at):
        return _reject(
            repo_root,
            code="expired",
            detail=(
                "grant has expired (expires_at="
                f"{expires_at!r}, now={now!r}). Mint a fresh one."
            ),
            context=context,
            now=now,
            pid=pid,
            host=host,
            grant=grant,
        )

    append_receipt(
        repo_root,
        {
            "ts": now,
            "event": "prepush_override_consumed",
            "code": "accepted",
            "context": context,
            "pid": pid,
            "host": host,
            "repo_root": str(repo_root),
            "head_sha": head_sha,
            "nonce": grant.get("nonce"),
            "reason": grant.get("reason"),
            "issued_at": grant.get("issued_at"),
            "expires_at": expires_at,
        },
    )
    write_activation(
        repo_root,
        {
            "version": GRANT_SCHEMA_VERSION,
            "nonce": grant.get("nonce"),
            "repo_root": str(repo_root.resolve()),
            "head_sha": head_sha,
            "owner_pid": pid,
            "expires_at": float(expires_at),
            "context": context,
            "reason": grant.get("reason"),
        },
    )
    return ConsumeResult(
        accepted=True,
        code="accepted",
        detail=(
            f"consumed single-use override grant {str(grant.get('nonce'))[:12]} "
            f"(reason: {grant.get('reason')}). It is now spent -- no child process "
            "and no later run can reuse it. Receipt appended to "
            f"{receipts_path(repo_root)}."
        ),
        grant=grant,
    )


# --------------------------------------------------------------------------
# Activation record (hook -> child pytest hand-off)
# --------------------------------------------------------------------------


def write_activation(repo_root: Path, record: dict[str, object]) -> Path:
    target = activation_path(repo_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.parent / (
        f"{ACTIVATION_FILENAME}.tmp.{os.getpid()}.{secrets.token_hex(4)}"
    )
    tmp.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    tmp.chmod(0o600)
    tmp.replace(target)
    return target


def read_activation(repo_root: Path) -> dict[str, object] | None:
    try:
        raw = activation_path(repo_root).read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        record = json.loads(raw)
    except (ValueError, TypeError):
        return None
    return record if isinstance(record, dict) else None


def activation_covers(
    record: dict[str, object] | None,
    *,
    repo_root: Path,
    head_sha: str,
    now: float,
    pid: int,
    ppid_resolver: Callable[[int], int | None] = default_ppid_resolver,
) -> bool:
    """Whether an activation record authorizes THIS process.

    Every leg must hold: same schema, same repo, same HEAD, unexpired, and the
    consuming process is this process or one of its live ancestors. The last leg
    is what keeps the record from becoming a shared, ambient permission again --
    an unrelated process running during the TTL is not covered.
    """
    if not record:
        return False
    if record.get("version") != GRANT_SCHEMA_VERSION:
        return False
    if str(record.get("repo_root")) != str(Path(repo_root).resolve()):
        return False
    if str(record.get("head_sha")) != str(head_sha):
        return False
    expires_at = record.get("expires_at")
    if not isinstance(expires_at, (int, float)) or now > float(expires_at):
        return False
    owner_pid = record.get("owner_pid")
    if not isinstance(owner_pid, int):
        return False
    return is_self_or_ancestor(owner_pid, pid, ppid_resolver)


def has_active_override(
    *,
    repo_root: Path,
    head_sha: str,
    now: float | None = None,
    pid: int | None = None,
    ppid_resolver: Callable[[int], int | None] = default_ppid_resolver,
) -> bool:
    return activation_covers(
        read_activation(repo_root),
        repo_root=repo_root,
        head_sha=head_sha,
        now=time.time() if now is None else now,
        pid=os.getpid() if pid is None else pid,
        ppid_resolver=ppid_resolver,
    )


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _cmd_mint(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root()
    head_sha = resolve_head_sha(repo_root)
    grant = build_grant(
        repo_root=repo_root,
        head_sha=head_sha,
        reason=args.reason,
        ttl_minutes=args.ttl_minutes,
        now=time.time(),
        pid=os.getpid(),
        host=socket.gethostname().split(".", 1)[0],
    )
    target = write_grant(repo_root, grant)
    append_receipt(
        repo_root,
        {
            "ts": grant["issued_at"],
            "event": "prepush_override_minted",
            "code": "minted",
            "pid": grant["issued_by_pid"],
            "host": grant["issued_on_host"],
            "repo_root": grant["repo_root"],
            "head_sha": grant["head_sha"],
            "nonce": grant["nonce"],
            "reason": grant["reason"],
            "expires_at": grant["expires_at"],
        },
    )
    print(
        f"[prepush-override] minted single-use grant {str(grant['nonce'])[:12]} "
        f"at {target}\n"
        f"[prepush-override]   repo   : {grant['repo_root']}\n"
        f"[prepush-override]   HEAD   : {head_sha[:12]} (an amend/rebase voids it)\n"
        f"[prepush-override]   expires: {args.ttl_minutes:g} minute(s) from now\n"
        f"[prepush-override]   reason : {grant['reason']}\n"
        "[prepush-override] It is consumed by the FIRST guard that reads it and "
        "cannot be reused, inherited, or re-presented.",
        file=sys.stderr,
    )
    print(json.dumps(grant, sort_keys=True))
    return 0


def _cmd_consume(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root()
    head_sha = resolve_head_sha(repo_root)
    result = consume(repo_root=repo_root, head_sha=head_sha, context=args.context)
    prefix = "[prepush-override]"
    if result.accepted:
        print(f"{prefix} {result.detail}", file=sys.stderr)
        return 0
    print(f"{prefix} refused ({result.code}): {result.detail}", file=sys.stderr)
    return 1


def _cmd_status(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root()
    head_sha = resolve_head_sha(repo_root)
    now = time.time()
    grant_file = grant_path(repo_root)
    payload: dict[str, object] = {
        "repo_root": str(repo_root),
        "head_sha": head_sha,
        "grant_present": grant_file.is_file(),
        "activation_covers_this_process": has_active_override(
            repo_root=repo_root, head_sha=head_sha, now=now
        ),
        "inherited_override_env_vars": inherited_override_env_vars(os.environ),
        "receipts": str(receipts_path(repo_root)),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prepush_override_grant",
        description=(
            "Single-use, repo+HEAD-scoped grant tokens for pre-push gate "
            "overrides (OMN-16480). Replaces the inheritable "
            f"{OVERRIDE_ENV_PREFIX}* environment variables, which are now "
            "rejected outright."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    mint_parser = sub.add_parser("mint", help="mint a single-use override grant")
    mint_parser.add_argument(
        "--reason",
        required=True,
        help="why this run must proceed here; recorded in the receipt line",
    )
    mint_parser.add_argument(
        "--ttl-minutes",
        type=float,
        default=DEFAULT_TTL_MINUTES,
        help=(
            f"grant lifetime in minutes (default {DEFAULT_TTL_MINUTES}, hard cap "
            f"{MAX_TTL_MINUTES})"
        ),
    )
    mint_parser.set_defaults(func=_cmd_mint)

    consume_parser = sub.add_parser(
        "consume", help="claim the outstanding grant (exit 0 if authorized)"
    )
    consume_parser.add_argument(
        "--context",
        default="unspecified",
        help="which guard is consuming, recorded in the receipt line",
    )
    consume_parser.set_defaults(func=_cmd_consume)

    status_parser = sub.add_parser("status", help="report override state as JSON")
    status_parser.set_defaults(func=_cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except GrantError as exc:
        print(f"[prepush-override] ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
