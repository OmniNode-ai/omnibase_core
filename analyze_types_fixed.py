#!/usr/bin/env python3
"""
Script to analyze type usage patterns in omnibase_core models
"""
import os
import re
import ast
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

class TypeAnalyzer:
    def __init__(self):
        self.basic_types = {
            'str', 'int', 'float', 'bool', 'dict', 'list', 'Dict', 'List',
            'Optional', 'Union', 'Any', 'None', 'tuple', 'Tuple', 'set', 'Set'
        }
        self.issues = []

    def find_files_by_type(self, base_dirs, exclude_patterns=None):
        """Find all Python files categorized by type"""
        if exclude_patterns is None:
            exclude_patterns = ['archive', '__pycache__', 'tests']

        model_files = []
        enum_files = []

        for base_dir in base_dirs:
            if not os.path.exists(base_dir):
                print(f"Directory does not exist: {base_dir}")
                continue

            for root, dirs, filenames in os.walk(base_dir):
                # Skip excluded directories
                dirs[:] = [d for d in dirs if not any(pattern in d for pattern in exclude_patterns)]

                # Skip if current directory matches exclude patterns
                if any(pattern in root for pattern in exclude_patterns):
                    continue

                for filename in filenames:
                    if filename.endswith('.py') and filename != '__init__.py':
                        file_path = os.path.join(root, filename)

                        # Categorize files
                        if '/models/' in root or 'server/models' in root:
                            model_files.append(file_path)
                        elif '/enums/' in root:
                            enum_files.append(file_path)

        return sorted(model_files), sorted(enum_files)

    def extract_class_and_field_types(self, file_path):
        """Extract class definitions and field types from a Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            classes = []

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = {
                        'name': node.name,
                        'fields': [],
                        'base_classes': [self.extract_type_annotation(base) for base in node.bases],
                        'line': node.lineno
                    }

                    # Look for field annotations
                    for item in node.body:
                        if isinstance(item, ast.AnnAssign) and item.target:
                            if hasattr(item.target, 'id'):
                                field_name = item.target.id
                                field_type = self.extract_type_annotation(item.annotation)
                                class_info['fields'].append({
                                    'name': field_name,
                                    'type': field_type,
                                    'line': item.lineno
                                })

                    classes.append(class_info)

            return classes
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return []

    def extract_type_annotation(self, annotation):
        """Extract type annotation as string"""
        try:
            if hasattr(annotation, 'id'):
                return annotation.id
            elif hasattr(annotation, 'attr'):
                # Handle module.Class type references
                if hasattr(annotation, 'value') and hasattr(annotation.value, 'id'):
                    return f"{annotation.value.id}.{annotation.attr}"
                return annotation.attr
            elif isinstance(annotation, ast.Subscript):
                # Handle generic types like List[str], Dict[str, int]
                base = self.extract_type_annotation(annotation.value)
                if hasattr(annotation, 'slice'):
                    slice_val = annotation.slice
                    if hasattr(slice_val, 'elts'):
                        # Multiple type args
                        args = [self.extract_type_annotation(arg) for arg in slice_val.elts]
                        return f"{base}[{', '.join(args)}]"
                    else:
                        # Single type arg
                        arg = self.extract_type_annotation(slice_val)
                        return f"{base}[{arg}]"
                return base
            elif isinstance(annotation, ast.Constant):
                return str(annotation.value)
            elif isinstance(annotation, ast.Name):
                return annotation.id
            else:
                return str(type(annotation).__name__)
        except:
            return "unknown"

    def analyze_field_types(self, classes, file_path):
        """Analyze field types for issues"""
        issues = []

        for class_info in classes:
            for field in class_info['fields']:
                field_type = field['type']

                # Check for basic types that could be enums
                if self.should_use_enum(field, field_type):
                    issues.append({
                        'type': 'basic_type_should_be_enum',
                        'file': file_path,
                        'class': class_info['name'],
                        'field': field['name'],
                        'current_type': field_type,
                        'line': field['line'],
                        'suggestion': self.suggest_enum_replacement(field['name'], field_type)
                    })

                # Check for basic types that could be models
                if self.should_use_model(field, field_type):
                    issues.append({
                        'type': 'basic_type_should_be_model',
                        'file': file_path,
                        'class': class_info['name'],
                        'field': field['name'],
                        'current_type': field_type,
                        'line': field['line'],
                        'suggestion': self.suggest_model_replacement(field['name'], field_type)
                    })

        return issues

    def should_use_enum(self, field, field_type):
        """Check if a field should use an enum instead of basic type"""
        field_name = field['name'].lower()

        # String fields that sound like they should be enums
        if field_type == 'str':
            enum_indicators = [
                'status', 'state', 'type', 'kind', 'mode', 'level', 'category',
                'priority', 'severity', 'format', 'method', 'strategy', 'policy',
                'role', 'phase', 'stage', 'action', 'operation', 'command'
            ]
            return any(indicator in field_name for indicator in enum_indicators)

        return False

    def should_use_model(self, field, field_type):
        """Check if a field should use a model instead of basic type"""
        field_name = field['name'].lower()

        # Dict fields that might be complex objects
        if 'dict' in field_type.lower() or 'Dict' in field_type:
            model_indicators = [
                'config', 'settings', 'metadata', 'properties', 'parameters',
                'data', 'info', 'details', 'specs', 'options', 'context'
            ]
            return any(indicator in field_name for indicator in model_indicators)

        return False

    def suggest_enum_replacement(self, field_name, current_type):
        """Suggest an enum replacement for a field"""
        # Convert field name to enum name format
        words = re.findall(r'[A-Z][a-z]*|[a-z]+', field_name)
        enum_name = 'Enum' + ''.join(word.capitalize() for word in words)
        return enum_name

    def suggest_model_replacement(self, field_name, current_type):
        """Suggest a model replacement for a field"""
        # Convert field name to model name format
        words = re.findall(r'[A-Z][a-z]*|[a-z]+', field_name)
        model_name = 'Model' + ''.join(word.capitalize() for word in words)
        return model_name

    def analyze_enum_values(self, enum_files):
        """Analyze enum values for overlaps"""
        enum_values = defaultdict(list)  # value -> [(enum_name, file_path)]

        for file_path in enum_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract enum class name
                class_match = re.search(r'class\s+(\w+)\(.*Enum\)', content)
                if not class_match:
                    continue

                enum_name = class_match.group(1)

                # Extract enum values
                value_pattern = r'^\s*(\w+)\s*=\s*["\']([^"\']+)["\']'
                matches = re.findall(value_pattern, content, re.MULTILINE)

                for member_name, value in matches:
                    enum_values[value].append((enum_name, file_path, member_name))

            except Exception as e:
                print(f"Error analyzing enum {file_path}: {e}")

        # Find overlapping values
        overlaps = {value: enums for value, enums in enum_values.items() if len(enums) > 1}
        return overlaps

    def check_omnibase_spi_usage(self, files):
        """Check for proper omnibase_spi protocol usage"""
        issues = []

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check if file imports omnibase_spi
                has_spi_import = 'omnibase_spi' in content

                # Look for class definitions that might need protocol implementation
                classes = self.extract_class_and_field_types(file_path)

                for class_info in classes:
                    # Check if class should implement protocols but doesn't import them
                    if self.should_implement_protocols(class_info) and not has_spi_import:
                        issues.append({
                            'type': 'missing_spi_protocol',
                            'file': file_path,
                            'class': class_info['name'],
                            'line': class_info['line'],
                            'suggestion': 'Consider implementing omnibase_spi protocols'
                        })

            except Exception as e:
                print(f"Error checking SPI usage in {file_path}: {e}")

        return issues

    def should_implement_protocols(self, class_info):
        """Check if a class should implement SPI protocols"""
        class_name = class_info['name'].lower()

        # Classes that typically should implement protocols
        protocol_indicators = [
            'node', 'function', 'workflow', 'contract', 'execution',
            'metadata', 'configuration', 'validation'
        ]

        return any(indicator in class_name for indicator in protocol_indicators)

def main():
    """Main analysis function"""
    analyzer = TypeAnalyzer()

    # Define target directories
    target_dirs = [
        '/root/repo/src/omnibase_core/models',
        '/root/repo/src/omnibase_core/enums',
        '/root/repo/python/src/server/models'
    ]

    # Find and categorize files
    model_files, enum_files = analyzer.find_files_by_type(target_dirs)

    print(f"Found files:")
    print(f"  Model files: {len(model_files)}")
    print(f"  Enum files: {len(enum_files)}")

    # Analyze type usage in models
    all_issues = []

    print(f"\nAnalyzing model field types...")
    for i, file_path in enumerate(model_files):
        if i % 50 == 0:
            print(f"  Processed {i}/{len(model_files)} model files...")
        classes = analyzer.extract_class_and_field_types(file_path)
        issues = analyzer.analyze_field_types(classes, file_path)
        all_issues.extend(issues)

    # Analyze enum value overlaps
    print(f"\nAnalyzing enum value overlaps...")
    enum_overlaps = analyzer.analyze_enum_values(enum_files)

    # Check omnibase_spi usage
    print(f"\nChecking omnibase_spi protocol usage...")
    spi_issues = analyzer.check_omnibase_spi_usage(model_files[:50])  # Sample first 50 files
    all_issues.extend(spi_issues)

    # Print results
    print(f"\n=== TYPE USAGE ANALYSIS RESULTS ===")

    # Group issues by type
    issues_by_type = defaultdict(list)
    for issue in all_issues:
        issues_by_type[issue['type']].append(issue)

    for issue_type, issues in issues_by_type.items():
        print(f"\n{issue_type.replace('_', ' ').title()}: {len(issues)} issues")

        # Show some examples
        for i, issue in enumerate(issues[:5]):  # Show first 5 of each type
            relative_path = issue['file'].replace('/root/repo/', '')
            print(f"  {relative_path}:{issue['line']}")
            print(f"    Class: {issue['class']}")
            if 'field' in issue:
                print(f"    Field: {issue['field']} ({issue.get('current_type', '')})")
            if 'suggestion' in issue:
                print(f"    Suggestion: {issue['suggestion']}")
            print()

        if len(issues) > 5:
            print(f"    ... and {len(issues) - 5} more similar issues\n")

    # Print enum overlaps
    print(f"=== ENUM VALUE OVERLAPS ===")
    if enum_overlaps:
        print(f"Found {len(enum_overlaps)} overlapping enum values:")

        for value, enums in list(enum_overlaps.items())[:10]:  # Show first 10
            print(f"\nValue '{value}' appears in:")
            for enum_name, file_path, member_name in enums:
                relative_path = file_path.replace('/root/repo/', '')
                print(f"  {enum_name}.{member_name} ({relative_path})")

        if len(enum_overlaps) > 10:
            print(f"\n... and {len(enum_overlaps) - 10} more overlapping values")
    else:
        print("No enum value overlaps found.")

    print(f"\n=== ANALYSIS SUMMARY ===")
    print(f"Files analyzed:")
    print(f"  Model files: {len(model_files)}")
    print(f"  Enum files: {len(enum_files)}")
    print(f"Issues found:")
    print(f"  Type usage issues: {len(all_issues)}")
    print(f"  Enum value overlaps: {len(enum_overlaps)}")

    for issue_type, issues in issues_by_type.items():
        print(f"  {issue_type.replace('_', ' ').title()}: {len(issues)}")

if __name__ == "__main__":
    main()