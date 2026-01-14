"""
Checker for Literal type alias duplication.

Prevents creating Literal type aliases that duplicate existing enums.
This is a pre-commit hook that scans for patterns like:
- LiteralValidationLevel (duplicates EnumValidationLevel)
- StepTypeLiteral (duplicates EnumStepType)

The ONEX codebase uses enums as the canonical source for type-constrained values.
Using Literal aliases creates synchronization problems when enum values change
and violates the DRY (Don't Repeat Yourself) principle.

Usage:
    python -m omnibase_core.validation.checker_literal_duplication [paths...]

Exit codes:
    0: No duplications found
    1: Duplications detected (with actionable error messages)

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
import fnmatch
import logging
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# =============================================================================
# KNOWN ENUM NAMES
# =============================================================================
# This set is derived from the enum_*.py files in omnibase_core/enums/.
# It uses lowercase normalized names for case-insensitive matching.
#
# To regenerate this list:
#   ls src/omnibase_core/enums/ | grep -E "^enum_" | sed 's/^enum_//' | \
#     sed 's/\.py$//' | sort
#
# Key enums that commonly have Literal duplicates:
# - validationlevel, validationmode, validationseverity
# - healthstatus, operationstatus, servicestatus
# - loglevel, nodekind, nodetype
# - eventpriority, registrationstatus
# - injectionscope, servicelifecycle, serviceresolutionstatus
# - steptype (compute_step_type)
# =============================================================================

KNOWN_ENUM_NAMES: frozenset[str] = frozenset(
    {
        # Core status enums
        "healthstatus",
        "operationstatus",
        "servicestatus",
        "basestatus",
        "registrationstatus",
        "serviceresolutionstatus",
        # Validation enums
        "validationlevel",
        "validationmode",
        "validationseverity",
        "validationtype",
        "validationresult",
        # Pipeline enums
        "pipelinevalidationmode",
        # Node enums
        "nodekind",
        "nodetype",
        "nodestatus",
        # Logging and events
        "loglevel",
        "eventpriority",
        "eventtype",
        # Service lifecycle
        "servicelifecycle",
        "injectionscope",
        # Step types
        "steptype",
        "computesteptype",
        # Other common enums
        "environment",
        "priority",
        "severity",
        "status",
        "category",
    }
)


def get_enum_names_from_directory(enums_dir: Path) -> frozenset[str]:
    """Dynamically extract enum names from the enums directory.

    Scans the enums directory for files matching enum_*.py pattern and
    extracts normalized enum names (lowercase, no prefix/suffix).

    Args:
        enums_dir: Path to the enums directory containing enum_*.py files.

    Returns:
        Frozenset of lowercase enum names (e.g., {"validationlevel", "nodekind"}).
        Returns KNOWN_ENUM_NAMES if the directory doesn't exist.
    """
    if not enums_dir.exists():
        return KNOWN_ENUM_NAMES

    enum_names: set[str] = set()
    pattern = re.compile(r"^enum_(.+)\.py$")

    for file_path in enums_dir.iterdir():
        if file_path.is_file():
            match = pattern.match(file_path.name)
            if match:
                # Convert enum_validation_level.py -> validationlevel
                raw_name = match.group(1)
                normalized = raw_name.replace("_", "").lower()
                enum_names.add(normalized)

    # Merge with known enums to ensure we catch common cases
    return frozenset(enum_names | KNOWN_ENUM_NAMES)


def extract_literal_aliases(file_path: Path) -> list[tuple[str, int]]:
    """Extract Literal type alias names and line numbers from a file.

    Parses the file's AST and finds type alias assignments matching patterns:
    - LiteralFoo = Literal[...]
    - FooLiteral = Literal[...]

    Args:
        file_path: Path to the Python file to analyze.

    Returns:
        List of tuples (alias_name, line_number) for each Literal alias found.
        Returns empty list if file cannot be parsed.
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (OSError, SyntaxError, UnicodeDecodeError) as e:
        # fallback-ok: skip files that cannot be parsed
        logger.debug("Skipping %s: %s", file_path, e)
        return []

    aliases: list[tuple[str, int]] = []

    for node in ast.walk(tree):
        # Look for simple assignments: Name = Literal[...]
        if isinstance(node, ast.Assign):
            # Check if the value is a Literal subscript
            if _is_literal_subscript(node.value):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        alias_name = target.id
                        if _is_literal_alias_name(alias_name):
                            aliases.append((alias_name, node.lineno))

        # Look for annotated assignments: Name: TypeAlias = Literal[...]
        elif isinstance(node, ast.AnnAssign):
            if node.value is not None and isinstance(node.target, ast.Name):
                if _is_literal_subscript(node.value):
                    alias_name = node.target.id
                    if _is_literal_alias_name(alias_name):
                        aliases.append((alias_name, node.lineno))

    return aliases


