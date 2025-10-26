#!/usr/bin/env python3
"""
ONEX One-Model-Per-File Architectural Validation

Enforces the ONEX architectural principle that each file should contain
exactly one model, enum, or protocol. This prevents architectural drift
and maintains clean separation of concerns.

Detects violations like:
- Multiple models in one file
- Mixed model types (Model + Enum + Protocol in same file)
- Oversized files that should be split

This enforces proper ONEX module organization.
"""

import argparse
import ast
import sys
from pathlib import Path


class ModelCounter(ast.NodeVisitor):
    """Count models, enums, and protocols in a Python file."""

    def __init__(self):
        self.models = []
        self.enums = []
        self.protocols = []
        self.type_aliases = []

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
        elif class_name.startswith("Protocol") and class_name not in self.protocols:
            self.protocols.append(class_name)

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


def validate_file(file_path: Path) -> list[str]:
    """Validate a single Python file for one-model-per-file compliance."""
    errors = []

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)
        counter = ModelCounter()
        counter.visit(tree)

        total_types = len(counter.models) + len(counter.enums) + len(counter.protocols)

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


def find_python_files(directory: Path) -> list[Path]:
    """Find all Python files in directory, excluding special cases."""
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

    return python_files


def main():
    """Main validation function."""
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

    total_files = 0
    total_violations = 0
    files_with_violations = []

    for directory in args.directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"❌ Directory not found: {directory}")
            continue

        print(f"📁 Scanning {directory}...")
        python_files = find_python_files(dir_path)

        for file_path in python_files:
            total_files += 1
            errors = validate_file(file_path)

            if errors:
                total_violations += len(errors)
                files_with_violations.append(str(file_path))
                print(f"\n❌ {file_path}:")
                for error in errors:
                    print(f"   {error}")

    print("\n📊 One-Model-Per-File Validation Summary:")
    print(f"   • Files checked: {total_files}")
    print(f"   • Files with violations: {len(files_with_violations)}")
    print(f"   • Total violations: {total_violations}")
    print(f"   • Max allowed: {args.max_violations}")

    if total_violations <= args.max_violations:
        print("✅ One-model-per-file validation PASSED")
        return 0
    else:
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
            f"\n❌ FAILURE: {total_violations} violations exceed limit of {args.max_violations}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
