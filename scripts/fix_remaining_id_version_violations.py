#!/usr/bin/env python3
"""
Fix remaining string ID/version violations in function parameters.

This script handles violations that the field-based AST script missed:
- Function/method parameter annotations
- Factory method parameters that should be UUID/ModelSemVer
"""

import ast
from pathlib import Path
from typing import Set


class FunctionParamRewriter(ast.NodeTransformer):
    """AST transformer to fix function parameter string ID/version types."""

    # ID field patterns (same as before)
    ID_PATTERNS = {
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
        "target_node_id",
        "key_id",
    }

    def __init__(self):
        self.needs_uuid_import = False
        self.needs_modelsemver_import = False
        self.changes_made = False

    def _is_id_field(self, name: str) -> bool:
        """Check if field name matches ID patterns."""
        return any(pattern in name.lower() for pattern in self.ID_PATTERNS)

    def _is_version_field(self, name: str) -> bool:
        """Check if field name is a version field."""
        return "version" in name.lower() and not name.startswith("_")

    def _has_string_type(self, annotation: ast.expr) -> bool:
        """Check if annotation is str or str | None."""
        if isinstance(annotation, ast.Name) and annotation.id == "str":
            return True
        if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
            # Check str | None pattern
            if isinstance(annotation.left, ast.Name) and annotation.left.id == "str":
                return True
            if isinstance(annotation.right, ast.Name) and annotation.right.id == "str":
                return True
        return False

    def _replace_with_uuid(self, annotation: ast.expr) -> ast.expr:
        """Replace str annotation with UUID."""
        if isinstance(annotation, ast.Name) and annotation.id == "str":
            return ast.Name(id="UUID", ctx=ast.Load())
        if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
            # Handle str | None → UUID | None
            if isinstance(annotation.left, ast.Name) and annotation.left.id == "str":
                annotation.left = ast.Name(id="UUID", ctx=ast.Load())
            if isinstance(annotation.right, ast.Name) and annotation.right.id == "str":
                annotation.right = ast.Name(id="UUID", ctx=ast.Load())
        return annotation

    def _replace_with_modelsemver(self, annotation: ast.expr) -> ast.expr:
        """Replace str annotation with ModelSemVer | str for backward compat."""
        # For version parameters, allow both ModelSemVer and str for flexibility
        if isinstance(annotation, ast.Name) and annotation.id == "str":
            # str → ModelSemVer | str
            return ast.BinOp(
                left=ast.Name(id="ModelSemVer", ctx=ast.Load()),
                op=ast.BitOr(),
                right=ast.Name(id="str", ctx=ast.Load()),
            )
        if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
            # str | None → ModelSemVer | str | None
            if isinstance(annotation.left, ast.Name) and annotation.left.id == "str":
                # Create ModelSemVer | str | None
                return ast.BinOp(
                    left=ast.BinOp(
                        left=ast.Name(id="ModelSemVer", ctx=ast.Load()),
                        op=ast.BitOr(),
                        right=ast.Name(id="str", ctx=ast.Load()),
                    ),
                    op=ast.BitOr(),
                    right=annotation.right,  # Keep the None
                )
        return annotation

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Visit function definitions to update parameter annotations."""
        for arg in node.args.args:
            if arg.annotation is None:
                continue

            # Check if this is an ID parameter
            if self._is_id_field(arg.arg):
                if self._has_string_type(arg.annotation):
                    arg.annotation = self._replace_with_uuid(arg.annotation)
                    self.needs_uuid_import = True
                    self.changes_made = True
                    print(f"  ✓ Fixed ID parameter: {arg.arg}")

            # Check if this is a version parameter
            elif self._is_version_field(arg.arg):
                if self._has_string_type(arg.annotation):
                    arg.annotation = self._replace_with_modelsemver(arg.annotation)
                    self.needs_modelsemver_import = True
                    self.changes_made = True
                    print(f"  ✓ Fixed version parameter: {arg.arg}")

        # Also check keyword-only args
        for arg in node.args.kwonlyargs:
            if arg.annotation is None:
                continue

            if self._is_id_field(arg.arg):
                if self._has_string_type(arg.annotation):
                    arg.annotation = self._replace_with_uuid(arg.annotation)
                    self.needs_uuid_import = True
                    self.changes_made = True
                    print(f"  ✓ Fixed ID parameter: {arg.arg}")

            elif self._is_version_field(arg.arg):
                if self._has_string_type(arg.annotation):
                    arg.annotation = self._replace_with_modelsemver(arg.annotation)
                    self.needs_modelsemver_import = True
                    self.changes_made = True
                    print(f"  ✓ Fixed version parameter: {arg.arg}")

        # Continue traversing
        self.generic_visit(node)
        return node


def add_missing_imports(source: str, needs_uuid: bool, needs_modelsemver: bool) -> str:
    """Add missing imports to the source code."""
    lines = source.split("\n")
    imports_to_add: list[str] = []

    # Check if imports already exist
    has_uuid_import = any(
        "from uuid import UUID" in line or "import uuid" in line for line in lines
    )
    has_modelsemver_import = any(
        "ModelSemVer" in line and "import" in line for line in lines
    )

    if needs_uuid and not has_uuid_import:
        imports_to_add.append("from uuid import UUID")

    if needs_modelsemver and not has_modelsemver_import:
        imports_to_add.append(
            "from omnibase_core.models.core.model_semver import ModelSemVer"
        )

    if not imports_to_add:
        return source

    # Find where to insert imports (after existing imports)
    insert_index = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("from ") or line.strip().startswith("import "):
            insert_index = i + 1
        elif (
            line.strip()
            and not line.strip().startswith("#")
            and not line.strip().startswith('"""')
        ):
            break

    # Insert imports
    for imp in reversed(imports_to_add):
        lines.insert(insert_index, imp)

    return "\n".join(lines)


