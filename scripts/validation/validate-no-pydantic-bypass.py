#!/usr/bin/env python3
"""Validate that Pydantic bypass patterns are not used in production code.

This script enforces that model_construct(), direct __dict__ manipulation,
and object.__setattr__() on frozen models are ONLY used in tests/fixtures/.

These patterns bypass Pydantic's validation, type coercion, and defaults,
which is acceptable in test fixtures for performance but NEVER in production.

EXCEPTIONS:
- object.__setattr__() IS allowed in __init__ methods (frozen model initialization)
- object.__setattr__() IS allowed in Pydantic validators (avoid validate_assignment recursion)

Usage:
    # Check specific files (typically via pre-commit hook)
    python scripts/validation/validate_no_pydantic_bypass.py src/file1.py src/file2.py

    # Check entire src directory
    python scripts/validation/validate_no_pydantic_bypass.py src/

Exit Codes:
    0: No violations found
    1: Pydantic bypass patterns found in production code
    2: Script error (invalid arguments, file not found, etc.)
"""

import re
import sys
import tokenize
from io import StringIO
from pathlib import Path

# Patterns that indicate Pydantic validation bypass
BYPASS_PATTERNS = [
    (r"\.model_construct\s*\(", "model_construct() bypasses validation"),
    (r"\.__dict__\s*\[", "Direct __dict__ access bypasses validation"),
    (r"object\.__setattr__\s*\(", "object.__setattr__() bypasses frozen models"),
]

# Patterns that are acceptable (false positives to ignore)
# NOTE: This is deprecated in favor of tokenize-based detection,
# but kept for backward compatibility
ALLOWED_PATTERNS = [
    r"#.*model_construct",  # Comments mentioning model_construct
    r'""".*model_construct.*"""',  # Docstrings mentioning model_construct
    r"'''.*model_construct.*'''",  # Docstrings mentioning model_construct
    r'"[^"]*model_construct[^"]*"',  # String literals with model_construct
    r"'[^']*model_construct[^']*'",  # String literals with model_construct
    r"#.*__dict__",  # Comments mentioning __dict__
    r'""".*__dict__.*"""',  # Docstrings mentioning __dict__
    r"'''.*__dict__.*'''",  # Docstrings mentioning __dict__
    r'"[^"]*__dict__[^"]*"',  # String literals with __dict__
    r"'[^']*__dict__[^']*'",  # String literals with __dict__
    r"#.*object\.__setattr__",  # Comments mentioning object.__setattr__
    r'""".*object\.__setattr__.*"""',  # Docstrings mentioning object.__setattr__
    r"'''.*object\.__setattr__.*'''",  # Docstrings mentioning object.__setattr__
    r'"[^"]*object\.__setattr__[^"]*"',  # String literals with object.__setattr__
    r"'[^']*object\.__setattr__[^']*'",  # String literals with object.__setattr__
]

# Files with existing violations (technical debt) - tracked in GitHub issues
# TODO(GitHub #XX): Fix object.__setattr__() usage outside __init__/validators
EXCLUDED_FILES = [
    "src/omnibase_core/models/metadata/node_info/model_node_core.py",  # Lines 123, 147
    "src/omnibase_core/infrastructure/node_core_base.py",  # Lines 379, 401
    "src/omnibase_core/mixins/mixin_event_bus.py",  # Line 109
    "src/omnibase_core/mixins/mixin_metrics.py",  # Lines 49, 54, 61, 77, 82, 89, 102, 107, 113, 118
    "src/omnibase_core/models/contracts/model_contract_compute.py",  # Lines 222, 223
    "src/omnibase_core/models/contracts/model_contract_effect.py",  # Lines 122, 123
    # Legitimate perf optimization: bypasses validate_assignment (not frozen) for timestamp updates
    "src/omnibase_core/models/core/model_examples_collection.py",  # Lines 273, 291, 311
]


