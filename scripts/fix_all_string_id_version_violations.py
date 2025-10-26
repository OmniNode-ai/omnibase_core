#!/usr/bin/env python3
"""
AST-based script to automatically fix string ID and version field violations.

This script:
1. Parses Python files using AST
2. Identifies Pydantic Field definitions with str type for ID/version fields
3. Replaces them with UUID/ModelSemVer types
4. Adds necessary imports (UUID, ModelSemVer)
5. Writes the modified code back

Usage:
    poetry run python scripts/fix_all_string_id_version_violations.py
"""

import ast
import re
from pathlib import Path


class StringFieldRewriter(ast.NodeTransformer):
    """AST transformer to replace string ID/version fields with proper types."""

    def __init__(self):
        self.needs_uuid_import = False
        self.needs_modelsemver_import = False
        self.changes_made = False

    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.AnnAssign:
        """Visit annotated assignments (field: type = ...)."""
        if not isinstance(node.target, ast.Name):
            return node

        field_name = node.target.id

        # Check if this is an ID field
        if self._is_id_field(field_name):
            if self._has_string_type(node.annotation):
                # Replace str with UUID
                node.annotation = self._replace_with_uuid(node.annotation)
                self.needs_uuid_import = True
                self.changes_made = True

        # Check if this is a version field
        elif self._is_version_field(field_name):
            if self._has_string_type(node.annotation):
                # Replace str with ModelSemVer
                node.annotation = self._replace_with_modelsemver(node.annotation)
                self.needs_modelsemver_import = True
                self.changes_made = True

        return node

    def _is_id_field(self, field_name: str) -> bool:
        """Check if field name indicates an ID field."""
        id_patterns = [
            "_id",
            "id_",
            "correlation_id",
            "event_id",
            "node_id",
            "user_id",
            "agent_id",
            "task_id",
            "request_id",
            "session_id",
            "hub_id",
            "collection_id",
            "ruleset_id",
            "policy_id",
            "pattern_id",
            "thread_id",
            "system_id",
            "input_id",
            "requester_id",
            "replacement_node_id",
            "envelope_id",
            "source_node_id",
            "vulnerability_id",
            "api_client_id",
        ]
        return any(pattern in field_name.lower() for pattern in id_patterns)

    def _is_version_field(self, field_name: str) -> bool:
        """Check if field name indicates a version field."""
        return "version" in field_name.lower() and not field_name.startswith("_")

    def _has_string_type(self, annotation: ast.expr) -> bool:
        """Check if annotation is str or str | None."""
        # Handle simple "str"
        if isinstance(annotation, ast.Name) and annotation.id == "str":
            return True

        # Handle "str | None" or "Optional[str]"
        if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
            left_is_str = (
                isinstance(annotation.left, ast.Name) and annotation.left.id == "str"
            )
            right_is_str = (
                isinstance(annotation.right, ast.Name) and annotation.right.id == "str"
            )
            return left_is_str or right_is_str

        # Handle Optional[str]
        if isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name):
                if annotation.value.id == "Optional":
                    slice_val = annotation.slice
                    if isinstance(slice_val, ast.Name) and slice_val.id == "str":
                        return True

        return False

    def _replace_with_uuid(self, annotation: ast.expr) -> ast.expr:
        """Replace str with UUID in annotation."""
        # Handle "str"
        if isinstance(annotation, ast.Name) and annotation.id == "str":
            return ast.Name(id="UUID", ctx=ast.Load())

        # Handle "str | None"
        if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
            if isinstance(annotation.left, ast.Name) and annotation.left.id == "str":
                annotation.left = ast.Name(id="UUID", ctx=ast.Load())
            if isinstance(annotation.right, ast.Name) and annotation.right.id == "str":
                annotation.right = ast.Name(id="UUID", ctx=ast.Load())
            return annotation

        # Handle Optional[str]
        if isinstance(annotation, ast.Subscript):
            if (
                isinstance(annotation.value, ast.Name)
                and annotation.value.id == "Optional"
            ):
                if (
                    isinstance(annotation.slice, ast.Name)
                    and annotation.slice.id == "str"
                ):
                    annotation.slice = ast.Name(id="UUID", ctx=ast.Load())
            return annotation

        return annotation

    def _replace_with_modelsemver(self, annotation: ast.expr) -> ast.expr:
        """Replace str with ModelSemVer in annotation."""
        # Handle "str"
        if isinstance(annotation, ast.Name) and annotation.id == "str":
            return ast.Name(id="ModelSemVer", ctx=ast.Load())

        # Handle "str | None"
        if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
            if isinstance(annotation.left, ast.Name) and annotation.left.id == "str":
                annotation.left = ast.Name(id="ModelSemVer", ctx=ast.Load())
            if isinstance(annotation.right, ast.Name) and annotation.right.id == "str":
                annotation.right = ast.Name(id="ModelSemVer", ctx=ast.Load())
            return annotation

        # Handle Optional[str]
        if isinstance(annotation, ast.Subscript):
            if (
                isinstance(annotation.value, ast.Name)
                and annotation.value.id == "Optional"
            ):
                if (
                    isinstance(annotation.slice, ast.Name)
                    and annotation.slice.id == "str"
                ):
                    annotation.slice = ast.Name(id="ModelSemVer", ctx=ast.Load())
            return annotation

        return annotation


