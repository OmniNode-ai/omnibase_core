#!/usr/bin/env python3
"""
Protocol Syntax Validation Script

Validates that protocol implementations are syntactically correct and properly structured
without requiring omnibase_spi installation.
"""

import ast
import re
from pathlib import Path
from typing import Any


class ProtocolSyntaxValidator:
    """Validates protocol implementation syntax across model files."""

    EXPECTED_PROTOCOLS = {
        "Configurable",
        "Executable",
        "Identifiable",
        "MetadataProvider",
        "Nameable",
        "Serializable",
        "Validatable",
    }

    PROTOCOL_METHODS = {
        "Configurable": {"configure"},
        "Executable": {"execute"},
        "Identifiable": {"get_id"},
        "MetadataProvider": {"get_metadata", "set_metadata"},
        "Nameable": {"get_name", "set_name"},
        "Serializable": {"serialize"},
        "Validatable": {"validate"},
    }

    def __init__(self, models_dir: str):
        self.models_dir = Path(models_dir)
        self.validation_results: list[dict[str, Any]] = []
        self.errors: list[str] = []

    def find_model_files(self) -> list[Path]:
        """Find all actual model files (not re-export files)."""
        all_files = list(self.models_dir.rglob("model_*.py"))
        model_files = []

        for file_path in all_files:
            # Read file to check if it contains actual model classes
            try:
                with open(file_path) as f:
                    content = f.read()

                # Skip re-export files
                if (
                    "from ." in content
                    and "__all__ = [" in content
                    and "class " not in content
                ):
                    continue

                # Check if it has actual model classes
                if re.search(r"class\s+Model\w+\s*\([^)]*BaseModel", content):
                    model_files.append(file_path)

            except Exception as e:
                self.errors.append(f"Error reading {file_path}: {e}")

        return model_files

    def parse_file_ast(self, file_path: Path) -> tuple[ast.Module, str]:
        """Parse file into AST and return content."""
        with open(file_path) as f:
            content = f.read()

        try:
            tree = ast.parse(content)
            return tree, content
        except SyntaxError as e:
            raise SyntaxError(f"Syntax error in {file_path}: {e}")

    def find_protocol_imports(self, tree: ast.Module) -> set[str]:
        """Find protocol imports in the AST."""
        protocols = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == "omnibase_core.core.type_constraints":
                    for alias in node.names:
                        if alias.name in self.EXPECTED_PROTOCOLS:
                            protocols.add(alias.name)

        return protocols

    def find_model_classes(self, tree: ast.Module) -> list[tuple[str, ast.ClassDef]]:
        """Find model classes that inherit from BaseModel."""
        model_classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name.startswith("Model"):
                    # Check if it inherits from BaseModel and protocols
                    has_basemodel = False
                    protocols = set()

                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            if base.id == "BaseModel":
                                has_basemodel = True
                            elif base.id in self.EXPECTED_PROTOCOLS:
                                protocols.add(base.id)

                    if has_basemodel:
                        model_classes.append((node.name, node))

        return model_classes

    def find_class_methods(self, class_node: ast.ClassDef) -> set[str]:
        """Find method names in a class."""
        methods = set()

        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                methods.add(node.name)

        return methods

    def get_class_protocols(self, class_node: ast.ClassDef) -> set[str]:
        """Get protocols implemented by a class."""
        protocols = set()

        for base in class_node.bases:
            if isinstance(base, ast.Name) and base.id in self.EXPECTED_PROTOCOLS:
                protocols.add(base.id)

        return protocols

    def validate_protocol_methods(
        self, class_name: str, class_protocols: set[str], class_methods: set[str]
    ) -> dict[str, bool]:
        """Validate that required protocol methods are implemented."""
        results = {}

        for protocol in class_protocols:
            if protocol in self.PROTOCOL_METHODS:
                required_methods = self.PROTOCOL_METHODS[protocol]
                for method in required_methods:
                    method_key = f"{protocol}.{method}"
                    results[method_key] = method in class_methods

        return results

    def validate_docstring_protocols(
        self, content: str, class_protocols: set[str]
    ) -> bool:
        """Check if docstring documents implemented protocols."""
        return "Implements omnibase_spi protocols:" in content

    def validate_file(self, file_path: Path) -> dict[str, Any]:
        """Validate protocol implementations in a single file."""
        try:
            tree, content = self.parse_file_ast(file_path)

            # Find imports
            imported_protocols = self.find_protocol_imports(tree)

            # Find model classes
            model_classes = self.find_model_classes(tree)

            if not model_classes:
                return {
                    "file": str(file_path.relative_to(self.models_dir)),
                    "status": "no_models",
                    "imported_protocols": list(imported_protocols),
                    "classes": [],
                }

            # Validate each class
            class_results = []
            for class_name, class_node in model_classes:
                class_protocols = self.get_class_protocols(class_node)
                class_methods = self.find_class_methods(class_node)

                # Validate protocol methods
                method_validation = self.validate_protocol_methods(
                    class_name, class_protocols, class_methods
                )

                # Check docstring
                has_protocol_docs = self.validate_docstring_protocols(
                    content, class_protocols
                )

                class_results.append(
                    {
                        "class_name": class_name,
                        "protocols": list(class_protocols),
                        "methods": list(class_methods),
                        "method_validation": method_validation,
                        "has_protocol_docs": has_protocol_docs,
                        "protocol_comment": "# Protocol method implementations"
                        in content,
                    }
                )

            return {
                "file": str(file_path.relative_to(self.models_dir)),
                "status": "success",
                "imported_protocols": list(imported_protocols),
                "classes": class_results,
            }

        except Exception as e:
            return {
                "file": str(file_path.relative_to(self.models_dir)),
                "status": "error",
                "error": str(e),
                "imported_protocols": [],
                "classes": [],
            }

    def validate_all_files(self) -> dict[str, Any]:
        """Validate all model files."""
        model_files = self.find_model_files()
        print(f"🔍 Found {len(model_files)} actual model files to validate")

        for file_path in model_files:
            result = self.validate_file(file_path)
            self.validation_results.append(result)

        return self.generate_summary()

    def generate_summary(self) -> dict[str, Any]:
        """Generate validation summary."""
        total_files = len(self.validation_results)
        successful_files = len(
            [r for r in self.validation_results if r["status"] == "success"]
        )

        # Count classes and protocol implementations
        total_classes = 0
        classes_with_protocols = 0
        protocol_counts = {}
        method_validation_stats = {}

        for result in self.validation_results:
            if result["status"] == "success":
                for class_data in result["classes"]:
                    total_classes += 1

                    if class_data["protocols"]:
                        classes_with_protocols += 1

                    # Count protocol implementations
                    for protocol in class_data["protocols"]:
                        protocol_counts[protocol] = protocol_counts.get(protocol, 0) + 1

                    # Count method validation results
                    for method, is_valid in class_data["method_validation"].items():
                        if method not in method_validation_stats:
                            method_validation_stats[method] = {"passed": 0, "failed": 0}

                        if is_valid:
                            method_validation_stats[method]["passed"] += 1
                        else:
                            method_validation_stats[method]["failed"] += 1

        return {
            "summary": {
                "total_files": total_files,
                "successful_files": successful_files,
                "success_rate": (
                    (successful_files / total_files * 100) if total_files > 0 else 0
                ),
                "total_classes": total_classes,
                "classes_with_protocols": classes_with_protocols,
                "protocol_adoption_rate": (
                    (classes_with_protocols / total_classes * 100)
                    if total_classes > 0
                    else 0
                ),
            },
            "protocol_implementations": protocol_counts,
            "method_validation": method_validation_stats,
            "detailed_results": self.validation_results,
            "errors": self.errors,
        }


