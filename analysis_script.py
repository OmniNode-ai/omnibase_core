#!/usr/bin/env python3
"""
Analysis script to check for duplicate models/enums and type usage issues.
"""

import os
import re
import ast
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any


class ModelEnumAnalyzer:
    def __init__(self, src_dir: str = "src"):
        self.src_dir = src_dir
        self.model_files = []
        self.enum_files = []
        self.models = {}  # filename -> {class_name: class_info}
        self.enums = {}   # filename -> {enum_name: enum_info}
        self.duplicates = defaultdict(list)
        self.basic_type_usage = []
        self.protocol_usage = []

    def find_files(self):
        """Find all model and enum files in non-archived directories."""
        for root, dirs, files in os.walk(self.src_dir):
            # Skip archived directories
            dirs[:] = [d for d in dirs if 'archive' not in d.lower()]

            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    file_path = os.path.join(root, file)
                    if 'model' in file.lower():
                        self.model_files.append(file_path)
                    elif 'enum' in file.lower():
                        self.enum_files.append(file_path)

    def parse_python_file(self, file_path: str) -> Dict[str, Any]:
        """Parse a Python file and extract class definitions."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            classes = {}
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Extract base classes
                    bases = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            bases.append(base.id)
                        elif isinstance(base, ast.Attribute):
                            bases.append(ast.unparse(base))

                    # Extract field types from annotations
                    fields = {}
                    for item in node.body:
                        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                            field_name = item.target.id
                            field_type = ast.unparse(item.annotation) if item.annotation else 'Any'
                            fields[field_name] = field_type

                    classes[node.name] = {
                        'bases': bases,
                        'fields': fields,
                        'line': node.lineno
                    }

                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        for alias in node.names:
                            imports.append(f"{node.module}.{alias.name}")

            return {
                'classes': classes,
                'imports': imports,
                'content': content
            }
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return {'classes': {}, 'imports': [], 'content': ''}

    def analyze_duplicates(self):
        """Find duplicate class names across files."""
        all_classes = defaultdict(list)

        # Collect all class names from models
        for file_path in self.model_files:
            file_info = self.parse_python_file(file_path)
            self.models[file_path] = file_info

            for class_name in file_info['classes']:
                all_classes[class_name].append(file_path)

        # Collect all class names from enums
        for file_path in self.enum_files:
            file_info = self.parse_python_file(file_path)
            self.enums[file_path] = file_info

            for class_name in file_info['classes']:
                all_classes[class_name].append(file_path)

        # Find duplicates
        for class_name, file_paths in all_classes.items():
            if len(file_paths) > 1:
                self.duplicates[class_name] = file_paths

    def analyze_basic_type_usage(self):
        """Check for models using basic types that could use enums or other models."""
        basic_types = {'str', 'int', 'float', 'bool', 'Any', 'Optional[str]', 'Optional[int]', 'Optional[float]', 'Optional[bool]'}

        all_files = {**self.models, **self.enums}

        for file_path, file_info in all_files.items():
            for class_name, class_info in file_info['classes'].items():
                for field_name, field_type in class_info['fields'].items():
                    # Check if field uses basic type that might have enum alternatives
                    if any(basic in field_type for basic in basic_types):
                        if self._might_need_enum(field_name, field_type):
                            self.basic_type_usage.append({
                                'file': file_path,
                                'class': class_name,
                                'field': field_name,
                                'current_type': field_type,
                                'suggestion': self._suggest_alternative(field_name, field_type)
                            })

    def _might_need_enum(self, field_name: str, field_type: str) -> bool:
        """Determine if a field might benefit from using an enum."""
        enum_indicators = [
            'status', 'state', 'type', 'category', 'mode', 'level', 'format',
            'kind', 'phase', 'action', 'method', 'strategy', 'policy'
        ]

        return any(indicator in field_name.lower() for indicator in enum_indicators)

    def _suggest_alternative(self, field_name: str, field_type: str) -> str:
        """Suggest an alternative enum or model type."""
        # Check if there's an existing enum that matches
        enum_pattern = f"enum_{field_name.lower()}"
        for file_path in self.enum_files:
            if enum_pattern in file_path.lower():
                basename = os.path.basename(file_path).replace('.py', '')
                class_name = ''.join(word.capitalize() for word in basename.split('_'))
                return f"Consider using {class_name}"

        return f"Consider creating Enum{field_name.capitalize()}"

    def analyze_protocol_usage(self):
        """Check if models are properly using protocols from omnibase_spi."""
        for file_path, file_info in self.models.items():
            has_spi_import = any('omnibase_spi' in imp for imp in file_info['imports'])

            for class_name, class_info in file_info['classes'].items():
                # Check if class should implement protocols based on naming
                protocol_suggestions = []

                if 'node' in class_name.lower():
                    if not any('ProtocolNode' in base for base in class_info['bases']):
                        protocol_suggestions.append('ProtocolNodeLike')

                if 'metadata' in class_name.lower():
                    if not any('ProtocolMetadata' in base for base in class_info['bases']):
                        protocol_suggestions.append('ProtocolMetadataProvider')

                if 'config' in class_name.lower():
                    if not any('ProtocolConfig' in base for base in class_info['bases']):
                        protocol_suggestions.append('ProtocolConfigurable')

                if protocol_suggestions:
                    self.protocol_usage.append({
                        'file': file_path,
                        'class': class_name,
                        'has_spi_import': has_spi_import,
                        'suggested_protocols': protocol_suggestions
                    })

    def generate_report(self):
        """Generate a comprehensive analysis report."""
        report = []
        report.append("="*80)
        report.append("MODEL AND ENUM ANALYSIS REPORT")
        report.append("="*80)
        report.append(f"Analysis Date: {os.popen('date').read().strip()}")
        report.append(f"Source Directory: {self.src_dir}")
        report.append(f"Model files found: {len(self.model_files)}")
        report.append(f"Enum files found: {len(self.enum_files)}")
        report.append("")

        # Duplicates section
        report.append("DUPLICATE CLASSES FOUND:")
        report.append("-" * 40)
        if self.duplicates:
            for class_name, file_paths in self.duplicates.items():
                report.append(f"\n🔴 DUPLICATE: {class_name}")
                for i, file_path in enumerate(file_paths, 1):
                    report.append(f"  {i}. {file_path}")
        else:
            report.append("✅ No duplicate classes found!")
        report.append("")

        # Basic type usage section
        report.append("BASIC TYPE USAGE ANALYSIS:")
        report.append("-" * 40)
        if self.basic_type_usage:
            for issue in self.basic_type_usage:
                report.append(f"\n🟡 SUGGESTION: {issue['file']}")
                report.append(f"  Class: {issue['class']}")
                report.append(f"  Field: {issue['field']} ({issue['current_type']})")
                report.append(f"  Suggestion: {issue['suggestion']}")
        else:
            report.append("✅ No obvious basic type issues found!")
        report.append("")

        # Protocol usage section
        report.append("PROTOCOL USAGE ANALYSIS:")
        report.append("-" * 40)
        if self.protocol_usage:
            for issue in self.protocol_usage:
                report.append(f"\n🔵 PROTOCOL SUGGESTION: {issue['file']}")
                report.append(f"  Class: {issue['class']}")
                report.append(f"  Has SPI import: {issue['has_spi_import']}")
                report.append(f"  Suggested protocols: {', '.join(issue['suggested_protocols'])}")
        else:
            report.append("✅ No obvious protocol issues found!")
        report.append("")

        # Summary section
        report.append("SUMMARY:")
        report.append("-" * 20)
        report.append(f"Duplicate classes: {len(self.duplicates)}")
        report.append(f"Basic type suggestions: {len(self.basic_type_usage)}")
        report.append(f"Protocol suggestions: {len(self.protocol_usage)}")

        return "\n".join(report)

    def run_analysis(self):
        """Run the complete analysis."""
        print("🔍 Finding files...")
        self.find_files()

        print("🔍 Analyzing duplicates...")
        self.analyze_duplicates()

        print("🔍 Analyzing basic type usage...")
        self.analyze_basic_type_usage()

        print("🔍 Analyzing protocol usage...")
        self.analyze_protocol_usage()

        print("📊 Generating report...")
        return self.generate_report()


if __name__ == "__main__":
    analyzer = ModelEnumAnalyzer()
    report = analyzer.run_analysis()
    print(report)

    # Save report to file
    with open("model_enum_analysis_report.txt", "w") as f:
        f.write(report)
    print("\n📄 Report saved to: model_enum_analysis_report.txt")