def _is_literal_subscript(node: ast.AST) -> bool:
    """Check if an AST node is a Literal[...] subscript.

    Args:
        node: AST node to check.

    Returns:
        True if the node is a Literal subscript, False otherwise.
    """
    if isinstance(node, ast.Subscript):
        if isinstance(node.value, ast.Name):
            return node.value.id == "Literal"
        # Handle typing.Literal
        if isinstance(node.value, ast.Attribute):
            return node.value.attr == "Literal"
    return False


def _is_literal_alias_name(name: str) -> bool:
    """Check if a name follows Literal alias naming patterns.

    Matches patterns like:
    - LiteralFoo (starts with Literal, followed by capital letter)
    - FooLiteral (ends with Literal, preceded by PascalCase prefix of 2+ chars)

    Args:
        name: The alias name to check.

    Returns:
        True if the name matches a Literal alias pattern, False otherwise.

    Note:
        The FooLiteral pattern requires the prefix to:
        1. Start with an uppercase letter (PascalCase convention)
        2. Be at least 2 characters long (to avoid false positives like 'XLiteral')

        This prevents false positives on names like 'literalLiteral', '_somethingLiteral',
        or single-letter prefixes that are unlikely to be real type aliases.
    """
    # Pattern: LiteralFoo where Foo starts with uppercase and is at least 1 char
    if name.startswith("Literal") and len(name) > 7:
        suffix = name[7:]
        if suffix and suffix[0].isupper():
            return True

    # Pattern: FooLiteral where Foo follows PascalCase (starts with uppercase)
    # and is at least 2 characters long for meaningful prefix
    if name.endswith("Literal") and len(name) > 7:
        prefix = name[:-7]
        # Require prefix to:
        # 1. Start with uppercase for proper type alias convention
        # 2. Be at least 2 chars to avoid single-letter prefixes like 'XLiteral'
        # This prevents false positives like 'literalLiteral', '_fooLiteral', or 'ALiteral'
        if len(prefix) >= 2 and prefix[0].isupper():
            return True

    return False


def normalize_literal_name(alias_name: str) -> str:
    """Normalize a Literal alias name for comparison with enum names.

    Removes "Literal" prefix/suffix and converts to lowercase. Handles edge
    cases where "Literal" appears multiple times in the name by stripping
    iteratively until no more can be stripped.

    Examples:
        LiteralValidationLevel -> validationlevel
        StepTypeLiteral -> steptype
        LiteralHealthStatus -> healthstatus
        LiteralLiteral -> literal (edge case: strip prefix only to preserve meaning)
        LiteralFooLiteral -> foo (both prefix and suffix removed)
        FooLiteralLiteral -> foo (multiple suffixes stripped)
        LiteralLiteralFoo -> literalfoo (prefix stripped, remaining "LiteralFoo")

    Args:
        alias_name: The Literal alias name to normalize.

    Returns:
        Lowercase normalized name without "Literal" prefix/suffix.
        Returns at least the original name (lowercased) if stripping
        would result in an empty string.

    Note:
        Edge case handling:
        1. If stripping would result in empty string (e.g., "LiteralLiteral"),
           we only strip the prefix to preserve a meaningful name.
        2. Multiple "Literal" suffixes are stripped iteratively to handle
           cases like "FooLiteralLiteral" -> "Foo" -> "foo".
    """
    normalized = alias_name

    # First, handle prefix stripping (only once - "Literal" at start)
    if normalized.startswith("Literal") and len(normalized) > 7:
        after_prefix = normalized[7:]
        # Edge case: "LiteralLiteral" - only strip prefix to preserve meaning
        if after_prefix == "Literal":
            return "literal"
        normalized = after_prefix

    # Then, iteratively strip suffix "Literal" to handle cases like "FooLiteralLiteral"
    # Use a max iterations guard to prevent infinite loops on malformed input
    max_iterations = 10
    iterations = 0
    while (
        normalized.endswith("Literal")
        and len(normalized) > 7
        and iterations < max_iterations
    ):
        normalized = normalized[:-7]
        iterations += 1

    # Safety check: if we somehow stripped everything, return original lowercased
    if not normalized:
        return alias_name.lower()

    return normalized.lower()


