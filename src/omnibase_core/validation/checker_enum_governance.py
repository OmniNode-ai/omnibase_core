"""
CheckerEnumGovernance - Contract-driven validator for enum governance rules.

This module provides comprehensive enum governance validation including:
- ENUM_001: Member casing enforcement (UPPER_SNAKE_CASE)
- ENUM_002: Literal type alias detection (suggest Enum conversion)
- ENUM_003: Duplicate enum value detection across files

Key Features:
    - Multi-phase scanning for deterministic cross-file analysis
    - Contract-driven configuration via ModelValidatorSubcontract
    - AST-based analysis for accurate enum and Literal detection
    - Approved overlaps support for intentional duplicate values

Usage Examples:
    Programmatic usage::

        from pathlib import Path
        from omnibase_core.validation.checker_enum_governance import CheckerEnumGovernance

        validator = CheckerEnumGovernance()
        result = validator.validate(Path("src/"))
        if not result.is_valid:
            for issue in result.issues:
                print(f"{issue.file_path}:{issue.line_number}: {issue.message}")

    CLI usage::

        python -m omnibase_core.validation.checker_enum_governance src/

Thread Safety:
    CheckerEnumGovernance instances are NOT thread-safe. Create separate instances
    for concurrent use or protect with external synchronization.

Schema Version:
    v1.0.0 - Initial version (OMN-1313)

See Also:
    - ValidatorBase: Base class for contract-driven validators
    - checker_enum_member_casing: Reused UPPER_SNAKE_CASE pattern and suggestion
"""

# NOTE(OMN-1313): This file contains tightly coupled data classes and visitor
# for the governance validator. Splitting would create unnecessary complexity.
# Excluded from single-class-per-file validation.

import ast
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation.checker_enum_member_casing import (
    ENUM_BASE_NAMES,
    UPPER_SNAKE_CASE_PATTERN,
    suggest_upper_snake_case,
)
from omnibase_core.validation.validator_base import ValidatorBase

# Configure logger for this module
logger = logging.getLogger(__name__)

# Rule IDs for enum governance
RULE_ENUM_MEMBER_CASING = "enum_member_casing"
RULE_LITERAL_SHOULD_BE_ENUM = "literal_should_be_enum"
RULE_DUPLICATE_ENUM_VALUES = "duplicate_enum_values"

# Pattern words that suggest a Literal might be better as an Enum
ENUM_PATTERN_WORDS = frozenset(
    {
        "Status",
        "State",
        "Phase",
        "Mode",
        "Health",
        "Type",
        "Kind",
        "Level",
        "Category",
        "Priority",
        "Severity",
        "Stage",
        "Role",
        "Action",
        "Result",
        "Outcome",
    }
)


@dataclass(frozen=True)
class _CollectedEnumData:
    """Information about an enum class discovered during scanning.

    Attributes:
        name: The class name of the enum.
        file_path: Path to the file containing the enum.
        line_number: Line number where the enum is defined.
        values: Frozenset of string values assigned to enum members.
        member_names: Tuple of member names (for casing validation).
    """

    name: str
    file_path: Path
    line_number: int
    values: frozenset[str]
    member_names: tuple[str, ...]


@dataclass(frozen=True)
class LiteralAliasInfo:
    """Information about a Literal type alias discovered during scanning.

    Attributes:
        name: The alias name.
        file_path: Path to the file containing the alias.
        line_number: Line number where the alias is defined.
        values: Tuple of string values in the Literal.
    """

    name: str
    file_path: Path
    line_number: int
    values: tuple[str, ...]


