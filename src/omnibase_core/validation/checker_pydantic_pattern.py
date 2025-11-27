"""
PydanticPatternChecker

Check for proper Pydantic patterns and anti-patterns.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""

import ast


class PydanticPatternChecker(ast.NodeVisitor):
    """Check for proper Pydantic patterns and anti-patterns."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.issues: list[str] = []
        self.classes_checked = 0

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions to check Pydantic patterns."""
        # Check if this is a Pydantic model
        is_pydantic = False
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "BaseModel":
                is_pydantic = True
                break
            if isinstance(base, ast.Attribute):
                if (
                    isinstance(base.value, ast.Name)
                    and base.value.id == "pydantic"
                    and base.attr == "BaseModel"
                ):
                    is_pydantic = True
                    break

        if is_pydantic:
            self.classes_checked += 1
            self._check_pydantic_class(node)

        self.generic_visit(node)

    def _check_pydantic_class(self, node: ast.ClassDef) -> None:
        """Check a Pydantic class for pattern violations."""
        class_name = node.name

        # Check naming convention
        if not class_name.startswith("Model"):
            self.issues.append(
                f"Line {node.lineno}: Pydantic model '{class_name}' should start with 'Model'",
            )

        # Check field patterns
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                field_name = item.target.id
                annotation = item.annotation

                # Check for string ID fields that should be UUID
                if field_name.endswith("_id") and self._is_str_annotation(annotation):
                    self.issues.append(
                        f"Line {item.lineno}: Field '{field_name}' should use UUID type instead of str",
                    )

                # Check for category/type/status fields that should be enums
                if field_name in [
                    "category",
                    "type",
                    "status",
                ] and self._is_str_annotation(annotation):
                    self.issues.append(
                        f"Line {item.lineno}: Field '{field_name}' should use Enum instead of str",
                    )

                # Check for name fields that reference entities
                if field_name.endswith("_name") and self._is_str_annotation(annotation):
                    self.issues.append(
                        f"Line {item.lineno}: Field '{field_name}' might reference an entity - consider using ID + display_name pattern",
                    )

    def _is_str_annotation(self, annotation: ast.AST) -> bool:
        """Check if annotation is str type."""
        if isinstance(annotation, ast.Name):
            return bool(annotation.id == "str")
        if isinstance(annotation, ast.Constant):
            return bool(annotation.value == "str")
        return False