def fix_file(file_path: Path) -> bool:
    """Fix string ID/version violations in function parameters."""
    try:
        source = file_path.read_text()
        tree = ast.parse(source)

        # Transform the AST
        rewriter = FunctionParamRewriter()
        new_tree = rewriter.visit(tree)

        if not rewriter.changes_made:
            return False

        # Convert back to source code
        new_source = ast.unparse(new_tree)

        # Add missing imports
        new_source = add_missing_imports(
            new_source, rewriter.needs_uuid_import, rewriter.needs_modelsemver_import
        )

        # Write back
        file_path.write_text(new_source)
        return True

    except Exception as e:
        print(f"  ❌ Error processing {file_path}: {e}")
        return False


def main():
    """Fix remaining violations in specific files."""
    # Files with remaining violations
    files_to_fix = [
        "src/omnibase_core/models/discovery/model_introspection_response_event.py",
        "src/omnibase_core/models/discovery/model_tooldiscoveryresponse.py",
        "src/omnibase_core/models/events/model_event_envelope.py",
        "src/omnibase_core/models/discovery/model_tool_invocation_event.py",
        "src/omnibase_core/models/security/model_nodesignature.py",
        "src/omnibase_core/models/service/model_node_weights.py",
        "src/omnibase_core/models/configuration/model_rate_limit_policy.py",
        "src/omnibase_core/mixins/mixin_introspection.py",
        "src/omnibase_core/models/security/model_detection_ruleset.py",
        "src/omnibase_core/models/discovery/model_node_shutdown_event.py",
        "src/omnibase_core/models/service/model_event_bus_input_output_state.py",
        "src/omnibase_core/models/service/model_event_bus_output_state.py",
        "src/omnibase_core/models/core/model_cli_execution.py",
        "src/omnibase_core/models/security/model_signature_chain.py",
        "src/omnibase_core/models/core/model_node_capability.py",
        "src/omnibase_core/models/service/model_event_bus_input_state.py",
        "scripts/fix_string_id_violations.py",
    ]

    base_path = Path.cwd()
    fixed_count = 0

    print(
        "🔧 Fixing remaining string ID/version violations in function parameters...\n"
    )

    for file_rel in files_to_fix:
        file_path = base_path / file_rel
        if not file_path.exists():
            print(f"⚠️  Skipping {file_rel} (not found)")
            continue

        print(f"📝 Processing: {file_rel}")
        if fix_file(file_path):
            fixed_count += 1
            print(f"  ✅ Fixed!\n")
        else:
            print(f"  ℹ️  No changes needed\n")

    print(f"📊 Summary: {fixed_count} files fixed")


if __name__ == "__main__":
    main()
