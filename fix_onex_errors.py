#!/usr/bin/env python3
"""
Systematic fix for ONEX error raising compliance.

This script automatically fixes standard Python exception raises by replacing them
with appropriate ModelOnexError instances with proper error codes.
"""

import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Mapping from standard exceptions to appropriate ModelCoreErrorCode values
EXCEPTION_TO_ERROR_CODE = {
    "ValueError": "ModelCoreErrorCode.VALIDATION_ERROR",
    "TypeError": "ModelCoreErrorCode.PARAMETER_TYPE_MISMATCH",
    "RuntimeError": "ModelCoreErrorCode.INTERNAL_ERROR",
    "KeyError": "ModelCoreErrorCode.NOT_FOUND",
    "AttributeError": "ModelCoreErrorCode.INVALID_OPERATION",
    "IndexError": "ModelCoreErrorCode.NOT_FOUND",
    "FileNotFoundError": "ModelCoreErrorCode.FILE_NOT_FOUND",
    "PermissionError": "ModelCoreErrorCode.PERMISSION_ERROR",
    "ImportError": "ModelCoreErrorCode.IMPORT_ERROR",
    "ModuleNotFoundError": "ModelCoreErrorCode.MODULE_NOT_FOUND",
    "OSError": "ModelCoreErrorCode.INTERNAL_ERROR",
    "IOError": "ModelCoreErrorCode.FILE_OPERATION_ERROR",
    "ConnectionError": "ModelCoreErrorCode.NETWORK_ERROR",
    "TimeoutError": "ModelCoreErrorCode.TIMEOUT_ERROR",
    "AssertionError": "ModelCoreErrorCode.VALIDATION_FAILED",
    "NotImplementedError": "ModelCoreErrorCode.METHOD_NOT_IMPLEMENTED",
}


class ErrorFixer(ast.NodeTransformer):
    """AST transformer to fix error raising violations."""

    def __init__(self, filename: str, source_lines: List[str]):
        self.filename = filename
        self.source_lines = source_lines
        self.changes_made = 0

    def visit_Raise(self, node: ast.Raise) -> ast.Raise:
        """Transform raise statements to use ModelOnexError."""
        if node.exc is None:
            return node

        exception_name = self._get_exception_name(node.exc)

        # Skip if not a standard exception we need to fix
        if exception_name not in EXCEPTION_TO_ERROR_CODE:
            return node

        # Check for error-ok comment
        line_num = node.lineno
        if self._has_error_ok_comment(line_num):
            return node

        # Check for stub-ok comment (for NotImplementedError)
        if exception_name == "NotImplementedError" and self._has_stub_ok_comment(
            line_num
        ):
            return node

        # Create the replacement raise node
        self.changes_made += 1
        return self._create_onex_error_raise(node, exception_name)

    def _get_exception_name(self, node: ast.expr) -> str | None:
        """Extract exception name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node.func.id
            elif isinstance(node.func, ast.Attribute):
                return node.func.attr
        elif isinstance(node, ast.Attribute):
            return node.attr
        return None

    def _has_error_ok_comment(self, line_num: int) -> bool:
        """Check if line has # error-ok: comment."""
        if line_num < 1 or line_num > len(self.source_lines):
            return False

        line = self.source_lines[line_num - 1]
        if "# error-ok:" in line:
            return True

        if line_num > 1:
            prev_line = self.source_lines[line_num - 2]
            if "# error-ok:" in prev_line.strip():
                return True

        return False

    def _has_stub_ok_comment(self, line_num: int) -> bool:
        """Check if line has # stub-ok: comment."""
        if line_num < 1 or line_num > len(self.source_lines):
            return False

        line = self.source_lines[line_num - 1]
        if "# stub-ok:" in line:
            return True

        if line_num > 1:
            prev_line = self.source_lines[line_num - 2]
            if "# stub-ok:" in prev_line.strip():
                return True

        return False

    def _create_onex_error_raise(
        self, original_node: ast.Raise, exception_name: str
    ) -> ast.Raise:
        """Create a new raise node that uses ModelOnexError."""
        error_code = EXCEPTION_TO_ERROR_CODE[exception_name]

        # Extract the original message if possible
        original_message = self._extract_message(original_node.exc)

        # Create ModelOnexError constructor call
        onex_error_call = ast.Call(
            func=ast.Name(id="ModelOnexError", ctx=ast.Load()),
            args=[
                (
                    original_message
                    if original_message
                    else ast.Constant(value="Error occurred")
                )
            ],
            keywords=[
                ast.keyword(arg="code", value=ast.Name(id=error_code, ctx=ast.Load()))
            ],
        )

        return ast.Raise(exc=onex_error_call, cause=None)

    def _extract_message(self, node: ast.expr) -> ast.expr | None:
        """Extract message from exception constructor call."""
        if isinstance(node, ast.Call) and len(node.args) > 0:
            return node.args[0]
        return None


def fix_file(file_path: Path) -> Tuple[bool, int]:
    """Fix error raising violations in a single file."""
    # Skip test files and validation scripts
    if any(
        pattern in str(file_path) for pattern in ["tests/", "/validation/", "/scripts/"]
    ):
        return True, 0

    if file_path.suffix != ".py":
        return True, 0

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
            source_lines = source.splitlines()

        # Parse the AST
        tree = ast.parse(source, filename=str(file_path))

        # Apply transformations
        fixer = ErrorFixer(str(file_path), source_lines)
        new_tree = fixer.visit(tree)

        if fixer.changes_made == 0:
            return True, 0

        # Generate the fixed source code
        fixed_source = ast.unparse(new_tree)

        # Add necessary imports if missing
        if fixer.changes_made > 0:
            fixed_source = _ensure_imports(source, fixed_source)

        # Write the fixed file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(fixed_source)

        print(f"Fixed {fixer.changes_made} violations in {file_path}")
        return True, fixer.changes_made

    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False, 0


def _ensure_imports(original_source: str, fixed_source: str) -> str:
    """Ensure necessary imports are present while preserving original formatting."""
    imports_needed = []

    # Check if ModelOnexError is imported
    if (
        "ModelOnexError" not in original_source
        and "from omnibase_core.errors" not in original_source
    ):
        imports_needed.append("from omnibase_core.errors import ModelOnexError")

    # Check if ModelCoreErrorCode is imported
    if "ModelCoreErrorCode" not in original_source:
        imports_needed.append(
            "from omnibase_core.errors.error_codes import ModelCoreErrorCode"
        )

    if not imports_needed:
        return fixed_source

    # Find the insertion point in the original source
    lines = original_source.splitlines()
    insert_index = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(("import ", "from ")):
            insert_index = i + 1
        elif (
            stripped
            and not stripped.startswith("#")
            and not stripped.startswith(("import ", "from "))
        ):
            break

    # Find the same position in the fixed source
    fixed_lines = fixed_source.splitlines()

    # Insert the new imports
    for import_line in reversed(imports_needed):
        fixed_lines.insert(insert_index, import_line)

    return "\n".join(fixed_lines) + "\n"


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: fix_onex_errors.py <file1.py> [file2.py] ...")
        return 1

    total_fixed = 0
    files_processed = 0

    for file_arg in sys.argv[1:]:
        file_path = Path(file_arg)
        if not file_path.exists():
            print(f"File not found: {file_path}")
            continue

        success, fixed_count = fix_file(file_path)
        files_processed += 1
        if success:
            total_fixed += fixed_count

    print(f"\nProcessed {files_processed} files, fixed {total_fixed} violations")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
