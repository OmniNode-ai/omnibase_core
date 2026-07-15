# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorBackendSecretDiscipline — reject literal credentials; require secret-refs.

Ported from omnimarket/scripts/ci/check_backend_secret_discipline.py (OMN-12971)
to a canonical COMPUTE handler (OMN-13305, parent OMN-9048 W8).

ENFORCEMENT RATCHET, not detection. Wired as a pre-commit hook (remote, via
omnibase_core/.pre-commit-hooks.yaml) and as a required CI gate.

Why this exists
---------------
The Vertex runtime wiring (OMN-12971) added a credential-backed backend
(``cloud-vertex-gemini``) whose ADC credential is a FILE resolved from the
secret store at the effect boundary. The whole point of secret-ref discipline
is that the *credential value never lands in committed config*. This gate makes
that invariant mechanically enforced so a future edit cannot regress it by
pasting a literal key / service-account JSON / bearer token into the routing
authority.

What it checks (over the scanned config files or supplied file paths)
---------------------------------------------------------------------
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

The gate FAILS (exit 1) on any violation. There is no warn-only mode: a literal
credential in committed config is never acceptable.

COMPUTE handler usage (definition B — typed request/response)
---------------------------------------------------------------
::

    from omnibase_core.validation.validator_backend_secret_discipline import (
        HandlerBackendSecretDisciplineCompute,
        ModelBackendSecretDisciplineInput,
    )

    handler = HandlerBackendSecretDisciplineCompute()
    output = handler.handle(ModelBackendSecretDisciplineInput(config_contents={...}))
    # Pure, deterministic, no filesystem I/O in the handler — the shared runtime
    # adapter (omnibase_core.runtime.runtime_local_adapter) owns the bus-message
    # boundary; this module never references the envelope type (OMN-14355 def-B).

CLI / pre-commit usage
----------------------
::

    python -m omnibase_core.validation.validator_backend_secret_discipline
    python -m omnibase_core.validation.validator_backend_secret_discipline --json
    python -m omnibase_core.validation.validator_backend_secret_discipline file1.yaml file2.yaml

Port equivalence
----------------
Pre-port source SHA-256:
    e2344b5cf9d696b7160ac3cbb9eca9380da4addc854fa5ccf1fd12f5da901aab

The scanning logic (patterns, backend checks, mutual-exclusion check) is
preserved verbatim. The handler wraps these pure functions behind the
canonical COMPUTE interface; the CLI ``main()`` entry-point preserves the
original invocation contract. No behavioral change — only the invocation
surface is extended.

Schema Version:
    v1.0.0 — OMN-13305
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from yaml import YAMLError, safe_load

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.validation.model_backend_ref_violation import (
    ModelBackendRefViolation,
)
from omnibase_core.models.validation.model_backend_secret_discipline_input import (
    ModelBackendSecretDisciplineInput,
)
from omnibase_core.models.validation.model_backend_secret_discipline_output import (
    ModelBackendSecretDisciplineOutput,
)
from omnibase_core.models.validation.model_credential_violation import (
    ModelCredentialViolation,
)

__all__ = [
    "HandlerBackendSecretDisciplineCompute",
    "NodeBackendSecretDisciplineCompute",
    "ModelBackendSecretDisciplineInput",
    "ModelBackendSecretDisciplineOutput",
    "scan_literal_credentials",
    "scan_bifrost_backends",
    "build_report_from_files",
]

# ---------------------------------------------------------------------------
# Constants — identical to the ported script
# ---------------------------------------------------------------------------

_REPO_ROOT_MARKER = ".git"

# Literal-credential signatures. A match means a real secret value leaked into
# committed config — always a hard failure.
_CREDENTIAL_LITERAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("pem-private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("service-account-private-key", re.compile(r'"private_key"\s*:')),
    ("service-account-client-email", re.compile(r'"client_email"\s*:')),
    ("bearer-token", re.compile(r"Bearer\s+[A-Za-z0-9._\-]{16,}")),
    ("openai-style-key", re.compile(r"\bsk-[A-Za-z0-9]{20,}")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z._\-]{30,}")),
    ("gcp-oauth-token", re.compile(r"\bya29\.[0-9A-Za-z._\-]{20,}")),
)

# Local backends do not require cloud auth.
_LOCAL_TIERS: frozenset[str] = frozenset({"local"})

# Tiers whose backends route to a provider that requires authentication.
_CLOUD_TIERS: frozenset[str] = frozenset(
    {"cheap_cloud", "cheap_frontier", "frontier_api"}
)

# Backend ids dispatched via subprocess (CLI agents) or using OAuth with no
# committed secret — no secret/credential ref required.
_NO_SECRET_BACKEND_IDS: frozenset[str] = frozenset(
    {"cli-claude", "cli-opencode", "cloud-sonnet", "cloud-haiku"}
)

