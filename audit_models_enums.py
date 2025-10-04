#!/usr/bin/env python3
"""
Comprehensive audit script for models, enums, and protocols in omnibase_core.
"""
import ast
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
import json

# Base directory
BASE_DIR = Path("/root/repo/src/omnibase_core")

# Storage for findings
models_by_name = defaultdict(list)  # model_name -> [(file_path, class_def)]
enums_by_name = defaultdict(list)   # enum_name -> [(file_path, class_def)]
all_enums = {}  # file_path -> {enum_name: values}
all_models = {}  # file_path -> {model_name: {fields}}

class ModelEnumVisitor(ast.NodeVisitor):
    """Visit and extract model and enum definitions"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.models = {}
        self.enums = {}
        self.imports = []

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module = node.module or ""
        for alias in node.names:
            self.imports.append(f"{module}.{alias.name}")
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        # Check if it's a BaseModel subclass
        is_base_model = False
        is_enum = False

        for base in node.bases:
            base_name = self._get_name(base)
            if 'BaseModel' in base_name:
                is_base_model = True
            elif 'Enum' in base_name or base_name in ['IntEnum', 'StrEnum', 'Flag']:
                is_enum = True

        if is_base_model:
            fields = {}
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    field_name = item.target.id
                    field_type = self._get_annotation(item.annotation)
                    fields[field_name] = field_type
            self.models[node.name] = fields

        elif is_enum:
            enum_values = []
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            enum_values.append(target.id)
            self.enums[node.name] = enum_values

        self.generic_visit(node)

    def _get_name(self, node):
        """Extract name from AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            return self._get_name(node.value)
        return ""

    def _get_annotation(self, node):
        """Extract type annotation as string"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Subscript):
            value = self._get_name(node.value)
            if isinstance(node.slice, ast.Tuple):
                elts = [self._get_annotation(e) for e in node.slice.elts]
                return f"{value}[{', '.join(elts)}]"
            else:
                return f"{value}[{self._get_annotation(node.slice)}]"
        elif isinstance(node, ast.Attribute):
            return f"{self._get_annotation(node.value)}.{node.attr}"
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            left = self._get_annotation(node.left)
            right = self._get_annotation(node.right)
            return f"{left} | {right}"
        return str(type(node).__name__)


def analyze_files():
    """Analyze all Python files in omnibase_core"""
    for py_file in BASE_DIR.rglob("*.py"):
        # Skip archive directories
        if 'archive' in py_file.parts:
            continue

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)

            visitor = ModelEnumVisitor(str(py_file))
            visitor.visit(tree)

            # Store models
            for model_name, fields in visitor.models.items():
                models_by_name[model_name].append((str(py_file), fields))
                all_models[str(py_file)] = visitor.models

            # Store enums
            for enum_name, values in visitor.enums.items():
                enums_by_name[enum_name].append((str(py_file), values))
                all_enums[str(py_file)] = visitor.enums

        except Exception as e:
            print(f"Error processing {py_file}: {e}", file=sys.stderr)


def find_duplicates():
    """Find duplicate model and enum names"""
    duplicate_models = {name: files for name, files in models_by_name.items() if len(files) > 1}
    duplicate_enums = {name: files for name, files in enums_by_name.items() if len(files) > 1}

    return duplicate_models, duplicate_enums


def check_basic_types():
    """Check for models using basic types that should use enums/models"""
    findings = []

    # Get all available enum names
    available_enums = set(enums_by_name.keys())

    for file_path, models in all_models.items():
        for model_name, fields in models.items():
            for field_name, field_type in fields.items():
                # Check for basic str that might need enum
                if field_type == 'str':
                    # Common patterns that should be enums
                    if any(keyword in field_name.lower() for keyword in [
                        'type', 'status', 'category', 'mode', 'kind', 'level',
                        'format', 'action', 'state', 'phase', 'severity'
                    ]):
                        findings.append({
                            'file': file_path,
                            'model': model_name,
                            'field': field_name,
                            'current_type': field_type,
                            'issue': 'str field might need enum',
                            'suggestion': f'Consider creating/using enum for {field_name}'
                        })

                # Check for dict that might need model
                elif field_type == 'dict' or 'Dict' in field_type:
                    findings.append({
                        'file': file_path,
                        'model': model_name,
                        'field': field_name,
                        'current_type': field_type,
                        'issue': 'dict should use typed model',
                        'suggestion': 'Create a Pydantic model instead of dict'
                    })

                # Check for Any
                elif field_type == 'Any':
                    findings.append({
                        'file': file_path,
                        'model': model_name,
                        'field': field_name,
                        'current_type': field_type,
                        'issue': 'Any type is too permissive',
                        'suggestion': 'Use specific type or Union'
                    })

    return findings


def main():
    print("=== Starting Audit ===")
    print(f"Analyzing files in: {BASE_DIR}")

    # Analyze all files
    analyze_files()

    # Prepare results
    results = {
        'summary': {
            'total_models': sum(len(files) for files in models_by_name.values()),
            'unique_model_names': len(models_by_name),
            'total_enums': sum(len(files) for files in enums_by_name.values()),
            'unique_enum_names': len(enums_by_name),
        },
        'duplicate_models': {},
        'duplicate_enums': {},
        'basic_type_issues': [],
        'all_models': {},
        'all_enums': {}
    }

    # Find duplicates
    dup_models, dup_enums = find_duplicates()

    for name, files in dup_models.items():
        results['duplicate_models'][name] = [f for f, _ in files]

    for name, files in dup_enums.items():
        results['duplicate_enums'][name] = [f for f, _ in files]

    # Check basic types
    results['basic_type_issues'] = check_basic_types()

    # Store all models and enums for reference
    results['all_models'] = {name: [f for f, _ in files] for name, files in models_by_name.items()}
    results['all_enums'] = {name: [f for f, _ in files] for name, files in enums_by_name.items()}

    # Output results
    output_file = "/root/repo/audit_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n=== Audit Complete ===")
    print(f"Results saved to: {output_file}")
    print(f"\nSummary:")
    print(f"  Total models: {results['summary']['total_models']}")
    print(f"  Unique model names: {results['summary']['unique_model_names']}")
    print(f"  Total enums: {results['summary']['total_enums']}")
    print(f"  Unique enum names: {results['summary']['unique_enum_names']}")
    print(f"  Duplicate models: {len(results['duplicate_models'])}")
    print(f"  Duplicate enums: {len(results['duplicate_enums'])}")
    print(f"  Basic type issues: {len(results['basic_type_issues'])}")


if __name__ == "__main__":
    main()
