"""
Enum Member Casing Checker for ONEX Codebase.

This module enforces UPPER_SNAKE_CASE naming convention for enum members
throughout the omnibase_core codebase. It is designed to be run as a
pre-commit hook or standalone validation tool.

Key Features:
    - AST-based analysis for accurate enum detection
    - Detects all Enum subclass patterns (Enum, str Enum, IntEnum, etc.)
    - Validates member names against UPPER_SNAKE_CASE pattern
    - Ignores dunder (__name__) and private (_name) members
    - Ignores methods and non-member class attributes

Usage Examples:
    As a module (validates src/omnibase_core by default)::

        poetry run python -m omnibase_core.validation.checker_enum_member_casing

    With specific files (for pre-commit integration)::

        poetry run python -m omnibase_core.validation.checker_enum_member_casing file1.py file2.py

    With verbose output::

        poetry run python -m omnibase_core.validation.checker_enum_member_casing -v

    Programmatic usage::

        from pathlib import Path
        from omnibase_core.validation.checker_enum_member_casing import (
            CheckerMemberCasing,
            validate_file,
            validate_directory,
        )

        # Check a single file
        issues = validate_file(Path("src/omnibase_core/enums/enum_example.py"))
        for issue in issues:
            print(issue)

        # Validate an entire directory
        issues = validate_directory(Path("src/omnibase_core/"), verbose=True)

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
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
from pathlib import Path

logger = logging.getLogger(__name__)

# Pattern for valid UPPER_SNAKE_CASE enum member names
# Pattern breakdown: ^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$
#   - Must start with uppercase letter
#   - Followed by zero or more uppercase letters or digits
#   - Optionally followed by underscore + one or more uppercase letters/digits (repeatable)
# Allows: EMPTY, HTTP_2, V1_BETA, SHA256, SOME_LONG_NAME
# Rejects: empty, Unvalidated, validated_okay, HTTP_, STATUS__, _LEADING
UPPER_SNAKE_CASE_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$")

# Known Enum base classes and mixins
# When a class inherits from any of these (directly or indirectly),
# we consider it an Enum class
ENUM_BASE_NAMES = frozenset(
    {
        "Enum",
        "IntEnum",
        "StrEnum",
        "Flag",
        "IntFlag",
    }
)


def suggest_upper_snake_case(name: str) -> str:
    """Convert a name to UPPER_SNAKE_CASE format.

    Handles various input formats:
    - lowercase: "active" -> "ACTIVE"
    - camelCase: "someValue" -> "SOME_VALUE"
    - PascalCase: "SomeValue" -> "SOME_VALUE"
    - mixed_case: "some_Value" -> "SOME_VALUE"
    - Already UPPER_SNAKE_CASE: "SOME_VALUE" -> "SOME_VALUE"

    Args:
        name: The original name to convert.

    Returns:
        The name converted to UPPER_SNAKE_CASE format.

    Example:
        >>> suggest_upper_snake_case("active")
        'ACTIVE'
        >>> suggest_upper_snake_case("someValue")
        'SOME_VALUE'
        >>> suggest_upper_snake_case("HTTPResponse")
        'HTTP_RESPONSE'
    """
    if not name:
        return name

    # Insert underscore before uppercase letters that follow lowercase letters
    # or before uppercase letters followed by lowercase (for acronyms like HTTP)
    result: list[str] = []
    prev_char = ""

    for i, char in enumerate(name):
        if char.isupper():
            # Add underscore before uppercase if:
            # 1. Previous char was lowercase (camelCase boundary)
            # 2. Previous char was uppercase AND next char is lowercase (acronym end)
            if prev_char.islower() or (
                prev_char.isupper() and i + 1 < len(name) and name[i + 1].islower()
            ):
                result.append("_")
        result.append(char.upper())
        prev_char = char

    suggested = "".join(result)

    # Clean up: replace multiple underscores with single, strip leading/trailing
    suggested = re.sub(r"_+", "_", suggested)
    suggested = suggested.strip("_")

    return suggested


class CheckerMemberCasing(ast.NodeVisitor):
    """AST-based checker for enum member naming conventions.

    This class uses Python's Abstract Syntax Tree (AST) module to analyze
    source code and detect enum members that violate the UPPER_SNAKE_CASE
    naming convention without executing the code.

    Attributes:
        file_path (str): Path to the file being checked. Used for context
            in error messages.
        issues (list[str]): List of detected naming convention violations.
            Each issue is a formatted string with line number and description.

    Example:
        >>> import ast
        >>> source_code = '''
        ... from enum import Enum
        ...
        ... class Status(str, Enum):
        ...     active = "active"  # Violation!
        ...     INACTIVE = "inactive"  # OK
        ... '''
        >>> tree = ast.parse(source_code)
        >>> checker = CheckerMemberCasing("example.py")
        >>> checker.visit(tree)
        >>> for issue in checker.issues:
        ...     print(issue)
        example.py:5: Status.active violates UPPER_SNAKE_CASE, suggested: ACTIVE
    """

    def __init__(self, file_path: str) -> None:
        """Initialize the enum member casing checker.

        Args:
            file_path: Path to the source file being analyzed. This is used
                for generating meaningful error messages.
        """
        self.file_path = file_path
        self.issues: list[str] = []

    def _is_enum_class(self, node: ast.ClassDef) -> bool:
        """Check if a class definition is an Enum subclass.

        Examines the base classes of a ClassDef node to determine if
        it inherits from Enum or any of its variants (IntEnum, StrEnum,
        Flag, etc.).

        Args:
            node: The AST ClassDef node to check.

        Returns:
            True if the class is an Enum subclass, False otherwise.

        Note:
            This handles various inheritance patterns:
            - class Foo(Enum): ...
            - class Foo(str, Enum): ...
            - class Foo(IntEnum): ...
            - class Foo(SomeOtherEnum): ... (if SomeOtherEnum inherits from Enum)

            For the last case, we can only detect it if the base class name
            contains "Enum" since we don't have runtime type information.
        """
        for base in node.bases:
            base_name = self._extract_base_name(base)
            if base_name is None:
                continue

            # Direct match with known enum bases
            if base_name in ENUM_BASE_NAMES:
                return True

            # Heuristic: class name ends with "Enum" (e.g., MyCustomEnum)
            # This catches custom enum subclasses
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
            # Handle cases like enum.Enum
            return base.attr
        return None

    def _is_enum_member(self, node: ast.stmt) -> tuple[bool, str | None, int]:
        """Determine if a statement is an enum member assignment.

        Enum members are detected by looking for simple assignments in
        the class body that assign to a simple name (not a tuple/list unpack).
        This includes both regular assignments (x = 1) and annotated assignments
        with values (x: int = 1).

        Args:
            node: AST statement node to check.

        Returns:
            A tuple of (is_member, member_name, line_number).
            is_member is True if this is an enum member assignment.
            member_name is the name of the member (or None if not a member).
            line_number is the line where the assignment occurs.

        Note:
            The following are NOT enum members:
            - Method definitions (def/async def)
            - Annotations without assignment (name: type)
            - Class-level docstrings
            - Dunder names (__name__)
            - Private names (_name)
            - Tuple/list unpacking assignments
        """
        # Handle regular assignments (MEMBER = "value")
        if isinstance(node, ast.Assign):
            # Get the first target (handles simple assignment)
            targets = node.targets
            if len(targets) != 1:
                return False, None, 0

            target = targets[0]
            if not isinstance(target, ast.Name):
                return False, None, 0

            name = target.id

            # Skip dunder names (__init__, __str__, etc.)
            if name.startswith("__") and name.endswith("__"):
                return False, None, 0

            # Skip private names (_private)
            if name.startswith("_"):
                return False, None, 0

            return True, name, node.lineno

        # Handle annotated assignments (member: str = "value")
        if isinstance(node, ast.AnnAssign):
            # Only check if there's a value (member: str = "value", not just member: str)
            if node.value is None:
                return False, None, 0

            target = node.target
            if not isinstance(target, ast.Name):
                return False, None, 0

            name = target.id

            # Skip dunder names (__init__, __str__, etc.)
            if name.startswith("__") and name.endswith("__"):
                return False, None, 0

            # Skip private names (_private)
            if name.startswith("_"):
                return False, None, 0

            return True, name, node.lineno

        return False, None, 0

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check enum member naming conventions for a class definition node.

        If the class is determined to be an Enum subclass, validates that
        all member names conform to UPPER_SNAKE_CASE.

        Args:
            node: The AST ClassDef node representing a class definition.
        """
        if not self._is_enum_class(node):
            self.generic_visit(node)
            return

        class_name = node.name

        # Check each statement in the class body for enum members
        for stmt in node.body:
            is_member, member_name, line_no = self._is_enum_member(stmt)

            if is_member and member_name is not None:
                if not UPPER_SNAKE_CASE_PATTERN.match(member_name):
                    suggested = suggest_upper_snake_case(member_name)
                    self.issues.append(
                        f"{self.file_path}:{line_no}: {class_name}.{member_name} "
                        f"violates UPPER_SNAKE_CASE, suggested: {suggested}"
                    )

        # Continue visiting nested classes
        self.generic_visit(node)