def check_for_duplications(
    aliases: list[tuple[str, int]],
    file_path: Path,
    known_enums: frozenset[str],
) -> list[str]:
    """Check if any Literal aliases duplicate known enums.

    Args:
        aliases: List of (alias_name, line_number) tuples from extract_literal_aliases.
        file_path: Path to the file being checked (for error messages).
        known_enums: Set of lowercase enum names to check against.

    Returns:
        List of error messages for each duplication found.
        Each message includes file path, line number, and suggested action.
    """
    errors: list[str] = []

    for alias_name, line_no in aliases:
        normalized = normalize_literal_name(alias_name)

        if normalized in known_enums:
            # Convert normalized name to PascalCase for enum suggestion
            # e.g., "validationlevel" -> "ValidationLevel"
            enum_name = _to_pascal_case(normalized)

            errors.append(
                f"{file_path}:{line_no}: '{alias_name}' duplicates Enum{enum_name}. "
                f"Use Enum{enum_name} from omnibase_core.enums instead of "
                f"creating a Literal alias."
            )

    return errors


def _to_pascal_case(name: str) -> str:
    """Convert a lowercase name to PascalCase.

    Attempts to intelligently split common words and capitalize.
    Falls back to simple capitalize if no known patterns match.

    Args:
        name: Lowercase name to convert.

    Returns:
        PascalCase version of the name.
    """
    # Known word boundaries for common enum names
    # NOTE: Keep in sync with KNOWN_ENUM_NAMES frozenset above
    word_boundaries = {
        "validationlevel": "ValidationLevel",
        "validationmode": "ValidationMode",
        "validationseverity": "ValidationSeverity",
        "validationtype": "ValidationType",
        "validationresult": "ValidationResult",
        "pipelinevalidationmode": "PipelineValidationMode",
        "healthstatus": "HealthStatus",
        "operationstatus": "OperationStatus",
        "servicestatus": "ServiceStatus",
        "basestatus": "BaseStatus",
        "registrationstatus": "RegistrationStatus",
        "serviceresolutionstatus": "ServiceResolutionStatus",
        "nodekind": "NodeKind",
        "nodetype": "NodeType",
        "nodestatus": "NodeStatus",
        "loglevel": "LogLevel",
        "eventpriority": "EventPriority",
        "eventtype": "EventType",
        "servicelifecycle": "ServiceLifecycle",
        "injectionscope": "InjectionScope",
        "steptype": "StepType",
        "computesteptype": "ComputeStepType",
        # Single-word enum names (PascalCase is just capitalized)
        "environment": "Environment",
        "priority": "Priority",
        "severity": "Severity",
        "status": "Status",
        "category": "Category",
    }

    if name in word_boundaries:
        return word_boundaries[name]

    # Fallback: simple capitalize
    return name.capitalize()


def validate_file(file_path: Path, known_enums: frozenset[str]) -> list[str]:
    """Validate a single file for Literal duplication.

    Args:
        file_path: Path to the Python file to validate.
        known_enums: Set of known enum names (lowercase).

    Returns:
        List of error messages for duplications found in this file.
    """
    aliases = extract_literal_aliases(file_path)
    if not aliases:
        return []

    return check_for_duplications(aliases, file_path, known_enums)


