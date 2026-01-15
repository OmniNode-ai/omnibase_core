"""
Naming Convention Checker for ONEX Codebase.

This module enforces file, class, and function naming conventions for the
omnibase_core codebase. It is designed to be run as a pre-commit hook or
standalone validation tool.

**NEW VALIDATION (PR #314, OMN-1224, OMN-1225)**: This validation is being
rolled out incrementally. The pre-push hook currently runs in warning mode
(non-blocking) to allow time for migration of existing files.

Key Features:
    - File naming validation based on directory-specific prefix rules
    - Class naming convention checks (PascalCase, anti-pattern detection)
    - Function naming convention checks (snake_case)
    - AST-based analysis for accurate detection

Usage Examples:
    As a module (validates src/omnibase_core by default)::

        poetry run python -m omnibase_core.validation.checker_naming_convention

    With a specific directory::

        poetry run python -m omnibase_core.validation.checker_naming_convention /path/to/dir

    With verbose output::

        poetry run python -m omnibase_core.validation.checker_naming_convention -v

    Programmatic usage::

        from pathlib import Path
        from omnibase_core.validation.checker_naming_convention import (
            check_file_name,
            validate_directory,
            NamingConventionChecker,
        )

        # Check a single file name
        error = check_file_name(Path("src/omnibase_core/models/my_model.py"))
        if error:
            print(f"Naming violation: {error}")

        # Validate an entire directory
        errors = validate_directory(Path("src/omnibase_core/"), verbose=True)

        # Check class/function names in a file using AST
        import ast
        with open("myfile.py") as f:
            tree = ast.parse(f.read())
        checker = NamingConventionChecker("myfile.py")
        checker.visit(tree)
        for issue in checker.issues:
            print(issue)

Module Attributes:
    DIRECTORY_PREFIX_RULES (dict[str, tuple[str, ...]]): Maps directory names
        to their required file name prefixes. Files in these directories must
        start with one of the specified prefixes.
    ALLOWED_FILES (set[str]): Set of file names that are always allowed
        regardless of directory (e.g., __init__.py, conftest.py).
    ALLOWED_FILE_PREFIXES (tuple[str, ...]): Tuple of prefixes for files that
        are always allowed (e.g., private modules starting with underscore).

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
from pathlib import Path

logger = logging.getLogger(__name__)

# =============================================================================
# MIGRATION PLAN FOR EXISTING VIOLATIONS
# =============================================================================
#
# As of PR #314 (OMN-1224, OMN-1225), there are approximately 71 existing file
# naming violations in the codebase.
#
# Migration Strategy:
# -------------------
# 1. Phase 1 (Current): Pre-push hook runs in WARNING mode (non-blocking)
#    - Developers see violations but can still push
#    - New files must follow conventions (enforced in code review)
#
# 2. Phase 2: Create tracking tickets for each directory with violations
#    - cli/ (3 violations) -> rename to cli_*.py
#    - constants/ (2 violations) -> rename to constants_*.py
#    - decorators/ (4 violations) -> rename to decorator_*.py
#    - errors/ (3 violations) -> rename to error_*.py or exception_*.py
#    - etc.
#
# 3. Phase 3: Rename files incrementally, updating all imports
#    - Use IDE refactoring tools to update imports across codebase
#    - One directory at a time to minimize merge conflicts
#    - Each rename is a separate PR for easy review
#
# 4. Phase 4: Enable BLOCKING mode after all violations fixed
#    - Update pre-push hook to fail on violations
#    - Add to CI pipeline as required check
#
# Tracking: See Linear tickets OMN-1224, OMN-1225 for progress
# =============================================================================

# DIRECTORY_PREFIX_RULES: Maps top-level directory names under omnibase_core/
# to their required file name prefixes.
#
# Structure:
#     Key: Directory name (e.g., "models", "enums", "validation")
#     Value: Tuple of allowed prefixes for files in that directory
#
# Rules:
#     - Files must start with at least one of the specified prefixes
#     - Prefixes include trailing underscore (e.g., "model_" not "model")
#     - Some directories allow multiple prefixes (e.g., "errors" allows both
#       "error_" and "exception_")
#     - Rules apply to the FIRST directory after omnibase_core/, not nested dirs
#       (e.g., models/cli/model_cli.py follows "models" rule, not "cli" rule)
#
# Example:
#     A file at omnibase_core/models/model_user.py is valid (starts with "model_")
#     A file at omnibase_core/models/user.py is INVALID (must start with "model_")
DIRECTORY_PREFIX_RULES: dict[str, tuple[str, ...]] = {
    "cli": ("cli_",),
    "constants": ("constants_",),
    "container": ("container_",),
    "context": ("context_",),
    "contracts": ("contract_",),
    "decorators": ("decorator_",),
    "enums": ("enum_",),
    "errors": ("error_", "exception_"),
    "factories": ("factory_",),
    "infrastructure": ("node_", "infra_"),
    "logging": ("logging_",),
    "mixins": ("mixin_",),
    "models": ("model_",),
    "nodes": ("node_",),
    "pipeline": (
        "builder_",
        "runner_",
        "manifest_",
        "composer_",
        "registry_",
        "pipeline_",
        "handler_",
    ),
    "protocols": ("protocol_",),
    "resolution": ("resolver_",),
    "rendering": ("renderer_",),
    # runtime/ accepts handler_ prefix because:
    # - runtime/handler_registry.py manages handler registration
    # - runtime/handlers/handler_local.py implements local handler logic
    # The runtime module is responsible for handler dispatch and management.
    "runtime": ("runtime_", "handler_"),
    "schemas": ("schema_",),
    "services": ("service_",),
    "tools": ("tool_",),
    "types": ("typed_dict_", "type_", "converter_"),
    "utils": ("util_",),
    "validation": ("validator_", "checker_"),
}

# ALLOWED_FILES: Set of file names that bypass all naming convention checks.
#
# These files are essential Python module files that have standardized names
# defined by Python itself or by common tooling conventions:
#     - __init__.py: Package initialization file (Python standard)
#     - conftest.py: pytest configuration file (pytest convention)
#     - py.typed: PEP 561 marker file for typed packages
ALLOWED_FILES: set[str] = {"__init__.py", "conftest.py", "py.typed"}

# ALLOWED_FILE_PREFIXES: Tuple of prefixes that bypass naming convention checks.
#
# Files starting with these prefixes are considered internal/private and are
# exempt from the directory-based naming rules. Currently only underscore prefix
# is allowed, which matches Python's convention for private modules.
#
# Example:
#     _internal.py in any directory is allowed (private module)
#     _helpers.py in models/ is allowed (doesn't need model_ prefix)
ALLOWED_FILE_PREFIXES: tuple[str, ...] = ("_",)


def check_file_name(file_path: Path) -> str | None:
    """Check if a file name conforms to the naming convention for its directory.

    Validates that Python files in omnibase_core directories follow the
    required naming prefix conventions defined in DIRECTORY_PREFIX_RULES.

    Rules only apply to top-level directories under omnibase_core (or
    src/omnibase_core). Nested directories inherit the parent's rule.
    For example, models/cli/ follows the 'models/' rule (model_*), not 'cli/' rule.

    Args:
        file_path: Path to the file to check. Can be absolute or relative,
            but must contain "omnibase_core" in the path for rules to apply.

    Returns:
        Error message string if the file violates naming conventions,
        None if the file is compliant or not subject to any rules.

    Examples:
        Valid file (starts with required prefix)::

            >>> check_file_name(Path("src/omnibase_core/models/model_user.py"))
            None

        Invalid file (missing required prefix)::

            >>> check_file_name(Path("src/omnibase_core/models/user.py"))
            "File 'user.py' in 'models/' directory must start with 'model_'"

        Allowed file (special files are exempt)::

            >>> check_file_name(Path("src/omnibase_core/models/__init__.py"))
            None

        Private module (underscore prefix is exempt)::

            >>> check_file_name(Path("src/omnibase_core/models/_internal.py"))
            None
    """
    file_name = file_path.name

    # Skip allowed files
    if file_name in ALLOWED_FILES:
        return None

    # Skip files with allowed prefixes (e.g., private modules starting with _)
    if any(file_name.startswith(prefix) for prefix in ALLOWED_FILE_PREFIXES):
        return None

    # Skip non-Python files
    if not file_name.endswith(".py"):
        return None

    # Find the relevant directory - the first directory after omnibase_core
    # that has a rule defined.
    #
    # Path structure explanation:
    #   parts = ("src", "omnibase_core", "models", "cli", "model_cli.py")
    #            ^0      ^1               ^2        ^3     ^4 (filename)
    #   len(parts) = 5, so len(parts) - 1 = 4 (index of filename)
    #
    # For path "src/omnibase_core/models/cli/model_cli.py":
    #   - omnibase_idx = 1 (position of "omnibase_core")
    #   - omnibase_idx + 1 = 2 (position of "models", the rule-relevant dir)
    #   - We need at least one directory between omnibase_core and the filename
    #   - Condition: omnibase_idx + 1 < len(parts) - 1
    #     Ensures there's a directory (not just filename) after omnibase_core
    parts = file_path.parts
    try:
        # Find omnibase_core in the path
        omnibase_idx = parts.index("omnibase_core")
        # The rule-relevant directory is the one immediately after omnibase_core.
        # We use len(parts) - 1 to exclude the filename from consideration:
        # if omnibase_idx + 1 equals len(parts) - 1, we'd be pointing at the
        # filename itself, not a directory, so we need strict less-than.
        if omnibase_idx + 1 < len(parts) - 1:
            relevant_dir = parts[omnibase_idx + 1]
            if relevant_dir in DIRECTORY_PREFIX_RULES:
                required_prefixes = DIRECTORY_PREFIX_RULES[relevant_dir]

                # Check if file name starts with any of the required prefixes
                if not any(
                    file_name.startswith(prefix) for prefix in required_prefixes
                ):
                    prefix_str = (
                        f"'{required_prefixes[0]}'"
                        if len(required_prefixes) == 1
                        else f"one of {required_prefixes}"
                    )
                    return (
                        f"File '{file_name}' in '{relevant_dir}/' directory must start "
                        f"with {prefix_str}"
                    )
    except ValueError:
        # omnibase_core not in path, skip validation
        pass

    # No directory rule applies or file is valid
    return None


class NamingConventionChecker(ast.NodeVisitor):
    """AST-based checker for class and function naming conventions.

    This class uses Python's Abstract Syntax Tree (AST) module to analyze
    source code and detect naming convention violations without executing
    the code. It checks for:

    1. **Class naming**: Must use PascalCase (e.g., MyClassName)
    2. **Anti-pattern detection**: Flags generic class names like "Manager",
       "Handler", "Helper", "Service", etc. that indicate poor domain modeling
    3. **Function naming**: Must use snake_case (e.g., my_function_name)

    Attributes:
        file_path (str): Path to the file being checked. Used for context in
            error messages and to determine exempt directories.
        issues (list[str]): List of detected naming convention violations.
            Each issue is a formatted string with line number and description.

    Example:
        >>> import ast
        >>> source_code = '''
        ... class BadManager:
        ...     def badMethod(self):
        ...         pass
        ... '''
        >>> tree = ast.parse(source_code)
        >>> checker = NamingConventionChecker("example.py")
        >>> checker.visit(tree)
        >>> for issue in checker.issues:
        ...     print(issue)
        Line 2: Class name 'BadManager' contains anti-pattern 'Manager'...
        Line 3: Function name 'badMethod' should use snake_case

    Note:
        Error classes (ending with "Error" or "Exception") and classes in
        errors/ or handlers/ directories are exempt from anti-pattern checks,
        as they legitimately use terms like "Handler" in their names.
    """

    def __init__(self, file_path: str) -> None:
        """Initialize the naming convention checker.

        Args:
            file_path: Path to the source file being analyzed. This is used
                for generating meaningful error messages and determining
                whether the file is in an exempt directory (errors/, handlers/).
        """
        self.file_path = file_path
        # Cache Path object for efficient reuse in visit methods
        # Avoids creating new Path objects on each class/function visit
        self._file_path = Path(file_path)
        self.issues: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check class naming conventions for a class definition node.

        Validates that class names:

        1. Use PascalCase naming style (e.g., MyClass, not my_class or myClass)
        2. Do not contain anti-pattern terms that indicate poor domain modeling

        Anti-pattern terms include: Manager, Handler, Helper, Utility, Util,
        Service, Controller, Processor, Worker. These terms are too generic
        and should be replaced with specific domain terminology.

        Exempt from anti-pattern checks:
            - Classes ending with "Error" or "Exception" (error taxonomy)
            - Classes in errors/ or handlers/ directories
            - Classes in files named errors.py

        Args:
            node: The AST ClassDef node representing a class definition.
                Contains the class name, base classes, decorators, and body.

        Note:
            After checking, this method calls generic_visit() to continue
            traversing nested class definitions (inner classes).
        """
        class_name = node.name

        # Skip anti-pattern check for error taxonomy classes and handler classes
        # Error classes legitimately use terms like "Handler" in names like "HandlerConfigurationError"
        # or "Service" in names like "InfraServiceUnavailableError"
        # Handler classes in handlers/ directories are exempt (e.g., HandlerHttp)
        is_error_class = class_name.endswith(("Error", "Exception"))
        # Use cached Path object for efficient cross-platform path handling
        is_in_exempt_dir = (
            "errors" in self._file_path.parts
            or "handlers" in self._file_path.parts
            or "services" in self._file_path.parts
            or self._file_path.name == "errors.py"
        )

        # Check for anti-pattern names (skip for error taxonomy classes)
        anti_patterns = [
            "Manager",
            "Handler",
            "Helper",
            "Utility",
            "Util",
            "Service",
            "Controller",
            "Processor",
            "Worker",
        ]

        # Only check anti-patterns for non-error classes outside exempt directories
        if not is_error_class and not is_in_exempt_dir:
            for pattern in anti_patterns:
                if pattern.lower() in class_name.lower():
                    self.issues.append(
                        f"Line {node.lineno}: Class name '{class_name}' contains anti-pattern '{pattern}' - use specific domain terminology",
                    )

        # Check naming style
        if not re.match(r"^[A-Z][a-zA-Z0-9]*$", class_name):
            self.issues.append(
                f"Line {node.lineno}: Class name '{class_name}' should use PascalCase",
            )

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function naming conventions for a function definition node.

        Validates that function names use snake_case style (e.g., my_function,
        not myFunction or MyFunction). The snake_case pattern allows:

        - Lowercase letters (a-z)
        - Digits (0-9), but not as the first character
        - Underscores for word separation

        Special methods (dunder methods like __init__, __str__) are skipped
        as they follow Python's own naming conventions.

        Args:
            node: The AST FunctionDef node representing a function definition.
                Contains the function name, arguments, body, and decorators.

        Note:
            This method also handles methods defined inside classes. After
            checking, it calls generic_visit() to continue traversing nested
            function definitions (inner functions, closures).
        """
        func_name = node.name

        # Skip special methods
        if func_name.startswith("__") and func_name.endswith("__"):
            return

        # Check naming style
        if not re.match(r"^[a-z_][a-z0-9_]*$", func_name):
            self.issues.append(
                f"Line {node.lineno}: Function name '{func_name}' should use snake_case",
            )

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check async function naming conventions for an async function definition node.

        Validates that async function names use snake_case style (e.g., my_async_func,
        not myAsyncFunc or MyAsyncFunc). The snake_case pattern allows:

        - Lowercase letters (a-z)
        - Digits (0-9), but not as the first character
        - Underscores for word separation

        Special methods (dunder methods like __aenter__, __aexit__) are skipped
        as they follow Python's own naming conventions.

        Args:
            node: The AST AsyncFunctionDef node representing an async function
                definition. Contains the function name, arguments, body, and decorators.

        Note:
            This method mirrors visit_FunctionDef but handles async functions.
            After checking, it calls generic_visit() to continue traversing nested
            function definitions (inner functions, closures).
        """
        func_name = node.name

        # Skip special methods
        if func_name.startswith("__") and func_name.endswith("__"):
            return

        # Check naming style
        if not re.match(r"^[a-z_][a-z0-9_]*$", func_name):
            self.issues.append(
                f"Line {node.lineno}: Async function name '{func_name}' should use snake_case",
            )

        self.generic_visit(node)


