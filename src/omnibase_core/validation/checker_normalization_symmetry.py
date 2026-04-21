# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Checker for producer/consumer topic-normalization symmetry (OMN-9333).

Detects the OMN-9215 class of bug: a producer emits ``TopicBase.X.strip()``
while a consumer subscribes to the raw ``TopicBase.X`` (or vice versa). Unit
tests on each side pass independently, but the dispatcher key drift only
surfaces at runtime.

Scope (minimum viable — Option A):
    * ``.strip()`` asymmetry on ``TopicBase.X`` arguments to producer/consumer
      call patterns.

Producer patterns (anything matches = producer use):
    * ``<any>.send(topic_expr, ...)``
    * ``<any>.produce(topic_expr, ...)``
    * ``<any>.publish(topic_expr, ...)``
    * ``<any>.emit(topic_expr, ...)``

Consumer patterns (anything matches = consumer use):
    * ``<any>.subscribe([topic_expr, ...])``
    * ``<any>.subscribe(topic_expr, ...)``
    * ``<any>.lookup(topic_expr, ...)``
    * ``handler_for(topic_expr)`` decorator / call

Follow-ups filed:
    * OMN-9339 Pydantic schema field-set symmetry
    * OMN-9340 casefold/lower/upper symmetry
    * OMN-9341 contract-YAML-driven topic discovery

IMPORT ORDER CONSTRAINTS (Critical — Do Not Break):
    * Standard library only — this module runs as a pre-commit hook without
      project dependencies installed.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

_PRODUCER_METHODS: frozenset[str] = frozenset({"send", "produce", "publish", "emit"})
_CONSUMER_METHODS: frozenset[str] = frozenset({"subscribe", "lookup"})
_CONSUMER_FREE_FUNCTIONS: frozenset[str] = frozenset({"handler_for"})
_TOPIC_BASE_NAME = "TopicBase"

Role = Literal["producer", "consumer"]


@dataclass(frozen=True)
class TopicUse:
    """A single producer- or consumer-side use of a TopicBase member."""

    file_path: str
    line_number: int
    role: Role
    topic_name: str
    normalizations: tuple[str, ...]


@dataclass(frozen=True)
class SymmetryIssue:
    """Normalization asymmetry found between producer and consumer sites."""

    topic_name: str
    producer_file: str
    producer_line: int
    producer_normalizations: tuple[str, ...]
    consumer_file: str
    consumer_line: int
    consumer_normalizations: tuple[str, ...]

    @property
    def message(self) -> str:
        prod = ", ".join(self.producer_normalizations) or "(none)"
        cons = ", ".join(self.consumer_normalizations) or "(none)"
        return (
            f"Normalization asymmetry on TopicBase.{self.topic_name}: "
            f"producer applies [{prod}] at {self.producer_file}:"
            f"{self.producer_line}, consumer applies [{cons}] at "
            f"{self.consumer_file}:{self.consumer_line}. "
            "Normalization must match on both sides."
        )