def validate_paths(
    paths: list[Path],
    known_enums: frozenset[str],
    exclude_patterns: list[str] | None = None,
    verbose: bool = False,
) -> list[str]:
    """Validate multiple paths (files or directories) for Literal duplication.

    Args:
        paths: List of file or directory paths to validate.
        known_enums: Set of known enum names (lowercase).
        exclude_patterns: Optional list of path patterns to exclude.
        verbose: If True, log progress for each file.

    Returns:
        List of all error messages found across all paths.
    """
    errors: list[str] = []
    exclude_patterns = exclude_patterns or []

    for path in paths:
        if path.is_file():
            if _should_exclude(path, exclude_patterns):
                if verbose:
                    logger.debug("Skipping excluded: %s", path)
                continue
            if path.suffix == ".py":
                file_errors = validate_file(path, known_enums)
                errors.extend(file_errors)
                if verbose and not file_errors:
                    logger.debug("Checked: %s", path)
        elif path.is_dir():
            for file_path in path.rglob("*.py"):
                if file_path.is_symlink():
                    continue
                if _should_exclude(file_path, exclude_patterns):
                    if verbose:
                        logger.debug("Skipping excluded: %s", file_path)
                    continue
                file_errors = validate_file(file_path, known_enums)
                errors.extend(file_errors)
                if verbose and not file_errors:
                    logger.debug("Checked: %s", file_path)

    return errors


def _should_exclude(file_path: Path, exclude_patterns: list[str]) -> bool:
    """Check if a file should be excluded from validation.

    Args:
        file_path: Path to check. Both absolute and relative paths are supported;
            relative paths are resolved to absolute paths before matching.
        exclude_patterns: List of patterns to match against. Patterns are matched
            as exact path components, not as substrings. For example, "test" will
            only exclude paths containing a directory named exactly "test", not
            paths containing "mytest" or "testing". Relative path prefixes like
            "./" are stripped before matching (e.g., "./tests/" matches "tests").

    Returns:
        True if the file should be excluded, False otherwise.
    """
    # Resolve the path to handle cases like "src/../tests/foo.py"
    # This normalizes away ".." and "." components for reliable matching
    try:
        resolved_path = file_path.resolve()
    except OSError:
        # fallback-ok: if resolution fails, use original path
        resolved_path = file_path

    # Always exclude test files using Path.parts for robust path component matching
    # This correctly handles both absolute and relative paths across all operating systems:
    # - tests/unit/foo.py -> parts = ('tests', 'unit', 'foo.py')
    # - ./tests/unit/foo.py -> resolved -> parts without '.'
    # - /abs/path/tests/bar.py -> parts = ('/', 'abs', 'path', 'tests', 'bar.py')
    # - src/../tests/foo.py -> resolved -> parts = (..., 'tests', 'foo.py')
    if "tests" in resolved_path.parts:
        return True

    # Exclude the checker itself
    if resolved_path.name == "checker_literal_duplication.py":
        return True

    # Check custom exclude patterns using exact path component matching
    # This prevents false positives where a pattern like "test" would match
    # paths containing "contest" or "testing"
    path_parts = resolved_path.parts
    for pattern in exclude_patterns:
        # Strip trailing path separators to handle patterns like "tests/" or "src/"
        # This ensures "tests/" matches the "tests" path component correctly
        normalized_pattern = pattern.rstrip("/\\")

        # Strip leading "./" or ".\" for relative path patterns
        # This handles patterns like "./tests" or ".\tests" that should match
        # as the component "tests", not as a path to resolve relative to cwd.
        # Example: "./tests/" -> "tests" (matches any path with "tests" component)
        while normalized_pattern.startswith(("./", ".\\")):
            normalized_pattern = normalized_pattern[2:]

        # Skip empty patterns (e.g., if pattern was just "./" or "./")
        if not normalized_pattern:
            continue

        # Handle full path patterns (e.g., "/full/path/tests" or "src/tests")
        # If pattern contains path separators, treat it as a path prefix match
        if "/" in normalized_pattern or "\\" in normalized_pattern:
            try:
                pattern_path = Path(normalized_pattern).resolve()
                # Check if file is under the pattern directory
                resolved_path.relative_to(pattern_path)
                return True
            except (OSError, ValueError):
                # Pattern is not a parent of the file, continue checking
                pass

        # Check if pattern matches any path component exactly
        if normalized_pattern in path_parts:
            return True
        # Also support fnmatch-style glob patterns for flexibility
        # e.g., "test_*" to match "test_utils", "test_helpers", etc.
        if (
            "*" in normalized_pattern
            or "?" in normalized_pattern
            or "[" in normalized_pattern
        ):
            for part in path_parts:
                if fnmatch.fnmatch(part, normalized_pattern):
                    return True

    return False