def validate_directory(directory: Path, verbose: bool = False) -> list[str]:
    """Validate all Python files in a directory against naming conventions.

    Recursively traverses the given directory and checks each Python file
    for naming convention compliance using the check_file_name() function.

    Symbolic links are skipped to avoid infinite loops from circular symlinks
    and to prevent duplicate validation of the same file through different paths.

    Args:
        directory: Path to the directory to validate. The function will
            recursively check all .py files in this directory and its
            subdirectories.
        verbose: If True, log each file as it's checked at DEBUG level
            (useful for debugging or progress tracking on large codebases).

    Returns:
        List of error messages for files that violate naming conventions.
        Each message includes the full file path and the specific violation.
        Returns an empty list if all files are compliant.

    Example:
        >>> from pathlib import Path
        >>> errors = validate_directory(Path("src/omnibase_core/models/"))
        >>> if errors:
        ...     print(f"Found {len(errors)} violations")
        ...     for error in errors:
        ...         print(f"  - {error}")
    """
    errors: list[str] = []

    for file_path in directory.rglob("*.py"):
        # Skip symbolic links to avoid infinite loops from circular symlinks
        # and prevent duplicate validation of files accessible via multiple paths
        if file_path.is_symlink():
            if verbose:
                logger.debug("Skipping symlink: %s", file_path)
            continue

        error = check_file_name(file_path)
        if error:
            errors.append(f"{file_path}: {error}")
        elif verbose:
            logger.debug("Checked: %s", file_path)

    return errors


