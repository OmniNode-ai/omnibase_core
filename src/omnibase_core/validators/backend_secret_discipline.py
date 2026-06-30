# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Backend secret-ref / credential-ref discipline validator (OMN-13290).

Ported to ``omnibase_core`` from ``omnimarket``'s
``scripts/ci/check_backend_secret_discipline.py`` (OMN-12971) so it can be wired
fleet-wide on every repo that carries cloud-backend routing-authority config
(omnibase_infra, omnibase_core, omnimarket, ...). The omnimarket-local script is
deleted in the same change set — this module is the single canonical
implementation.

Enforcement ratchet, not detection. Wired as a pre-commit hook and a CI gate.

Why this exists
---------------
Credential-backed backends (e.g. ``cloud-vertex-gemini``) resolve their secret
value from the secret store at the effect boundary. The whole point of
secret-ref discipline is that the *credential value never lands in committed
config*. This gate makes that invariant mechanically enforced so a future edit
cannot regress it by pasting a literal key / service-account JSON / bearer token
into the routing authority.

What it checks (over the supplied config files)
-----------------------------------------------
1. NO literal credential value appears anywhere in the scanned config:
   - PEM private-key blocks (``-----BEGIN ... PRIVATE KEY-----``)
   - service-account JSON markers (``"private_key"``, ``"client_email"``)
   - bearer/api-key-shaped literals (``Bearer <...>``, ``sk-...``, ``AIza...``,
     ``ya29.`` OAuth tokens, Google API keys)
2. Every CLOUD backend that requires authentication declares a LOGICAL
   reference (``secret_ref`` / ``api_key_ref`` / ``api_key_env`` for API-key
   backends, or ``credential_ref`` for ADC backends) — not an inline value.
3. ADC and API-key auth are mutually exclusive on a single backend
   (``credential_ref`` must not coexist with ``secret_ref`` / ``api_key_ref`` /
   ``api_key_env``).

The literal-credential scan applies to every supplied file. The backend-ref /
exclusivity scan applies only to files that parse to a mapping carrying a
``backends:`` list (bifrost-delegation-shaped routing authority); other config
files are scanned for literals only.

Purity
------
This module is a pure, deterministic function over its inputs: the only I/O is
reading the supplied file paths at the boundary (``validate_paths``). The
analysis functions (``scan_literal_credentials``, ``scan_backends``) take text /
parsed data and return findings with no I/O — they are directly testable against
fixtures. This is the COMPUTE-validator shape (§1A of the validator-
standardization plan): a pure verdict function, no bespoke base class.

The gate FAILS (exit 1) on any violation. There is no warn-only mode: a literal
credential in committed config is never acceptable.

Exit codes
----------
``0`` — no violations.
``1`` — at least one violation.
``2`` — internal error (parse failure of a backends file, missing --base ref).

Usage::

    # pre-commit (staged files supplied by pre-commit)
    python -m omnibase_core.validators.backend_secret_discipline FILE [...]

    # CI (diff against base ref, scans changed config files)
    python -m omnibase_core.validators.backend_secret_discipline --base origin/dev

    # JSON report
    python -m omnibase_core.validators.backend_secret_discipline --json FILE [...]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import yaml

