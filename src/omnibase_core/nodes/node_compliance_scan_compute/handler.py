# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""NodeComplianceScanCompute — compliance scanner COMPUTE handler.

Scans a directory tree for contract.yaml files and runs 8 structural
compliance checks per node, classified by verification type:

  Contract Parse:      (1) YAML valid and parseable
  Handler Resolution:  (2) handler_routing references importable
  Schema Conformance:  (3) input/output schemas valid Pydantic models
                       (4) node_kind matches handler output constraints
  Naming Policy:       (5) publish_topics follow naming convention
                       (6) subscribe_topics follow naming convention
  Config Readiness:    (7) config_requirements have env/Infisical mappings
  Codepath Consumption:(8) validator parameter compliance via AST

ONEX node type: COMPUTE
Input:  repo root path (str)
Output: list[ModelComplianceCheckResult]

.. versionadded:: OMN-7069
"""

from __future__ import annotations

import ast
import importlib
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from omnibase_core.models.nodes.compliance_scan.model_check_result import (
    ModelCheckResult,
)
from omnibase_core.models.nodes.compliance_scan.model_compliance_check_result import (
    ModelComplianceCheckResult,
)

__all__ = [
    "NodeComplianceScanCompute",
]

# Topic naming convention: onex.{cmd|evt}.{service}.{event-name}.v{N}
_TOPIC_PATTERN = re.compile(
    r"^onex\.(cmd|evt)\.[a-z][a-z0-9_-]*\.[a-z][a-z0-9_-]*\.v\d+$"
)

# Valid node kinds for output constraint checking
_COMPUTE_KINDS = {"compute", "COMPUTE"}
_ORCHESTRATOR_KINDS = {"orchestrator", "ORCHESTRATOR"}


class NodeComplianceScanCompute:
    """Compliance scanner compute handler.

    Discovers all contract.yaml files under a root directory and runs
    8 structural checks per contract.
    """

    def scan(self, repo_root: str) -> list[ModelComplianceCheckResult]:
        """Scan all contract.yaml files under repo_root.

        Args:
            repo_root: Absolute path to the repository root.

        Returns:
            List of per-node compliance results.
        """
        root = Path(repo_root)
        contracts = sorted(root.rglob("contract.yaml"))
        results: list[ModelComplianceCheckResult] = []

        for contract_path in contracts:
            result = self._check_contract(contract_path)
            results.append(result)

        return results

    def _check_contract(self, contract_path: Path) -> ModelComplianceCheckResult:
        """Run all 8 checks on a single contract.yaml."""
        checks: list[ModelCheckResult] = []

        # Check 1: Contract Parse
        contract_data = self._check_contract_parse(contract_path, checks)

        if contract_data is not None:
            # Check 2: Handler Resolution
            self._check_handler_resolution(contract_data, checks)

            # Check 3: Schema Conformance — input/output models
            self._check_schema_conformance(contract_data, checks)

            # Check 4: Schema Conformance — node_kind constraints
            self._check_node_kind_constraints(contract_data, checks)

            # Check 5: Naming Policy — publish_topics
            self._check_publish_topics(contract_data, checks)

            # Check 6: Naming Policy — subscribe_topics
            self._check_subscribe_topics(contract_data, checks)

            # Check 7: Config Readiness
            self._check_config_readiness(contract_data, checks)

            # Check 8: Codepath Consumption
            self._check_codepath_consumption(contract_data, contract_path, checks)
        else:
            # Fill remaining checks as skipped
            for check_id, (name, cls) in enumerate(
                [
                    ("handler_resolution", "Handler Resolution"),
                    ("input_output_schemas", "Schema Conformance"),
                    ("node_kind_constraints", "Schema Conformance"),
                    ("publish_topics_naming", "Naming Policy"),
                    ("subscribe_topics_naming", "Naming Policy"),
                    ("config_readiness", "Config Readiness"),
                    ("codepath_consumption", "Codepath Consumption"),
                ],
                start=2,
            ):
                checks.append(
                    ModelCheckResult(
                        check_id=check_id,
                        check_name=name,
                        check_class=cls,
                        passed=False,
                        message="Skipped: contract parse failed",
                    )
                )

        node_id = ""
        if contract_data is not None:
            node_id = str(
                contract_data.get("node_id")
                or contract_data.get("handler_id")
                or contract_data.get("name")
                or contract_path.parent.name
            )
        else:
            node_id = contract_path.parent.name

        all_passed = all(c.passed for c in checks)

        return ModelComplianceCheckResult(
            node_id=node_id,
            contract_path=str(contract_path),
            passed=all_passed,
            checks=checks,
        )

    # ─────────────────────────────────────────────────────────────────
    # Individual checks
    # ─────────────────────────────────────────────────────────────────

    # ONEX_EXCLUDE: dict_str_any — contract YAML has no fixed Pydantic model
    def _check_contract_parse(
        self, contract_path: Path, checks: list[ModelCheckResult]
    ) -> dict[str, Any] | None:
        """Check 1: contract.yaml is valid YAML and parseable."""
        try:
            text = contract_path.read_text(encoding="utf-8")
            data = yaml.safe_load(text)
            if not isinstance(data, dict):
                checks.append(
                    ModelCheckResult(
                        check_id=1,
                        check_name="contract_parse",
                        check_class="Contract Parse",
                        passed=False,
                        message=f"Expected mapping, got {type(data).__name__}",
                    )
                )
                return None
            checks.append(
                ModelCheckResult(
                    check_id=1,
                    check_name="contract_parse",
                    check_class="Contract Parse",
                    passed=True,
                    message="Valid YAML mapping",
                )
            )
            return data
        except yaml.YAMLError as exc:
            checks.append(
                ModelCheckResult(
                    check_id=1,
                    check_name="contract_parse",
                    check_class="Contract Parse",
                    passed=False,
                    message=f"YAML parse error: {exc}",
                )
            )
            return None
        except OSError as exc:
            checks.append(
                ModelCheckResult(
                    check_id=1,
                    check_name="contract_parse",
                    check_class="Contract Parse",
                    passed=False,
                    message=f"File read error: {exc}",
                )
            )
            return None

    # ONEX_EXCLUDE: dict_str_any — contract YAML has no fixed Pydantic model
    def _check_handler_resolution(
        self, data: dict[str, Any], checks: list[ModelCheckResult]
    ) -> None:
        """Check 2: handler_routing references resolve (handler importable)."""
        handler_routing = data.get("handler_routing")
        if handler_routing is None:
            checks.append(
                ModelCheckResult(
                    check_id=2,
                    check_name="handler_resolution",
                    check_class="Handler Resolution",
                    passed=True,
                    message="No handler_routing declared (optional)",
                )
            )
            return

        default_handler = None
        if isinstance(handler_routing, dict):
            default_handler = handler_routing.get("default_handler")
        elif isinstance(handler_routing, str):
            default_handler = handler_routing

        if not default_handler:
            checks.append(
                ModelCheckResult(
                    check_id=2,
                    check_name="handler_resolution",
                    check_class="Handler Resolution",
                    passed=True,
                    message="handler_routing present but no default_handler",
                )
            )
            return

        # Format: module.path:ClassName or just module:ClassName
        if ":" not in default_handler:
            checks.append(
                ModelCheckResult(
                    check_id=2,
                    check_name="handler_resolution",
                    check_class="Handler Resolution",
                    passed=False,
                    message=f"Invalid handler format (missing ':'): {default_handler}",
                )
            )
            return

        module_path, attr_name = default_handler.rsplit(":", 1)
        try:
            mod = importlib.import_module(module_path)
            if hasattr(mod, attr_name):
                checks.append(
                    ModelCheckResult(
                        check_id=2,
                        check_name="handler_resolution",
                        check_class="Handler Resolution",
                        passed=True,
                        message=f"Handler {default_handler} importable",
                    )
                )
            else:
                checks.append(
                    ModelCheckResult(
                        check_id=2,
                        check_name="handler_resolution",
                        check_class="Handler Resolution",
                        passed=False,
                        message=f"Module '{module_path}' found but '{attr_name}' not defined",
                    )
                )
        except ImportError as exc:
            checks.append(
                ModelCheckResult(
                    check_id=2,
                    check_name="handler_resolution",
                    check_class="Handler Resolution",
                    passed=False,
                    message=f"Cannot import '{module_path}': {exc}",
                )
            )

    # ONEX_EXCLUDE: dict_str_any — contract YAML has no fixed Pydantic model
    def _check_schema_conformance(
        self, data: dict[str, Any], checks: list[ModelCheckResult]
    ) -> None:
        """Check 3: input/output schemas are valid Pydantic models."""
        input_model = data.get("input_model")
        output_model = data.get("output_model")

        if not input_model and not output_model:
            checks.append(
                ModelCheckResult(
                    check_id=3,
                    check_name="input_output_schemas",
                    check_class="Schema Conformance",
                    passed=True,
                    message="No input/output models declared (optional)",
                )
            )
            return

        errors: list[str] = []
        for label, model_ref in [
            ("input_model", input_model),
            ("output_model", output_model),
        ]:
            if model_ref is None:
                continue
            if not isinstance(model_ref, str):
                errors.append(f"{label} is not a string: {type(model_ref).__name__}")
                continue
            # Try to import the model
            if "." not in model_ref:
                errors.append(f"{label} has no module path: {model_ref}")
                continue
            module_path, _, class_name = model_ref.rpartition(".")
            try:
                mod = importlib.import_module(module_path)
                cls = getattr(mod, class_name, None)
                if cls is None:
                    errors.append(
                        f"{label}: '{class_name}' not found in '{module_path}'"
                    )
                elif not (isinstance(cls, type) and issubclass(cls, BaseModel)):
                    errors.append(
                        f"{label}: '{class_name}' is not a Pydantic BaseModel"
                    )
            except ImportError as exc:
                errors.append(f"{label}: cannot import '{module_path}': {exc}")

        if errors:
            checks.append(
                ModelCheckResult(
                    check_id=3,
                    check_name="input_output_schemas",
                    check_class="Schema Conformance",
                    passed=False,
                    message="; ".join(errors),
                )
            )
        else:
            checks.append(
                ModelCheckResult(
                    check_id=3,
                    check_name="input_output_schemas",
                    check_class="Schema Conformance",
                    passed=True,
                    message="All declared schemas are valid Pydantic models",
                )
            )

    # ONEX_EXCLUDE: dict_str_any — contract YAML has no fixed Pydantic model
    def _check_node_kind_constraints(
        self, data: dict[str, Any], checks: list[ModelCheckResult]
    ) -> None:
        """Check 4: node_kind matches handler output constraints."""
        node_kind = data.get("node_kind") or data.get("node_type") or ""
        node_kind_str = str(node_kind).upper()

        if not node_kind_str:
            checks.append(
                ModelCheckResult(
                    check_id=4,
                    check_name="node_kind_constraints",
                    check_class="Schema Conformance",
                    passed=True,
                    message="No node_kind declared",
                )
            )
            return

        valid_kinds = {"COMPUTE", "REDUCER", "EFFECT", "ORCHESTRATOR"}
        if node_kind_str not in valid_kinds:
            checks.append(
                ModelCheckResult(
                    check_id=4,
                    check_name="node_kind_constraints",
                    check_class="Schema Conformance",
                    passed=False,
                    message=f"Unknown node_kind '{node_kind}'; valid: {sorted(valid_kinds)}",
                )
            )
            return

        # ORCHESTRATOR must not declare output_model (no result)
        if node_kind_str == "ORCHESTRATOR" and data.get("output_model"):
            checks.append(
                ModelCheckResult(
                    check_id=4,
                    check_name="node_kind_constraints",
                    check_class="Schema Conformance",
                    passed=False,
                    message="ORCHESTRATOR nodes cannot declare output_model (no result)",
                )
            )
            return

        checks.append(
            ModelCheckResult(
                check_id=4,
                check_name="node_kind_constraints",
                check_class="Schema Conformance",
                passed=True,
                message=f"node_kind '{node_kind_str}' constraints satisfied",
            )
        )

    def _check_topic_list(
        self,
        topics: Any,
        check_id: int,
        check_name: str,
        label: str,
        checks: list[ModelCheckResult],
    ) -> None:
        """Shared logic for checks 5 and 6: topic naming validation."""
        if topics is None:
            checks.append(
                ModelCheckResult(
                    check_id=check_id,
                    check_name=check_name,
                    check_class="Naming Policy",
                    passed=True,
                    message=f"No {label} declared (optional)",
                )
            )
            return

        if not isinstance(topics, list):
            checks.append(
                ModelCheckResult(
                    check_id=check_id,
                    check_name=check_name,
                    check_class="Naming Policy",
                    passed=False,
                    message=f"{label} is not a list",
                )
            )
            return

        violations: list[str] = []
        for topic in topics:
            topic_str = str(topic)
            if not _TOPIC_PATTERN.match(topic_str):
                violations.append(topic_str)

        if violations:
            checks.append(
                ModelCheckResult(
                    check_id=check_id,
                    check_name=check_name,
                    check_class="Naming Policy",
                    passed=False,
                    message=f"Topics violate naming convention: {violations}",
                )
            )
        else:
            checks.append(
                ModelCheckResult(
                    check_id=check_id,
                    check_name=check_name,
                    check_class="Naming Policy",
                    passed=True,
                    message=f"All {len(topics)} {label} follow naming convention",
                )
            )

    # ONEX_EXCLUDE: dict_str_any — contract YAML has no fixed Pydantic model
    def _check_publish_topics(
        self, data: dict[str, Any], checks: list[ModelCheckResult]
    ) -> None:
        """Check 5: publish_topics follow naming convention."""
        # Topics may be at top level or under event_bus
        topics = data.get("publish_topics")
        if topics is None:
            event_bus = data.get("event_bus")
            if isinstance(event_bus, dict):
                topics = event_bus.get("publish_topics")
        # Also check events.emits as an alternative declaration
        if topics is None:
            events = data.get("events")
            if isinstance(events, dict):
                topics = events.get("emits")

        self._check_topic_list(
            topics, 5, "publish_topics_naming", "publish_topics", checks
        )

    # ONEX_EXCLUDE: dict_str_any — contract YAML has no fixed Pydantic model
    def _check_subscribe_topics(
        self, data: dict[str, Any], checks: list[ModelCheckResult]
    ) -> None:
        """Check 6: subscribe_topics follow naming convention."""
        topics = data.get("subscribe_topics")
        if topics is None:
            event_bus = data.get("event_bus")
            if isinstance(event_bus, dict):
                topics = event_bus.get("subscribe_topics")
        if topics is None:
            events = data.get("events")
            if isinstance(events, dict):
                topics = events.get("subscribes")

        self._check_topic_list(
            topics, 6, "subscribe_topics_naming", "subscribe_topics", checks
        )

    # ONEX_EXCLUDE: dict_str_any — contract YAML has no fixed Pydantic model
    def _check_config_readiness(
        self, data: dict[str, Any], checks: list[ModelCheckResult]
    ) -> None:
        """Check 7: config_requirements have env var or Infisical mappings."""
        config_reqs = data.get("config_requirements")
        if config_reqs is None:
            checks.append(
                ModelCheckResult(
                    check_id=7,
                    check_name="config_readiness",
                    check_class="Config Readiness",
                    passed=True,
                    message="No config_requirements declared (optional)",
                )
            )
            return

        if not isinstance(config_reqs, (list, dict)):
            checks.append(
                ModelCheckResult(
                    check_id=7,
                    check_name="config_readiness",
                    check_class="Config Readiness",
                    passed=False,
                    message=f"config_requirements is not a list or dict: {type(config_reqs).__name__}",
                )
            )
            return

        # For list form: each item should have env_var or infisical_path
        missing: list[str] = []
        items = (
            config_reqs if isinstance(config_reqs, list) else list(config_reqs.values())
        )
        for item in items:
            if isinstance(item, dict):
                has_env = bool(item.get("env_var") or item.get("env"))
                has_infisical = bool(
                    item.get("infisical_path") or item.get("infisical")
                )
                if not has_env and not has_infisical:
                    key = item.get("key") or item.get("name") or str(item)
                    missing.append(key)
            elif isinstance(item, str):
                # String-only config requirement: presence check passes
                # (the string itself is the env var name)
                pass

        if missing:
            checks.append(
                ModelCheckResult(
                    check_id=7,
                    check_name="config_readiness",
                    check_class="Config Readiness",
                    passed=False,
                    message=f"Config requirements missing env/Infisical mapping: {missing}",
                )
            )
        else:
            checks.append(
                ModelCheckResult(
                    check_id=7,
                    check_name="config_readiness",
                    check_class="Config Readiness",
                    passed=True,
                    message=f"All {len(items)} config requirements have mappings",
                )
            )

    # ONEX_EXCLUDE: dict_str_any — contract YAML has no fixed Pydantic model
    def _check_codepath_consumption(
        self,
        data: dict[str, Any],
        contract_path: Path,
        checks: list[ModelCheckResult],
    ) -> None:
        """Check 8: Validator parameter compliance via AST analysis.

        If a contract declares parameters, verifies those parameter names
        appear in meaningful execution-relevant code paths in the handler
        (not just imports or comments).
        """
        # Look for parameters declaration
        parameters = data.get("parameters")
        if parameters is None:
            checks.append(
                ModelCheckResult(
                    check_id=8,
                    check_name="codepath_consumption",
                    check_class="Codepath Consumption",
                    passed=True,
                    message="No parameters declared (optional)",
                )
            )
            return

        if not isinstance(parameters, dict):
            checks.append(
                ModelCheckResult(
                    check_id=8,
                    check_name="codepath_consumption",
                    check_class="Codepath Consumption",
                    passed=True,
                    message="Parameters not a dict, skipping AST check",
                )
            )
            return

        param_names = set(parameters.keys())
        if not param_names:
            checks.append(
                ModelCheckResult(
                    check_id=8,
                    check_name="codepath_consumption",
                    check_class="Codepath Consumption",
                    passed=True,
                    message="Empty parameters declaration",
                )
            )
            return

        # Find handler Python files in the same directory
        handler_dir = contract_path.parent
        py_files = list(handler_dir.glob("handler_*.py")) + list(
            handler_dir.glob("handler.py")
        )

        if not py_files:
            checks.append(
                ModelCheckResult(
                    check_id=8,
                    check_name="codepath_consumption",
                    check_class="Codepath Consumption",
                    passed=False,
                    message="Parameters declared but no handler files found",
                )
            )
            return

        # Collect all names referenced in execution-relevant contexts
        consumed_names: set[str] = set()
        for py_file in py_files:
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(py_file))
                consumed_names.update(self._find_consumed_names(tree))
            except (SyntaxError, OSError):
                continue

        unconsumed = param_names - consumed_names
        if unconsumed:
            checks.append(
                ModelCheckResult(
                    check_id=8,
                    check_name="codepath_consumption",
                    check_class="Codepath Consumption",
                    passed=False,
                    message=f"Parameters not consumed in handler code: {sorted(unconsumed)}",
                )
            )
        else:
            checks.append(
                ModelCheckResult(
                    check_id=8,
                    check_name="codepath_consumption",
                    check_class="Codepath Consumption",
                    passed=True,
                    message=f"All {len(param_names)} parameters consumed in handler code",
                )
            )

    @staticmethod
    def _find_consumed_names(tree: ast.AST) -> set[str]:
        """Extract names used in execution-relevant AST contexts.

        Looks for names in assignments, conditionals, function calls,
        subscripts, and comparisons — NOT just imports or string literals.
        """
        names: set[str] = set()
        for node in ast.walk(tree):
            # Names in assignments (targets or values)
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    names.update(_extract_names(target))
                names.update(_extract_names(node.value))
            # Augmented assignments
            elif isinstance(node, ast.AugAssign):
                names.update(_extract_names(node.target))
                names.update(_extract_names(node.value))
            # Conditionals
            elif isinstance(node, ast.If):
                names.update(_extract_names(node.test))
            # Function calls
            elif isinstance(node, ast.Call):
                names.update(_extract_names(node.func))
                for arg in node.args:
                    names.update(_extract_names(arg))
                for kw in node.keywords:
                    names.update(_extract_names(kw.value))
            # Subscripts
            elif isinstance(node, ast.Subscript):
                names.update(_extract_names(node.slice))
            # Comparisons
            elif isinstance(node, ast.Compare):
                names.update(_extract_names(node.left))
                for comp in node.comparators:
                    names.update(_extract_names(comp))
            # Return statements
            elif isinstance(node, ast.Return) and node.value is not None:
                names.update(_extract_names(node.value))
        return names


def _extract_names(node: ast.AST) -> set[str]:
    """Extract all Name.id values from an AST subtree."""
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
        elif isinstance(child, ast.Attribute):
            names.add(child.attr)
        elif isinstance(child, ast.Constant) and isinstance(child.value, str):
            names.add(child.value)
    return names
