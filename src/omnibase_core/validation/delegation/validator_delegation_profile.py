# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delegation runtime profile validator.

Rejects malformed profiles at parse time via two passes:
1. Pydantic schema validation (type errors, required fields, min_length)
2. Custom semantic rules (no raw URLs/IPs in ref fields, token limit consistency)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

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
