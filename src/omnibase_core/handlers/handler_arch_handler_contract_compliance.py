# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Handler contract compliance of every node in a repository (OMN-20074).

Ported from onex_change_control (``arch_handler_contract_compliance``, the scanner
``handler_contract_compliance.cross_reference`` and its CLI) for OCC retirement
step S8. The decisions are the source's: for every ``node_*`` directory under
``src/**/nodes`` that has a ``handlers/`` directory, each handler module is judged
against the node's ``contract.yaml`` for

- a quoted topic literal in the handler (declared in the contract or not),
- a transport used at a call site that the contract does not declare,
- a handler module missing from ``handler_routing``, and
- custom methods in the node's ``node.py``.

Two or more violations are IMPERATIVE, one is HYBRID, none is COMPLIANT; an
allowlisted handler is ALLOWLISTED, and a node without a ``contract.yaml`` is
MISSING_CONTRACT and carries no violation. The run fails when a handler has a
violation and is not allowlisted.

The handler is pure over explicit node sources
(:class:`ModelHandlerContractComplianceInput`); ``main`` reads the repository tree
and the allowlist, then prints the source's summary lines. Only the node scan is
ported: the freestanding-module scan, the scripts baseline and the allowlist ticket
check belong to the imperative-contract-guard, not to this validator's CLI.

Usage::

    python -m omnibase_core.handlers.handler_arch_handler_contract_compliance \\
        --repo-root . --allowlist-path arch-handler-contract-compliance-allowlist.yaml

    # Generate an initial allowlist from the current violations
    python -m omnibase_core.handlers.handler_arch_handler_contract_compliance \\
        --repo-root . --generate-allowlist

Exit code 0 = clean (or no node directories found). Exit code 1 = a handler has a
violation that is not allowlisted. Exit code 2 = unsupported arguments.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Final

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.governance.enum_compliance_verdict import (
    EnumComplianceVerdict,
)
from omnibase_core.enums.governance.enum_compliance_violation import (
    EnumComplianceViolation,
)
from omnibase_core.enums.governance.enum_reachability import EnumReachability
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.governance.model_handler_compliance_result import (
    ModelHandlerComplianceResult,
)
from omnibase_core.models.nodes.handler_contract_compliance.model_compliance_node_source import (
    ModelComplianceNodeSource,
)
from omnibase_core.models.nodes.handler_contract_compliance.model_handler_contract_compliance_input import (
    ModelHandlerContractComplianceInput,
)
from omnibase_core.models.nodes.handler_contract_compliance.model_handler_contract_compliance_report import (
    ModelHandlerContractComplianceReport,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile

# Known ONEX topic patterns.
_ONEX_TOPIC_RE: Final[re.Pattern[str]] = re.compile(
    r"onex\.evt\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.v\d+"
)

# Known bare topic names used in the platform.
_BARE_TOPIC_NAMES: Final[frozenset[str]] = frozenset(
    {
        "agent-actions",
        "agent-transformation-events",
        "agent.routing.requested.v1",
        "agent.routing.completed.v1",
        "agent.routing.failed.v1",
        "router-performance-metrics",
        "documentation-changed",
    }
)

# Call-site transport indicators (precise call-site detection only).
_TRANSPORT_CALLSITE_PATTERNS: Final[dict[str, str]] = {
    "session.execute": "DATABASE",
    "session.query": "DATABASE",
    "asyncpg.connect": "DATABASE",
    "asyncpg.create_pool": "DATABASE",
    "psycopg.connect": "DATABASE",
    "create_engine": "DATABASE",
    "create_async_engine": "DATABASE",
    "AsyncClient": "HTTP",
    "httpx.get": "HTTP",
    "httpx.post": "HTTP",
    "requests.get": "HTTP",
    "requests.post": "HTTP",
    "KafkaProducer": "KAFKA",
    "KafkaConsumer": "KAFKA",
    "AIOKafkaProducer": "KAFKA",
    "AIOKafkaConsumer": "KAFKA",
    "QdrantClient": "QDRANT",
}

_IMPERATIVE_VIOLATION_THRESHOLD: Final[int] = 2


# What a node's contract.yaml declares: topics, transports and routed handler modules.
_ContractFacts = tuple[list[str], list[str], frozenset[str]]


def _load_yaml_text(text: str | None) -> dict[str, object] | None:
    """Parse YAML text to a mapping; None when absent or not a mapping."""
    if text is None:
        return None
    data = yaml.load(
        text, Loader=yaml.SafeLoader
    )  # SafeLoader, as the source's safe_load
    if not isinstance(data, dict):
        return None
    return data


def _mapping(value: object, what: str) -> dict[str, object]:
    """Return ``value or {}`` as a mapping; a non-mapping value is malformed."""
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    raise ModelOnexError(
        message=f"{what} must be a mapping, got {type(value).__name__}",
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    )


def _entries(value: object, what: str) -> list[object]:
    """Return ``value or []`` as a list; a non-list value is malformed."""
    if not value:
        return []
    if isinstance(value, list):
        return value
    raise ModelOnexError(
        message=f"{what} must be a list, got {type(value).__name__}",
        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
    )


def _normalize_topic_list(raw: list[object]) -> list[str]:
    """Normalize a topic list that may contain strings or dicts with a 'topic' key."""
    result: list[str] = []
    for item in raw:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict) and "topic" in item:
            result.append(str(item["topic"]))
    return result


