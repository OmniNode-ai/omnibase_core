"""
Enum Governance Checker for ONEX Codebase.

This module enforces enum governance rules for the omnibase_core codebase.
It is designed to be run as a pre-commit hook or standalone validation tool.

Key Features:
    - Enum member casing validation (UPPER_SNAKE_CASE)
    - Literal type duplication detection
    - AST-based analysis for accurate detection
    - CI-friendly exit codes (0=pass, 1=fail)

P0 Rules (Block in CI):
    - E001: Enum member must use UPPER_SNAKE_CASE
    - E002: Literal type duplicates enum values

Usage Examples:
    As a module (validates src/omnibase_core by default)::

        poetry run python -m omnibase_core.validation.checker_enum_governance

    With a specific directory::

        poetry run python -m omnibase_core.validation.checker_enum_governance /path/to/dir

    With verbose output::

        poetry run python -m omnibase_core.validation.checker_enum_governance -v

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===================================================
This module is part of a carefully managed import chain to avoid circular
dependencies.

Safe Runtime Imports (OK to import at module level):
    - Standard library modules only

Note:
    This module intentionally uses only standard library imports to ensure
    it can be used in pre-commit hooks without additional dependencies.
"""

import argparse
import ast
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Pattern for UPPER_SNAKE_CASE validation
UPPER_SNAKE_CASE_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$")


@dataclass(frozen=True)
class GovernanceViolation:
    """Represents a single enum governance violation.

    Attributes:
        file_path: Path to the file containing the violation
        line: Line number where the violation occurs
        rule_code: Rule identifier (e.g., E001, E002)
        message: Human-readable description of the violation
        severity: Either "ERROR" or "WARNING"
    """

    file_path: Path
    line: int
    rule_code: str
    message: str
    severity: str = "ERROR"

    def __str__(self) -> str:
        """Format violation for output."""
        return f"{self.severity}: {self.file_path}:{self.line} - {self.rule_code}: {self.message}"


@dataclass(frozen=True)
class MemberInfo:
    """Information about an enum member.

    Attributes:
        enum_name: Name of the enum class
        member_name: Name of the enum member
        member_value: String value of the enum member (if available)
        file_path: Path to the file containing the enum
        line: Line number of the enum member
    """

    enum_name: str
    member_name: str
    member_value: str | None
    file_path: Path
    line: int


