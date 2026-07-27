# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""AST visitor that detects direct Kafka producer client usage.

Split out of ``handler.py`` (single-class-per-file, OMN-14656 convention) so
the COMPUTE handler module contains exactly one class
(``NodeNoDirectKafkaProducerCheckCompute``).

Port of ``DirectKafkaVisitor`` + ``is_allowed_path``
(``omniclaude/scripts/validation/validate_no_direct_kafka_producer.py:32-99``).
Detects ``AIOKafkaProducer`` / ``KafkaProducer`` / ``confluent_kafka`` /
``aiokafka`` via ``import``, ``from ... import``, bare-name usage, and
attribute access (``kafka.KafkaProducer``) — except on files that are part of
the shared publisher layer (matched by filename or parent-directory
substring, exactly like the oracle).

Line-level suppression (OMN-14665): a finding is dropped when its reported
line carries the ``# onex-allow-kafka-producer`` marker. Findings are always
reported at the AST node's ``lineno`` — for a multi-line ``from ... import (``
that is the ``from`` line, which is exactly where the marker sits. This is the
additive, opt-in
per-line exemption the other WS8 arch gates already ship (``# di-ok`` for
raw-sqlite3, ``# onex-allow-internal-ip`` for hardcoded-ip, ``# fallback-ok``
for env-fallbacks). It is needed because the oracle's import check is a
*substring* match on the symbol name, so a legitimate symbol that merely
*contains* a forbidden token — e.g. the ``ProtocolKafkaProducerAio`` health-check
protocol type, or this very node's own ``NodeNoDirectKafkaProducerCheckCompute``
class — is a false positive that has no other escape hatch. A corpus line
without the marker is unaffected, so oracle message/flag parity is preserved.
"""

from __future__ import annotations

import ast
from pathlib import PurePosixPath
from typing import Final

from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)

__all__ = ["VALIDATOR_ID", "DirectKafkaProducerVisitor", "is_allowed_publisher_path"]

_SEVERITY_FAIL: Final = "FAIL"

VALIDATOR_ID: Final[str] = "arch-no-direct-kafka-producer"
_REMEDIATION: Final[str] = (
    "route through the shared publisher layer "
    "(emit_via_daemon() or the shared publisher abstraction) "
    "instead of instantiating a Kafka producer client directly"
)

# Forbidden direct Kafka producer symbols (oracle FORBIDDEN_SYMBOLS).
_FORBIDDEN_SYMBOLS: Final[tuple[str, ...]] = (
    "AIOKafkaProducer",
    "KafkaProducer",
    "confluent_kafka",
    "aiokafka",
)

# Per-line suppression marker (OMN-14665) — see module docstring.
_SUPPRESS_MARKER: Final[str] = "# onex-allow-kafka-producer"

# Modules that are allowed to use these symbols — the shared publisher layer
# (oracle ALLOWED_PATHS).
_ALLOWED_PATHS: Final[tuple[str, ...]] = (
    "publisher",
    "kafka_publisher_base",
    "kafka_producer_utils",
    "action_event_publisher",
    "embedded_publisher",
    "emit_client",
)


def is_allowed_publisher_path(path: str) -> bool:
    """Return True if ``path`` is part of the shared publisher layer.

    Checks only the filename and immediate parent directory name — not the
    full path — matching the oracle's ``is_allowed_path`` exactly (so pytest
    temporary directories don't cause false positives).
    """
    posix = PurePosixPath(path.replace("\\", "/"))
    name_lower = posix.name.lower()
    parent_lower = posix.parent.name.lower()
    for allowed in _ALLOWED_PATHS:
        if allowed in name_lower or allowed in parent_lower:
            return True
    return False


class DirectKafkaProducerVisitor(ast.NodeVisitor):
    """Walk an AST looking for direct Kafka producer client usage."""

    def __init__(self, path: str, source_lines: list[str] | None = None) -> None:
        self._path = path
        self._source_lines = source_lines or []
        self.findings: list[ModelValidationFinding] = []

    def _check_name(self, name: str, lineno: int, context: str) -> None:
        for sym in _FORBIDDEN_SYMBOLS:
            if sym in name:
                self._add_finding(
                    lineno,
                    f"{context} uses direct Kafka producer symbol '{sym}'",
                )
                return

    def _is_suppressed(self, lineno: int) -> bool:
        """True if the finding's reported line carries the
        ``# onex-allow-kafka-producer`` marker.

        Every finding is reported at its AST node's ``lineno``; for a multi-line
        ``from ... import (`` that is the ``from`` line, which is exactly where
        the marker is placed. Only that line is consulted — deliberately NOT the
        line above — so a marker can never leak onto an unrelated violation on
        the following line.
        """
        return (
            0 < lineno <= len(self._source_lines)
            and _SUPPRESS_MARKER in self._source_lines[lineno - 1]
        )

    def _add_finding(self, lineno: int, message: str) -> None:
        if self._is_suppressed(lineno):
            return
        self.findings.append(
            ModelValidationFinding(
                validator_id=VALIDATOR_ID,
                severity=_SEVERITY_FAIL,
                location=f"{self._path}:{lineno}",
                message=f"{self._path}:{lineno}: {message}",
                remediation=_REMEDIATION,
            )
        )

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._check_name(alias.name, node.lineno, f"import '{alias.name}'")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        self._check_name(module, node.lineno, f"from '{module}' import")
        for alias in node.names:
            self._check_name(alias.name, node.lineno, f"imported name '{alias.name}'")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        for sym in _FORBIDDEN_SYMBOLS:
            if node.id == sym:
                self._add_finding(
                    node.lineno, f"direct usage of Kafka producer symbol '{sym}'"
                )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Catch attribute access like `kafka.KafkaProducer` where the module
        # is imported as a bare name (e.g., `import kafka; kafka.KafkaProducer(...)`)
        if node.attr in _FORBIDDEN_SYMBOLS:
            self._add_finding(
                node.lineno,
                f"direct usage of Kafka producer symbol '{node.attr}' via attribute access",
            )
        self.generic_visit(node)