def get_string_and_comment_ranges(content: str) -> dict[int, list[tuple[int, int]]]:
    """Use tokenize to identify character ranges that are strings or comments.

    Args:
        content: File content as string

    Returns:
        Dictionary mapping line numbers (1-indexed) to list of (start_col, end_col)
        tuples indicating character ranges that are strings or comments
    """
    string_comment_ranges: dict[int, list[tuple[int, int]]] = {}

    try:
        tokens = tokenize.generate_tokens(StringIO(content).readline)
        for token in tokens:
            if token.type in (tokenize.STRING, tokenize.COMMENT):
                start_line, start_col = token.start
                end_line, end_col = token.end

                # For single-line tokens
                if start_line == end_line:
                    if start_line not in string_comment_ranges:
                        string_comment_ranges[start_line] = []
                    string_comment_ranges[start_line].append((start_col, end_col))
                else:
                    # For multi-line tokens (docstrings), mark entire lines
                    for line_num in range(start_line, end_line + 1):
                        if line_num not in string_comment_ranges:
                            string_comment_ranges[line_num] = []
                        # For first and last line, use actual positions
                        if line_num == start_line:
                            string_comment_ranges[line_num].append((start_col, 9999))
                        elif line_num == end_line:
                            string_comment_ranges[line_num].append((0, end_col))
                        else:
                            # Middle lines - entire line is in string
                            string_comment_ranges[line_num].append((0, 9999))
    except tokenize.TokenError:
        # If tokenization fails (e.g., incomplete file), fall back to empty dict
        # This means we'll check all lines, which is safer than skipping them
        pass

    return string_comment_ranges


def is_match_in_string_or_comment(
    line_num: int,
    match_start: int,
    match_end: int,
    ranges: dict[int, list[tuple[int, int]]],
) -> bool:
    """Check if a regex match is inside a string or comment.

    Args:
        line_num: Line number (1-indexed)
        match_start: Start column of match
        match_end: End column of match
        ranges: Dictionary of string/comment ranges from get_string_and_comment_ranges()

    Returns:
        True if the match overlaps with any string or comment range
    """
    if line_num not in ranges:
        return False

    for start_col, end_col in ranges[line_num]:
        # Check if match overlaps with this string/comment range
        if not (match_end <= start_col or match_start >= end_col):
            return True

    return False


def is_allowed_context(line: str) -> bool:
    """Check if line is in an allowed context (comment, docstring, string).

    DEPRECATED: This function is kept for backward compatibility but is no longer
    used. Use get_string_and_comment_lines() with tokenize instead.
    """
    for pattern in ALLOWED_PATTERNS:
        if re.search(pattern, line):
            return True
    return False


def check_file(filepath: Path) -> tuple[list[tuple[int, str, str]], str | None]:
    """Check file for Pydantic bypass patterns.

    Uses tokenize module to skip strings and comments, avoiding false positives.

    Args:
        filepath: Path to Python file to check

    Returns:
        Tuple of (violations_list, error_message)
        - violations_list: List of tuples (line_number, line_content, violation_description)
        - error_message: Error message if file couldn't be read, None otherwise
    """
    violations = []

    # Skip excluded files (existing technical debt tracked in GitHub issues)
    filepath_str = str(filepath)
    for excluded in EXCLUDED_FILES:
        if filepath_str.endswith(excluded) or excluded in filepath_str:
            return (violations, None)

    try:
        content = filepath.read_text()
    except Exception as e:
        return ([], f"Error reading {filepath}: {e}")

    # Build character-range map of strings and comments using tokenize
    string_comment_ranges = get_string_and_comment_ranges(content)

    lines = content.splitlines()
    in_init_method = False
    init_indent = -1
    in_validator = False
    validator_function_indent = -1
    seen_validator_def = False

    for line_num, line in enumerate(lines, 1):
        # Track Pydantic validator context
        if re.search(r"@(field_validator|model_validator|root_validator)", line):
            in_validator = True
            seen_validator_def = False
            validator_function_indent = -1
        elif (
            in_validator
            and not seen_validator_def
            and re.search(r"^\s*def\s+\w+\s*\(", line)
        ):
            # This is the validator function definition
            seen_validator_def = True
            validator_function_indent = len(line) - len(line.lstrip())
        elif in_validator and seen_validator_def and line.strip():
            # Check if we've exited validator (new decorator/method at same/lower indent)
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= validator_function_indent:
                # If it's a decorator or new function at same/lower indent, we've exited
                if re.search(r"@\w+", line) or re.search(r"^\s*def\s+\w+\s*\(", line):
                    in_validator = False
                    seen_validator_def = False

        # Track __init__ method context
        if re.search(r"^\s*def\s+__init__\s*\(", line):
            in_init_method = True
            init_indent = len(line) - len(line.lstrip())
        elif in_init_method and line.strip():
            # Check if we've exited __init__ (new method def at same indent level)
            current_indent = len(line) - len(line.lstrip())
            if current_indent == init_indent and re.search(r"^\s*def\s+\w+\s*\(", line):
                in_init_method = False

        # Check for bypass patterns
        for pattern, description in BYPASS_PATTERNS:
            match = re.search(pattern, line)
            if match:
                # Check if match is inside a string or comment using tokenize
                if is_match_in_string_or_comment(
                    line_num, match.start(), match.end(), string_comment_ranges
                ):
                    continue

                # Allow object.__setattr__ in __init__ methods and Pydantic validators
                if pattern == r"object\.__setattr__\s*\(" and (
                    in_init_method or in_validator
                ):
                    continue
                violations.append((line_num, line.strip(), description))

    return (violations, None)


