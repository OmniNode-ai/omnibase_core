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

    def __init__(self, path: str) -> None:
        self._path = path
        self.findings: list[ModelValidationFinding] = []

    def _check_name(self, name: str, lineno: int, context: str) -> None:
        for sym in _FORBIDDEN_SYMBOLS:
            if sym in name:
                self._add_finding(
                    lineno,
                    f"{context} uses direct Kafka producer symbol '{sym}'",
                )
                return

    def _add_finding(self, lineno: int, message: str) -> None:
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