def _parse_contract_topics(data: dict[str, object]) -> tuple[list[str], list[str]]:
    """Extract publish and subscribe topics from a parsed contract."""
    event_bus = _mapping(data.get("event_bus"), "event_bus")
    publish = _normalize_topic_list(
        _entries(event_bus.get("publish_topics"), "publish_topics")
    )
    subscribe = _normalize_topic_list(
        _entries(event_bus.get("subscribe_topics"), "subscribe_topics")
    )
    return publish, subscribe


def _normalize_declared_transports(raw: object) -> list[str]:
    """Normalize a ``transport_type`` declaration into upper-case transport names.

    The slot accepts either a single transport name or a list of them. Entries
    that are not scalar strings, and blank entries, are dropped rather than
    coerced: a declaration that cannot be read never widens the set of
    transports a handler may use.
    """
    items = raw if isinstance(raw, list) else [raw]
    normalized: list[str] = []
    for item in items:
        if item is None or isinstance(item, (list, tuple, dict, set)):
            continue
        name = str(item).strip().upper()
        if name and name not in normalized:
            normalized.append(name)
    return normalized


def _infer_kafka_transport(data: dict[str, object], transports: list[str]) -> None:
    """Add KAFKA transport if an EFFECT node has declared topics."""
    node_type = data.get("node_type", "")
    if "EFFECT" not in str(node_type):
        return
    event_bus = _mapping(data.get("event_bus"), "event_bus")
    has_topics = event_bus.get("publish_topics") or event_bus.get("subscribe_topics")
    if has_topics and "KAFKA" not in transports:
        transports.append("KAFKA")


def _handler_entries(data: dict[str, object]) -> list[dict[str, object]]:
    """Return the ``handler_routing.handlers`` entries of a parsed contract."""
    handler_routing = _mapping(data.get("handler_routing"), "handler_routing")
    return [
        _mapping(entry, "handler_routing entry")
        for entry in _entries(handler_routing.get("handlers"), "handlers")
    ]


def _parse_contract_transports(data: dict[str, object]) -> list[str]:
    """Extract declared transport types from a parsed contract.

    Looks at metadata.transport_type and handler_routing.handlers[].handler_type;
    EFFECT nodes with declared topics also declare KAFKA.
    """
    transports: list[str] = []

    metadata = _mapping(data.get("metadata"), "metadata")
    if transport := metadata.get("transport_type"):
        transports.extend(_normalize_declared_transports(transport))

    for handler_entry in _handler_entries(data):
        handler_info = _mapping(handler_entry.get("handler"), "handler")
        if handler_type := handler_info.get("handler_type"):
            transports.extend(_normalize_declared_transports(handler_type))

    _infer_kafka_transport(data, transports)
    return transports


def _parse_routed_modules(data: dict[str, object]) -> frozenset[str]:
    """Extract the handler modules named in handler_routing."""
    return frozenset(
        str(_mapping(entry.get("handler"), "handler").get("module", ""))
        for entry in _handler_entries(data)
    )