_CONFIG_SUFFIXES: frozenset[str] = frozenset({".yaml", ".yml", ".json"})
_SUPPRESSION_TOKEN = "# backend-secret-ok:"

# ---------------------------------------------------------------------------
# Pure scanning functions — identical logic to ported script
# ---------------------------------------------------------------------------


def scan_literal_credentials(rel: str, text: str) -> list[ModelCredentialViolation]:
    """Return all literal-credential violations found in *text*.

    Args:
        rel: Relative path label (used in violation messages).
        text: Raw file content to scan.

    Returns:
        List of ``ModelCredentialViolation`` instances, one per matching line.
    """
    violations: list[ModelCredentialViolation] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if _SUPPRESSION_TOKEN in line:
            continue
        for label, pattern in _CREDENTIAL_LITERAL_PATTERNS:
            if pattern.search(line):
                violations.append(
                    ModelCredentialViolation(
                        file=rel,
                        line=lineno,
                        kind=label,
                        message=(
                            f"{rel}:{lineno}: literal credential ({label}) in committed "
                            f"config — credentials must live in the secret store, never "
                            f"in routing-authority config"
                        ),
                    )
                )
    return violations


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


def scan_bifrost_backends(
    rel: str, data: dict[str, object]
) -> list[ModelBackendRefViolation]:
    """Scan bifrost_delegation YAML data for missing/conflicting secret refs.

    Args:
        rel: Relative path label.
        data: Parsed YAML mapping (expected to contain a ``backends`` list).

    Returns:
        List of ``ModelBackendRefViolation`` instances.
    """
    violations: list[ModelBackendRefViolation] = []
    backends = data.get("backends", [])
    if not isinstance(backends, list):
        return [
            ModelBackendRefViolation(
                file=rel, message=f"{rel}: backends must be a list"
            )
        ]
    for backend in backends:
        if not isinstance(backend, dict):
            continue
        backend_data = cast("dict[str, object]", backend)
        backend_id = backend_data.get("backend_id", "<unknown>")
        tier = backend_data.get("tier", "")
        if backend_id in _NO_SECRET_BACKEND_IDS:
            continue
        if tier in _LOCAL_TIERS:
            continue
        if tier in _CLOUD_TIERS and not _backend_has_logical_ref(backend_data):
            violations.append(
                ModelBackendRefViolation(
                    file=rel,
                    message=(
                        f"{rel}: cloud backend {backend_id!r} (tier={tier!r}) requires a "
                        f"logical secret reference (secret_ref/api_key_ref/api_key_env for "
                        f"API-key auth, or credential_ref for ADC) — none declared"
                    ),
                )
            )
        if not _backend_auth_is_exclusive(backend_data):
            violations.append(
                ModelBackendRefViolation(
                    file=rel,
                    message=(
                        f"{rel}: backend {backend_id!r} declares both credential_ref (ADC) "
                        f"and api-key auth — they are mutually exclusive"
                    ),
                )
            )
    return violations


def build_report_from_files(
    config_contents: dict[str, str],
) -> ModelBackendSecretDisciplineOutput:
    """Build a ``ModelBackendSecretDisciplineOutput`` from pre-loaded file contents.

    This is the pure core of the validator — no filesystem I/O. The caller
    (EFFECT boundary or CLI) supplies the file contents.

    Args:
        config_contents: Map of relative-path → raw text.

    Returns:
        ``ModelBackendSecretDisciplineOutput`` with verdict and all findings.
    """
    literal_violations: list[ModelCredentialViolation] = []
    backend_violations: list[ModelBackendRefViolation] = []
    errors: list[str] = []

    for rel, text in config_contents.items():
        literal_violations.extend(scan_literal_credentials(rel, text))
        if "backends" in text:
            try:
                parsed = safe_load(text)
            except YAMLError as exc:
                errors.append(f"{rel}: YAML parse error — {exc}")
                continue
            if isinstance(parsed, dict) and "backends" in parsed:
                backend_violations.extend(
                    scan_bifrost_backends(rel, cast("dict[str, object]", parsed))
                )
            elif not isinstance(parsed, dict):
                errors.append(f"{rel}: did not parse to a mapping")

    all_violations = literal_violations + backend_violations
    return ModelBackendSecretDisciplineOutput(
        literal_credential_violations=literal_violations,
        backend_ref_violations=backend_violations,
        errors=errors,
        passed=len(all_violations) == 0 and len(errors) == 0,
    )


# ---------------------------------------------------------------------------
# COMPUTE handler — ProtocolMessageHandler implementation
# ---------------------------------------------------------------------------


