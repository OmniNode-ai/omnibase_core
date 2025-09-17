#!/usr/bin/env python3
"""
Analyze custom to_dict() methods in the codebase and categorize them for cleanup.

This script identifies which custom to_dict() methods are:
1. Simple redundant wrappers around model_dump()
2. Complex methods with custom logic
3. Semi-redundant methods that could be simplified
"""

import ast
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


class ToDigtMethodAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze to_dict() method implementations."""

    def __init__(self):
        self.methods: List[Dict[str, Any]] = []
        self.current_class = None

    def visit_ClassDef(self, node):
        """Track current class for context."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node):
        """Analyze to_dict() method definitions."""
        if node.name == "to_dict":
            method_info = self._analyze_to_dict_method(node)
            if method_info:
                self.methods.append(method_info)

    def _analyze_to_dict_method(self, node) -> Dict[str, Any]:
        """Analyze a to_dict() method and categorize it."""
        # Get method source lines
        lines = []
        for stmt in node.body:
            if isinstance(stmt, ast.Return):
                lines.extend(self._get_return_analysis(stmt))
            elif isinstance(stmt, ast.Assign):
                lines.extend(self._get_assignment_analysis(stmt))

        # Categorize based on content
        category = self._categorize_method(lines, node)

        return {
            "class_name": self.current_class,
            "line_number": node.lineno,
            "category": category,
            "lines": lines,
            "complexity_score": len(node.body),
            "docstring": ast.get_docstring(node),
        }

    def _get_return_analysis(self, stmt) -> List[str]:
        """Analyze return statement."""
        if isinstance(stmt.value, ast.Call):
            if (
                isinstance(stmt.value.func, ast.Attribute)
                and stmt.value.func.attr == "model_dump"
            ):
                return ["model_dump_call"]
            elif (
                isinstance(stmt.value.func, ast.Attribute)
                and stmt.value.func.attr == "dict"
            ):
                return ["dict_call"]
        elif isinstance(stmt.value, ast.Dict):
            return ["literal_dict"]
        return ["other_return"]

    def _get_assignment_analysis(self, stmt) -> List[str]:
        """Analyze assignment statements."""
        if (
            isinstance(stmt.value, ast.Call)
            and isinstance(stmt.value.func, ast.Attribute)
            and stmt.value.func.attr == "model_dump"
        ):
            return ["model_dump_assignment"]
        elif isinstance(stmt.value, ast.Dict):
            return ["dict_construction"]
        return ["other_assignment"]

    def _categorize_method(self, lines: List[str], node) -> str:
        """Categorize the method based on its implementation."""
        # Simple wrapper - just returns model_dump()
        if len(node.body) == 1 and len(lines) == 1 and lines[0] == "model_dump_call":
            return "simple_wrapper"

        # Semi-redundant - model_dump() with minor modifications
        if "model_dump_call" in lines or "model_dump_assignment" in lines:
            if len(node.body) <= 3:
                return "semi_redundant"
            else:
                return "complex_with_model_dump"

        # Complex custom logic
        if (
            "dict_construction" in lines
            or "literal_dict" in lines
            or len(node.body) > 3
        ):
            return "complex_custom"

        return "unknown"


def analyze_file(file_path: Path) -> List[Dict[str, Any]]:
    """Analyze a single Python file for to_dict() methods."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)
        analyzer = ToDigtMethodAnalyzer()
        analyzer.visit(tree)

        # Add file context to each method
        for method in analyzer.methods:
            method["file_path"] = str(file_path)

        return analyzer.methods

    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return []


def find_to_dict_files() -> List[Path]:
    """Find all Python files containing to_dict() methods."""
    files = []
    for root, dirs, filenames in os.walk("src"):
        for filename in filenames:
            if filename.endswith(".py"):
                file_path = Path(root) / filename
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if "def to_dict(" in content:
                            files.append(file_path)
                except Exception:
                    pass
    return files


def main():
    """Main analysis function."""
    print("🔍 Analyzing custom to_dict() methods...")

    # Find all files with to_dict() methods
    files = find_to_dict_files()
    print(f"Found {len(files)} files with to_dict() methods")

    # Analyze each file
    all_methods = []
    for file_path in files:
        methods = analyze_file(file_path)
        all_methods.extend(methods)

    # Categorize results
    categories = {}
    for method in all_methods:
        category = method["category"]
        if category not in categories:
            categories[category] = []
        categories[category].append(method)

    # Print summary
    print(f"\n📊 Analysis Results ({len(all_methods)} methods):")
    print("=" * 50)

    for category, methods in categories.items():
        print(f"\n{category.upper().replace('_', ' ')} ({len(methods)} methods):")
        for method in methods:
            file_rel = method["file_path"].replace("src/omnibase_core/", "")
            print(f"  - {file_rel}:{method['line_number']} ({method['class_name']})")

    # Generate cleanup recommendations
    print(f"\n🛠️  Cleanup Recommendations:")
    print("=" * 50)

    simple_wrappers = categories.get("simple_wrapper", [])
    if simple_wrappers:
        print(f"\n✅ REMOVE ({len(simple_wrappers)} methods) - Simple wrappers:")
        for method in simple_wrappers:
            print(f"  - {method['file_path']}:{method['line_number']}")

    semi_redundant = categories.get("semi_redundant", [])
    if semi_redundant:
        print(f"\n⚠️  REVIEW ({len(semi_redundant)} methods) - Semi-redundant:")
        for method in semi_redundant:
            print(f"  - {method['file_path']}:{method['line_number']}")

    complex_methods = categories.get("complex_custom", []) + categories.get(
        "complex_with_model_dump", []
    )
    if complex_methods:
        print(f"\n🔧 KEEP ({len(complex_methods)} methods) - Complex logic needed:")
        for method in complex_methods:
            print(f"  - {method['file_path']}:{method['line_number']}")


if __name__ == "__main__":
    main()
