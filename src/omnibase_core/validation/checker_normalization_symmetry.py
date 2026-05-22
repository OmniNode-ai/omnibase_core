# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Checker for producer/consumer topic-normalization symmetry (OMN-9333).

Detects the OMN-9215 class of bug: a producer emits ``TopicBase.X.strip()``
while a consumer subscribes to the raw ``TopicBase.X`` (or vice versa). Unit
tests on each side pass independently, but the dispatcher key drift only
surfaces at runtime.

Scope:
    * ``.strip()`` / ``.lower()`` / ``.upper()`` / ``.casefold()`` asymmetry
      on ``TopicBase.X`` arguments to producer/consumer call patterns.
    * Pydantic schema field-set asymmetry between statically discoverable
      producer/consumer models for the same topic.

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

Follow-up filed:
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
_NORMALIZATION_METHODS: frozenset[str] = frozenset(
    {"strip", "lstrip", "rstrip", "lower", "upper", "casefold"}
)
_TOPIC_BASE_NAME = "TopicBase"

Role = Literal["producer", "consumer"]


@dataclass(frozen=True)
class SourceModule:
    """Parsed Python source file plus importable module-name candidates."""

    path: Path
    module_names: frozenset[str]
    tree: ast.Module


@dataclass(frozen=True)
class ModelAlias:
    """Local AST reference to a Pydantic model class."""

    module_name: str | None
    model_name: str


@dataclass(frozen=True)
class ModelPydanticSchema:
    """Static field-set schema for a Pydantic BaseModel class."""

    model_name: str
    file_path: str
    line_number: int
    fields: frozenset[str]
    module_names: frozenset[str]


@dataclass(frozen=True)
class ModelRegistry:
    """Lookup table for statically discovered Pydantic model schemas."""

    by_name: dict[str, tuple[ModelPydanticSchema, ...]]
    by_qualified_name: dict[tuple[str, str], ModelPydanticSchema]

    def resolve(
        self, alias: ModelAlias, current_module_names: frozenset[str]
    ) -> ModelPydanticSchema | None:
        """Resolve an imported/local model alias to its static schema."""
        if alias.module_name is not None:
            schema = self.by_qualified_name.get((alias.module_name, alias.model_name))
            if schema is not None:
                return schema

        for module_name in current_module_names:
            schema = self.by_qualified_name.get((module_name, alias.model_name))
            if schema is not None:
                return schema

        candidates = self.by_name.get(alias.model_name, ())
        if len(candidates) == 1:
            return candidates[0]
        return None


@dataclass(frozen=True)
class TopicUse:
    """A single producer- or consumer-side use of a TopicBase member."""

    file_path: str
    line_number: int
    role: Role
    topic_name: str
    normalizations: tuple[str, ...]
    model_schema: ModelPydanticSchema | None = None


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
            f"Normalization transform asymmetry on TopicBase.{self.topic_name}: "
            f"producer applies [{prod}] at {self.producer_file}:"
            f"{self.producer_line}, consumer applies [{cons}] at "
            f"{self.consumer_file}:{self.consumer_line}. "
            "Normalization must match on both sides."
        )


@dataclass(frozen=True)
class ModelSchemaSymmetryIssue:
    """Pydantic producer/consumer schema field-set asymmetry."""

    topic_name: str
    producer_file: str
    producer_line: int
    producer_model: str
    producer_fields: frozenset[str]
    consumer_file: str
    consumer_line: int
    consumer_model: str
    consumer_fields: frozenset[str]

    @property
    def message(self) -> str:
        missing_from_consumer = sorted(self.producer_fields - self.consumer_fields)
        extra_in_consumer = sorted(self.consumer_fields - self.producer_fields)
        missing = ", ".join(missing_from_consumer) or "(none)"
        extra = ", ".join(extra_in_consumer) or "(none)"
        return (
            f"Pydantic schema field-set asymmetry on TopicBase.{self.topic_name}: "
            f"producer model {self.producer_model} at {self.producer_file}:"
            f"{self.producer_line}, consumer model {self.consumer_model} at "
            f"{self.consumer_file}:{self.consumer_line}. "
            f"Missing from consumer: [{missing}]. "
            f"Extra in consumer: [{extra}]."
        )