def main():
    """Main validation execution."""
    print("🚀 Protocol Syntax Validation")
    print("=" * 50)

    # Determine models directory
    script_dir = Path(__file__).parent
    models_dir = script_dir.parent / "src" / "omnibase_core" / "models"

    if not models_dir.exists():
        print(f"❌ Models directory not found: {models_dir}")
        return 1

    # Run validation
    validator = ProtocolSyntaxValidator(str(models_dir))
    results = validator.validate_all_files()

    # Print summary
    summary = results["summary"]
    print("\n📊 Validation Results:")
    print(f"   Files Validated: {summary['total_files']}")
    print(f"   Successful Files: {summary['successful_files']}")
    print(f"   File Success Rate: {summary['success_rate']:.1f}%")
    print(f"   Total Classes: {summary['total_classes']}")
    print(f"   Classes with Protocols: {summary['classes_with_protocols']}")
    print(f"   Protocol Adoption Rate: {summary['protocol_adoption_rate']:.1f}%")

    # Print protocol implementations
    print("\n🔧 Protocol Implementations:")
    for protocol, count in results["protocol_implementations"].items():
        print(f"   {protocol}: {count} classes")

    # Print method validation results
    print("\n✅ Method Validation Results:")
    for method, stats in results["method_validation"].items():
        total = stats["passed"] + stats["failed"]
        success_rate = (stats["passed"] / total * 100) if total > 0 else 0
        print(f"   {method}: {stats['passed']}/{total} passed ({success_rate:.1f}%)")

    # Print any errors
    if results["errors"]:
        print("\n⚠️  Validation Errors:")
        for error in results["errors"][:5]:  # Show first 5 errors
            print(f"   - {error}")

    # Overall assessment
    overall_success = (
        summary["success_rate"] >= 95 and summary["protocol_adoption_rate"] >= 90
    )
    status = (
        "✅ EXCELLENT"
        if overall_success
        else "⚠️  GOOD"
        if summary["success_rate"] >= 80
        else "❌ NEEDS WORK"
    )
    print(f"\n🎯 Protocol Implementation Quality: {status}")

    return 0 if overall_success else 1


if __name__ == "__main__":
    exit(main())
