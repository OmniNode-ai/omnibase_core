#!/usr/bin/env python3
"""
Comprehensive audit of models, enums, and protocols in omnibase_core.
Excludes archived directories.
"""

import ast
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


class CodeAuditor:
    def __init__(self, root_path: str = "src/omnibase_core"):
        self.root = Path(root_path)
        self.enums = []
        self.models = []
        self.protocols_used = set()
        self.enum_values_map = defaultdict(list)

    def should_skip(self, path: Path) -> bool:
        """Check if path should be skipped."""
        parts = path.parts
        return 'archive' in parts or 'archived' in parts

    def extract_enum_info(self, file_path: Path):
        """Extract enum class information from a file."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's an Enum class
                    is_enum = False
                    base_types = []
                    for base in node.bases:
                        base_name = None
                        if isinstance(base, ast.Name):
                            base_name = base.id
                            base_types.append(base_name)
                        elif isinstance(base, ast.Attribute):
                            base_name = base.attr
                            base_types.append(base_name)

                        if base_name and "Enum" in base_name:
                            is_enum = True

                    if is_enum:
                        values = []
                        for item in node.body:
                            if isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, ast.Name) and target.id.isupper():
                                        if isinstance(item.value, ast.Constant):
                                            values.append(f"{target.id}={item.value.value}")
                                        elif isinstance(item.value, ast.Attribute):
                                            values.append(f"{target.id}=<ref>")

                        enum_info = {
                            'file': str(file_path),
                            'class': node.name,
                            'base_types': base_types,
                            'values': values,
                            'value_count': len(values)
                        }
                        self.enums.append(enum_info)

                        # Track value patterns for duplicate detection
                        for val in values:
                            if '=' in val:
                                value_part = val.split('=')[1]
                                self.enum_values_map[value_part].append((node.name, str(file_path)))

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

    def extract_model_info(self, file_path: Path):
        """Extract Pydantic model information from a file."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            tree = ast.parse(content)

            # Check for omnibase_spi imports
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and 'omnibase_spi' in node.module:
                        for alias in node.names:
                            self.protocols_used.add(f"{node.module}.{alias.name}")

            # Find model classes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a BaseModel class
                    is_model = False
                    base_types = []
                    protocols = []

                    for base in node.bases:
                        base_name = None
                        if isinstance(base, ast.Name):
                            base_name = base.id
                            base_types.append(base_name)
                        elif isinstance(base, ast.Attribute):
                            base_name = f"{base.value.id if isinstance(base.value, ast.Name) else '?'}.{base.attr}"
                            base_types.append(base_name)

                        if base_name and ("BaseModel" in base_name or "Protocol" in base_name):
                            is_model = True
                        if base_name and "Protocol" in base_name:
                            protocols.append(base_name)

                    if is_model or node.name.startswith("Model"):
                        fields = []
                        field_types = {}

                        for item in node.body:
                            if isinstance(item, ast.AnnAssign):
                                if isinstance(item.target, ast.Name):
                                    field_name = item.target.id
                                    field_type = self.get_type_string(item.annotation)
                                    fields.append(field_name)
                                    field_types[field_name] = field_type

                        model_info = {
                            'file': str(file_path),
                            'class': node.name,
                            'base_types': base_types,
                            'protocols': protocols,
                            'fields': fields,
                            'field_types': field_types,
                            'field_count': len(fields)
                        }
                        self.models.append(model_info)

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

    def get_type_string(self, node) -> str:
        """Convert AST annotation to string."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Subscript):
            base = self.get_type_string(node.value)
            arg = self.get_type_string(node.slice)
            return f"{base}[{arg}]"
        elif isinstance(node, ast.Tuple):
            elts = [self.get_type_string(e) for e in node.elts]
            return f"({', '.join(elts)})"
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            left = self.get_type_string(node.left)
            right = self.get_type_string(node.right)
            return f"{left} | {right}"
        elif isinstance(node, ast.Attribute):
            return f"{node.value.id if isinstance(node.value, ast.Name) else '?'}.{node.attr}"
        else:
            return "Any"

    def scan_directory(self, directory: Path, file_pattern: str, processor):
        """Scan directory for files matching pattern."""
        for file_path in directory.rglob(file_pattern):
            if not self.should_skip(file_path):
                processor(file_path)

    def analyze(self):
        """Run the full analysis."""
        print("Scanning enums...")
        enum_dir = self.root / "enums"
        if enum_dir.exists():
            self.scan_directory(enum_dir, "*.py", self.extract_enum_info)

        print("Scanning models...")
        model_dir = self.root / "models"
        if model_dir.exists():
            self.scan_directory(model_dir, "*.py", self.extract_model_info)

        print("\nAnalysis complete!")
        print(f"Found {len(self.enums)} enums")
        print(f"Found {len(self.models)} models")
        print(f"Found {len(self.protocols_used)} protocol imports")

    def find_duplicates(self):
        """Find duplicate and similar enums/models."""
        duplicates = {
            'enum_duplicates': [],
            'model_duplicates': [],
            'similar_names': []
        }

        # Check for enum value overlap
        for value, occurrences in self.enum_values_map.items():
            if len(occurrences) > 3 and '<ref>' not in value:  # More than 3 enums share this value
                duplicates['enum_duplicates'].append({
                    'value': value,
                    'enums': [e[0] for e in occurrences],
                    'count': len(occurrences)
                })

        # Check for similar model names
        model_names = [m['class'] for m in self.models]
        for i, name1 in enumerate(model_names):
            for name2 in model_names[i+1:]:
                # Simple similarity: check if one contains the other (ignoring case)
                if name1.lower() in name2.lower() or name2.lower() in name1.lower():
                    if name1 != name2:
                        duplicates['similar_names'].append((name1, name2))

        return duplicates

    def find_fields_needing_enums(self):
        """Find model fields that use basic types but should use enums."""
        candidates = []

        basic_types = ['str', 'int', 'bool']
        status_keywords = ['status', 'state', 'type', 'category', 'level', 'mode', 'kind']

        for model in self.models:
            for field_name, field_type in model['field_types'].items():
                # Check if field type is basic and name suggests it should be an enum
                is_basic = any(bt in field_type for bt in basic_types)
                has_keyword = any(kw in field_name.lower() for kw in status_keywords)

                if is_basic and has_keyword:
                    candidates.append({
                        'model': model['class'],
                        'file': model['file'],
                        'field': field_name,
                        'current_type': field_type
                    })

        return candidates

    def generate_report(self) -> dict:
        """Generate comprehensive report."""
        duplicates = self.find_duplicates()
        enum_candidates = self.find_fields_needing_enums()

        # Group enums by name patterns
        status_enums = [e for e in self.enums if 'status' in e['class'].lower()]
        type_enums = [e for e in self.enums if 'type' in e['class'].lower()]
        complexity_enums = [e for e in self.enums if 'complexity' in e['class'].lower()]

        report = {
            'summary': {
                'total_enums': len(self.enums),
                'total_models': len(self.models),
                'total_protocols': len(self.protocols_used),
                'status_enums': len(status_enums),
                'type_enums': len(type_enums),
                'complexity_enums': len(complexity_enums)
            },
            'enums': self.enums,
            'models': self.models,
            'protocols_used': sorted(list(self.protocols_used)),
            'duplicates': duplicates,
            'enum_candidates': enum_candidates
        }

        return report


if __name__ == "__main__":
    auditor = CodeAuditor()
    auditor.analyze()

    report = auditor.generate_report()

    # Save full report to JSON
    with open('/root/repo/audit_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    print("\n" + "="*80)
    print("AUDIT SUMMARY")
    print("="*80)
    print(f"Total Enums: {report['summary']['total_enums']}")
    print(f"Total Models: {report['summary']['total_models']}")
    print(f"Total Protocol Imports: {report['summary']['total_protocols']}")
    print(f"\nStatus Enums: {report['summary']['status_enums']}")
    print(f"Type Enums: {report['summary']['type_enums']}")
    print(f"Complexity Enums: {report['summary']['complexity_enums']}")

    print(f"\n\nDuplicate/Similar Items:")
    print(f"  Enum value overlaps: {len(report['duplicates']['enum_duplicates'])}")
    print(f"  Similar model names: {len(report['duplicates']['similar_names'])}")

    print(f"\n\nFields Potentially Needing Enums: {len(report['enum_candidates'])}")

    if report['enum_candidates']:
        print("\nTop 10 examples:")
        for candidate in report['enum_candidates'][:10]:
            print(f"  {candidate['model']}.{candidate['field']} ({candidate['current_type']})")

    print(f"\n\nFull report saved to: /root/repo/audit_report.json")
