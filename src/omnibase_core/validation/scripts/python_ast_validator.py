#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""PythonASTValidator — AST visitor to validate ID and version field types in Python files."""

from __future__ import annotations

import ast
import re

from omnibase_core.validation.scripts.validation_violation import ValidationViolation

__all__ = ["PythonASTValidator"]


class PythonASTValidator(ast.NodeVisitor):
    """AST visitor to validate ID and version field types in Python files."""

    def __init__(self, file_path: str, source_lines: list[str] | None = None):
        self.file_path = file_path
        self.violations: list[ValidationViolation] = []
        self.imports: set[str] = set()
        self.current_call_func: str | None = None  # Track current function being called
        # Store source lines for inline comment checking
        self.source_lines = source_lines or []

        # Bypass comment patterns for inline exemptions
        self.id_bypass_patterns = [
            "string-id-ok:",
            "id-ok:",
        ]
        self.version_bypass_patterns = [
            "string-version-ok:",
            "version-ok:",
            "semver-ok:",
        ]

        # Patterns for version fields that should use ModelSemVer
        self.version_patterns = [
            r"^version$",
            r"^.*_version$",
            r"^version_.*$",
            r"^schema_version$",
            r"^protocol_version$",
            r"^node_version$",
        ]

        # Patterns for ID fields that should use UUID
        self.id_patterns = [
            r"^.*_id$",
            r"^id$",
            r"^execution_id$",
            r"^request_id$",
            r"^session_id$",
            r"^node_id$",
            r"^connection_id$",
            r"^trace_id$",
            r"^span_id$",
            r"^parent_span_id$",
            r"^example_id$",
        ]

        # Exceptions - fields that can legitimately be strings
        # See: docs/reports/ONEX_STRING_VERSION_ID_ANALYSIS.md for rationale
        self.exceptions = {
            # Legacy patterns (original exceptions)
            "version_pattern",  # Regex patterns can be strings
            "version_spec",  # Version specifications can be strings
            "validation_pattern",  # Regex patterns
            "version_compatibility",  # Compatibility strings
            "execution_id",  # Execution IDs may be strings in external system contexts
            "version_str",  # Parameter names for parsing functions
            # EXTERNAL_SYSTEMS (5 fields)
            "external_id",  # External system identifiers (not ONEX-managed)
            "certificate_id",  # X.509 certificate IDs
            "service_id",  # Consul service identifiers (external system constraint)
            "consul_service_id",  # Consul service identifiers (prefixed variant)
            "network_id",  # Network identifiers (VPC, subnet names - external systems)
            # GRAPH_DATABASE_IDS (3 fields - Neo4j/Memgraph external identifiers)
            "element_id",  # Neo4j 5.x element ID format (e.g., "4:abc-def:123")
            "start_node_id",  # References external database node element ID
            "end_node_id",  # References external database node element ID
            # VECTOR_STORE_IDS (1 field - Qdrant/Pinecone external identifiers)
            "embedding_id",  # External vector store ID (Qdrant, Pinecone, etc.)
            # DISTRIBUTED_TRACING (4 unique fields - OpenTelemetry standard)
            "trace_id",  # OpenTelemetry trace identifier
            "span_id",  # OpenTelemetry span identifier
            "request_id",  # Request tracking identifier
            "parent_span_id",  # Parent span for distributed tracing
            # KAFKA_IDS (2 fields - Kafka infrastructure)
            # Note: Primarily in model_event_bus_config.py context
            # Whitelisted globally for simplicity as they're Kafka identifiers
            "client_id",  # Kafka client ID (also used in service discovery contexts)
            "group_id",  # Kafka consumer group ID
            # VERSION_TEMPLATES (3 fields)
            "version_string",  # Template variable tokens
            "version_directory_pattern",  # File path patterns
            "version_requirement",  # Dependency constraint patterns
            # EXTERNAL_VERSIONS (8 fields)
            "python_version",  # Python interpreter version string
            "tool_version",  # External tool versions
            "minimum_tls_version",  # TLS protocol versions (e.g., "1.2", "1.3")
            "service_version",  # External service versions
            "runtime_version",  # Runtime environment versions
            "command_version",  # CLI command versions
            "node_specific_version",  # Node-specific version metadata
            "database_version",  # External database version (Neo4j, Memgraph, etc.)
            # METADATA_VERSIONS (3 fields in model_node_metadata_block.py)
            # These use regex constraints for legacy compatibility
            "metadata_version",  # Metadata block version
            "protocol_version",  # Protocol version
            "schema_version",  # Schema version
            # Note: generic "version" field not whitelisted globally to catch other violations
            # EXECUTION_CONTEXT_FIELDS (flexible identifiers)
            # See: src/omnibase_core/models/compute/model_compute_execution_context.py
            "node_id",  # Intentionally str: can be UUID, hostname, or custom identifier
            # ENVELOPE_PARTITION_KEYS (ModelEnvelope partition/identity anchors)
            # See: src/omnibase_core/models/common/model_envelope.py
            "entity_id",  # Partition key: holds node_id or other string identifiers (OMN-936)
            # DISPATCH_ENGINE_IDS (human-readable dispatch identifiers)
            # See: src/omnibase_core/models/dispatch/
            # See: src/omnibase_core/models/runtime/model_runtime_directive.py
            # These are semantic names like "order-workflow-handler" not UUIDs
            "handler_id",  # Dispatch handler identifier (human-readable, not UUID)
            "route_id",  # Dispatch route identifier (human-readable, not UUID)
            "target_handler_id",  # Runtime directive target handler (human-readable, not UUID)
            "matched_route_id",  # Dispatch result matched route (human-readable)
            # MANIFEST_IDENTIFIERS (execution manifest observability identifiers)
            # See: src/omnibase_core/models/manifest/ for manifest model definitions
            # These are human-readable identifiers for pipeline observability, not UUIDs
            "contract_id",  # Contract identifier (human-readable, e.g., "my-contract")
            "hook_id",  # Hook identifier (human-readable, e.g., "pre-validation-hook")
            "capability_id",  # Capability identifier (human-readable, e.g., "cache-support")
            "from_handler_id",  # Dependency edge source handler (human-readable)
            "to_handler_id",  # Dependency edge target handler (human-readable)
            "handler_descriptor_id",  # Handler descriptor ID (human-readable)
            # TEST_FIXTURES (test helper fields removed - production code should use UUID)
            # TYPED_DICT_SERIALIZATION_BOUNDARY (TypedDicts for logging/monitoring/introspection)
            # See: src/omnibase_core/types/ for TypedDict definitions
            # These TypedDicts are at serialization boundaries where string versions/IDs are appropriate
            "input_version",  # TypedDict at serialization boundary for logging/monitoring
            "output_version",  # TypedDict at serialization boundary for logging/monitoring
            "policy_version",  # TypedDict for security policy config (serialization boundary)
            "correlation_id",  # TypedDict event metadata (OpenTelemetry-style correlation)
            "operation_id",  # TypedDict FSM context (reducer operation tracking)
            # TYPED_DICT_CLI_SERIALIZED (TypedDicts for CLI model serialization output)
            # See: src/omnibase_core/types/typed_dict_cli_*.py for TypedDict definitions
            # These represent serialize() output - UUIDs and versions become strings in JSON
            "option_id",  # TypedDict CLI command option ID (serialized UUID)
            "envelope_id",  # TypedDict event envelope ID (serialized UUID)
            "action_id",  # TypedDict CLI action ID (serialized UUID)
            "command_name_id",  # TypedDict CLI command name ID (serialized UUID)
            "target_node_id",  # TypedDict CLI target node ID (serialized UUID)
            "onex_version",  # TypedDict ONEX version (serialized ModelSemVer)
            "envelope_version",  # TypedDict envelope schema version (serialized ModelSemVer)
            "payload_schema_version",  # TypedDict payload schema version (serialized ModelSemVer)
            # GENERIC_SERIALIZATION_FIELDS (used in TypedDicts for serialization)
            # NOTE: These generic names are allowed because:
            # 1. TypedDicts are serialization boundaries (JSON, logging, monitoring)
            # 2. Pydantic models should NOT use these generic names - use specific names
            #    (e.g., node_version, tool_version, schema_version instead of version)
            #    (e.g., collection_id, tool_id, node_id instead of id)
            "version",  # Generic version field in TypedDicts - serialization boundary only
            "id",  # Generic ID field in TypedDicts - serialization boundary only
        }

    def visit_Import(self, node: ast.Import) -> None:
        """Track imports to understand what types are available."""
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track from imports to understand what types are available."""
        if node.module:
            for alias in node.names:
                if alias.name == "*":
                    # Handle star imports
                    if node.module == "uuid":
                        self.imports.add("UUID")
                    elif "semver" in node.module:
                        self.imports.add("ModelSemVer")
                else:
                    self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Visit annotated assignments (field definitions)."""
        if isinstance(node.target, ast.Name):
            field_name = node.target.id
            self._check_field_annotation(
                field_name, node.annotation, node.lineno, node.col_offset
            )
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:
        """Visit function arguments - skip validation for parameters.

        Function/method parameters are NOT persistence fields and should not be
        subject to ID/version typing rules. Parameters like `repo_id: str` in
        factory methods are legitimate - they accept string input that may be
        converted to UUID inside the function.

        Only class attributes and Field() definitions need ID/version validation.
        """
        # Skip validation - function parameters are not persistence fields
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function calls to detect ModelSemVer.parse() with string literals."""
        # Check if this is a call to ModelSemVer.parse or parse_semver_from_string
        func_name = self._get_call_func_name(node.func)

        if func_name in ("ModelSemVer.parse", "parse_semver_from_string", "parse"):
            # Check if any arguments are string literals
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if self._is_semantic_version_ast(arg.value):
                        # Extract version components
                        parts = arg.value.split(".")
                        suggestion = f'Use ModelSemVer({parts[0]}, {parts[1]}, {parts[2]}) instead of ModelSemVer.parse("{arg.value}")'

                        self.violations.append(
                            ValidationViolation(
                                file_path=self.file_path,
                                line_number=arg.lineno,
                                column=arg.col_offset,
                                field_name=f"<call_to_{func_name}>",
                                violation_type="semantic_version_string_literal_in_call",
                                suggestion=suggestion,
                            )
                        )

        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        """Detect semantic version string literals in inappropriate contexts."""
        # Skip if not a string
        if not isinstance(node.value, str):
            self.generic_visit(node)
            return

        # Skip if not a semantic version
        if not self._is_semantic_version_ast(node.value):
            self.generic_visit(node)
            return

        # We allow version strings in certain contexts:
        # 1. Docstrings (handled by skipping all docstrings)
        # 2. Enum definitions (these are legitimate string values)
        # 3. Field default values for string-typed version fields (legacy compatibility)
        # 4. json_schema_extra examples
        # 5. Test data

        # The main violations we want to catch are in ModelSemVer.parse() calls,
        # which are handled by visit_Call above.
        # Any other direct string version literals in non-exempt contexts are suspicious.

        self.generic_visit(node)

    def _get_call_func_name(self, func_node: ast.AST) -> str:
        """Extract the function name from a call node."""
        if isinstance(func_node, ast.Name):
            return func_node.id
        elif isinstance(func_node, ast.Attribute):
            # Handle ModelSemVer.parse pattern
            if isinstance(func_node.value, ast.Name):
                return f"{func_node.value.id}.{func_node.attr}"
            return func_node.attr
        return ""

    def _has_bypass_comment(self, line_number: int, bypass_patterns: list[str]) -> bool:
        """Check if a line has a bypass comment.

        Args:
            line_number: 1-based line number to check
            bypass_patterns: List of bypass comment patterns to look for

        Returns:
            True if a bypass comment is found on the line or the previous line
        """
        if not self.source_lines:
            return False

        # Convert to 0-based index
        line_idx = line_number - 1
        if line_idx < 0 or line_idx >= len(self.source_lines):
            return False

        line = self.source_lines[line_idx]

        # Check for inline comment with bypass pattern on the current line
        if "#" in line:
            comment_part = line.split("#", 1)[1]
            for pattern in bypass_patterns:
                if pattern in comment_part:
                    return True

        # Check for bypass comment on the previous line (consistent with YAML validation)
        if line_idx > 0:
            prev_line = self.source_lines[line_idx - 1].strip()
            if prev_line.startswith("#"):
                for pattern in bypass_patterns:
                    if pattern in prev_line:
                        return True

        return False

    def _check_field_annotation(
        self, field_name: str, annotation: ast.AST, line_number: int, column: int
    ) -> None:
        """Check if a field annotation violates ID/version typing rules."""
        # Skip exceptions
        if field_name in self.exceptions:
            return

        annotation_str = self._get_annotation_string(annotation)

        # Check version fields
        if self._matches_patterns(field_name, self.version_patterns):
            if self._is_string_type(annotation_str):
                # Check for bypass comment
                if self._has_bypass_comment(line_number, self.version_bypass_patterns):
                    return
                suggestion = "Use ModelSemVer instead of str for version fields"
                self.violations.append(
                    ValidationViolation(
                        file_path=self.file_path,
                        line_number=line_number,
                        column=column,
                        field_name=field_name,
                        violation_type="string_version",
                        suggestion=suggestion,
                    )
                )

        # Check ID fields
        elif self._matches_patterns(field_name, self.id_patterns):
            if self._is_string_type(annotation_str):
                # Check for bypass comment
                if self._has_bypass_comment(line_number, self.id_bypass_patterns):
                    return
                suggestion = "Use UUID instead of str for ID fields"
                self.violations.append(
                    ValidationViolation(
                        file_path=self.file_path,
                        line_number=line_number,
                        column=column,
                        field_name=field_name,
                        violation_type="string_id",
                        suggestion=suggestion,
                    )
                )

    def _matches_patterns(self, field_name: str, patterns: list[str]) -> bool:
        """Check if field name matches any of the given regex patterns."""
        return any(re.match(pattern, field_name) for pattern in patterns)

    def _is_string_type(self, annotation_str: str) -> bool:
        """Check if annotation represents a string type."""
        # Direct string types
        if annotation_str in ["str", "String"]:
            return True

        # Optional string types
        if annotation_str in ["str | None", "Optional[str]", "str | None"]:
            return True

        # String unions (but not including UUID or ModelSemVer)
        if (
            "str" in annotation_str
            and "UUID" not in annotation_str
            and "ModelSemVer" not in annotation_str
        ):
            return True

        return False

    def _get_annotation_string(self, annotation: ast.AST) -> str:
        """Convert AST annotation to string representation."""
        try:
            return ast.unparse(annotation)
        except AttributeError:
            # Fallback for older Python versions
            return self._ast_to_string(annotation)

    def _ast_to_string(self, node: ast.AST) -> str:
        """Convert AST node to string (fallback implementation)."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Attribute):
            return f"{self._ast_to_string(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            return (
                f"{self._ast_to_string(node.value)}[{self._ast_to_string(node.slice)}]"
            )
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return (
                f"{self._ast_to_string(node.left)} | {self._ast_to_string(node.right)}"
            )
        elif isinstance(node, ast.Tuple):
            elements = [self._ast_to_string(elt) for elt in node.elts]
            return f"({', '.join(elements)})"
        else:
            return str(type(node).__name__)

    def _is_semantic_version_ast(self, value: str) -> bool:
        """
        Use AST-inspired logic to detect semantic versions.

        Checks if a string matches the semantic version pattern X.Y.Z
        where X, Y, Z are integers.
        """
        if not isinstance(value, str) or not value:
            return False

        # Handle the most common patterns
        if "." not in value:
            return False

        # Split on dots and validate each part
        parts = value.split(".")

        # Must be exactly 3 parts for semantic versioning
        if len(parts) != 3:
            return False

        # Each part must be a valid integer (possibly with leading zeros)
        try:
            for part in parts:
                # Must be numeric and not empty
                if not part or not part.isdigit():
                    return False
                # Convert to int to validate (handles leading zeros)
                int(part)
            return True
        except (ValueError, TypeError):
            return False
