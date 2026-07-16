# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""AST visitor that detects ``*.utcnow`` attribute access.

Split out of ``handler.py`` (single-class-per-file, OMN-14656 remediation)
so the COMPUTE handler module contains exactly one class
(``NodeNoUtcnowCheckCompute``).

Port of ``UtcNowVisitor`` (``omniclaude/scripts/validation/validate_no_utcnow.py:28-60``).
Detects ``datetime.utcnow`` / ``datetime.datetime.utcnow`` / any other
``*.utcnow`` attribute access and produces one finding per hit.

CRITICAL fidelity requirement (per OMN-14656 Characterize spec): the oracle's
``UtcNowVisitor.visit_Attribute`` keys purely on ``node.attr == "utcnow"`` for
ANY ``ast.Attribute`` — it flags unrelated ``foo.utcnow`` / ``self.utcnow``
too (an intentional over-broad match in the CI gate), and it fires on bare
attribute *access*, not only on a call. This visitor reproduces that
over-broad match exactly rather than "improving" it by resolving the
receiver to ``datetime`` — a stricter matcher would diverge from the CI gate
and fail the shadow-compare. The em dash (U+2014) in every message is
literal, not a hyphen.
"""

from __future__ import annotations

import ast
from typing import Final

from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)

__all__ = ["VALIDATOR_ID", "UtcNowVisitor"]

# Canonical ModelValidationFinding.severity is Literal["PASS", "WARN", "FAIL",
# "ERROR", "SKIP", "NOT_APPLICABLE"] (uppercase) — this is the canonical
# outcome type's own spelling, used directly rather than through the
# (lowercase-valued) generated omnibase_core.enums.enum_validation_status.
_SEVERITY_FAIL: Final = "FAIL"

VALIDATOR_ID: Final[str] = "arch-no-utcnow"
_REMEDIATION: Final[str] = "use datetime.now(tz=timezone.utc) or datetime.now(UTC)"


class UtcNowVisitor(ast.NodeVisitor):
    """Walk an AST looking for ``*.utcnow`` attribute access."""

    def __init__(self, path: str) -> None:
        self._path = path
        self.findings: list[ModelValidationFinding] = []

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr == "utcnow":
            if isinstance(node.value, ast.Name) and node.value.id in (
                "datetime",
                "dt",
            ):
                message = (
                    f"{self._path}:{node.lineno}: "
                    f"use of {node.value.id}.utcnow() — use datetime.now(tz=timezone.utc) instead"
                )
            elif (
                isinstance(node.value, ast.Attribute) and node.value.attr == "datetime"
            ):
                message = (
                    f"{self._path}:{node.lineno}: "
                    f"use of datetime.datetime.utcnow() — "
                    f"use datetime.datetime.now(tz=timezone.utc) instead"
                )
            else:
                message = (
                    f"{self._path}:{node.lineno}: "
                    f"use of .utcnow() — use .now(tz=timezone.utc) instead"
                )
            self.findings.append(
                ModelValidationFinding(
                    validator_id=VALIDATOR_ID,
                    severity=_SEVERITY_FAIL,
                    location=f"{self._path}:{node.lineno}",
                    message=message,
                    remediation=_REMEDIATION,
                )
            )
        self.generic_visit(node)
