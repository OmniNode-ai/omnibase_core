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
from pathlib import Path
from typing import List, Tuple

# Patterns that indicate Pydantic validation bypass
BYPASS_PATTERNS = [
    (r"\.model_construct\s*\(", "model_construct() bypasses validation"),
    (r"\.__dict__\s*\[", "Direct __dict__ access bypasses validation"),
    (r"object\.__setattr__\s*\(", "object.__setattr__() bypasses frozen models"),
]

# Patterns that are acceptable (false positives to ignore)
ALLOWED_PATTERNS = [
    r"#.*model_construct",  # Comments mentioning it
    r'""".*model_construct.*"""',  # Docstrings mentioning it
    r"'''.*model_construct.*'''",  # Docstrings mentioning it
    r'"[^"]*model_construct[^"]*"',  # String literals
    r"'[^']*model_construct[^']*'",  # String literals
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
]


def is_allowed_context(line: str) -> bool:
    """Check if line is in an allowed context (comment, docstring, string)."""
    for pattern in ALLOWED_PATTERNS:
        if re.search(pattern, line):
            return True
    return False


def check_file(filepath: Path) -> List[Tuple[int, str, str]]:
    """Check file for Pydantic bypass patterns.

    Args:
        filepath: Path to Python file to check

    Returns:
        List of tuples (line_number, line_content, violation_description)
    """
    violations = []

    # Skip excluded files (existing technical debt tracked in GitHub issues)
    filepath_str = str(filepath)
    for excluded in EXCLUDED_FILES:
        if filepath_str.endswith(excluded) or excluded in filepath_str:
            return violations

    try:
        content = filepath.read_text()
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return violations

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

        # Skip if line is in allowed context
        if is_allowed_context(line):
            continue

        # Check for bypass patterns
        for pattern, description in BYPASS_PATTERNS:
            if re.search(pattern, line):
                # Allow object.__setattr__ in __init__ methods and Pydantic validators
                if pattern == r"object\.__setattr__\s*\(" and (
                    in_init_method or in_validator
                ):
                    continue
                violations.append((line_num, line.strip(), description))

    return violations


def check_path(path: Path) -> List[Tuple[Path, int, str, str]]:
    """Check path (file or directory) for violations.

    Args:
        path: Path to check (file or directory)

    Returns:
        List of tuples (filepath, line_number, line_content, violation_description)
    """
    all_violations = []

    if path.is_file():
        if path.suffix == ".py":
            violations = check_file(path)
            all_violations.extend(
                (path, line_num, line, desc) for line_num, line, desc in violations
            )
    elif path.is_dir():
        # Recursively check all Python files in directory
        for py_file in path.rglob("*.py"):
            violations = check_file(py_file)
            all_violations.extend(
                (py_file, line_num, line, desc) for line_num, line, desc in violations
            )
    else:
        print(f"Warning: {path} is not a file or directory", file=sys.stderr)

    return all_violations


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: validate_no_pydantic_bypass.py <file_or_dir> [<file_or_dir> ...]")
        print("\nChecks production code (src/) for Pydantic bypass patterns.")
        print("These patterns are only allowed in tests/fixtures/.")
        return 2

    # Collect all violations
    all_violations = []
    for arg in sys.argv[1:]:
        path = Path(arg)
        if not path.exists():
            print(f"Error: {path} does not exist", file=sys.stderr)
            return 2

        violations = check_path(path)
        all_violations.extend(violations)

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

    print("✅ No Pydantic bypass patterns found in production code")
    return 0


if __name__ == "__main__":
    sys.exit(main())