class CollectorAST(ast.NodeVisitor):
    """AST visitor that collects enum class definitions and their members.

    Attributes:
        enums: Dictionary mapping enum names to their member info list
        file_path: Path to the file being analyzed
    """

    def __init__(self, file_path: Path) -> None:
        """Initialize the collector.

        Args:
            file_path: Path to the source file being analyzed
        """
        self.file_path = file_path
        self.enums: dict[str, list[MemberInfo]] = {}

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit a class definition to check if it's an enum.

        Args:
            node: The AST ClassDef node
        """
        # Check if this class inherits from Enum
        is_enum = False
        for base in node.bases:
            base_name = self._get_base_name(base)
            # Note: "str, Enum" is NOT needed here because for `class Foo(str, Enum)`,
            # the AST represents multiple bases, each checked separately. The "Enum"
            # check handles this case since _get_base_name() returns individual names.
            if base_name in {
                "Enum",
                "IntEnum",
                "StrEnum",
                "Flag",
                "IntFlag",
            }:
                is_enum = True
                break

        if is_enum:
            self.enums[node.name] = []

            # Process class body to find enum members
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            member_name = target.id
                            # Skip dunder and private members during collection
                            if member_name.startswith("_"):
                                continue
                            member_value = self._extract_value(item.value)
                            self.enums[node.name].append(
                                MemberInfo(
                                    enum_name=node.name,
                                    member_name=member_name,
                                    member_value=member_value,
                                    file_path=self.file_path,
                                    line=item.lineno,
                                )
                            )
                elif isinstance(item, ast.AnnAssign) and item.target:
                    if isinstance(item.target, ast.Name):
                        member_name = item.target.id
                        # Skip dunder and private members during collection
                        if member_name.startswith("_"):
                            continue
                        member_value = (
                            self._extract_value(item.value) if item.value else None
                        )
                        self.enums[node.name].append(
                            MemberInfo(
                                enum_name=node.name,
                                member_name=member_name,
                                member_value=member_value,
                                file_path=self.file_path,
                                line=item.lineno,
                            )
                        )

        self.generic_visit(node)

    def _get_base_name(self, base: ast.expr) -> str:
        """Extract the name of a base class from AST node.

        Args:
            base: AST expression node representing the base class

        Returns:
            String representation of the base class name
        """
        if isinstance(base, ast.Name):
            return base.id
        if isinstance(base, ast.Attribute):
            return base.attr
        if isinstance(base, ast.Subscript):
            # Handle generic types like Enum[str]
            if isinstance(base.value, ast.Name):
                return base.value.id
        # Handle tuple bases like (str, Enum)
        # Note: This appears in source as "class Foo(str, Enum)" which
        # AST represents as multiple bases, not a tuple
        return ""

    def _extract_value(self, node: ast.expr | None) -> str | None:
        """Extract string value from an AST expression.

        Args:
            node: AST expression node

        Returns:
            String value if extractable, None otherwise
        """
        if node is None:
            return None
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return node.value
        if isinstance(node, ast.Call):
            # Handle auto() or similar
            if isinstance(node.func, ast.Name) and node.func.id == "auto":
                return None
            # Handle explicit value calls
            if node.args and isinstance(node.args[0], ast.Constant):
                if isinstance(node.args[0].value, str):
                    return node.args[0].value
        return None


class LiteralCollector(ast.NodeVisitor):
    """AST visitor that collects Literal type definitions.

    Attributes:
        literals: List of tuples (line, literal_values_set)
        file_path: Path to the file being analyzed
    """

    def __init__(self, file_path: Path) -> None:
        """Initialize the collector.

        Args:
            file_path: Path to the source file being analyzed
        """
        self.file_path = file_path
        self.literals: list[tuple[int, set[str]]] = []

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Visit subscript expressions to find Literal[...] types.

        Args:
            node: The AST Subscript node
        """
        # Check if this is Literal[...]
        if (isinstance(node.value, ast.Name) and node.value.id == "Literal") or (
            isinstance(node.value, ast.Attribute) and node.value.attr == "Literal"
        ):
            values = self._extract_literal_values(node.slice)
            if values:
                self.literals.append((node.lineno, values))

        self.generic_visit(node)

    def _extract_literal_values(self, slice_node: ast.expr) -> set[str]:
        """Extract string values from a Literal type's slice.

        Args:
            slice_node: The slice expression of the Literal subscript

        Returns:
            Set of string values found in the Literal
        """
        values: set[str] = set()

        if isinstance(slice_node, ast.Tuple):
            # Literal["a", "b", "c"]
            for elt in slice_node.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    values.add(elt.value)
        elif isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
            # Literal["single_value"]
            values.add(slice_node.value)

        return values


def check_enum_member_casing(
    enum_members: list[MemberInfo],
) -> list[GovernanceViolation]:
    """Check that all enum members use UPPER_SNAKE_CASE naming.

    Rule E001: Enum members must use UPPER_SNAKE_CASE naming convention.

    Args:
        enum_members: List of enum member info to check

    Returns:
        List of violations found

    Examples:
        Valid names: ACTIVE, PENDING_APPROVAL, HTTP_404
        Invalid names: active, PendingApproval, httpError
    """
    violations: list[GovernanceViolation] = []

    for member in enum_members:
        # Skip private/dunder members
        if member.member_name.startswith("_"):
            continue

        if not UPPER_SNAKE_CASE_PATTERN.match(member.member_name):
            violations.append(
                GovernanceViolation(
                    file_path=member.file_path,
                    line=member.line,
                    rule_code="E001",
                    message=(
                        f"Enum member '{member.enum_name}.{member.member_name}' "
                        f"must use UPPER_SNAKE_CASE"
                    ),
                )
            )

    return violations