def add_missing_imports(source: str, needs_uuid: bool, needs_modelsemver: bool) -> str:
    """Add missing imports to the source code."""
    lines = source.split("\n")

    # Find where to insert imports (after docstring, before other imports or code)
    insert_index = 0
    in_docstring = False
    docstring_found = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Track docstrings
        if stripped.startswith(('"""', "'''")):
            if in_docstring:
                in_docstring = False
                docstring_found = True
                insert_index = i + 1
            else:
                in_docstring = True
        elif docstring_found and not in_docstring:
            # After docstring, find first import or code
            if stripped and not stripped.startswith("#"):
                insert_index = i
                break

    # Check if imports already exist
    has_uuid_import = "from uuid import UUID" in source or "import uuid" in source
    has_modelsemver_import = (
        "from omnibase_core.models.core.model_semver import ModelSemVer" in source
    )

    # Add imports
    imports_to_add = []
    if needs_uuid and not has_uuid_import:
        imports_to_add.append("from uuid import UUID")
    if needs_modelsemver and not has_modelsemver_import:
        imports_to_add.append(
            "from omnibase_core.models.core.model_semver import ModelSemVer"
        )

    if imports_to_add:
        # Insert imports at the appropriate location
        for import_line in reversed(imports_to_add):
            lines.insert(insert_index, import_line)
        # Add blank line after imports if not already there
        if insert_index + len(imports_to_add) < len(lines):
            if lines[insert_index + len(imports_to_add)].strip():
                lines.insert(insert_index + len(imports_to_add), "")

    return "\n".join(lines)


def fix_file(file_path: Path) -> bool:
    """Fix string ID/version violations in a single file."""
    try:
        source = file_path.read_text()
        tree = ast.parse(source)

        # Transform the AST
        rewriter = StringFieldRewriter()
        new_tree = rewriter.visit(tree)

        if not rewriter.changes_made:
            return False

        # Convert back to source code (Python 3.9+)
        new_source = ast.unparse(new_tree)

        # Add missing imports
        new_source = add_missing_imports(
            new_source, rewriter.needs_uuid_import, rewriter.needs_modelsemver_import
        )

        # Write back
        file_path.write_text(new_source)
        return True

    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False


def main():
    """Main entry point."""
    src_dir = Path("src/omnibase_core")

    print("🔍 Scanning for string ID/version violations...")

    violations_found = []
    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        if fix_file(py_file):
            violations_found.append(py_file)
            print(f"✅ Fixed: {py_file}")

    print("\n📊 Summary:")
    print(f"   Files fixed: {len(violations_found)}")
    print("\n✨ Done! Run 'pre-commit run --all-files' to verify.")


if __name__ == "__main__":
    main()
