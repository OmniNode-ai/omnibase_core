# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Block Plugin* classes from owning daemon, service, or worker lifecycles.

Canonical COMPUTE handler for the no-plugin-daemon-classes gate (OMN-13309).

This module ships three surfaces:

1. **Pure validation helpers** (``validate_paths`` / ``validate_file`` /
   ``validate_source``) — pure functions, no I/O beyond reading the files
   listed by the caller.  These are the deterministic core that every entry-
   point delegates to.

2. **COMPUTE handler** (``HandlerNoPluginDaemonClasses``) — implements
   ``ProtocolMessageHandler`` with ``node_kind = EnumNodeKind.COMPUTE``.
   Accepts a ``ModelNoPluginDaemonInput`` payload and returns a
   ``ModelHandlerOutput[ModelNoPluginDaemonResult]``.  File contents are
   supplied by the caller (EFFECT boundary); the handler itself performs no
   filesystem I/O.

3. **CLI entry-point** (``main``) — thin wrapper for the pre-commit hook;
   reads files from ``sys.argv``, delegates to ``validate_paths``, exits
   non-zero on findings.

Architecture:
    Node kind:   COMPUTE (pure, deterministic, no I/O inside the handler)
    Message cat: COMMAND (a validation request is a one-shot command)
    Ticket:      OMN-13309 (W9 — Validator Standardization Remediation)

