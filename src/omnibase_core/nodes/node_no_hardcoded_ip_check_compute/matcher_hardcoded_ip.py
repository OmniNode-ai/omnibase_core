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

OMN-14713 hardened the octet grammar against two false-positive classes the
ported ``\\d{1,3}`` regex admitted: invalid octets (e.g. ``10.256.999.1`` and
``10.999.0.0`` matched despite octets exceeding 255) and RFC1918 literals
embedded in longer tokens (a digit- or letter-prefixed token such as
``210.0.0.x`` or ``x10.0.0.x`` matched its inner ``10.*`` substring). Each
octet is now bounded to ``0-255`` and the literal is anchored on
non-word/non-dot boundaries. This strictly *narrows* matches, so the
fail-closed gate keeps every real violation (all ``must_flag`` corpus cases
still fire).
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

# A single octet constrained to 0-255 (rejects invalid octets like 256/999 that
# a bare ``\d{1,3}`` would otherwise admit).
_OCTET: Final[str] = r"(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])"

_IP_PATTERN: Final[re.Pattern[str]] = re.compile(
    # Left boundary: the RFC1918 literal must not be preceded by a word char or
    # dot, so an embedded substring (a digit- or letter-prefixed token whose
    # tail happens to be a valid 10.* literal) is not flagged. The optional
    # scheme sits inside the boundary so an http(s):// prefixed literal still
    # matches.
    r"""(?<![\w.])"""
    r"""(?:https?://)?"""
    rf"""(?:192\.168\.{_OCTET}\.{_OCTET}"""
    rf"""|10\.{_OCTET}\.{_OCTET}\.{_OCTET}"""
    rf"""|172\.(?:1[6-9]|2[0-9]|3[01])\.{_OCTET}\.{_OCTET})"""
    r"""(?::\d+)?"""
    # Right boundary: reject trailing word chars/dots so a valid IP prefix of a
    # longer numeric token is not flagged.
    r"""(?![\w.])""",
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