__all__ = [
    "CREDENTIAL_LITERAL_PATTERNS",
    "Finding",
    "scan_backends",
    "scan_literal_credentials",
    "validate_paths",
    "build_report",
    "main",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Local backends do not require cloud auth; identified by tier == "local".
_LOCAL_TIERS: frozenset[str] = frozenset({"local"})

# Tiers whose backends route to a provider that requires authentication.
_CLOUD_TIERS: frozenset[str] = frozenset(
    {"cheap_cloud", "cheap_frontier", "frontier_api"}
)

# Backend ids that are dispatched via subprocess (CLI agents) or use OAuth with
# no committed secret (Claude Code OAuth) — no secret/credential ref required.
_NO_SECRET_BACKEND_IDS: frozenset[str] = frozenset(
    {"cli-claude", "cli-opencode", "cloud-sonnet", "cloud-haiku"}
)

# Config file extensions eligible for the literal-credential scan.
_CONFIG_SUFFIXES: frozenset[str] = frozenset({".yaml", ".yml", ".json"})

_EXCLUDED_PATH_PARTS: frozenset[str] = frozenset(
    {
        ".venv",
        "__pycache__",
        "build",
        "dist",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "node_modules",
        ".git",
        "archived",
        "archive",
    }
)

SUPPRESSION_TOKEN = "# backend-secret-ok:"  # env-var-ok: comment marker, not an env var  # secret-ok: literal comment marker, not a credential

# Literal-credential signatures. A match means a real secret value leaked into
# committed config — always a hard failure.
CREDENTIAL_LITERAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("pem-private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("service-account-private-key", re.compile(r'"private_key"\s*:')),
    ("service-account-client-email", re.compile(r'"client_email"\s*:')),
    ("bearer-token", re.compile(r"Bearer\s+[A-Za-z0-9._\-]{16,}")),
    ("openai-style-key", re.compile(r"\bsk-[A-Za-z0-9]{20,}")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z._\-]{30,}")),
    ("gcp-oauth-token", re.compile(r"\bya29\.[0-9A-Za-z._\-]{20,}")),
)


# ---------------------------------------------------------------------------
# Finding (internal-dataclass-ok: validator-internal finding)
# ---------------------------------------------------------------------------


class Finding:
    """A single backend-secret-discipline violation."""

    __slots__ = ("category", "message", "rel")

    def __init__(self, category: str, rel: str, message: str) -> None:
        self.category = category
        self.rel = rel
        self.message = message

    def format(self) -> str:
        return f"{self.category}: {self.message}"


# ---------------------------------------------------------------------------
# Pure analysis (no I/O)
# ---------------------------------------------------------------------------


def scan_literal_credentials(rel: str, text: str) -> list[Finding]:
    """Return literal-credential findings for the text of one config file.

    Lines carrying the suppression token are skipped (an explicit, reviewed
    test-fixture exception).
    """
    findings: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if SUPPRESSION_TOKEN in line:
            continue
        for label, pattern in CREDENTIAL_LITERAL_PATTERNS:
            if pattern.search(line):
                findings.append(
                    Finding(
                        "literal-credential",
                        rel,
                        f"{rel}:{lineno}: literal credential ({label}) in committed "
                        f"config — credentials must live in the secret store, never "
                        f"in routing-authority config",
                    )
                )
    return findings


def _backend_has_logical_ref(backend: dict[str, object]) -> bool:
    for key in ("secret_ref", "api_key_ref", "api_key_env", "credential_ref"):
        value = backend.get(key)
        if isinstance(value, str) and value.strip():
            return True
    return False


def _backend_auth_is_exclusive(backend: dict[str, object]) -> bool:
    credential = backend.get("credential_ref")
    has_credential = isinstance(credential, str) and bool(credential.strip())
    has_api_key = False
    for key in ("secret_ref", "api_key_ref", "api_key_env"):
        value = backend.get(key)
        if isinstance(value, str) and value.strip():
            has_api_key = True
            break
    return not (has_credential and has_api_key)


def scan_backends(rel: str, data: dict[str, object]) -> list[Finding]:
    """Return backend-ref / exclusivity findings for a parsed bifrost config."""
    findings: list[Finding] = []
    backends = data.get("backends", [])
    if not isinstance(backends, list):
        return [Finding("backend-ref", rel, f"{rel}: backends must be a list")]
    for backend in backends:
        if not isinstance(backend, dict):
            continue
        backend_id = backend.get("backend_id", "<unknown>")
        tier = backend.get("tier", "")
        if backend_id in _NO_SECRET_BACKEND_IDS:
            continue
        if tier in _LOCAL_TIERS:
            continue
        if tier in _CLOUD_TIERS and not _backend_has_logical_ref(backend):
            findings.append(
                Finding(
                    "backend-ref",
                    rel,
                    f"{rel}: cloud backend {backend_id!r} (tier={tier!r}) requires a "
                    f"logical secret reference (secret_ref/api_key_ref/api_key_env for "
                    f"API-key auth, or credential_ref for ADC) — none declared",
                )
            )
        if not _backend_auth_is_exclusive(backend):
            findings.append(
                Finding(
                    "backend-ref",
                    rel,
                    f"{rel}: backend {backend_id!r} declares both credential_ref (ADC) "
                    f"and api-key auth — they are mutually exclusive",
                )
            )
    return findings


# ---------------------------------------------------------------------------
# File / path boundary (the only I/O)
# ---------------------------------------------------------------------------


def _is_config_file(path: Path) -> bool:
    if path.suffix not in _CONFIG_SUFFIXES:
        return False
    return not (set(path.parts) & _EXCLUDED_PATH_PARTS)


def _iter_config_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for suffix in _CONFIG_SUFFIXES:
        files.extend(
            p
            for p in root.rglob(f"*{suffix}")
            if not (set(p.parts) & _EXCLUDED_PATH_PARTS)
        )
    return sorted(files)


def validate_paths(
    paths: Sequence[Path], cwd: Path | None = None
) -> tuple[list[Finding], list[str]]:
    """Validate all supplied config paths. Returns (findings, errors).

    A directory is walked for config files. A non-config file is ignored. The
    backend-ref scan runs only for files that parse to a mapping with a
    ``backends`` list.
    """
    base = cwd or Path.cwd()
    findings: list[Finding] = []
    errors: list[str] = []
    targets: list[Path] = []
    for path in paths:
        if path.is_dir():
            targets.extend(_iter_config_files(path))
        elif _is_config_file(path) and path.exists():
            targets.append(path)

    for path in sorted(set(targets)):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{path}: cannot read: {exc}")
            continue
        rel = _rel(path, base)
        findings.extend(scan_literal_credentials(rel, text))
        if "backends" not in text:
            continue
        try:
            parsed = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            errors.append(f"{rel}: YAML parse error: {exc}")
            continue
        if isinstance(parsed, dict) and isinstance(parsed.get("backends"), list):
            findings.extend(scan_backends(rel, parsed))

    # Order-independent: sort by stable key for deterministic output.
    findings.sort(key=lambda f: (f.category, f.message))
    return findings, errors


def _rel(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def build_report(paths: Sequence[Path], cwd: Path | None = None) -> dict[str, object]:
    findings, errors = validate_paths(paths, cwd)
    literal = [f.message for f in findings if f.category == "literal-credential"]
    backend = [f.message for f in findings if f.category == "backend-ref"]
    return {
        "ticket": "OMN-13290",
        "gate": "backend-secret-discipline",
        "literal_credential_violations": literal,
        "backend_ref_violations": backend,
        "errors": errors,
        "passed": not findings and not errors,
    }


# ---------------------------------------------------------------------------
# Git helper (CI mode)
# ---------------------------------------------------------------------------


def _git_changed_files(base: str) -> list[Path]:
    proc = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit(2)  # error-ok: CLI exit code at the git-hook boundary
    return [Path(p) for p in proc.stdout.splitlines() if p.strip()]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="backend-secret-discipline",
        description=(
            "Reject literal credentials in committed config and require a logical "
            "secret/credential ref for every authenticated cloud backend (OMN-13290)."
        ),
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Config file or directory paths to scan (pre-commit passes staged files).",
    )
    parser.add_argument(
        "--base",
        default=None,
        help="Git base ref to diff HEAD against (CI mode); scans changed config files.",
    )
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)

    if args.base is not None:
        paths = _git_changed_files(args.base)
    else:
        paths = [Path(p) for p in args.files]

    if not paths:
        # No files supplied — scan nothing (pre-commit passes only staged files).
        return 0

    findings, errors = validate_paths(paths)
    passed = not findings and not errors

    if args.json:
        report = build_report(paths)
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
        return 0 if passed else 1

    if passed:
        return 0

    sys.stderr.write("[backend-secret-discipline] FAIL\n")
    for err in errors:
        sys.stderr.write(f"  error: {err}\n")
    for finding in findings:
        sys.stderr.write(f"  {finding.format()}\n")
    sys.stderr.write(
        "\nFix: keep credential VALUES in the secret store; declare only logical "
        "refs (secret_ref / credential_ref) in routing-authority config.\n"
        f"Suppression (test fixtures only): add '{SUPPRESSION_TOKEN} <reason>' "
        "on the offending line.\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())  # error-ok: standard CLI module entry point
