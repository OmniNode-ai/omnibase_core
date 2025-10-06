#!/usr/bin/env python3
"""
AST-based String Version Fixer for ONEX Compliance

Fixes remaining string version violations by:
1. Converting ID fields from str to UUID
2. Converting version fields from str to ModelSemVer
3. Adding necessary imports
"""

import ast
import sys
from pathlib import Path
from typing import Set


class ImportTracker:
    """Track what imports are needed based on replacements."""

    def __init__(self):
        self.needs_uuid = False
        self.needs_semver = False
        self.has_uuid_import = False
        self.has_semver_import = False

    def check_existing_imports(self, tree: ast.Module):
        """Check what imports already exist."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == "uuid" and any(
                    alias.name == "UUID" for alias in node.names
                ):
                    self.has_uuid_import = True
                elif node.module == "omnibase_core.models.core.model_semver" and any(
                    alias.name == "ModelSemVer" for alias in node.names
                ):
                    self.has_semver_import = True

    def mark_uuid_needed(self):
        """Mark that UUID import is needed."""
        self.needs_uuid = True

    def mark_semver_needed(self):
        """Mark that ModelSemVer import is needed."""
        self.needs_semver = True

    def get_missing_imports(self) -> list[ast.ImportFrom]:
        """Get list of missing import statements."""
        imports = []

        if self.needs_uuid and not self.has_uuid_import:
            imports.append(
                ast.ImportFrom(
                    module="uuid",
                    names=[ast.alias(name="UUID", asname=None)],
                    level=0,
                )
            )

        if self.needs_semver and not self.has_semver_import:
            imports.append(
                ast.ImportFrom(
                    module="omnibase_core.models.core.model_semver",
                    names=[ast.alias(name="ModelSemVer", asname=None)],
                    level=0,
                )
            )

        return imports


class StringVersionFixer(ast.NodeTransformer):
    """Transform AST to fix string version violations."""

    # Field names that should use UUID
    ID_FIELDS = {
        "run_id",
        "batch_id",
        "parent_id",
        "node_id",
        "service_id",
        "event_id",
        "pattern_id",
        "backend_id",
    }

    # Field names that should use ModelSemVer
    VERSION_FIELDS = {
        "contract_version",
        "protocol_version",
        "version",
    }

    def __init__(self, import_tracker: ImportTracker):
        self.import_tracker = import_tracker

    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.AnnAssign:
        """Fix annotated assignments (field declarations)."""
        if isinstance(node.target, ast.Name):
            field_name = node.target.id

            # Fix ID fields: field_name: str | None = ... → field_name: UUID | None = ...
            if field_name in self.ID_FIELDS:
                node.annotation = self._convert_str_to_uuid(node.annotation)
                self.import_tracker.mark_uuid_needed()

            # Fix version fields: version: str | None = ... → version: ModelSemVer | None = ...
            elif field_name in self.VERSION_FIELDS:
                node.annotation = self._convert_str_to_semver(node.annotation)
                self.import_tracker.mark_semver_needed()

        return node

    def visit_arg(self, node: ast.arg) -> ast.arg:
        """Fix function/method parameters."""
        if node.arg in self.ID_FIELDS:
            node.annotation = self._convert_str_to_uuid(node.annotation)
            self.import_tracker.mark_uuid_needed()
        elif node.arg in self.VERSION_FIELDS:
            node.annotation = self._convert_str_to_semver(node.annotation)
            self.import_tracker.mark_semver_needed()

        return node

    def _convert_str_to_uuid(self, annotation):
        """Convert str type annotation to UUID."""
        if annotation is None:
            return None

        # Handle: str → UUID
        if isinstance(annotation, ast.Name) and annotation.id == "str":
            return ast.Name(id="UUID", ctx=ast.Load())

        # Handle: str | None → UUID | None
        if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
            if isinstance(annotation.left, ast.Name) and annotation.left.id == "str":
                annotation.left = ast.Name(id="UUID", ctx=ast.Load())
            if isinstance(annotation.right, ast.Name) and annotation.right.id == "str":
                annotation.right = ast.Name(id="UUID", ctx=ast.Load())

        return annotation

    def _convert_str_to_semver(self, annotation):
        """Convert str type annotation to ModelSemVer."""
        if annotation is None:
            return None

        # Handle: str → ModelSemVer
        if isinstance(annotation, ast.Name) and annotation.id == "str":
            return ast.Name(id="ModelSemVer", ctx=ast.Load())

        # Handle: str | None → ModelSemVer | None
        if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
            if isinstance(annotation.left, ast.Name) and annotation.left.id == "str":
                annotation.left = ast.Name(id="ModelSemVer", ctx=ast.Load())
            if isinstance(annotation.right, ast.Name) and annotation.right.id == "str":
                annotation.right = ast.Name(id="ModelSemVer", ctx=ast.Load())

        return annotation


def add_imports_to_tree(tree: ast.Module, imports: list[ast.ImportFrom]) -> ast.Module:
    """Add missing imports to the AST tree."""
    if not imports:
        return tree

    # Find the position to insert imports (after __future__ imports if present)
    insert_pos = 0
    for i, node in enumerate(tree.body):
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            insert_pos = i + 1
        elif not isinstance(node, (ast.Import, ast.ImportFrom, ast.Expr)):
            # Stop at first non-import, non-docstring statement
            break

    # Insert imports
    for imp in reversed(imports):
        tree.body.insert(insert_pos, imp)

    return tree


def fix_file(filepath: Path, backup: bool = True) -> tuple[bool, str]:
    """
    Fix string version violations in a file.

    Returns:
        (success, message) tuple
    """
    try:
        # Read original content
        content = filepath.read_text()

        # Parse AST
        tree = ast.parse(content)

        # Track imports
        tracker = ImportTracker()
        tracker.check_existing_imports(tree)

        # Fix violations
        fixer = StringVersionFixer(tracker)
        new_tree = fixer.visit(tree)

        # Add missing imports
        missing_imports = tracker.get_missing_imports()
        if missing_imports:
            new_tree = add_imports_to_tree(new_tree, missing_imports)

        # Generate new code
        ast.fix_missing_locations(new_tree)
        new_content = ast.unparse(new_tree)

        # Only write if content changed
        if new_content != content:
            if backup:
                backup_path = filepath.with_suffix(filepath.suffix + ".bak")
                filepath.rename(backup_path)
                print(f"  📝 Backed up to: {backup_path}")

            filepath.write_text(new_content)
            return True, "Fixed"
        else:
            return False, "No changes needed"

    except Exception as e:
        return False, f"Error: {e}"


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python fix_string_versions_ast.py <file> [--backup]")
        print("\nOr: Get list from pre-commit output:")
        print(
            "  pre-commit run validate-string-versions --all-files 2>&1 | "
            "grep '📁' | awk '{print $2}' | while read f; do "
            'python scripts/fix_string_versions_ast.py "$f" --backup; done'
        )
        sys.exit(1)

    filepath = Path(sys.argv[1])
    backup = "--backup" in sys.argv

    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        sys.exit(1)

    print(f"🔧 Processing: {filepath}")
    success, message = fix_file(filepath, backup)

    if success:
        print(f"✅ {message}")
        sys.exit(0)
    else:
        print(f"⚠️  {message}")
        sys.exit(0 if message == "No changes needed" else 1)


if __name__ == "__main__":
    main()