type SymmetryFinding = SymmetryIssue | ModelSchemaSymmetryIssue


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

    def __init__(
        self,
        file_path: str,
        *,
        module_names: frozenset[str] | None = None,
        model_registry: ModelRegistry | None = None,
    ) -> None:
        self.file_path = file_path
        self.module_names = module_names or frozenset()
        self.model_registry = model_registry
        self.topic_uses: list[TopicUse] = []
        self._name_bindings: dict[str, tuple[str, tuple[str, ...]]] = {}
        self._model_name_bindings: dict[str, ModelAlias] = {}
        self._model_aliases: dict[str, ModelAlias] = {}
        self._module_aliases: dict[str, str] = {}

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Isolate name bindings per function scope so a topic binding from one
        # function cannot be incorrectly resolved in a sibling function.
        saved_topics = self._name_bindings
        saved_models = self._model_name_bindings
        self._name_bindings = {}
        self._model_name_bindings = {}
        self.generic_visit(node)
        self._name_bindings = saved_topics
        self._model_name_bindings = saved_models

    # Why: Runtime compatibility requires assigning through a broader static type.
    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]  # NOTE(OMN-9333): alias assignment — async variant shares sync visitor; mypy flags method-vs-function type mismatch  # noqa: N815

    def visit_Assign(self, node: ast.Assign) -> None:
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target_name = node.targets[0].id
            topic_name, normalizations = self._extract_topic_use(node.value)
            if topic_name is not None:
                self._name_bindings[target_name] = (topic_name, normalizations)
            model_alias = self._extract_model_alias(node.value)
            if model_alias is not None:
                self._model_name_bindings[target_name] = model_alias
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            local_name = alias.asname or alias.name.split(".")[0]
            self._module_aliases[local_name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module is None:
            self.generic_visit(node)
            return
        for alias in node.names:
            local_name = alias.asname or alias.name
            self._model_aliases[local_name] = ModelAlias(
                module_name=node.module,
                model_name=alias.name,
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self._record_call(node)
        self.generic_visit(node)

    def _record_call(self, node: ast.Call) -> None:
        role = self._classify_call(node)
        if role is None:
            return

        model_schema = self._extract_model_schema_from_call(node)
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
                    model_schema=model_schema,
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
            if inner_func.attr not in _NORMALIZATION_METHODS:
                return None, ()
            normalizations.append(inner_func.attr)
            current = inner_func.value

        if isinstance(current, ast.Attribute) and isinstance(current.value, ast.Name):
            if current.value.id == _TOPIC_BASE_NAME:
                return current.attr, tuple(reversed(normalizations))

        return None, ()

    def _extract_model_schema_from_call(
        self, node: ast.Call
    ) -> ModelPydanticSchema | None:
        if self.model_registry is None:
            return None
        for candidate in self._model_arg_candidates(node):
            if isinstance(candidate, ast.Name):
                model_alias = self._model_name_bindings.get(candidate.id)
                if model_alias is None:
                    model_alias = self._extract_model_alias(candidate)
            else:
                model_alias = self._extract_model_alias(candidate)
            if model_alias is None:
                continue
            schema = self.model_registry.resolve(model_alias, self.module_names)
            if schema is not None:
                return schema
        return None

    @staticmethod
    def _model_arg_candidates(node: ast.Call) -> Iterable[ast.expr]:
        positional_start = 1
        yield from node.args[positional_start:]
        for keyword in node.keywords:
            if keyword.arg in {
                "event_model",
                "model",
                "payload_model",
                "payload_type",
                "schema",
            }:
                yield keyword.value

    def _extract_model_alias(self, expr: ast.expr) -> ModelAlias | None:
        if isinstance(expr, ast.Call):
            return self._extract_model_alias(expr.func)

        if isinstance(expr, ast.Name):
            alias = self._model_aliases.get(expr.id)
            if alias is not None:
                return alias
            return ModelAlias(module_name=None, model_name=expr.id)

        if isinstance(expr, ast.Attribute):
            if isinstance(expr.value, ast.Name):
                module_name = self._module_aliases.get(expr.value.id)
                return ModelAlias(module_name=module_name, model_name=expr.attr)
            return ModelAlias(module_name=None, model_name=expr.attr)

        return None


class ModelPydanticCollector(ast.NodeVisitor):
    """Collect statically declared Pydantic model class field sets."""

    def __init__(self, source_module: SourceModule) -> None:
        self.source_module = source_module
        self.schemas: list[ModelPydanticSchema] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if self._is_pydantic_model(node):
            self.schemas.append(
                ModelPydanticSchema(
                    model_name=node.name,
                    file_path=str(self.source_module.path),
                    line_number=node.lineno,
                    fields=frozenset(self._field_names(node)),
                    module_names=self.source_module.module_names,
                )
            )
        self.generic_visit(node)

    @staticmethod
    def _is_pydantic_model(node: ast.ClassDef) -> bool:
        return any(_name_of(base) == "BaseModel" for base in node.bases)

    @staticmethod
    def _field_names(node: ast.ClassDef) -> tuple[str, ...]:
        names: list[str] = []
        for statement in node.body:
            if not isinstance(statement, ast.AnnAssign):
                continue
            if not isinstance(statement.target, ast.Name):
                continue
            if statement.target.id.startswith("_"):
                continue
            if _name_of(statement.annotation) == "ClassVar":
                continue
            names.append(statement.target.id)
        return tuple(names)


def _name_of(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return _name_of(node.value)
    return None


def _module_names(root: Path, path: Path) -> frozenset[str]:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return frozenset({path.stem})
    without_suffix = relative.with_suffix("")
    parts = without_suffix.parts
    names = {path.stem}
    if parts:
        dotted = ".".join(parts)
        names.add(dotted)
        if parts[-1] == "__init__" and len(parts) > 1:
            names.add(".".join(parts[:-1]))
    return frozenset(name for name in names if name)


def _parse_source_modules(root: Path) -> list[SourceModule]:
    modules: list[SourceModule] = []
    for path in sorted(root.rglob("*.py")):
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        modules.append(
            SourceModule(
                path=path,
                module_names=_module_names(root, path),
                tree=tree,
            )
        )
    return modules


def _collect_model_registry(modules: Iterable[SourceModule]) -> ModelRegistry:
    schemas: list[ModelPydanticSchema] = []
    for source_module in modules:
        collector = ModelPydanticCollector(source_module)
        collector.visit(source_module.tree)
        schemas.extend(collector.schemas)

    by_name: dict[str, list[ModelPydanticSchema]] = {}
    by_qualified_name: dict[tuple[str, str], ModelPydanticSchema] = {}
    for schema in schemas:
        by_name.setdefault(schema.model_name, []).append(schema)
        for module_name in schema.module_names:
            by_qualified_name[(module_name, schema.model_name)] = schema
    return ModelRegistry(
        by_name={
            model_name: tuple(model_schemas)
            for model_name, model_schemas in by_name.items()
        },
        by_qualified_name=by_qualified_name,
    )


def scan_source_tree(root: Path) -> list[SymmetryFinding]:
    """Scan *root* recursively and return symmetry findings.

    Collects every producer/consumer TopicBase use across all Python files
    under *root*, then groups by topic member name. Emits findings for
    divergent normalization chains and statically discoverable Pydantic model
    field sets.
    """
    source_modules = _parse_source_modules(root)
    model_registry = _collect_model_registry(source_modules)

    all_uses: list[TopicUse] = []
    for source_module in source_modules:
        checker = NormalizationSymmetryChecker(
            str(source_module.path),
            module_names=source_module.module_names,
            model_registry=model_registry,
        )
        checker.visit(source_module.tree)
        all_uses.extend(checker.topic_uses)

    by_topic: dict[str, list[TopicUse]] = {}
    for use in all_uses:
        by_topic.setdefault(use.topic_name, []).append(use)

    issues: list[SymmetryFinding] = []
    for topic_name, uses in by_topic.items():
        producers = [u for u in uses if u.role == "producer"]
        consumers = [u for u in uses if u.role == "consumer"]
        if not producers or not consumers:
            continue

        producer_chains = {u.normalizations for u in producers}
        consumer_chains = {u.normalizations for u in consumers}

        if producer_chains != consumer_chains:
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

        schema_issue = _schema_symmetry_issue(topic_name, producers, consumers)
        if schema_issue is not None:
            issues.append(schema_issue)

    return issues


def _schema_symmetry_issue(
    topic_name: str, producers: Iterable[TopicUse], consumers: Iterable[TopicUse]
) -> ModelSchemaSymmetryIssue | None:
    producer_models = [use for use in producers if use.model_schema is not None]
    consumer_models = [use for use in consumers if use.model_schema is not None]
    for producer in producer_models:
        producer_schema = producer.model_schema
        if producer_schema is None:
            continue
        for consumer in consumer_models:
            consumer_schema = consumer.model_schema
            if consumer_schema is None:
                continue
            if producer_schema.fields == consumer_schema.fields:
                continue
            return ModelSchemaSymmetryIssue(
                topic_name=topic_name,
                producer_file=producer.file_path,
                producer_line=producer.line_number,
                producer_model=producer_schema.model_name,
                producer_fields=producer_schema.fields,
                consumer_file=consumer.file_path,
                consumer_line=consumer.line_number,
                consumer_model=consumer_schema.model_name,
                consumer_fields=consumer_schema.fields,
            )
    return None


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

    all_issues: list[SymmetryFinding] = []
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