def main() -> int:
    """Main entry point for command-line validation.

    Parses command-line arguments and validates Python file naming conventions
    in the specified directory (or src/omnibase_core by default).

    CLI Usage:
        Default (validates src/omnibase_core)::

            python -m omnibase_core.validation.checker_naming_convention

        With verbose output::

            python -m omnibase_core.validation.checker_naming_convention -v

        Validate a specific directory::

            python -m omnibase_core.validation.checker_naming_convention /path/to/dir

        Validate specific directory with verbose output::

            python -m omnibase_core.validation.checker_naming_convention /path/to/dir -v

    Returns:
        int: Exit code for shell integration.

            - 0: All files conform to naming conventions (success)
            - 1: Violations found or directory not found (failure)

    Note:
        This function is designed for CI/CD integration. A non-zero exit code
        will cause pre-commit hooks and CI pipelines to fail, preventing
        merges of non-conforming code.
    """
    parser = argparse.ArgumentParser(
        description="Check file naming conventions in omnibase_core",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Check src/omnibase_core (default)
  %(prog)s -v                 Check with verbose output (show each file)
  %(prog)s path/to/dir        Check a specific directory
  %(prog)s path/to/dir -v     Check specific directory with verbose output
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

    args = parser.parse_args()

    # Configure logging for CLI usage
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

    logger.info("Checking naming conventions in: %s", target_dir)
    logger.info("-" * 60)

    errors = validate_directory(target_dir, verbose=args.verbose)

    if errors:
        logger.warning("Found %d naming convention violation(s):", len(errors))
        for error in sorted(errors):
            logger.warning("  %s", error)
        return 1

    logger.info("All files conform to naming conventions!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
