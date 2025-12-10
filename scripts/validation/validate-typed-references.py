#!/usr/bin/env python3
"""
ONEX Typed References Anti-Pattern Detection.

Detects generic string references that should be typed entity references:
- `list[str]` fields with entity-like names (should be `list[UUID]`)
- Properties returning `list[str]` for entity collections
- String fields that should be UUID or typed ID references

"""

import argparse
import ast
import re
from pathlib import Path
from typing import NamedTuple


class TypedReferenceViolation(NamedTuple):
    """Typed reference violation details."""

    file_path: Path
    line_number: int
    field_name: str
    current_type: str
    violation_type: str
    suggested_fix: str
    context: str


class TypedReferenceValidator:
    """Validates proper usage of typed references in Pydantic models."""

    def __init__(self):
        # Patterns that suggest entity references (should be UUID-based)
        self.entity_reference_patterns = [
            r".*_id$",  # user_id, node_id
            r".*_ids$",  # user_ids, node_ids
            r".*_uuid$",  # user_uuid, node_uuid
            r".*_uuids$",  # user_uuids, node_uuids
            r".*_ref$",  # user_ref, node_ref
            r".*_refs$",  # user_refs, node_refs
            r".*_nodes$",  # related_nodes, child_nodes
            r".*_users$",  # related_users, admin_users
            r".*_entities$",  # related_entities
            r"^dependencies$",  # dependencies
            r"^dependents$",  # dependents
            r"^parents$",  # parents
            r"^children$",  # children
            r"^related_.*$",  # related_anything
        ]

        # Compiled regex patterns
        self.entity_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.entity_reference_patterns
        ]

        self.violations: list[TypedReferenceViolation] = []

    def is_entity_reference_name(self, field_name: str) -> bool:
        """Check if field name suggests it should be a typed entity reference."""
        return any(pattern.match(field_name) for pattern in self.entity_patterns)

    def validate_file(self, file_path: Path) -> None:
        """Validate typed references in a single file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))
            self._validate_ast(tree, file_path, content.splitlines())

        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"⚠️  Skipping {file_path}: {e}")

    def _validate_ast(self, tree: ast.AST, file_path: Path, lines: list[str]) -> None:
        """Validate AST for typed reference violations."""

        class TypedReferenceVisitor(ast.NodeVisitor):
            def __init__(self, validator: TypedReferenceValidator):
                self.validator = validator
                self.file_path = file_path
                self.lines = lines

            def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
                """Visit annotated assignments (field definitions)."""
                if isinstance(node.target, ast.Name):
                    field_name = node.target.id

                    if self.validator.is_entity_reference_name(field_name):
                        type_annotation = ast.unparse(node.annotation)

                        # Check for problematic patterns
                        if self._is_string_list(type_annotation):
                            violation_type = "list_str_should_be_typed"
                            if field_name.endswith(("_ids", "_uuids")):
                                suggested_fix = f"Change 'list[str]' to 'list[UUID]' for {field_name}"
                            else:
                                suggested_fix = f"Change 'list[str]' to 'list[UUID]' or create proper typed reference for {field_name}"

                            self.validator.violations.append(
                                TypedReferenceViolation(
                                    file_path=file_path,
                                    line_number=node.lineno,
                                    field_name=field_name,
                                    current_type=type_annotation,
                                    violation_type=violation_type,
                                    suggested_fix=suggested_fix,
                                    context="Field definition",
                                )
                            )

                        elif self._is_string_type(
                            type_annotation
                        ) and self._suggests_entity_id(field_name):
                            violation_type = "str_should_be_uuid"
                            suggested_fix = f"Change 'str' to 'UUID' for {field_name}"

                            self.validator.violations.append(
                                TypedReferenceViolation(
                                    file_path=file_path,
                                    line_number=node.lineno,
                                    field_name=field_name,
                                    current_type=type_annotation,
                                    violation_type=violation_type,
                                    suggested_fix=suggested_fix,
                                    context="Field definition",
                                )
                            )

                self.generic_visit(node)

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                """Visit function/property definitions."""
                # Check property methods that return entity references
                if self._is_property(node):
                    prop_name = node.name

                    if self.validator.is_entity_reference_name(prop_name):
                        # Check return annotation
                        if node.returns:
                            return_type = ast.unparse(node.returns)

                            if self._is_string_list(return_type):
                                violation_type = "property_returns_list_str"
                                suggested_fix = f"Change return type from 'list[str]' to 'list[UUID]' for property {prop_name}"

                                self.validator.violations.append(
                                    TypedReferenceViolation(
                                        file_path=file_path,
                                        line_number=node.lineno,
                                        field_name=prop_name,
                                        current_type=return_type,
                                        violation_type=violation_type,
                                        suggested_fix=suggested_fix,
                                        context="Property method",
                                    )
                                )

                            elif self._is_string_type(
                                return_type
                            ) and self._suggests_entity_id(prop_name):
                                violation_type = "property_returns_str"
                                suggested_fix = f"Change return type from 'str' to 'UUID' for property {prop_name}"

                                self.validator.violations.append(
                                    TypedReferenceViolation(
                                        file_path=file_path,
                                        line_number=node.lineno,
                                        field_name=prop_name,
                                        current_type=return_type,
                                        violation_type=violation_type,
                                        suggested_fix=suggested_fix,
                                        context="Property method",
                                    )
                                )

                self.generic_visit(node)

            def _is_property(self, node: ast.FunctionDef) -> bool:
                """Check if function is decorated with @property."""
                return any(
                    isinstance(decorator, ast.Name) and decorator.id == "property"
                    for decorator in node.decorator_list
                )

            def _is_string_list(self, type_annotation: str) -> bool:
                """Check if type annotation is list[str]."""
                return "list[str]" in type_annotation

            def _is_string_type(self, type_annotation: str) -> bool:
                """Check if type annotation is str or str | None."""
                return (
                    "str" in type_annotation
                    and "list" not in type_annotation
                    and "dict" not in type_annotation
                )

            def _suggests_entity_id(self, field_name: str) -> bool:
                """Check if field name strongly suggests it should be a UUID."""
                strong_id_patterns = [
                    r".*_id$",
                    r".*_uuid$",
                    r".*_ref$",
                ]
                return any(
                    re.match(pattern, field_name, re.IGNORECASE)
                    for pattern in strong_id_patterns
                )

        visitor = TypedReferenceVisitor(self)
        visitor.visit(tree)

    def validate_directory(self, directory: Path, recursive: bool = True) -> None:
        """Validate all Python files in directory."""
        pattern = "**/*.py" if recursive else "*.py"
        python_files = directory.glob(pattern)

        for file_path in python_files:
            if file_path.is_file() and not self._should_skip_file(file_path):
                self.validate_file(file_path)

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        skip_patterns = [
            "__pycache__",
            ".pyc",
            "test_",
            "_test.py",
            "migrations/",
            "venv/",
            ".venv/",
            "node_modules/",
        ]

        file_str = str(file_path)
        return any(pattern in file_str for pattern in skip_patterns)

    def print_report(self) -> bool:
        """Print validation report and return success status."""
        print("🔍 ONEX Typed References Anti-Pattern Validation Report")
        print("=" * 60)

        if not self.violations:
            print("✅ SUCCESS: No typed reference violations found")
            print("All entity references use proper typing")
            return True

        print(f"❌ FAILURE: {len(self.violations)} typed reference violations found")
        print()

        # Group violations by file
        violations_by_file = {}
        for violation in self.violations:
            if violation.file_path not in violations_by_file:
                violations_by_file[violation.file_path] = []
            violations_by_file[violation.file_path].append(violation)

        for file_path, file_violations in violations_by_file.items():
            print(f"📁 {file_path}")
            for violation in file_violations:
                print(
                    f"  🚨 Line {violation.line_number}: {violation.field_name} ({violation.context})"
                )
                print(f"     Current:   {violation.current_type}")
                print(f"     Violation: {violation.violation_type}")
                print(f"     💡 {violation.suggested_fix}")
                print()

        print("🔧 Quick Fix Examples:")
        print("  Before: related_nodes: list[str] = Field(default_factory=list)")
        print("  After:  related_nodes: list[UUID] = Field(default_factory=list)")
        print()
        print("  Before: user_id: str | None = Field(None)")
        print("  After:  user_id: UUID | None = Field(None)")
        print()
        print("  Before: def dependencies(self) -> list[str]:")
        print("  After:  def dependencies(self) -> list[UUID]:")

        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate proper typed references in ONEX models"
    )
    parser.add_argument("path", help="Path to Python file or directory to validate")
    parser.add_argument(
        "--max-violations",
        type=int,
        default=-1,
        help="Maximum allowed violations (default: unlimited)",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        default=True,
        help="Recursively scan directories (default: True)",
    )

    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"❌ Error: Path '{path}' does not exist")
        return 1

    validator = TypedReferenceValidator()

    if path.is_file():
        validator.validate_file(path)
    else:
        validator.validate_directory(path, args.recursive)

    success = validator.print_report()

    # Check max violations limit
    if args.max_violations >= 0 and len(validator.violations) > args.max_violations:
        print(
            f"\n❌ VIOLATION LIMIT EXCEEDED: {len(validator.violations)} > {args.max_violations}"
        )
        return 1

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