def validate_file(file_path: Path) -> list[str]:
    """Validate enum member casing in a single file.

    Parses the file and runs the CheckerMemberCasing to find
    any enum members that violate UPPER_SNAKE_CASE naming.

    Args:
        file_path: Path to the Python file to validate.

    Returns:
        List of violation messages. Empty if the file is compliant or
        cannot be parsed.

    Example:
        >>> issues = validate_file(Path("my_enum.py"))
        >>> for issue in issues:
        ...     print(issue)
    """
    try:
        source = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        logger.warning("Failed to read %s: %s", file_path, e)
        return []

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as e:
        logger.warning("Syntax error in %s: %s", file_path, e)
        return []

    checker = CheckerMemberCasing(str(file_path))
    checker.visit(tree)
    return checker.issues


def validate_directory(directory: Path, verbose: bool = False) -> list[str]:
    """Validate all Python files in a directory against enum member casing conventions.

    Recursively traverses the given directory and checks each Python file
    for enum member casing compliance.

    Args:
        directory: Path to the directory to validate.
        verbose: If True, log each file as it's checked at DEBUG level.

    Returns:
        List of violation messages from all files. Empty if all files
        are compliant.

    Example:
        >>> from pathlib import Path
        >>> issues = validate_directory(Path("src/omnibase_core/enums/"))
        >>> if issues:
        ...     print(f"Found {len(issues)} violations")
    """
    all_issues: list[str] = []

    for file_path in directory.rglob("*.py"):
        # Skip symbolic links
        if file_path.is_symlink():
            if verbose:
                logger.debug("Skipping symlink: %s", file_path)
            continue

        if verbose:
            logger.debug("Checking: %s", file_path)

        issues = validate_file(file_path)
        all_issues.extend(issues)

    return all_issues


