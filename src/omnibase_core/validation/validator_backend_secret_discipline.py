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
   reference (``secret_ref`` / ``api_key_ref`` for API-key backends, or
   ``credential_ref`` for ADC backends) — not an inline value.
3. ADC and API-key auth are mutually exclusive on a single backend
   (``credential_ref`` must not coexist with ``secret_ref`` / ``api_key_ref``).
4. ``api_key_env`` is NOT a logical reference (OMN-17931, OMN-17372 AC3). It
   names a HOUSE environment variable, so a backend carrying it resolves a
   platform-held provider credential from the runtime env. A cloud backend
   whose only credential declaration is ``api_key_env`` is reported as missing
   a logical reference; ``api_key_env`` beside a real reference is reported as
   migration debt. This aligns the gate with the OMN-12878 guard in
   ``omnibase_core.validation.api_key_ref_discipline``.

The gate FAILS (exit 1) on any violation. There is no warn-only mode: a literal
credential in committed config is never acceptable.

COMPUTE handler usage (definition B — typed request/response)
---------------------------------------------------------------
The handler is the node's, bound in its ``contract.yaml``::

    from omnibase_core.nodes.node_backend_secret_discipline_compute.handler_backend_secret_discipline import (
        HandlerBackendSecretDisciplineCompute,
    )
    from omnibase_core.validation.validator_backend_secret_discipline import (
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

    python -m omnibase_core.nodes.node_backend_secret_discipline_compute.runtime_backend_secret_discipline
    python -m omnibase_core.nodes.node_backend_secret_discipline_compute.runtime_backend_secret_discipline --json
    python -m omnibase_core.nodes.node_backend_secret_discipline_compute.runtime_backend_secret_discipline file1.yaml file2.yaml

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

import re
from typing import cast

from yaml import YAMLError, safe_load

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
    "ModelBackendSecretDisciplineInput",
    "ModelBackendSecretDisciplineOutput",
    "scan_literal_credentials",
    "scan_bifrost_backends",
    "build_report_from_files",
]

# ---------------------------------------------------------------------------
# Constants — identical to the ported script
# ---------------------------------------------------------------------------

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

_SUPPRESSION_TOKEN = "# backend-secret-ok:"  # secret-ok: detector grammar

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


# The only credential declarations that are LOGICAL references resolved through
# the secret store. ``api_key_env`` is deliberately absent: it names a HOUSE
# environment variable, so a backend carrying it resolves a platform-held
# provider credential from the runtime env — the path OMN-17372 AC3 requires to
# be unreachable by construction (OMN-17931; aligned with the OMN-12878 guard in
# ``omnibase_core.validation.api_key_ref_discipline``).
_LOGICAL_REF_KEYS: tuple[str, ...] = ("secret_ref", "api_key_ref", "credential_ref")
_LEGACY_ENV_KEY = "api_key_env"


def _declares(backend: dict[str, object], key: str) -> bool:
    value = backend.get(key)
    return isinstance(value, str) and bool(value.strip())


def _backend_has_logical_ref(backend: dict[str, object]) -> bool:
    return any(_declares(backend, key) for key in _LOGICAL_REF_KEYS)


def _backend_declares_legacy_env(backend: dict[str, object]) -> bool:
    return _declares(backend, _LEGACY_ENV_KEY)


def _backend_auth_is_exclusive(backend: dict[str, object]) -> bool:
    has_credential = _declares(backend, "credential_ref")
    has_api_key = _declares(backend, "secret_ref") or _declares(backend, "api_key_ref")
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
        has_logical_ref = _backend_has_logical_ref(backend_data)
        declares_env = _backend_declares_legacy_env(backend_data)
        if tier in _CLOUD_TIERS and not has_logical_ref:
            if declares_env:
                detail = (
                    "only the legacy 'api_key_env' is declared — that is a HOUSE "
                    "environment-variable name, not a logical secret reference "
                    "(OMN-17931 / OMN-17372 AC3); declare a store-resolved ref and "
                    "remove api_key_env"
                )
            else:
                detail = "none declared"
            violations.append(
                ModelBackendRefViolation(
                    file=rel,
                    message=(
                        f"{rel}: cloud backend {backend_id!r} (tier={tier!r}) requires a "
                        f"logical secret reference (secret_ref/api_key_ref for API-key "
                        f"auth, or credential_ref for ADC) — {detail}"
                    ),
                )
            )
        elif declares_env:
            violations.append(
                ModelBackendRefViolation(
                    file=rel,
                    message=(
                        f"{rel}: backend {backend_id!r} carries the legacy 'api_key_env' "
                        f"beside its logical secret reference — migration debt: the "
                        f"store-resolved ref is the only credential declaration allowed; "
                        f"remove api_key_env (OMN-17931 / OMN-17372 AC3)"
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