class NormalizationSymmetryChecker(ast.NodeVisitor):
    """ast.NodeVisitor that records TopicBase producer/consumer uses.

    For each call-site that takes a ``TopicBase.X`` expression as its topic
    argument, records the role (producer vs consumer) and the chain of
    ``.strip()`` / similar normalization methods applied to the topic before
    the call.

    Also tracks single-line local-name bindings of the form
    ``topic = TopicBase.X.strip()`` and resolves them at call sites where
    the first argument is a bare Name. This handles the common OMN-9215
    producer pattern of extracting the topic expression to a local before
    ``.send(topic, payload)``.
    """

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.topic_uses: list[TopicUse] = []
        self._name_bindings: dict[str, tuple[str, tuple[str, ...]]] = {}

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Isolate name bindings per function scope so a topic binding from one
        # function cannot be incorrectly resolved in a sibling function.
        saved = self._name_bindings
        self._name_bindings = {}
        self.generic_visit(node)
        self._name_bindings = saved

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]  # NOTE(OMN-9333): alias assignment — async variant shares sync visitor; mypy flags method-vs-function type mismatch  # noqa: N815

    def visit_Assign(self, node: ast.Assign) -> None:
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            topic_name, normalizations = self._extract_topic_use(node.value)
            if topic_name is not None:
                self._name_bindings[node.targets[0].id] = (topic_name, normalizations)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self._record_call(node)
        self.generic_visit(node)

    def _record_call(self, node: ast.Call) -> None:
        role = self._classify_call(node)
        if role is None:
            return

        for arg in self._topic_arg_candidates(node):
            topic_name, normalizations = self._extract_topic_use(arg)
            if topic_name is None and isinstance(arg, ast.Name):
                bound = self._name_bindings.get(arg.id)
                if bound is not None:
                    topic_name, normalizations = bound
            if topic_name is None:
                continue
            self.topic_uses.append(
                TopicUse(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    role=role,
                    topic_name=topic_name,
                    normalizations=normalizations,
                )
            )

    @staticmethod
    def _classify_call(node: ast.Call) -> Role | None:
        func = node.func
        if isinstance(func, ast.Attribute):
            attr = func.attr
            if attr in _PRODUCER_METHODS:
                return "producer"
            if attr in _CONSUMER_METHODS:
                return "consumer"
        elif isinstance(func, ast.Name):
            if func.id in _CONSUMER_FREE_FUNCTIONS:
                return "consumer"
        return None

    @staticmethod
    def _topic_arg_candidates(node: ast.Call) -> Iterable[ast.expr]:
        """Yield argument expressions that could be a topic reference.

        Producer convention: first positional arg is the topic.
        Consumer ``.subscribe([...])`` convention: first positional arg may be
        a list/tuple of topics. Both shapes are normalized here.
        """
        if not node.args:
            return
        first = node.args[0]
        if isinstance(first, (ast.List, ast.Tuple)):
            yield from first.elts
        else:
            yield first

    @staticmethod
    def _extract_topic_use(expr: ast.expr) -> tuple[str | None, tuple[str, ...]]:
        """Return (topic_member_name, normalizations) or (None, ()) if not a topic ref.

        Walks outward from a TopicBase.X attribute access through any chained
        no-arg method calls (``.strip()``, etc.) to collect the normalization
        chain applied before the topic is passed as an argument.
        """
        normalizations: list[str] = []
        current = expr
        while (
            isinstance(current, ast.Call) and not current.args and not current.keywords
        ):
            inner_func = current.func
            if not isinstance(inner_func, ast.Attribute):
                return None, ()
            normalizations.append(inner_func.attr)
            current = inner_func.value

        if isinstance(current, ast.Attribute) and isinstance(current.value, ast.Name):
            if current.value.id == _TOPIC_BASE_NAME:
                return current.attr, tuple(reversed(normalizations))

        return None, ()


def scan_source_tree(root: Path) -> list[SymmetryIssue]:
    """Scan *root* recursively and return normalization-asymmetry findings.

    Collects every producer/consumer TopicBase use across all Python files
    under *root*, then groups by topic member name. If a topic has at least
    one producer AND one consumer site whose normalization chains differ, a
    ``SymmetryIssue`` is emitted pairing the first divergent sites.
    """
    all_uses: list[TopicUse] = []
    for path in sorted(root.rglob("*.py")):
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        checker = NormalizationSymmetryChecker(str(path))
        checker.visit(tree)
        all_uses.extend(checker.topic_uses)

    by_topic: dict[str, list[TopicUse]] = {}
    for use in all_uses:
        by_topic.setdefault(use.topic_name, []).append(use)

    issues: list[SymmetryIssue] = []
    for topic_name, uses in by_topic.items():
        producers = [u for u in uses if u.role == "producer"]
        consumers = [u for u in uses if u.role == "consumer"]
        if not producers or not consumers:
            continue

        producer_chains = {u.normalizations for u in producers}
        consumer_chains = {u.normalizations for u in consumers}

        if producer_chains == consumer_chains:
            continue

        # Find representative divergent producer/consumer pair: pick the first
        # producer whose normalization chain differs from any consumer's chain.
        divergent_producer = next(
            (p for p in producers if p.normalizations not in consumer_chains),
            producers[0],
        )
        divergent_consumer = next(
            (c for c in consumers if c.normalizations not in producer_chains),
            consumers[0],
        )
        issues.append(
            SymmetryIssue(
                topic_name=topic_name,
                producer_file=divergent_producer.file_path,
                producer_line=divergent_producer.line_number,
                producer_normalizations=divergent_producer.normalizations,
                consumer_file=divergent_consumer.file_path,
                consumer_line=divergent_consumer.line_number,
                consumer_normalizations=divergent_consumer.normalizations,
            )
        )

    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="checker-normalization-symmetry",
        description=(
            "Verify producer/consumer topic-normalization symmetry for the ONEX "
            "event bus. Fails on OMN-9215-class asymmetries (e.g. producer "
            "strips whitespace, consumer does not)."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["src"],
        help="Directories to scan recursively for .py files (default: src)",
    )
    args = parser.parse_args(argv)

    all_issues: list[SymmetryIssue] = []
    for path_str in args.paths:
        root = Path(path_str)
        if not root.exists():
            continue
        all_issues.extend(scan_source_tree(root))

    if not all_issues:
        return 0

    for issue in all_issues:
        sys.stderr.write(issue.message + "\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
