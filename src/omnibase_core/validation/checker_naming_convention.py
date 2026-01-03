"""
NamingConventionChecker

Check naming conventions for classes, functions, and file names.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""

import ast
import re
import sys
from pathlib import Path

# Directory to required prefix(es) mapping
# Each directory can have one or more valid prefixes
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
    "runtime": ("runtime_", "handler_"),
    "schemas": ("schema_",),
    "services": ("service_",),
    "tools": ("tool_",),
    "types": ("typed_dict_", "type_", "converter_"),
    "utils": ("util_",),
    "validation": ("validator_", "checker_"),
}

# Files that are always allowed regardless of directory
ALLOWED_FILES: set[str] = {"__init__.py", "conftest.py", "py.typed"}

# Prefixes for files that are always allowed (e.g., private modules)
ALLOWED_FILE_PREFIXES: tuple[str, ...] = ("_",)


def check_file_name(file_path: Path) -> str | None:
    """
    Check if a file name conforms to the naming convention for its directory.

    Rules only apply to top-level directories under omnibase_core (or src/omnibase_core).
    For example, models/cli/ follows the 'models/' rule (model_*), not 'cli/' rule.

    Args:
        file_path: Path to the file to check.

    Returns:
        Error message if the file violates naming conventions, None otherwise.
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
    # that has a rule defined
    parts = file_path.parts
    try:
        # Find omnibase_core in the path
        omnibase_idx = parts.index("omnibase_core")
        # The rule-relevant directory is the one immediately after omnibase_core
        if omnibase_idx + 1 < len(parts) - 1:  # -1 to exclude the filename
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
    """Check naming conventions."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.issues: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check class naming conventions."""
        class_name = node.name

        # Skip anti-pattern check for error taxonomy classes and handler classes
        # Error classes legitimately use terms like "Handler" in names like "HandlerConfigurationError"
        # or "Service" in names like "InfraServiceUnavailableError"
        # Handler classes in handlers/ directories are exempt (e.g., HandlerHttp)
        is_error_class = class_name.endswith(("Error", "Exception"))
        # Use pathlib for cross-platform path handling
        file_path = Path(self.file_path)
        is_in_exempt_dir = (
            "errors" in file_path.parts
            or "handlers" in file_path.parts
            or file_path.name == "errors.py"
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
        """Check function naming conventions."""
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


def validate_directory(directory: Path, verbose: bool = False) -> list[str]:
    """
    Validate all Python files in a directory against naming conventions.

    Args:
        directory: Path to the directory to validate.
        verbose: If True, print progress information.

    Returns:
        List of error messages for files that violate naming conventions.
    """
    errors: list[str] = []

    for file_path in directory.rglob("*.py"):
        error = check_file_name(file_path)
        if error:
            errors.append(f"{file_path}: {error}")
        elif verbose:
            print(f"✓ {file_path}")

    return errors


def main() -> int:
    """
    Main entry point for command-line validation.

    Returns:
        Exit code (0 for success, 1 for violations found).
    """
    # Default to src/omnibase_core if no arguments provided
    if len(sys.argv) > 1:
        target_dir = Path(sys.argv[1])
    else:
        # Find src/omnibase_core relative to this file
        this_file = Path(__file__)
        target_dir = this_file.parent.parent  # Go up from validation/ to omnibase_core/

    if not target_dir.exists():
        print(f"Error: Directory not found: {target_dir}")
        return 1

    print(f"Checking naming conventions in: {target_dir}")
    print("-" * 60)

    errors = validate_directory(target_dir)

    if errors:
        print(f"\n❌ Found {len(errors)} naming convention violation(s):\n")
        for error in sorted(errors):
            print(f"  • {error}")
        print()
        return 1

    print("✅ All files conform to naming conventions!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