def _get_docstring_nodes(tree: ast.Module) -> set[int]:
    """Collect ids of AST nodes that are docstrings."""
    docstring_ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)
        ) and (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            docstring_ids.add(id(node.body[0].value))
    return docstring_ids


def _get_attribute_string(node: ast.Attribute) -> str:
    """Extract the dotted string from an Attribute node."""
    parts: list[str] = [node.attr]
    current: ast.expr = node.value
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    parts.reverse()
    return ".".join(parts)


def _get_call_string(node: ast.Call) -> str | None:
    """Extract a dotted string representation of a Call node's function."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return _get_attribute_string(node.func)
    return None


def _parse_python(source: str) -> ast.Module | None:
    """Parse Python source; None when it does not parse."""
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _scan_handler_topics(source: str) -> list[str]:
    """Find topic string literals in handler code, skipping docstrings."""
    tree = _parse_python(source)
    if tree is None:
        return []

    topics: list[str] = []
    docstring_nodes = _get_docstring_nodes(tree)
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        if id(node) in docstring_nodes:
            continue
        value = node.value
        if _ONEX_TOPIC_RE.search(value) or value in _BARE_TOPIC_NAMES:
            topics.append(value)

    return sorted(set(topics))


def _scan_handler_transports(source: str) -> list[str]:
    """Detect transport usage at call sites, not bare imports."""
    tree = _parse_python(source)
    if tree is None:
        return []

    transports: set[str] = set()
    for node in ast.walk(tree):
        call_str: str | None = None
        if isinstance(node, ast.Call):
            call_str = _get_call_string(node)
        elif isinstance(node, ast.Attribute):
            call_str = _get_attribute_string(node)
        if call_str:
            for pattern, transport in _TRANSPORT_CALLSITE_PATTERNS.items():
                if pattern in call_str:
                    transports.add(transport)

    return sorted(transports)


def _scan_node_py_logic(source: str | None) -> list[str]:
    """Return custom method names in node.py beyond ``__init__``.

    A clean declarative node only has ``__init__`` calling ``super().__init__``;
    any other method is business logic in the wrong layer.
    """
    if source is None:
        return []
    tree = _parse_python(source)
    if tree is None:
        return []

    custom_methods: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            custom_methods.extend(
                item.name
                for item in node.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                and item.name != "__init__"
            )
    return custom_methods


def _infer_module_path(handler_path: PurePosixPath, node_dir: PurePosixPath) -> str:
    """Infer the Python module path of a handler file from its first ``src`` segment."""
    parts = handler_path.parts
    src_idx = parts.index("src") if "src" in parts else None

    if src_idx is not None:
        module_parts = parts[src_idx + 1 :]
    else:
        try:
            rel = handler_path.relative_to(node_dir.parent.parent)
        except ValueError:
            return ""
        module_parts = rel.parts

    last = module_parts[-1]
    if last.endswith(".py"):
        module_parts = (*module_parts[:-1], last[:-3])
    return ".".join(module_parts)


def _handler_reachability(rel_path: str, *, is_routed: bool) -> EnumReachability:
    """Classify handler reachability for static guard blocking."""
    parts = set(PurePosixPath(rel_path).parts)
    if "tests" in parts or PurePosixPath(rel_path).name.startswith("test_"):
        return EnumReachability.TEST_HARNESS
    return EnumReachability.LIVE if is_routed else EnumReachability.DEAD


def _determine_verdict(
    violations: list[EnumComplianceViolation],
    *,
    is_allowlisted: bool,
) -> EnumComplianceVerdict:
    """Determine the compliance verdict from violations."""
    if is_allowlisted:
        return EnumComplianceVerdict.ALLOWLISTED
    if not violations:
        return EnumComplianceVerdict.COMPLIANT
    if len(violations) >= _IMPERATIVE_VIOLATION_THRESHOLD:
        return EnumComplianceVerdict.IMPERATIVE
    return EnumComplianceVerdict.HYBRID


def _build_contract_facts(node: ModelComplianceNodeSource) -> _ContractFacts | None:
    """Extract all contract info needed for handler auditing; None without a contract."""
    if node.contract_yaml is None:
        return None

    data = _load_yaml_text(node.contract_yaml) or {}
    publish_topics, subscribe_topics = _parse_contract_topics(data)
    return (
        sorted(set(publish_topics + subscribe_topics)),
        _parse_contract_transports(data),
        _parse_routed_modules(data),
    )


def _collect_violations(
    handler: ModelSourceFile,
    node_dir: PurePosixPath,
    facts: _ContractFacts,
    node_logic: list[str],
) -> tuple[list[EnumComplianceViolation], list[str]]:
    """Collect all violations for a handler file."""
    declared_topics, declared_transports, routed_modules = facts
    violations: list[EnumComplianceViolation] = []
    details: list[str] = []

    # Check 1: any hardcoded topic literal is a violation, even if declared in the
    # contract. Declaration and hardcoding are orthogonal: handlers should use
    # contract-driven dispatch, not string literals.
    for topic in _scan_handler_topics(handler.source):
        violations.append(EnumComplianceViolation.HARDCODED_TOPIC)
        if topic in declared_topics:
            details.append(
                f"hardcoded topic '{topic}' (declared but should use contract dispatch)"
            )
        else:
            details.append(f"hardcoded topic '{topic}' not in contract")

    # Check 2: transport compliance.
    for transport in _scan_handler_transports(handler.source):
        if transport not in declared_transports:
            violations.append(EnumComplianceViolation.UNDECLARED_TRANSPORT)
            details.append(f"undeclared transport {transport} used in handler")

    # Check 3: handler routing registration.
    handler_module = _infer_module_path(PurePosixPath(handler.path), node_dir)
    if handler_module not in routed_modules:
        violations.append(EnumComplianceViolation.MISSING_HANDLER_ROUTING)
        details.append("handler not registered in contract handler_routing")

    # Check 4: logic in node.py.
    if node_logic:
        violations.append(EnumComplianceViolation.LOGIC_IN_NODE)
        details.append(f"node.py has custom methods: {', '.join(node_logic)}")

    return violations, details


def _audit_handler(
    handler: ModelSourceFile,
    node_dir: PurePosixPath,
    repo: str,
    facts: _ContractFacts | None,
    node_logic: list[str],
    allowlisted_paths: frozenset[str],
) -> ModelHandlerComplianceResult:
    """Audit a single handler file against its node's contract facts."""
    base_dir = node_dir.parent.parent.parent
    rel_path = str(PurePosixPath(handler.path).relative_to(base_dir))
    is_allowlisted = rel_path in allowlisted_paths
    node_rel = str(node_dir.relative_to(base_dir))

    if facts is None:
        return ModelHandlerComplianceResult(
            handler_path=rel_path,
            node_dir=node_rel,
            repo=repo,
            contract_path=None,
            verdict=EnumComplianceVerdict.MISSING_CONTRACT,
            allowlisted=is_allowlisted,
            reachability=_handler_reachability(rel_path, is_routed=True),
        )

    declared_topics, declared_transports, routed_modules = facts
    violations, violation_details = _collect_violations(
        handler, node_dir, facts, node_logic
    )
    used_topics = _scan_handler_topics(handler.source)
    used_transports = _scan_handler_transports(handler.source)
    handler_module = _infer_module_path(PurePosixPath(handler.path), node_dir)
    in_routing = handler_module in routed_modules

    return ModelHandlerComplianceResult(
        handler_path=rel_path,
        node_dir=node_rel,
        repo=repo,
        contract_path=str((node_dir / "contract.yaml").relative_to(base_dir)),
        violations=violations,
        violation_details=violation_details,
        declared_topics=declared_topics,
        used_topics=used_topics,
        undeclared_topics=[t for t in used_topics if t not in declared_topics],
        declared_transports=declared_transports,
        used_transports=used_transports,
        undeclared_transports=[
            t for t in used_transports if t not in declared_transports
        ],
        handler_in_routing=in_routing,
        verdict=_determine_verdict(violations, is_allowlisted=is_allowlisted),
        allowlisted=is_allowlisted,
        reachability=_handler_reachability(rel_path, is_routed=in_routing),
    )


class HandlerArchHandlerContractCompliance:
    """Decide, per supplied node source, which handlers breach their node's contract."""

    def handle(
        self, request: ModelHandlerContractComplianceInput
    ) -> ModelHandlerContractComplianceReport:
        """Return one compliance result per handler, in node then handler order."""
        allowlisted = frozenset(request.allowlisted_paths)
        results: list[ModelHandlerComplianceResult] = []
        for node in request.nodes:
            facts = _build_contract_facts(node)
            node_logic = _scan_node_py_logic(node.node_py)
            node_dir = PurePosixPath(node.node_dir)
            results.extend(
                _audit_handler(
                    handler=handler,
                    node_dir=node_dir,
                    repo=request.repo,
                    facts=facts,
                    node_logic=node_logic,
                    allowlisted_paths=allowlisted,
                )
                for handler in node.handlers
            )
        return ModelHandlerContractComplianceReport(results=results)


# --- Repository tree reads (the EFFECT boundary of ``main``) ---


def _find_node_dirs(repo_root: Path) -> list[Path]:
    """Find all node directories (``node_*`` with a ``handlers/`` directory)."""
    src_dir = repo_root / "src"
    if not src_dir.exists():
        return []

    node_dirs: list[Path] = []
    for nodes_dir in src_dir.rglob("nodes"):
        if not nodes_dir.is_dir():
            continue
        for child in sorted(nodes_dir.iterdir()):
            if child.is_dir() and child.name.startswith("node_"):
                handlers_dir = child / "handlers"
                if handlers_dir.exists():
                    node_dirs.append(child)

    return node_dirs


def _infer_repo_name(repo_root: Path) -> str:
    """Infer the repository name from the first package directory under ``src``."""
    src_dir = repo_root / "src"
    if src_dir.exists():
        for child in src_dir.iterdir():
            if child.is_dir() and not child.name.startswith("."):
                return child.name
    return repo_root.name


def _read_text_if_present(path: Path) -> str | None:
    """Read a UTF-8 file, or None when it does not exist."""
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _read_node(node_dir: Path) -> ModelComplianceNodeSource:
    """Read the contract, node.py and handler modules of one node directory."""
    handler_files = sorted(
        f
        for f in (node_dir / "handlers").rglob("*.py")
        if f.name != "__init__.py" and not f.name.startswith("_")
    )
    return ModelComplianceNodeSource(
        node_dir=node_dir.as_posix(),
        contract_yaml=_read_text_if_present(node_dir / "contract.yaml"),
        node_py=_read_text_if_present(node_dir / "node.py"),
        handlers=[
            ModelSourceFile(
                path=handler_file.as_posix(),
                source=handler_file.read_text(encoding="utf-8"),
            )
            for handler_file in handler_files
        ],
    )


def _load_allowlist(allowlist_path: Path) -> list[str]:
    """Load allowlist YAML, returning the allowlisted handler paths."""
    if not allowlist_path.exists():
        return []

    with allowlist_path.open(encoding="utf-8") as f:
        data = yaml.load(
            f, Loader=yaml.SafeLoader
        )  # SafeLoader, as the source's safe_load

    if not isinstance(data, dict):
        return []

    paths: list[str] = []
    for entry in data.get("allowlisted_handlers", []) or []:
        path = entry.get("path", "")
        if path:
            paths.append(path)
    return paths


def _write(msg: str) -> None:
    """Write a line to stdout (CI output)."""
    sys.stdout.write(msg + "\n")


def _output_allowlist(results: list[ModelHandlerComplianceResult]) -> None:
    """Output current violations as allowlist YAML."""
    entries = [
        {
            "path": r.handler_path,
            "violations": [str(v) for v in r.violations],
            "ticket": "# migration pending",
        }
        for r in results
        if r.violations
    ]
    _write(
        yaml.dump(
            {"allowlisted_handlers": entries}, default_flow_style=False, sort_keys=False
        )
    )


def run_scan(
    repo_root: Path,
    allowlist_path: Path | None = None,
    *,
    generate_allowlist: bool = False,
    output_json: bool = False,
) -> int:
    """Run the handler contract compliance scan; 0 if clean, 1 if violations found."""
    repo_name = _infer_repo_name(repo_root)
    node_dirs = _find_node_dirs(repo_root)

    if not node_dirs:
        _write(f"No node directories found in {repo_root}")
        return 0

    allowlisted_paths = _load_allowlist(allowlist_path) if allowlist_path else []
    report = HandlerArchHandlerContractCompliance().handle(
        ModelHandlerContractComplianceInput(
            repo=repo_name,
            nodes=[_read_node(node_dir) for node_dir in node_dirs],
            allowlisted_paths=allowlisted_paths,
        )
    )

    if generate_allowlist:
        _output_allowlist(report.results)
        return 0

    if output_json:
        _write(
            json.dumps([r.model_dump(mode="json") for r in report.results], indent=2)
        )

    new_violations = report.new_violations
    _write(f"\n=== Handler Contract Compliance: {repo_name} ===")
    _write(f"Total handlers: {report.total}")
    _write(f"Compliant: {report.compliant_count}")
    _write(f"Allowlisted: {report.allowlisted_count}")
    _write(f"New violations: {len(new_violations)}")

    if new_violations:
        _write("\n--- New violations (not allowlisted) ---")
        for r in new_violations:
            _write(f"\n  {r.handler_path}")
            _write(f"    Verdict: {r.verdict}")
            for detail in r.violation_details:
                _write(f"    - {detail}")
        return 1

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point; returns the exit code."""
    parser = argparse.ArgumentParser(
        description="Handler contract compliance validator"
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        required=True,
        help="Repository root path",
    )
    parser.add_argument(
        "--allowlist-path",
        type=Path,
        default=None,
        help="Path to allowlist YAML",
    )
    parser.add_argument(
        "--generate-allowlist",
        action="store_true",
        help="Output current violations as allowlist",
    )
    parser.add_argument(
        "--json",
        dest="output_json",
        action="store_true",
        help="Output JSON report",
    )

    args = parser.parse_args(sys.argv[1:] if argv is None else list(argv))
    return run_scan(
        repo_root=args.repo_root,
        allowlist_path=args.allowlist_path,
        generate_allowlist=args.generate_allowlist,
        output_json=args.output_json,
    )


if __name__ == "__main__":
    sys.exit(main())
