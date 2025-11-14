#!/usr/bin/env python3
"""
Fix missing 'self' in multi-line method signatures.

This script properly handles multi-line method definitions.
"""

import re
import subprocess
from pathlib import Path

ROOT_DIR = Path("/Volumes/PRO-G40/Code/omnibase_core")


def run_mypy_for_file(file_path: str) -> list[int]:
    """Run MyPy on a specific file and return line numbers with 'self' errors."""
    result = subprocess.run(
        ["poetry", "run", "mypy", file_path, "--no-error-summary"],
        capture_output=True,
        text=True,
        cwd=ROOT_DIR,
        check=False,
    )

    output = result.stdout + result.stderr
    error_lines = []

    pattern = r':(\d+): error: Name "self" is not defined'

    for line in output.split("\n"):
        match = re.search(pattern, line)
        if match:
            error_lines.append(int(match.group(1)))

    return error_lines


def find_method_start(lines: list[str], error_line_idx: int) -> int | None:
    """Find the start of the method definition for an error line."""
    # Search backwards for 'def '
    for i in range(error_line_idx, max(0, error_line_idx - 200), -1):
        if lines[i].strip().startswith("def "):
            return i
    return None


def find_method_end_of_signature(lines: list[str], start_idx: int) -> int | None:
    """Find the end of a method signature (the line with closing paren and colon)."""
    # Method signature might span multiple lines
    # Look for the line with '):' or ') ->'
    for i in range(start_idx, min(len(lines), start_idx + 20)):
        line = lines[i].strip()
        if "):" in line or ") ->" in line:
            return i
    return None


def get_full_signature(lines: list[str], start_idx: int, end_idx: int) -> str:
    """Get the full method signature across multiple lines."""
    return "\n".join(lines[start_idx : end_idx + 1])


def has_self_or_cls(signature: str) -> bool:
    """Check if signature already has 'self' or 'cls'."""
    # Extract content between first ( and first , or )
    match = re.search(r"\(\s*([^,\)]+)", signature, re.DOTALL)
    if match:
        first_param = match.group(1).strip()
        return first_param in ("self", "cls")
    return False


def has_decorator(
    lines: list[str], method_start_idx: int, decorator_names: list[str]
) -> bool:
    """Check if method has any of the specified decorators."""
    # Look at a few lines before the method
    for i in range(max(0, method_start_idx - 10), method_start_idx):
        line = lines[i].strip()
        for dec_name in decorator_names:
            if f"@{dec_name}" in line:
                return True
    return False


def add_self_to_signature(lines: list[str], start_idx: int, end_idx: int) -> bool:
    """
    Add 'self' to a multi-line method signature.

    Returns True if modification was made.
    """
    # Find the line with the opening parenthesis
    for i in range(start_idx, end_idx + 1):
        if "(" in lines[i]:
            # This is the line with (
            # Check if there's content after (
            before_paren, after_paren = lines[i].split("(", 1)

            # Check if there's already a parameter on this line
            if after_paren.strip() and not after_paren.strip().startswith(")"):
                # There's a parameter, add self before it
                # Handle indentation
                indent = len(lines[i]) - len(lines[i].lstrip())
                param_indent = " " * (indent + 4)  # Standard Python indent

                # Add self on next line
                lines.insert(i + 1, f"{param_indent}self,")
            else:
                # Empty params or closing paren on same line
                # Just add self
                lines[i] = f"{before_paren}(\n"
                indent = len(lines[i]) - len(lines[i].lstrip())
                param_indent = " " * (indent + 4)
                lines.insert(i + 1, f"{param_indent}self,")

            return True

    return False


def fix_file(file_path: str) -> int:
    """Fix all missing 'self' errors in a file."""
    path = Path(file_path)
    if not path.exists():
        return 0

    error_lines = run_mypy_for_file(file_path)
    if not error_lines:
        return 0

    content = path.read_text()
    lines = content.split("\n")

    fixed_count = 0
    processed_methods = set()

    for error_line_num in sorted(
        set(error_lines), reverse=True
    ):  # Process in reverse to maintain line numbers
        error_idx = error_line_num - 1

        # Find method start
        method_start = find_method_start(lines, error_idx)
        if method_start is None:
            continue

        # Skip if already processed
        if method_start in processed_methods:
            continue

        processed_methods.add(method_start)

        # Find method signature end
        method_end = find_method_end_of_signature(lines, method_start)
        if method_end is None:
            continue

        # Get full signature
        signature = get_full_signature(lines, method_start, method_end)

        # Check if has self/cls
        if has_self_or_cls(signature):
            continue

        # Check for decorators
        if has_decorator(lines, method_start, ["staticmethod", "classmethod"]):
            continue

        # Add self
        if add_self_to_signature(lines, method_start, method_end):
            method_match = re.match(r"\s*def\s+(\w+)", lines[method_start])
            method_name = method_match.group(1) if method_match else "unknown"
            print(f"    Fixed '{method_name}' at line {method_start + 1}")
            fixed_count += 1

    if fixed_count > 0:
        path.write_text("\n".join(lines))

    return fixed_count


def main():
    """Main function."""
    print("=" * 80)
    print("FIXING MULTI-LINE METHOD SIGNATURES")
    print("=" * 80)

    # Get list of files with self errors
    mixin_files = [
        "src/omnibase_core/mixins/mixin_canonical_serialization.py",
        "src/omnibase_core/mixins/mixin_contract_state_reducer.py",
        "src/omnibase_core/mixins/mixin_discovery_responder.py",
        "src/omnibase_core/mixins/mixin_event_bus.py",
        "src/omnibase_core/mixins/mixin_event_driven_node.py",
        "src/omnibase_core/mixins/mixin_event_listener.py",
        "src/omnibase_core/mixins/mixin_hash_computation.py",
        "src/omnibase_core/mixins/mixin_hybrid_execution.py",
        "src/omnibase_core/mixins/mixin_node_executor.py",
        "src/omnibase_core/mixins/mixin_node_lifecycle.py",
        "src/omnibase_core/mixins/mixin_request_response_introspection.py",
        "src/omnibase_core/mixins/mixin_service_registry.py",
        "src/omnibase_core/mixins/mixin_tool_execution.py",
        "src/omnibase_core/mixins/mixin_workflow_support.py",
    ]

    total_fixed = 0

    for file_path in mixin_files:
        print(f"\nProcessing: {file_path}")
        fixed = fix_file(file_path)
        total_fixed += fixed

        if fixed > 0:
            print(f"  ✓ Fixed {fixed} methods")
        else:
            print("  - No issues found")

    print("\n" + "=" * 80)
    print(f"TOTAL: {total_fixed} methods fixed")
    print("=" * 80)


if __name__ == "__main__":
    main()