def find_enums_directory() -> Path | None:
    """Find the omnibase_core/enums directory relative to this file.

    Returns:
        Path to the enums directory if found, None otherwise.
    """
    # Start from this file and walk up to find omnibase_core
    current = Path(__file__).resolve()

    # Walk up to find omnibase_core
    while current.name != "omnibase_core" and current.parent != current:
        current = current.parent

    if current.name == "omnibase_core":
        enums_dir = current / "enums"
        if enums_dir.exists():
            return enums_dir

    return None


def main() -> int:
    """Main entry point for command-line validation.

    Parses command-line arguments and validates Python files for Literal
    type alias duplications that could be replaced with existing enums.

    CLI Usage:
        Default (validates src/omnibase_core)::

            python -m omnibase_core.validation.checker_literal_duplication

        Validate specific paths::

            python -m omnibase_core.validation.checker_literal_duplication src/

        With verbose output::

            python -m omnibase_core.validation.checker_literal_duplication -v

    Returns:
        int: Exit code for shell integration.

            - 0: No duplications found (success)
            - 1: Duplications detected or error (failure)

    Note:
        This function is designed for CI/CD integration. A non-zero exit code
        will cause pre-commit hooks and CI pipelines to fail, preventing
        merges of code that introduces Literal duplication.
    """
    parser = argparse.ArgumentParser(
        description="Check for Literal type alias duplication with existing enums",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Check src/omnibase_core (default)
  %(prog)s src/               Check the src directory
  %(prog)s file1.py file2.py  Check specific files
  %(prog)s -v                 Check with verbose output

This checker prevents creating Literal type aliases that duplicate
existing enums in omnibase_core.enums/. Using Literal aliases creates
synchronization problems when enum values change.

Instead of:
    LiteralValidationLevel = Literal["BASIC", "STANDARD", "COMPREHENSIVE"]

Use:
    from omnibase_core.enums import EnumValidationLevel
""",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=None,
        help="Files or directories to check (default: src/omnibase_core)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print progress for each file checked",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="Additional path patterns to exclude",
    )

    args = parser.parse_args()

    # Configure logging for CLI usage
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(message)s", force=True)

    # Determine target paths
    if args.paths:
        target_paths = args.paths
    else:
        # Find src/omnibase_core relative to this file
        this_file = Path(__file__)
        # Go up from validation/ to omnibase_core/
        target_dir = this_file.parent.parent
        target_paths = [target_dir]

    # Validate paths exist
    for path in target_paths:
        if not path.exists():
            logger.error("Path not found: %s", path)
            return 1

    # Find enum names from the enums directory
    enums_dir = find_enums_directory()
    if enums_dir:
        known_enums = get_enum_names_from_directory(enums_dir)
        logger.debug("Loaded %d enum names from %s", len(known_enums), enums_dir)
    else:
        known_enums = KNOWN_ENUM_NAMES
        logger.debug("Using built-in enum names (%d)", len(known_enums))

    logger.info("Checking for Literal type alias duplication...")
    if args.verbose:
        logger.info("Paths: %s", [str(p) for p in target_paths])
    logger.info("-" * 60)

    errors = validate_paths(
        target_paths,
        known_enums,
        exclude_patterns=args.exclude,
        verbose=args.verbose,
    )

    if errors:
        logger.warning("Found %d Literal duplication(s):", len(errors))
        for error in sorted(errors):
            logger.warning("  %s", error)
        logger.info("")
        logger.info("Action: Replace Literal aliases with enum imports.")
        logger.info("Example:")
        logger.info("  - LiteralValidationLevel = Literal[...]")
        logger.info("  + from omnibase_core.enums import EnumValidationLevel")
        return 1

    logger.info("No Literal duplications found!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
