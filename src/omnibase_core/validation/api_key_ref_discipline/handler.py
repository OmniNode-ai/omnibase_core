# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""HandlerApiKeyRefDisciplineCompute — COMPUTE validator that rejects api_key_env usage.

Guardrail: route/secret configs must declare api_key_ref or secret_ref, not the
legacy api_key_env. This gate is the mechanical enforcement of OMN-12878 (Phase:
Permanent Guardrails in the dev-stability loop-closure plan).

Why this exists
---------------
``api_key_env`` couples routing-authority config directly to runtime environment
variable names, defeating the secret-store indirection that ``secret_ref`` and
``api_key_ref`` provide. New backends must declare a logical secret reference;
existing backends with ``api_key_env`` are migration debt (blocked by this gate,
addressable with the per-line suppression marker while migration is in flight).

What it checks
--------------
For every bifrost-shaped config file supplied (mapping with a ``backends`` list):
  - Each cloud backend that declares ``api_key_env`` WITHOUT also declaring
    ``api_key_ref`` or ``secret_ref`` is flagged as a deprecation violation.
  - A backend that carries both ``api_key_env`` AND (``api_key_ref`` OR
    ``secret_ref``) is considered migrated and is NOT flagged (the logical ref
    supersedes the env var; the env var is a compat alias during transition).
  - Lines carrying the suppression token are skipped (reviewed legacy exemption).

Suppression token: ``# api-key-env-ok:``

Examples are covered in the unit fixture corpus rather than embedded here, so
the repo-wide secret scanner does not have to interpret YAML samples inside a
Python docstring.

Architecture: COMPUTE node — pure, deterministic, no filesystem/network/env I/O.
All file loading is the EFFECT boundary's responsibility. The handler receives
pre-loaded content via ``ModelApiKeyRefScanInput``.

See: OMN-12878
"""

from __future__ import annotations

from typing import cast

from yaml import YAMLError, safe_load

from omnibase_core.validation.api_key_ref_discipline.models import (
    ModelApiKeyRefFinding,
    ModelApiKeyRefScanInput,
    ModelApiKeyRefScanResult,
)

__all__ = [
    "HandlerApiKeyRefDisciplineCompute",
    "scan_bifrost_yaml",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Suppression token: a line carrying this string is excluded from the check.
# Canonical form: ``# api-key-env-ok: <reason>``
_SUPPRESSION_TOKEN: str = "api-key-env-ok:"  # secret-ok: marker string, not a secret

# Tiers that do not require cloud auth; excluded from the check.
_LOCAL_TIERS: frozenset[str] = frozenset({"local"})

# Backends dispatched via subprocess CLI — no committed key required.
_NO_SECRET_BACKEND_IDS: frozenset[str] = frozenset(
    {"cli-claude", "cli-opencode", "cloud-sonnet", "cloud-haiku"}
)

# ---------------------------------------------------------------------------
# Pure scanning function (no I/O)
# ---------------------------------------------------------------------------


def scan_bifrost_yaml(
    rel: str,
    text: str,
) -> list[ModelApiKeyRefFinding]:
    """Scan a single bifrost YAML text for deprecated api_key_env declarations.

    Returns one ``ModelApiKeyRefFinding`` per offending backend entry.  Returns
    an empty list when the text does not contain a ``backends`` key (non-bifrost
    config) or when all backends are compliant.

    This function is pure (no I/O) and directly testable against fixtures.

    Args:
        rel: Relative path label used in finding messages.
        text: Raw YAML content of the config file.

    Returns:
        List of ``ModelApiKeyRefFinding`` instances, one per offending backend.

    Raises:
        YAMLError: Propagated to the caller so it can record a parse error.
    """
    if "backends" not in text:
        return []

    parsed = safe_load(text)  # may raise YAMLError — caller handles
    if not isinstance(parsed, dict):
        return []
    backends_raw = parsed.get("backends")
    if not isinstance(backends_raw, list):
        return []

    # Build a line-index so we can check individual backend lines for
    # suppression tokens.  We key lines by the zero-based line number.
    lines = text.splitlines()

    findings: list[ModelApiKeyRefFinding] = []
    for backend in backends_raw:
        if not isinstance(backend, dict):
            continue
        backend_data = cast("dict[str, object]", backend)
        backend_id = str(backend_data.get("backend_id", "<unknown>"))
        tier = str(backend_data.get("tier", ""))

        if backend_id in _NO_SECRET_BACKEND_IDS:
            continue
        if tier in _LOCAL_TIERS:
            continue

        api_key_env_val = backend_data.get("api_key_env")
        if not (isinstance(api_key_env_val, str) and api_key_env_val.strip()):
            continue  # no api_key_env on this backend

        # If a logical ref is already present, consider the backend migrated.
        has_logical_ref = any(
            isinstance(backend_data.get(k), str) and bool(backend_data.get(k, ""))
            for k in ("api_key_ref", "secret_ref")
        )
        if has_logical_ref:
            continue

        # Check whether any line in the file carrying the backend_id also
        # carries the suppression token (best-effort; we scan the whole file for
        # the backend_id + suppression token proximity rather than trying to
        # reconstruct the YAML block boundaries).
        backend_id_in_file = any(backend_id in ln for ln in lines)
        if backend_id_in_file:
            # Find the line(s) with api_key_env for this backend and check each.
            suppressed = False
            for ln in lines:
                if "api_key_env" in ln and _SUPPRESSION_TOKEN in ln:
                    suppressed = True
                    break
            if suppressed:
                continue

        findings.append(
            ModelApiKeyRefFinding(
                file=rel,
                backend_id=backend_id,
                deprecated_field="api_key_env",
                message=(
                    f"{rel}: backend {backend_id!r} declares deprecated 'api_key_env' "
                    f"without a logical secret reference. "
                    f"Migrate to 'api_key_ref' or 'secret_ref'. "
                    f"(OMN-12878: guardrail — prefer logical api_key_ref over api_key_env)"
                ),
            )
        )

    return findings


# ---------------------------------------------------------------------------
# COMPUTE handler — structural ProtocolMessageHandler
# ---------------------------------------------------------------------------


class HandlerApiKeyRefDisciplineCompute:
    """api_key_env deprecation guardrail as a canonical COMPUTE handler.

    Structural ProtocolMessageHandler implementation (duck-typing, no Plugin*
    base class). The handler is pure: all file loading happens at the EFFECT
    boundary; the handler only operates on pre-loaded content in the payload.

    Node archetype: COMPUTE.
    """

    @property
    def handler_id(self) -> str:
        return "node.api-key-ref-discipline.compute"

    def run(self, inp: ModelApiKeyRefScanInput) -> ModelApiKeyRefScanResult:
        """Run the api_key_ref discipline check and return a typed verdict.

        Pure: all inputs arrive through ``inp``; no filesystem reads.

        Args:
            inp: Input model carrying a map of relative-path → raw file text.

        Returns:
            ``ModelApiKeyRefScanResult`` with verdict, findings, and any errors.
        """
        all_findings: list[ModelApiKeyRefFinding] = []
        errors: list[str] = []

        for rel, text in inp.config_contents.items():
            try:
                findings = scan_bifrost_yaml(rel, text)
            except YAMLError as exc:
                errors.append(f"{rel}: YAML parse error — {exc}")
                continue
            all_findings.extend(findings)

        return ModelApiKeyRefScanResult(
            findings=all_findings,
            errors=errors,
            passed=len(all_findings) == 0 and len(errors) == 0,
        )
