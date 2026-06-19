# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delegation runtime profile validator.

Rejects malformed profiles at parse time via two passes:
1. Pydantic schema validation (type errors, required fields, min_length)
2. Custom semantic rules (no raw URLs/IPs in ref fields, token limit consistency)

Wired as a pre-commit hook (OMN-13306, W6b) via the ``check-delegation-profile``
hook ID in omnibase_core/.pre-commit-hooks.yaml.

CLI Usage (pre-commit hook):
    python -m omnibase_core.validation.delegation.validator_delegation_profile <file1.yaml> ...

CLI Usage (CI):
    python -m omnibase_core.validation.delegation.validator_delegation_profile \\
        --all --root .
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from omnibase_core.models.contracts.model_delegation_runtime_profile import (
    ModelDelegationRuntimeProfile,
)

__all__ = ["ValidationResult", "validate_delegation_profile"]

_URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)
_IP_PATTERN = re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)


def _looks_like_endpoint(value: str) -> bool:
    return bool(_URL_PATTERN.search(value) or _IP_PATTERN.search(value))


def _check_llm_backends(
    profile: ModelDelegationRuntimeProfile,
    errors: list[str],
) -> None:
    for backend_name, backend in profile.llm_backends.items():
        if _looks_like_endpoint(backend.bifrost_endpoint_ref):
            errors.append(
                f"llm_backends[{backend_name!r}].bifrost_endpoint_ref must be a "
                f"symbolic ref, not a raw URL or IP address: "
                f"{backend.bifrost_endpoint_ref!r}"
            )
        if backend.max_tokens_hard_limit < backend.max_tokens_default:
            errors.append(
                f"llm_backends[{backend_name!r}].max_tokens_hard_limit "
                f"({backend.max_tokens_hard_limit}) must be >= max_tokens_default "
                f"({backend.max_tokens_default})"
            )


def _check_event_bus(
    profile: ModelDelegationRuntimeProfile,
    errors: list[str],
) -> None:
    for server in profile.event_bus.bootstrap_servers:
        if _URL_PATTERN.search(server):
            errors.append(
                f"event_bus.bootstrap_servers entry must not be a URL "
                f"(use host:port form): {server!r}"
            )


def validate_delegation_profile(data: Any) -> ValidationResult:
    """Validate a delegation runtime profile dict.

    Returns a ValidationResult with is_valid=False and populated errors on any
    schema or semantic violation. Never raises.
    """
    try:
        profile = ModelDelegationRuntimeProfile.model_validate(data)
    except ValidationError as exc:
        return ValidationResult(
            is_valid=False,
            errors=[str(e["msg"]) for e in exc.errors()],
        )
    except Exception as exc:  # noqa: BLE001  # fallback-ok: validator contract — never raises, captures all errors into result
        return ValidationResult(is_valid=False, errors=[str(exc)])

    errors: list[str] = []
    _check_llm_backends(profile, errors)
    _check_event_bus(profile, errors)

    return ValidationResult(is_valid=not errors, errors=errors)


# ---------------------------------------------------------------------------
# CLI entry-point — pre-commit hook (OMN-13306, W6b)
# ---------------------------------------------------------------------------


def _validate_file(path: Path) -> list[str]:
    """Load and validate one YAML file; return list of error strings."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{path}: cannot read: {exc}"]
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return [f"{path}: YAML parse error: {exc}"]
    result = validate_delegation_profile(data)
    return [f"{path}: {err}" for err in result.errors]


def main(argv: list[str] | None = None) -> int:
    """CLI entry-point for pre-commit hook and CI use.

    Pre-commit mode (pass_filenames: true):
        python -m omnibase_core.validation.delegation.validator_delegation_profile file1.yaml ...

    CI scan mode:
        python -m omnibase_core.validation.delegation.validator_delegation_profile \\
            --all --root <repo-root>
    """

    parser = argparse.ArgumentParser(
        description="Delegation runtime profile validator (OMN-13306)"
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="YAML profile files to validate (pre-commit mode).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="scan_all",
        help="Scan all *.yaml files under --root matching delegation profile patterns.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root for --all scan.",
    )
    args = parser.parse_args(argv)

    paths: list[Path] = []
    if args.files:
        paths = [Path(f) for f in args.files]
    elif args.scan_all:
        root = Path(args.root)
        # Scan for YAML files that look like delegation runtime profiles.
        paths = [
            p
            for p in root.rglob("*.yaml")
            if "delegation" in p.name
            and "runtime_profile" in p.name
            and "__pycache__" not in str(p)
            and ".venv" not in str(p)
        ]
    else:
        # Nothing to validate — no error.
        return 0

    all_errors: list[str] = []
    for path in paths:
        all_errors.extend(_validate_file(path))

    for err in all_errors:
        print(f"[delegation-profile] ERROR: {err}", file=sys.stderr)

    if all_errors:
        print(
            f"[delegation-profile] FAIL — {len(all_errors)} error(s) in "
            f"{len(paths)} file(s). Fix: ensure all bifrost_endpoint_ref values "
            "are symbolic refs (not raw URLs/IPs), max_tokens_hard_limit >= "
            "max_tokens_default, and bootstrap_servers use host:port form.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