def check_literal_duplication(
    enum_index: dict[str, set[str]],
    literals: list[tuple[Path, int, set[str]]],
) -> list[GovernanceViolation]:
    """Check for Literal types that duplicate enum value sets.

    Rule E002: Literal types should not duplicate existing enum values.

    This rule detects when a Literal type contains the same set of string
    values as an existing enum. This indicates the Literal should be replaced
    with the enum for better type safety and maintainability.

    Args:
        enum_index: Dictionary mapping enum names to their value sets
        literals: List of (file_path, line, values_set) for each Literal found

    Returns:
        List of violations found
    """
    violations: list[GovernanceViolation] = []

    for file_path, line, literal_values in literals:
        if not literal_values:
            continue

        # Check if this Literal's values match any enum's values
        for enum_name, enum_values in enum_index.items():
            if literal_values == enum_values:
                violations.append(
                    GovernanceViolation(
                        file_path=file_path,
                        line=line,
                        rule_code="E002",
                        message=(
                            f"Literal type duplicates values from enum '{enum_name}'. "
                            f"Use {enum_name} instead of Literal[...]"
                        ),
                    )
                )
            elif literal_values.issubset(enum_values) and len(literal_values) > 1:
                # Warn if Literal is a subset of enum values (likely should use enum)
                violations.append(
                    GovernanceViolation(
                        file_path=file_path,
                        line=line,
                        rule_code="E002",
                        message=(
                            f"Literal type values are a subset of enum '{enum_name}'. "
                            f"Consider using {enum_name} for type safety"
                        ),
                        severity="WARNING",
                    )
                )

    return violations


def collect_enums_from_file(file_path: Path) -> dict[str, list[MemberInfo]]:
    """Parse a Python file and collect all enum definitions.

    Args:
        file_path: Path to the Python file to parse

    Returns:
        Dictionary mapping enum names to their member info lists
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError) as e:
        logger.warning("Could not parse %s: %s", file_path, e)
        return {}

    collector = CollectorAST(file_path)
    collector.visit(tree)
    return collector.enums


def collect_literals_from_file(file_path: Path) -> list[tuple[int, set[str]]]:
    """Parse a Python file and collect all Literal type definitions.

    Args:
        file_path: Path to the Python file to parse

    Returns:
        List of (line_number, values_set) tuples for each Literal found
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError) as e:
        logger.warning("Could not parse %s: %s", file_path, e)
        return []

    collector = LiteralCollector(file_path)
    collector.visit(tree)
    return collector.literals


def validate_enum_directory(
    enum_dir: Path, verbose: bool = False
) -> tuple[list[GovernanceViolation], dict[str, set[str]]]:
    """Validate all enum files in a directory for casing violations.

    Args:
        enum_dir: Path to the enums/ directory
        verbose: Whether to log progress

    Returns:
        Tuple of (violations list, enum_index dict)
        The enum_index maps enum names to their value sets for Literal checking
    """
    violations: list[GovernanceViolation] = []
    enum_index: dict[str, set[str]] = {}

    if not enum_dir.exists():
        logger.warning("Enum directory not found: %s", enum_dir)
        return violations, enum_index

    for file_path in enum_dir.glob("enum_*.py"):
        if file_path.is_symlink():
            continue

        if verbose:
            logger.debug("Checking enums in: %s", file_path)

        enums = collect_enums_from_file(file_path)

        for enum_name, members in enums.items():
            # Check casing for each member
            violations.extend(check_enum_member_casing(members))

            # Build index of enum values for Literal checking
            values: set[str] = set()
            for member in members:
                if member.member_value:
                    values.add(member.member_value)
            if values:
                enum_index[enum_name] = values

    return violations, enum_index