class HandlerBackendSecretDisciplineCompute:
    """Backend-secret-discipline validator as a canonical COMPUTE handler.

    Implements ``ProtocolMessageHandler`` (structural protocol, not base-class
    inheritance). The handler is pure and deterministic: all file-loading I/O
    happens at the EFFECT boundary (CLI / runner); the handler receives only
    pre-loaded content via the envelope payload.

    Node archetype: COMPUTE (pure, idempotent, no side effects).
    """

    # --- ProtocolMessageHandler protocol ---

    @property
    def handler_id(self) -> str:
        return "node.backend-secret-discipline.compute"

    @property
    def category(self) -> EnumMessageCategory:
        return EnumMessageCategory.COMMAND

    @property
    def message_types(self) -> set[str]:
        return {"BackendSecretDisciplineCheck"}

    @property
    def node_kind(self) -> EnumNodeKind:
        return EnumNodeKind.COMPUTE

    def handle(
        self, request: ModelBackendSecretDisciplineInput
    ) -> ModelBackendSecretDisciplineOutput:
        """Run the backend-secret-discipline check and return a typed verdict.

        Definition-B canonical shape (OMN-14355): typed request in, typed
        response out, no envelope reference in the core. The shared runtime
        adapter (``omnibase_core.runtime.runtime_local_adapter``) owns the
        envelope boundary and adapts this call from the bus message.

        ``request`` supplies all file contents to scan; the handler performs
        no filesystem I/O.

        Args:
            request: ``ModelBackendSecretDisciplineInput`` payload.

        Returns:
            ``ModelBackendSecretDisciplineOutput`` verdict.
        """
        return build_report_from_files(request.config_contents)


NodeBackendSecretDisciplineCompute = HandlerBackendSecretDisciplineCompute


# ---------------------------------------------------------------------------
# CLI entry-point — preserves original invocation contract
# ---------------------------------------------------------------------------


def _find_repo_root(start: Path) -> Path:
    candidate = start
    while candidate != candidate.parent:
        if (candidate / _REPO_ROOT_MARKER).exists():
            return candidate
        candidate = candidate.parent
    return start


def _run_on_files(paths: list[Path]) -> ModelBackendSecretDisciplineOutput:
    """Run the check on the explicitly supplied file paths."""
    repo_root = _find_repo_root(paths[0] if paths else Path.cwd())
    contents: dict[str, str] = {}
    for path in paths:
        try:
            rel = str(path.relative_to(repo_root))
        except ValueError:
            rel = str(path)
        contents[rel] = path.read_text(encoding="utf-8")
    return build_report_from_files(contents)


def _git_changed_files(base: str) -> list[Path]:
    import subprocess

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


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry-point for pre-commit hook and standalone invocation.

    Returns:
        0 on PASS, 1 on FAIL.
    """
    parser = argparse.ArgumentParser(
        description="Backend secret-ref / credential-ref discipline gate (OMN-13305)"
    )
    parser.add_argument("--json", action="store_true", help="Print the report as JSON")
    parser.add_argument(
        "--base",
        default=None,
        help="Git base ref to diff HEAD against (CI mode); scans changed config files.",
    )
    parser.add_argument(
        "filenames",
        nargs="*",
        help="Files to check (pre-commit passes staged filenames here)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.base is not None:
        paths = _git_changed_files(args.base)
    else:
        paths = [Path(f) for f in args.filenames]

    config_paths = [p for p in paths if p.suffix in _CONFIG_SUFFIXES]
    if not config_paths:
        if args.json:
            print(
                json.dumps(
                    {
                        "gate": "backend-secret-discipline",
                        "passed": True,
                        "note": "no config files to check",
                    },
                    indent=2,
                )
            )
        else:
            print("[backend-secret-discipline] PASS - no config files to check.")
        return 0

    report = _run_on_files(config_paths)

    if args.json:
        # Convert Pydantic models to dicts for JSON output.
        print(
            json.dumps(
                {
                    "ticket": report.ticket,
                    "gate": report.gate,
                    "literal_credential_violations": [
                        v.model_dump() for v in report.literal_credential_violations
                    ],
                    "backend_ref_violations": [
                        v.model_dump() for v in report.backend_ref_violations
                    ],
                    "errors": report.errors,
                    "passed": report.passed,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if report.passed else 1

    if report.passed:
        print(
            "[backend-secret-discipline] PASS — no literal credentials; every "
            "authenticated cloud backend declares a logical secret/credential ref."
        )
        return 0

    print("[backend-secret-discipline] FAIL")
    for err in report.errors:
        print(f"  error: {err}")
    for cred_v in report.literal_credential_violations:
        print(f"  literal-credential: {cred_v.message}")
    for ref_v in report.backend_ref_violations:
        print(f"  backend-ref: {ref_v.message}")
    print(
        "\nFix: keep credential VALUES in the secret store; declare only logical "
        "refs (secret_ref / credential_ref) in routing-authority config."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
