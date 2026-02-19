# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Duplicate protocols rule - detect protocol classes defined in multiple files.

Catches DRY violations and copy-paste drift by flagging when the same
protocol class name appears in multiple files within a repo.

Related ticket: OMN-1906
"""

from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.validation.model_rule_configs import (
    ModelRuleDuplicateProtocolsConfig,
)
from omnibase_core.validation.cross_repo.util_exclusion import (
    get_relative_path_safe,
    should_exclude_path,
)
from omnibase_core.validation.cross_repo.util_fingerprint import generate_fingerprint

if TYPE_CHECKING:
    from omnibase_core.validation.cross_repo.scanners.scanner_import_graph import (
        ModelFileImports,
    )


class RuleDuplicateProtocols:
    """Detects protocol classes with the same name in multiple files.

    Flags when a class ending in the configured suffix (default: 'Protocol')
    is defined in multiple files, indicating potential DRY violations.
    """

    rule_id: ClassVar[str] = "duplicate_protocols"  # string-id-ok: rule registry key
    requires_scanners: ClassVar[list[str]] = []  # Uses file discovery, parses AST

    def __init__(self, config: ModelRuleDuplicateProtocolsConfig) -> None:
        """Initialize with rule configuration.

        Args:
            config: Typed configuration for this rule.
        """
        self.config = config

    def validate(
        self,
        file_imports: dict[Path, ModelFileImports],
        repo_id: str,  # string-id-ok: human-readable repository identifier
        root_directory: Path | None = None,
    ) -> list[ModelValidationIssue]:
        """Find duplicate protocol definitions across files.

        Args:
            file_imports: Map of file paths to their imports.
            repo_id: The repository being validated.
            root_directory: Root directory being validated.

        Returns:
            List of validation issues for duplicate protocols.
        """
        if not self.config.enabled:
            return []

        # Collect all protocol definitions: {protocol_name: [(file, line)]}
        protocol_locations: dict[str, list[tuple[Path, int]]] = defaultdict(list)

        for file_path in file_imports:
            if should_exclude_path(
                file_path, root_directory, self.config.exclude_patterns
            ):
                continue

            protocols = self._find_protocols_in_file(file_path)
            for protocol_name, line_number in protocols:
                protocol_locations[protocol_name].append((file_path, line_number))

        # Generate issues for protocols defined in multiple files
        issues: list[ModelValidationIssue] = []

        for protocol_name, locations in protocol_locations.items():
            if len(locations) > 1:
                # Create an issue for each location
                file_list = [str(loc[0]) for loc in locations]
                for file_path, line_number in locations:
                    # Compute relative path for stable fingerprints across environments
                    relative_path = get_relative_path_safe(file_path, root_directory)
                    fingerprint = generate_fingerprint(
                        self.rule_id, str(relative_path), protocol_name
                    )
                    other_files = [f for f in file_list if f != str(file_path)]

                    issues.append(
                        ModelValidationIssue(
                            severity=self.config.severity,
                            message=f"Protocol '{protocol_name}' is defined in {len(locations)} files",
                            code="DUPLICATE_PROTOCOL",
                            file_path=file_path,
                            line_number=line_number,
                            rule_name=self.rule_id,
                            suggestion="Consider consolidating protocol definitions to avoid drift",
                            context={
                                "fingerprint": fingerprint,
                                "protocol_name": protocol_name,
                                "other_files": ", ".join(other_files),
                                "total_definitions": str(len(locations)),
                                "symbol": protocol_name,
                            },
                        )
                    )

        return issues

    def _find_protocols_in_file(
        self,
        file_path: Path,
    ) -> list[tuple[str, int]]:
        protocols: list[tuple[str, int]] = []

        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file_path))
        except (OSError, SyntaxError, UnicodeDecodeError):
            # Skip files that can't be read or parsed
            return protocols

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            if self._is_protocol_class(node):
                protocols.append((node.name, node.lineno))

        return protocols

    def _is_protocol_class(self, node: ast.ClassDef) -> bool:
        # Note: Aliased imports (e.g., "from typing import Protocol as P") are not
        # detected. The suffix check (e.g., "FooProtocol") provides primary coverage.

        # Check class name ends with configured suffix
        if node.name.endswith(self.config.protocol_suffix):
            return True

        # Also check if it inherits from Protocol (including qualified imports)
        # Handles: Protocol, typing.Protocol, typing_extensions.Protocol
        for base in node.bases:
            base_name = self._get_base_name(base)
            if base_name is None:
                continue
            # Check for simple "Protocol" or qualified names ending with ".Protocol"
            if base_name == "Protocol" or base_name.endswith(".Protocol"):
                return True

        return False

    def _get_base_name(self, base: ast.expr) -> str | None:
        """Get the name of a base class from AST.

        Handles simple names (e.g., Protocol), qualified names
        (e.g., typing.Protocol), and subscripted generics (e.g., Protocol[T]).

        Args:
            base: Base class AST expression.

        Returns:
            Name of the base class (fully qualified for attribute access),
            or None if can't determine.
        """
        if isinstance(base, ast.Name):
            return base.id
        if isinstance(base, ast.Attribute):
            # Return fully qualified name (e.g., "typing.Protocol")
            value_name = self._get_base_name(base.value)
            if value_name:
                return f"{value_name}.{base.attr}"
            return base.attr
        if isinstance(base, ast.Subscript):
            # Handle subscripted generics like Protocol[T] or typing.Protocol[T]
            return self._get_base_name(base.value)
        return None