def validate_literal_usage(
    source_dir: Path,
    enum_index: dict[str, set[str]],
    verbose: bool = False,
) -> list[GovernanceViolation]:
    """Scan source directory for Literal types that duplicate enum values.

    Args:
        source_dir: Path to source directory to scan
        enum_index: Dictionary mapping enum names to their value sets
        verbose: Whether to log progress

    Returns:
        List of violations found
    """
    violations: list[GovernanceViolation] = []

    if not enum_index:
        return violations

    # Collect all Literals from source files
    all_literals: list[tuple[Path, int, set[str]]] = []

    for file_path in source_dir.rglob("*.py"):
        if file_path.is_symlink():
            continue
        # Skip test files (use Path.parts for platform-independent check)
        if "tests" in file_path.parts:
            continue

        if verbose:
            logger.debug("Scanning for Literals in: %s", file_path)

        literals = collect_literals_from_file(file_path)
        for line, values in literals:
            all_literals.append((file_path, line, values))

    # Check for duplications
    violations.extend(check_literal_duplication(enum_index, all_literals))

    return violations


def validate_directory(
    directory: Path, verbose: bool = False
) -> list[GovernanceViolation]:
    """Validate a directory for all enum governance rules.

    Args:
        directory: Path to the omnibase_core directory
        verbose: Whether to log progress

    Returns:
        List of all violations found
    """
    violations: list[GovernanceViolation] = []

    # Find the enums directory
    enum_dir = directory / "enums"
    if not enum_dir.exists():
        # Try looking under src/omnibase_core/
        enum_dir = directory / "src" / "omnibase_core" / "enums"

    # Step 1: Validate enum casing and build index
    enum_violations, enum_index = validate_enum_directory(enum_dir, verbose)
    violations.extend(enum_violations)

    if verbose:
        logger.info(
            "Found %d enums with %d total values",
            len(enum_index),
            sum(len(v) for v in enum_index.values()),
        )

    # Step 2: Scan for Literal duplication
    source_dir = directory
    if (directory / "src" / "omnibase_core").exists():
        source_dir = directory / "src" / "omnibase_core"

    literal_violations = validate_literal_usage(source_dir, enum_index, verbose)
    violations.extend(literal_violations)

    return violations


def main() -> int:
    """Main entry point for command-line validation.

    Returns:
        int: Exit code (0=pass, 1=failures found)
    """
    parser = argparse.ArgumentParser(
        description="Check enum governance rules in omnibase_core",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Check src/omnibase_core (default)
  %(prog)s -v                 Check with verbose output
  %(prog)s path/to/dir        Check a specific directory
  %(prog)s --enums-only       Only check enum member casing (skip Literal check)

Rules:
  E001: Enum member must use UPPER_SNAKE_CASE
  E002: Literal type duplicates enum values
""",
    )
    parser.add_argument(
        "directory",
        nargs="?",
        type=Path,
        default=None,
        help="Directory to check (default: src/omnibase_core)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print progress for each file checked",
    )
    parser.add_argument(
        "--enums-only",
        action="store_true",
        help="Only check enum member casing, skip Literal duplication check",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(message)s", force=True)

    # Determine target directory
    if args.directory:
        target_dir = args.directory
    else:
        # Find src/omnibase_core relative to this file
        this_file = Path(__file__)
        target_dir = this_file.parent.parent  # Go up from validation/ to omnibase_core/

    if not target_dir.exists():
        logger.error("Directory not found: %s", target_dir)
        return 1

    logger.info("Checking enum governance in: %s", target_dir)
    logger.info("-" * 60)

    if args.enums_only:
        # Only check enum casing
        enum_dir = target_dir / "enums"
        if not enum_dir.exists():
            enum_dir = target_dir / "src" / "omnibase_core" / "enums"
        violations, _ = validate_enum_directory(enum_dir, args.verbose)
    else:
        violations = validate_directory(target_dir, args.verbose)

    # Report violations
    errors = [v for v in violations if v.severity == "ERROR"]
    warnings = [v for v in violations if v.severity == "WARNING"]

    if warnings:
        logger.warning("Found %d warning(s):", len(warnings))
        for violation in sorted(warnings, key=lambda v: (str(v.file_path), v.line)):
            logger.warning("  %s", violation)

    if errors:
        logger.error("Found %d error(s):", len(errors))
        for violation in sorted(errors, key=lambda v: (str(v.file_path), v.line)):
            logger.error("  %s", violation)
        return 1

    logger.info("All enum governance checks passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
