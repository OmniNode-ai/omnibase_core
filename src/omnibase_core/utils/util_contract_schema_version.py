# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Shared validation for ticket-contract schema versions."""

from __future__ import annotations

import re

_SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def validate_contract_schema_version(value: str) -> str:
    """Validate the basic SemVer form used by ``ModelTicketContract``."""
    if not _SEMVER_PATTERN.match(value):
        raise ValueError(  # error-ok: Pydantic must wrap this in ValidationError.
            f"schema_version: invalid SemVer format {value!r}. "
            "Expected major.minor.patch (e.g., '1.0.0'). "
            "Pre-release suffixes and build metadata are not supported."
        )
    return value