def main() -> int:
    """Main entry point for command-line validation.

    Parses command-line arguments and validates enum member casing
    in the specified files or directory.

    CLI Usage:
        Default (validates src/omnibase_core)::

            python -m omnibase_core.validation.checker_enum_member_casing

        With specific files (for pre-commit)::

            python -m omnibase_core.validation.checker_enum_member_casing file1.py file2.py

        With verbose output::

            python -m omnibase_core.validation.checker_enum_member_casing -v

    Returns:
        int: Exit code for shell integration.

            - 0: All enum members conform to UPPER_SNAKE_CASE (success)
            - 1: Violations found or error occurred (failure)
    """
    parser = argparse.ArgumentParser(
        description="Check enum member casing conventions (UPPER_SNAKE_CASE) in Python files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          Check src/omnibase_core (default)
  %(prog)s file1.py file2.py        Check specific files (for pre-commit)
  %(prog)s -v                       Check with verbose output
  %(prog)s --directory path/to/dir  Check a specific directory

Valid member names (UPPER_SNAKE_CASE):
  ACTIVE, HTTP_2, V1_BETA, SHA256, SOME_LONG_NAME

Invalid member names:
  active, Active, someValue, camelCase, mixed_CASE
""",
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="Files to check (if none specified, checks src/omnibase_core)",
    )
    parser.add_argument(
        "-d",
        "--directory",
        type=Path,
        default=None,
        help="Directory to check recursively (alternative to file list)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print progress for each file checked",
    )

    args = parser.parse_args()

    # Configure logging for CLI usage
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(message)s", force=True)

    all_issues: list[str] = []

    # Determine what to check
    if args.files:
        # Check specific files (pre-commit mode)
        for file_path in args.files:
            if not file_path.exists():
                logger.error("File not found: %s", file_path)
                continue

            if file_path.suffix != ".py":
                if args.verbose:
                    logger.debug("Skipping non-Python file: %s", file_path)
                continue

            issues = validate_file(file_path)
            all_issues.extend(issues)

    elif args.directory:
        # Check specified directory
        if not args.directory.exists():
            logger.error("Directory not found: %s", args.directory)
            return 1

        logger.info("Checking enum member casing in: %s", args.directory)
        logger.info("-" * 60)
        all_issues = validate_directory(args.directory, verbose=args.verbose)

    else:
        # Default: check src/omnibase_core
        this_file = Path(__file__)
        target_dir = this_file.parent.parent  # Go up from validation/ to omnibase_core/

        if not target_dir.exists():
            logger.error("Directory not found: %s", target_dir)
            return 1

        logger.info("Checking enum member casing in: %s", target_dir)
        logger.info("-" * 60)
        all_issues = validate_directory(target_dir, verbose=args.verbose)

    if all_issues:
        logger.warning("Found %d enum member casing violation(s):", len(all_issues))
        for issue in sorted(all_issues):
            logger.warning("  %s", issue)
        return 1

    if not args.files:  # Only print success message in directory mode
        logger.info("All enum members conform to UPPER_SNAKE_CASE!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