Pydantic models live in omnibase_core.validation.model_no_plugin_daemon_classes
(the validation/ directory carries a legacy mypy override that allows
Pydantic's generic BaseModel; the validators/ directory requires strict
explicit-any enforcement).
"""

from __future__ import annotations

__all__ = [
    "LIFECYCLE_TERMS",
    "COMPUTE_PLUGIN_BASE",
    "HandlerNoPluginDaemonClasses",
    "validate_paths",
    "validate_file",
    "validate_source",
    "main",
    # Re-exported for convenience
    "ModelNoPluginDaemonFinding",
    "ModelNoPluginDaemonInput",
    "ModelNoPluginDaemonResult",
]

import argparse
import ast
import sys
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.validation.model_no_plugin_daemon_classes import (
    ModelNoPluginDaemonFinding,
    ModelNoPluginDaemonInput,
    ModelNoPluginDaemonResult,
)

if TYPE_CHECKING:
    from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope

LIFECYCLE_TERMS: frozenset[str] = frozenset(
    (
        "Daemon",
        "Service",
        "Worker",
        "Runtime",
        "Consumer",
        "Publisher",
        "Controller",
        "Server",
        "Client",
    )
)
COMPUTE_PLUGIN_BASE: str = "PluginComputeBase"


# ---------------------------------------------------------------------------
# Pure validation helpers (no I/O, called by both the handler and the CLI)
# ---------------------------------------------------------------------------


def validate_paths(paths: Sequence[Path]) -> list[ModelNoPluginDaemonFinding]:
    """Validate Python files under the provided paths.

    Reads each file from disk — **this is the I/O boundary**.  Use
    ``validate_source`` inside the COMPUTE handler (which receives
    pre-read source text).
    """
    findings: list[ModelNoPluginDaemonFinding] = []
    for path in _iter_python_files(paths):
        findings.extend(validate_file(path))
    return findings


def validate_file(path: Path) -> list[ModelNoPluginDaemonFinding]:
    """Read and validate one Python file."""
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return [
            ModelNoPluginDaemonFinding(
                path=str(path),
                line=1,
                column=0,
                class_name="<parse-error>",
                bases=(),
                reason=f"could not decode as UTF-8: {exc}",
            )
        ]
    return validate_source(str(path), source)


def validate_source(path_label: str, source: str) -> list[ModelNoPluginDaemonFinding]:
    """Validate pre-read source text.

    This function is pure (no I/O) and is the function called from inside
    the COMPUTE handler.
    """
    try:
        tree = ast.parse(source, filename=path_label)
    except SyntaxError as exc:
        return [
            ModelNoPluginDaemonFinding(
                path=path_label,
                line=exc.lineno or 1,
                column=exc.offset or 0,
                class_name="<syntax-error>",
                bases=(),
                reason=exc.msg,
            )
        ]

    findings: list[ModelNoPluginDaemonFinding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            finding = _validate_class(path_label, node)
            if finding is not None:
                findings.append(finding)
    return findings


# ---------------------------------------------------------------------------
# Internal AST helpers
# ---------------------------------------------------------------------------


def _validate_class(
    path_label: str, node: ast.ClassDef
) -> ModelNoPluginDaemonFinding | None:
    if not node.name.startswith("Plugin"):
        return None

    base_names = tuple(
        name for base in node.bases if (name := _qualified_expr_name(base)) is not None
    )
    if _is_compute_base_definition(path_label, node):
        return None
    if _is_direct_compute_plugin(base_names):
        return None

    reason = _lifecycle_reason(node.name, base_names)
    if reason is None:
        return None

    return ModelNoPluginDaemonFinding(
        path=path_label,
        line=node.lineno,
        column=node.col_offset,
        class_name=node.name,
        bases=base_names,
        reason=reason,
    )


def _is_compute_base_definition(path_label: str, node: ast.ClassDef) -> bool:
    """Allow the PluginComputeBase definition itself."""
    return (
        node.name == COMPUTE_PLUGIN_BASE
        and Path(path_label).name == "plugin_compute_base.py"
    )


def _is_direct_compute_plugin(base_names: Iterable[str]) -> bool:
    """Allow Plugin* subclassing PluginComputeBase directly (legacy compute)."""
    names = tuple(base_names)
    return bool(names) and all(
        _simple_name(base) == COMPUTE_PLUGIN_BASE for base in names
    )


def _lifecycle_reason(class_name: str, base_names: Sequence[str]) -> str | None:
    class_term = _matching_lifecycle_term(class_name)
    if class_term is not None:
        return f"class name contains {class_term}"

    for base in base_names:
        base_term = _matching_lifecycle_term(base)
        if base_term is not None:
            return f"base class {base} contains {base_term}"
    return None


def _matching_lifecycle_term(value: str) -> str | None:
    value_lower = value.lower()
    for term in sorted(LIFECYCLE_TERMS):
        if term.lower() in value_lower:
            return term
    return None


def _qualified_expr_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _qualified_expr_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Subscript):
        return _qualified_expr_name(node.value)
    if isinstance(node, ast.Call):
        return _qualified_expr_name(node.func)
    return None


def _simple_name(value: str) -> str:
    return value.rsplit(".", maxsplit=1)[-1]


def _iter_python_files(paths: Sequence[Path]) -> Iterator[Path]:
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            yield path
        elif path.is_dir():
            yield from sorted(
                candidate
                for candidate in path.rglob("*.py")
                if "__pycache__" not in candidate.parts
            )


# ---------------------------------------------------------------------------
# COMPUTE handler — implements ProtocolMessageHandler
# ---------------------------------------------------------------------------


class HandlerNoPluginDaemonClasses:
    """COMPUTE handler: validate Python files for banned Plugin* lifecycle classes.

    Implements ``ProtocolMessageHandler``.  Node kind is ``COMPUTE``; message
    category is ``COMMAND`` (a one-shot validation request).

    The handler is **pure** — all I/O happens outside it.  The caller (an
    EFFECT ingress boundary) reads file content and places it in
    ``ModelNoPluginDaemonInput.files`` before dispatching the envelope.

    Example::

        from omnibase_core.validators.no_plugin_daemon_classes import (
            HandlerNoPluginDaemonClasses,
            ModelNoPluginDaemonInput,
        )
        from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
        from uuid import uuid4

        handler = HandlerNoPluginDaemonClasses()
        payload = ModelNoPluginDaemonInput(
            files=(("src/foo.py", "class PluginWorker: ..."),)
        )
        envelope = ModelEventEnvelope(payload=payload, correlation_id=uuid4())
        import asyncio
        output = asyncio.run(handler.handle(envelope))
        assert output.result is not None
        assert not output.result.is_clean  # violation found
    """

    HANDLER_ID: str = "no-plugin-daemon-classes"

    @property
    def handler_id(self) -> str:
        return self.HANDLER_ID

    @property
    def category(self) -> EnumMessageCategory:
        return EnumMessageCategory.COMMAND

    @property
    def message_types(self) -> set[str]:
        return {"ModelNoPluginDaemonInput"}

    @property
    def node_kind(self) -> EnumNodeKind:
        return EnumNodeKind.COMPUTE

    async def handle(
        self,
        envelope: ModelEventEnvelope[ModelNoPluginDaemonInput],
    ) -> ModelHandlerOutput[ModelNoPluginDaemonResult]:
        """Run the no-plugin-daemon validation over the supplied file contents.

        Args:
            envelope: Envelope whose ``payload`` must be a
                ``ModelNoPluginDaemonInput`` (or a dict coercible to it).

        Returns:
            ``ModelHandlerOutput.for_compute`` with a
            ``ModelNoPluginDaemonResult`` result.
        """
        correlation_id: UUID = (
            envelope.correlation_id if envelope.correlation_id is not None else uuid4()
        )
        input_envelope_id: UUID = envelope.envelope_id

        payload: ModelNoPluginDaemonInput = envelope.payload

        all_findings: list[ModelNoPluginDaemonFinding] = []
        for path_label, source_text in payload.files:
            all_findings.extend(validate_source(path_label, source_text))

        result = ModelNoPluginDaemonResult(findings=tuple(all_findings))
        return ModelHandlerOutput.for_compute(
            input_envelope_id=input_envelope_id,
            correlation_id=correlation_id,
            handler_id=self.HANDLER_ID,
            result=result,
        )


# ---------------------------------------------------------------------------
# CLI entry-point (pre-commit hook)
# ---------------------------------------------------------------------------


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Block Plugin* classes from owning daemon, service, worker, runtime, "
            "consumer, publisher, server, controller, or client lifecycles."
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Python file or directory paths to scan (passed by pre-commit).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry-point used by the pre-commit hook."""
    args = _parse_args(sys.argv[1:] if argv is None else list(argv))
    paths: list[Path] = list(args.paths)
    if not paths:
        return 0

    findings = validate_paths(paths)
    if not findings:
        return 0

    sys.stderr.write("Plugin lifecycle class guard failed:\n")
    for finding in findings:
        sys.stderr.write(f"  {finding.format()}\n")
    sys.stderr.write(
        "\nPlugin* classes may only represent deterministic compute plugins. "
        "Put daemon, service, worker, runtime, publisher, consumer, client, "
        "controller, or server lifecycles behind ONEX nodes/handlers instead.\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