def check_path(
    path: Path,
) -> tuple[list[tuple[Path, int, str, str]], list[str]]:
    """Check path (file or directory) for violations.

    Args:
        path: Path to check (file or directory)

    Returns:
        Tuple of (violations_list, errors_list)
        - violations_list: List of tuples (filepath, line_number, line_content, violation_description)
        - errors_list: List of error messages for unreadable files
    """
    all_violations = []
    all_errors = []

    if path.is_file():
        if path.suffix == ".py":
            violations, error = check_file(path)
            if error:
                all_errors.append(error)
            all_violations.extend(
                (path, line_num, line, desc) for line_num, line, desc in violations
            )
    elif path.is_dir():
        # Recursively check all Python files in directory
        for py_file in path.rglob("*.py"):
            violations, error = check_file(py_file)
            if error:
                all_errors.append(error)
            all_violations.extend(
                (py_file, line_num, line, desc) for line_num, line, desc in violations
            )
    else:
        print(f"Warning: {path} is not a file or directory", file=sys.stderr)

    return (all_violations, all_errors)


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: validate_no_pydantic_bypass.py <file_or_dir> [<file_or_dir> ...]")
        print("\nChecks production code (src/) for Pydantic bypass patterns.")
        print("These patterns are only allowed in tests/fixtures/.")
        return 2

    # Collect all violations and errors
    all_violations = []
    all_errors = []
    for arg in sys.argv[1:]:
        path = Path(arg)
        if not path.exists():
            print(f"Error: {path} does not exist", file=sys.stderr)
            return 2

        violations, errors = check_path(path)
        all_violations.extend(violations)
        all_errors.extend(errors)

    # Report results
    if all_violations:
        print("=" * 80)
        print("❌ PYDANTIC BYPASS PATTERNS FOUND IN PRODUCTION CODE")
        print("=" * 80)
        print()
        print("The following files use Pydantic bypass patterns that are ONLY")
        print("allowed in tests/fixtures/:")
        print()

        for filepath, line_num, line, description in all_violations:
            print(f"  {filepath}:{line_num}")
            print(f"    → {description}")
            print(f"    → {line}")
            print()

        print("=" * 80)
        print("⚠️  THESE PATTERNS SHOULD ONLY BE USED IN tests/fixtures/")
        print("=" * 80)
        print()
        print("Why these patterns are restricted:")
        print("  • model_construct() bypasses ALL Pydantic validation")
        print("  • __dict__ access bypasses validation and can break invariants")
        print("  • object.__setattr__() bypasses frozen model protections")
        print()
        print("Where they ARE allowed:")
        print("  • tests/fixtures/ - for fast test fixture creation")
        print("  • Performance: 10-100x faster than validated construction")
        print()
        print("How to fix:")
        print("  1. If this is production code: Use normal model construction")
        print("  2. If this is test code: Move to tests/fixtures/ and inherit")
        print("     from TestFixtureBase")
        print()
        print(f"Total violations: {len(all_violations)}")
        return 1

    # Report any file reading errors
    if all_errors:
        print("=" * 80)
        print("⚠️  FILE READING ERRORS")
        print("=" * 80)
        print()
        for error in all_errors:
            print(f"  {error}")
        print()
        print(f"Total files with errors: {len(all_errors)}")
        print("=" * 80)
        print()
        # Don't fail on read errors, just warn
        # return 2

    print("✅ No Pydantic bypass patterns found in production code")
    return 0


if __name__ == "__main__":
    sys.exit(main())
