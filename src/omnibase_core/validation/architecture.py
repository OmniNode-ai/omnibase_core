from __future__ import annotations

"""
ONEX ModelArchitecture validation tools.

This module provides validation functions for ONEX architectural principles:
- One model per file validation
- Naming pattern validation
- Structure validation
"""

import argparse
import ast
import sys
from pathlib import Path

from omnibase_core.models.common.model_validation_metadata import (
    ModelValidationMetadata,
)

from .validation_utils import ModelValidationResult


class ModelCounter(ast.NodeVisitor):
    """Count models, enums, and protocols in a Python file."""

    def __init__(self) -> None:
        self.models: list[str] = []
        self.enums: list[str] = []
        self.protocols: list[str] = []
        self.type_aliases: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions and categorize them."""
        class_name = node.name

        # Check base classes to determine type
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_name = base.id
                if base_name == "BaseModel":
                    self.models.append(class_name)
                    break
                if base_name == "Enum":
                    self.enums.append(class_name)
                    break
                if base_name == "Protocol":
                    self.protocols.append(class_name)
                    break
            elif isinstance(base, ast.Attribute):
                # Handle pydantic.BaseModel or typing.Protocol
                if (
                    isinstance(base.value, ast.Name)
                    and base.value.id == "pydantic"
                    and base.attr == "BaseModel"
                ):
                    self.models.append(class_name)
                    break

        # Check for model naming patterns
        if class_name.startswith("Model") and class_name not in self.models:
            self.models.append(class_name)
        elif class_name.startswith("Enum") and class_name not in self.enums:
            self.enums.append(class_name)

        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Visit type alias assignments."""
        if isinstance(node.target, ast.Name):
            # Check for TypeAlias pattern
            if (
                isinstance(node.annotation, ast.Name)
                and node.annotation.id == "TypeAlias"
            ):
                self.type_aliases.append(node.target.id)
        self.generic_visit(node)


def validate_one_model_per_file(file_path: Path) -> list[str]:
    """Validate a single Python file for one-model-per-file compliance."""
    errors = []

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)
        counter = ModelCounter()
        counter.visit(tree)

        # Check for multiple models
        if len(counter.models) > 1:
            errors.append(
                f"❌ {len(counter.models)} models in one file: {', '.join(counter.models)}"
            )

        # Check for multiple enums
        if len(counter.enums) > 1:
            errors.append(
                f"❌ {len(counter.enums)} enums in one file: {', '.join(counter.enums)}"
            )

        # Check for multiple protocols
        if len(counter.protocols) > 1:
            errors.append(
                f"❌ {len(counter.protocols)} protocols in one file: {', '.join(counter.protocols)}"
            )

        # Check for mixed types (models + enums + protocols)
        type_categories = []
        if counter.models:
            type_categories.append("models")
        if counter.enums:
            type_categories.append("enums")
        if counter.protocols:
            type_categories.append("protocols")

        if len(type_categories) > 1:
            errors.append(f"❌ Mixed types in one file: {', '.join(type_categories)}")

        # Special allowance for TypedDict + Model combinations (common pattern)
        if "TypedDict" in content and len(counter.models) == 1:
            # This is acceptable - TypedDict often accompanies a model
            pass

    except SyntaxError as e:
        errors.append(f"❌ Syntax error: {e}")
    except Exception as e:
        errors.append(f"❌ Parse error: {e}")

    return errors


def validate_architecture_directory(
    directory: Path, max_violations: int = 0
) -> ModelValidationResult[None]:
    """Validate ONEX architecture for a directory."""
    python_files = []

    for file_path in directory.rglob("*.py"):
        # Skip excluded directories and files
        if any(
            part in str(file_path)
            for part in [
                "__pycache__",
                ".git",
                "archived",
                "tests/fixtures",
                "__init__.py",  # Skip __init__.py files
            ]
        ):
            continue

        python_files.append(file_path)

    total_violations = 0
    files_with_violations = []
    all_errors = []

    for file_path in python_files:
        errors = validate_one_model_per_file(file_path)

        if errors:
            total_violations += len(errors)
            files_with_violations.append(str(file_path))
            all_errors.extend([f"{file_path}: {error}" for error in errors])

    is_valid = total_violations <= max_violations

    return ModelValidationResult(
        is_valid=is_valid,
        errors=all_errors,
        metadata=ModelValidationMetadata(
            validation_type="architecture",
            files_processed=len(python_files),
            max_violations=max_violations,
            violations_found=total_violations,
            files_with_violations_count=len(files_with_violations),
            files_with_violations=files_with_violations,
        ),
    )


def validate_architecture_cli() -> int:
    """CLI interface for architecture validation."""
    parser = argparse.ArgumentParser(
        description="Validate ONEX one-model-per-file architecture"
    )
    parser.add_argument(
        "directories", nargs="*", default=["src/"], help="Directories to validate"
    )
    parser.add_argument(
        "--max-violations",
        type=int,
        default=0,
        help="Maximum allowed violations (default: 0)",
    )

    args = parser.parse_args()

    print("🔍 ONEX One-Model-Per-File Validation")
    print("=" * 50)
    print("📋 Enforcing architectural separation of concerns")

    overall_result: ModelValidationResult[None] = ModelValidationResult(
        is_valid=True,
        errors=[],
        metadata=ModelValidationMetadata(files_processed=0),
    )

    for directory in args.directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"❌ Directory not found: {directory}")
            continue

        print(f"📁 Scanning {directory}...")
        result = validate_architecture_directory(dir_path, args.max_violations)

        # Merge results
        overall_result.is_valid = overall_result.is_valid and result.is_valid
        overall_result.errors.extend(result.errors)
        if overall_result.metadata and result.metadata:
            overall_result.metadata.files_processed = (
                overall_result.metadata.files_processed or 0
            ) + (result.metadata.files_processed or 0)

        if result.errors:
            print(f"\n❌ {directory}:")
            for error in result.errors:
                print(f"   {error}")

    print("\n📊 One-Model-Per-File Validation Summary:")
    files_processed = (
        overall_result.metadata.files_processed if overall_result.metadata else 0
    )
    print(f"   • Files checked: {files_processed}")
    print(f"   • Total violations: {len(overall_result.errors)}")
    print(f"   • Max allowed: {args.max_violations}")

    if overall_result.is_valid:
        print("✅ One-model-per-file validation PASSED")
        return 0
    print("\n🚨 ARCHITECTURAL VIOLATIONS DETECTED!")
    print("=" * 50)
    print("The ONEX one-model-per-file principle ensures:")
    print("• Clean separation of concerns")
    print("• Easy navigation and discovery")
    print("• Reduced merge conflicts")
    print("• Better code organization")
    print("\n💡 How to fix:")
    print("• Split files with multiple models into separate files")
    print("• Follow pattern: model_user_auth.py → ModelUserAuth")
    print("• Use __init__.py for convenient imports")
    print("• Keep related TypedDict with their model")

    print(
        f"\n❌ FAILURE: {len(overall_result.errors)} violations exceed limit of {args.max_violations}"
    )
    return 1


if __name__ == "__main__":
    sys.exit(validate_architecture_cli())
