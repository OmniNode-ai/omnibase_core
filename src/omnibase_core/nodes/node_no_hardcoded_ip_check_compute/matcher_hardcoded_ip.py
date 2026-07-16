# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Line-based matcher that detects hardcoded internal IP addresses.

Split out of ``handler.py`` (single-class-per-file convention established by
``node_no_utcnow_check_compute``, OMN-14656) — this module has no classes at
all since the port is a per-line regex match, not an AST walk.

Port of the module-level regex + scan loop in
``omniclaude/scripts/validation/validate_no_hardcoded_ip.py``. Detects RFC1918
internal IP literals (``192.168.x.x``, ``10.x.x.x``, ``172.16-31.x.x``),
optionally prefixed with ``http(s)://`` and suffixed with ``:port``, on any
line that does not carry the ``# onex-allow-internal-ip`` suppression marker.
"""

from __future__ import annotations

import re
from typing import Final

from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)

__all__ = ["VALIDATOR_ID", "find_hardcoded_ip_violations"]

VALIDATOR_ID: Final[str] = "arch-no-hardcoded-ip"
_REMEDIATION: Final[str] = (
    "configure the endpoint via an environment variable instead of a "
    "hardcoded internal IP; suppress with # onex-allow-internal-ip if justified"
)

# Suppression marker: lines containing this comment are exempt.
_SUPPRESS_MARKER: Final[str] = "onex-allow-internal-ip"

_IP_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"""(?:https?://)?"""
    r"""(?:192\.168\.\d{1,3}\.\d{1,3}"""
    r"""|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"""
    r"""|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})"""
    r"""(?::\d+)?""",
)


def find_hardcoded_ip_violations(
    path: str, source: str
) -> list[ModelValidationFinding]:
    """Port of the per-file scan loop (validate_no_hardcoded_ip.py:49-57)."""
    findings: list[ModelValidationFinding] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        if _IP_PATTERN.search(line) and _SUPPRESS_MARKER not in line:
            findings.append(
                ModelValidationFinding(
                    validator_id=VALIDATOR_ID,
                    severity="FAIL",
                    location=f"{path}:{lineno}",
                    message=f"{path}:{lineno}: {line.strip()}",
                    remediation=_REMEDIATION,
                )
            )
    return findings