class GovernanceASTVisitor(ast.NodeVisitor):
    """AST visitor for collecting enum and Literal type alias information.

    Collects metadata about enums and module-scope Literal type aliases
    for governance validation.

    Attributes:
        file_path: Path to the file being analyzed.
        enums: List of _CollectedEnumData objects found.
        literal_aliases: List of LiteralAliasInfo objects found.
    """

    def __init__(self, file_path: Path) -> None:
        """Initialize the visitor.

        Args:
            file_path: Path to the source file being analyzed.
        """
        self.file_path = file_path
        self.enums: list[_CollectedEnumData] = []
        self.literal_aliases: list[LiteralAliasInfo] = []
        self._scope_stack: list[str] = []  # Track current scope

    def _is_enum_class(self, node: ast.ClassDef) -> bool:
        """Check if a class definition is an Enum subclass.

        Args:
            node: The AST ClassDef node to check.

        Returns:
            True if the class is an Enum subclass, False otherwise.
        """
        for base in node.bases:
            base_name = self._extract_base_name(base)
            if base_name is None:
                continue

            # Direct match with known enum bases
            if base_name in ENUM_BASE_NAMES:
                return True

            # Heuristic: class name ends with "Enum" (e.g., MyCustomEnum)
            if base_name.endswith("Enum"):
                return True

        return False

    def _extract_base_name(self, base: ast.expr) -> str | None:
        """Extract the name from a base class expression.

        Args:
            base: AST expression node representing a base class.

        Returns:
            The base class name as a string, or None if it cannot be extracted.
        """
        if isinstance(base, ast.Name):
            return base.id
        if isinstance(base, ast.Attribute):
            return base.attr
        return None

    def _extract_enum_member_info(
        self, node: ast.stmt
    ) -> tuple[str | None, str | None]:
        """Extract member name and string value from an enum assignment.

        Args:
            node: AST statement node to check.

        Returns:
            Tuple of (member_name, string_value) or (None, None) if not a member.
        """
        target: ast.expr | None = None
        value: ast.expr | None = None

        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            value = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            target = node.target
            value = node.value

        if target is None or not isinstance(target, ast.Name):
            return None, None

        name = target.id

        # Skip dunder and private names
        if name.startswith("_"):
            return None, None

        # Extract string value if present
        str_value: str | None = None
        if value is not None:
            str_value = self._extract_string_value(value)

        return name, str_value

    def _extract_string_value(self, node: ast.expr) -> str | None:
        """Extract string value from an AST expression.

        Args:
            node: AST expression node.

        Returns:
            String value if the expression is a string constant, None otherwise.
        """
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions to detect enums.

        Args:
            node: The AST ClassDef node.
        """
        if self._is_enum_class(node):
            member_names: list[str] = []
            string_values: set[str] = set()

            for stmt in node.body:
                member_name, str_value = self._extract_enum_member_info(stmt)
                if member_name is not None:
                    member_names.append(member_name)
                    if str_value is not None:
                        string_values.add(str_value)

            self.enums.append(
                _CollectedEnumData(
                    name=node.name,
                    file_path=self.file_path,
                    line_number=node.lineno,
                    values=frozenset(string_values),
                    member_names=tuple(member_names),
                )
            )

        # Track scope for nested class detection
        self._scope_stack.append(node.name)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Track function scope to exclude nested Literals.

        Args:
            node: The AST FunctionDef node.
        """
        self._scope_stack.append(node.name)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Track async function scope to exclude nested Literals.

        Args:
            node: The AST AsyncFunctionDef node.
        """
        self._scope_stack.append(node.name)
        self.generic_visit(node)
        self._scope_stack.pop()

    def _is_module_scope(self) -> bool:
        """Check if currently at module scope.

        Returns:
            True if at module scope (not inside function or class).
        """
        return len(self._scope_stack) == 0

    def _extract_literal_values(self, node: ast.expr) -> tuple[str, ...] | None:
        """Extract string values from a Literal type annotation.

        Handles both Literal[...] and typing.Literal[...] patterns.

        Args:
            node: AST expression node representing the type annotation.

        Returns:
            Tuple of string values if valid Literal, None otherwise.
        """
        # Check for Literal[...] or typing.Literal[...]
        if not isinstance(node, ast.Subscript):
            return None

        # Get the base name
        base = node.value
        base_name: str | None = None

        if isinstance(base, ast.Name):
            base_name = base.id
        elif isinstance(base, ast.Attribute):
            base_name = base.attr

        if base_name != "Literal":
            return None

        # Extract the slice (the values inside Literal[...])
        slice_node = node.slice

        values: list[str] = []

        # Handle Literal["a", "b", "c"] (tuple of values)
        if isinstance(slice_node, ast.Tuple):
            for elt in slice_node.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    values.append(elt.value)
                else:
                    # Non-string value in Literal, skip this alias
                    return None
        # Handle Literal["single"] (single value)
        elif isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
            values.append(slice_node.value)
        else:
            return None

        return tuple(values) if values else None

    def _check_literal_alias(
        self, name: str, annotation: ast.expr, lineno: int
    ) -> None:
        """Check if an assignment is a Literal type alias.

        Args:
            name: The alias name.
            annotation: The AST expression for the annotation/value.
            lineno: Line number of the assignment.
        """
        if not self._is_module_scope():
            return

        values = self._extract_literal_values(annotation)
        if values is not None:
            self.literal_aliases.append(
                LiteralAliasInfo(
                    name=name,
                    file_path=self.file_path,
                    line_number=lineno,
                    values=values,
                )
            )

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignments to detect Literal type aliases.

        Args:
            node: The AST Assign node.
        """
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            self._check_literal_alias(node.targets[0].id, node.value, node.lineno)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Visit annotated assignments to detect Literal type aliases.

        Handles patterns like: MyType: TypeAlias = Literal["a", "b"]

        Args:
            node: The AST AnnAssign node.
        """
        if isinstance(node.target, ast.Name) and node.value is not None:
            self._check_literal_alias(node.target.id, node.value, node.lineno)
        self.generic_visit(node)


class CheckerEnumGovernance(ValidatorBase):
    """Validator for enum governance rules.

    Implements three governance rules:
    - ENUM_001: Enum member casing (UPPER_SNAKE_CASE)
    - ENUM_002: Literal type aliases that should be Enums
    - ENUM_003: Duplicate enum values across files

    Uses multi-phase scanning to ensure deterministic cross-file analysis.

    Thread Safety:
        CheckerEnumGovernance instances are NOT thread-safe due to internal
        mutable state inherited from ValidatorBase and the multi-phase scanning
        state (_all_enums, _all_literals).

    Attributes:
        validator_id: Unique identifier for this validator ("enum-governance").
    """

    validator_id: ClassVar[str] = "enum-governance"  # string-id-ok: registry key

    def __init__(self, contract: ModelValidatorSubcontract | None = None) -> None:
        """Initialize the enum governance validator.

        Args:
            contract: Pre-loaded validator contract. If None, the contract
                will be loaded from the default YAML location when first accessed.
        """
        super().__init__(contract)
        # Thread safety: The following instance variables maintain state across
        # multi-phase scanning and prevent thread-safe reuse. Each worker process
        # MUST create its own validator instance. See docs/guides/THREADING.md.
        self._all_enums: list[_CollectedEnumData] = []
        self._all_literals: list[LiteralAliasInfo] = []
        self._phase_a_complete: bool = False

    def validate(
        self,
        targets: Path | list[Path],
    ) -> ModelValidationResult[None]:
        """Validate target files with multi-phase scanning.

        Phase A: Scan all files and collect enum/literal metadata.
        Phase B: Run local validations (ENUM_001, ENUM_002).
        Phase C: Run global validations (ENUM_003).

        Args:
            targets: Single path or list of paths to validate.

        Returns:
            ModelValidationResult containing all issues found.
        """
        start_time = time.time()

        # Normalize to list
        if isinstance(targets, Path):
            targets = [targets]

        # Resolve all target files
        resolved_files = self._resolve_targets(targets)

        # Filter excluded files
        files_to_validate = [f for f in resolved_files if not self._is_excluded(f)]

        # Reset multi-phase state
        self._all_enums = []
        self._all_literals = []
        self._phase_a_complete = False

        # Phase A: Scan all files first
        for file_path in files_to_validate:
            self._scan_file(file_path)
        self._phase_a_complete = True

        # Phase B & C: Run validations
        all_issues: list[ModelValidationIssue] = []
        files_with_violations: list[str] = []

        try:
            for file_path in files_to_validate:
                file_issues = self._validate_file_with_suppression(file_path)
                if file_issues:
                    all_issues.extend(file_issues)
                    files_with_violations.append(str(file_path))

                # Check violation limit
                if (
                    self.contract.max_violations > 0
                    and len(all_issues) >= self.contract.max_violations
                ):
                    break

            # Phase C: Global validations (ENUM_003 - duplicate values)
            global_issues = self._validate_global()
            all_issues.extend(global_issues)

            duration_ms = int((time.time() - start_time) * 1000)

            return self._build_result(
                files_checked=files_to_validate,
                issues=all_issues,
                files_with_violations=files_with_violations,
                duration_ms=duration_ms,
            )
        finally:
            # Clear caches
            self._file_line_cache.clear()
            self._all_enums = []
            self._all_literals = []
            self._phase_a_complete = False

    def _scan_file(self, path: Path) -> None:
        """Scan a file and collect enum/literal metadata.

        Args:
            path: Path to the Python file to scan.
        """
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as e:
            # fallback-ok: log warning and skip file on read errors
            logger.warning("Cannot read file %s: %s", path, e)
            return

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as e:
            # fallback-ok: log warning and skip file with syntax errors
            logger.warning(
                "Skipping file with syntax error: path=%s, line=%s, error=%s",
                path,
                e.lineno,
                e.msg,
            )
            return

        visitor = GovernanceASTVisitor(path)
        visitor.visit(tree)

        self._all_enums.extend(visitor.enums)
        self._all_literals.extend(visitor.literal_aliases)

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        """Validate a single file for enum governance violations.

        Implements ENUM_001 (member casing) and ENUM_002 (Literal aliases).

        Args:
            path: Path to the Python file to validate.
            contract: Validator contract with configuration.

        Returns:
            Tuple of ModelValidationIssue instances for violations found.
        """
        issues: list[ModelValidationIssue] = []

        # Get enums and literals for this file from phase A data
        file_enums = [e for e in self._all_enums if e.file_path == path]
        file_literals = [lit for lit in self._all_literals if lit.file_path == path]

        # ENUM_001: Member casing validation
        enum_001_issues = self._validate_enum_001(file_enums, contract)
        issues.extend(enum_001_issues)

        # ENUM_002: Literal alias validation
        enum_002_issues = self._validate_enum_002(file_literals, contract)
        issues.extend(enum_002_issues)

        return tuple(issues)

    def _validate_enum_001(
        self,
        enums: list[_CollectedEnumData],
        contract: ModelValidatorSubcontract,
    ) -> list[ModelValidationIssue]:
        """Validate ENUM_001: Enum member casing.

        Args:
            enums: List of _CollectedEnumData objects to validate.
            contract: Validator contract with configuration.

        Returns:
            List of validation issues for casing violations.
        """
        enabled, severity = self._get_rule_config(RULE_ENUM_MEMBER_CASING, contract)
        if not enabled:
            return []

        issues: list[ModelValidationIssue] = []

        for enum_info in enums:
            for member_name in enum_info.member_names:
                if not UPPER_SNAKE_CASE_PATTERN.match(member_name):
                    suggested = suggest_upper_snake_case(member_name)
                    issues.append(
                        ModelValidationIssue(
                            severity=severity,
                            message=(
                                f"{enum_info.name}.{member_name} violates "
                                f"UPPER_SNAKE_CASE"
                            ),
                            code=RULE_ENUM_MEMBER_CASING,
                            file_path=enum_info.file_path,
                            line_number=enum_info.line_number,
                            rule_name="enum_member_casing",
                            suggestion=f"Rename to {suggested}",
                        )
                    )

        return issues

    def _validate_enum_002(
        self,
        literals: list[LiteralAliasInfo],
        contract: ModelValidatorSubcontract,
    ) -> list[ModelValidationIssue]:
        """Validate ENUM_002: Literal aliases that should be Enums.

        All 4 conditions must be met to flag a Literal:
        1. Module-scope only (already filtered by visitor)
        2. Alias name matches pattern word (Status, State, etc.)
        3. Minimum 3 string values in the Literal
        4. Values look like status vocabulary OR in allowed_aliases

        Args:
            literals: List of LiteralAliasInfo objects to validate.
            contract: Validator contract with configuration.

        Returns:
            List of validation issues for Literal aliases.
        """
        enabled, severity = self._get_rule_config(RULE_LITERAL_SHOULD_BE_ENUM, contract)
        if not enabled:
            return []

        # Get rule parameters with type narrowing
        rule_params = self._get_rule_parameters(RULE_LITERAL_SHOULD_BE_ENUM, contract)
        min_values_raw = rule_params.get("min_values", 3)
        min_values = (
            int(min_values_raw) if isinstance(min_values_raw, (int, float)) else 3
        )
        allowed_aliases_raw = rule_params.get("allowed_aliases", [])
        allowed_aliases: set[str] = (
            set(allowed_aliases_raw) if isinstance(allowed_aliases_raw, list) else set()
        )

        issues: list[ModelValidationIssue] = []

        for literal_info in literals:
            # Condition 2: Alias name matches pattern word
            name_matches_pattern = any(
                pattern_word in literal_info.name for pattern_word in ENUM_PATTERN_WORDS
            )
            if not name_matches_pattern:
                continue

            # Condition 3: Minimum values
            if len(literal_info.values) < min_values:
                continue

            # Check if in allowed aliases (skip if allowed)
            if literal_info.name in allowed_aliases:
                continue

            # Condition 4: Values look like status vocabulary
            if not self._values_look_like_enum(literal_info.values):
                continue

            # All conditions met - flag this Literal
            issues.append(
                ModelValidationIssue(
                    severity=severity,
                    message=(
                        f"Literal type alias '{literal_info.name}' with "
                        f"{len(literal_info.values)} values should be an Enum"
                    ),
                    code=RULE_LITERAL_SHOULD_BE_ENUM,
                    file_path=literal_info.file_path,
                    line_number=literal_info.line_number,
                    rule_name="literal_should_be_enum",
                    suggestion=(
                        f"Convert to Enum class: class {literal_info.name}(str, Enum)"
                    ),
                )
            )

        return issues

    def _values_look_like_enum(self, values: tuple[str, ...]) -> bool:
        """Check if Literal values look like enum vocabulary.

        Values that look like enum vocabulary:
        - Lowercase with underscores (e.g., "in_progress", "completed")
        - Short identifiers (single words like "active", "pending")
        - ALL_CAPS (already enum-like)

        Args:
            values: Tuple of string values to check.

        Returns:
            True if values look like enum vocabulary.
        """
        enum_like_count = 0
        for value in values:
            # Check for:
            # - lowercase/underscore pattern (snake_case or lowercase)
            # - ALL_CAPS
            # - short single words
            is_enum_like = (
                value.islower()
                or "_" in value.lower()
                or (value.isupper() and "_" in value)
                or (len(value) <= 20 and value.isalpha())
            )
            if is_enum_like:
                enum_like_count += 1

        # Most values should look enum-like
        return enum_like_count >= len(values) * 0.6

    def _validate_global(self) -> list[ModelValidationIssue]:
        """Validate global rules (ENUM_003: duplicate enum values).

        Returns:
            List of validation issues for global violations.
        """
        enabled, severity = self._get_rule_config(
            RULE_DUPLICATE_ENUM_VALUES, self.contract
        )
        if not enabled:
            return []

        # Get rule parameters with type narrowing
        rule_params = self._get_rule_parameters(
            RULE_DUPLICATE_ENUM_VALUES, self.contract
        )
        require_name_similarity_raw = rule_params.get("require_name_similarity", True)
        # Handle string "true"/"false" from YAML in addition to bool
        if isinstance(require_name_similarity_raw, str):
            require_name_similarity = require_name_similarity_raw.lower() in (
                "true",
                "1",
                "yes",
            )
        elif isinstance(require_name_similarity_raw, bool):
            require_name_similarity = require_name_similarity_raw
        else:
            require_name_similarity = True

        approved_overlaps_raw = rule_params.get("approved_overlaps", [])

        # Parse approved overlaps into frozenset of tuples
        # approved_overlaps in YAML is a list of [enum_a, enum_b] pairs
        approved_overlaps: set[frozenset[str]] = set()
        if isinstance(approved_overlaps_raw, list):
            for overlap_item in approved_overlaps_raw:
                # Handle "EnumA,EnumB" string format
                if isinstance(overlap_item, str) and "," in overlap_item:
                    parts = [p.strip() for p in overlap_item.split(",")]
                    if len(parts) == 2 and all(parts):
                        approved_overlaps.add(frozenset(parts))

        issues: list[ModelValidationIssue] = []

        # Compare all enum pairs
        for i, enum_a in enumerate(self._all_enums):
            for enum_b in self._all_enums[i + 1 :]:
                # Skip if no values or empty values
                if not enum_a.values or not enum_b.values:
                    continue

                # Check for overlapping values
                overlap = enum_a.values & enum_b.values
                if not overlap:
                    continue

                # Check if this pair is in approved overlaps
                pair_key = frozenset([enum_a.name, enum_b.name])
                if pair_key in approved_overlaps:
                    continue

                # If require_name_similarity, both names must contain pattern words
                if require_name_similarity:
                    name_a_has_pattern = any(
                        word in enum_a.name for word in ENUM_PATTERN_WORDS
                    )
                    name_b_has_pattern = any(
                        word in enum_b.name for word in ENUM_PATTERN_WORDS
                    )
                    if not (name_a_has_pattern and name_b_has_pattern):
                        continue

                # Flag the overlap
                overlap_list = sorted(overlap)[:5]  # Limit to 5 for readability
                overlap_str = ", ".join(f"'{v}'" for v in overlap_list)
                if len(overlap) > 5:
                    overlap_str += f" (and {len(overlap) - 5} more)"

                issues.append(
                    ModelValidationIssue(
                        severity=severity,
                        message=(
                            f"Enums '{enum_a.name}' and '{enum_b.name}' have "
                            f"{len(overlap)} overlapping values: {overlap_str}"
                        ),
                        code=RULE_DUPLICATE_ENUM_VALUES,
                        file_path=enum_a.file_path,
                        line_number=enum_a.line_number,
                        rule_name="duplicate_enum_values",
                        suggestion=(
                            "Consider extracting shared values to a common enum "
                            "or adding to approved_overlaps"
                        ),
                        context={
                            "enum_a": enum_a.name,
                            "enum_b": enum_b.name,
                            "file_b": str(enum_b.file_path),
                            "overlap_count": str(len(overlap)),
                        },
                    )
                )

        return issues

    def _get_rule_parameters(
        self,
        rule_id: str,  # string-id-ok: contract rule identifier
        contract: ModelValidatorSubcontract,
    ) -> dict[str, str | int | float | bool | list[str]]:
        """Get rule-specific parameters from the contract.

        Args:
            rule_id: The rule identifier to look up.
            contract: Validator contract with rule configurations.

        Returns:
            Dictionary of rule parameters, or empty dict if not found.
        """
        for rule in contract.rules:
            if rule.rule_id == rule_id and rule.parameters is not None:
                return rule.parameters
        return {}


# CLI entry point
if __name__ == "__main__":
    sys.exit(CheckerEnumGovernance.main())


__all__ = [
    "CheckerEnumGovernance",
    "GovernanceASTVisitor",
    "LiteralAliasInfo",
    "RULE_DUPLICATE_ENUM_VALUES",
    "RULE_ENUM_MEMBER_CASING",
    "RULE_LITERAL_SHOULD_BE_ENUM",
]
