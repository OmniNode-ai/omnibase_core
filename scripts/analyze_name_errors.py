#!/usr/bin/env python3
"""
Analyze MyPy name-defined and attr-defined errors to categorize and prioritize fixes.
"""
import re
from collections import defaultdict
from pathlib import Path


def parse_error_file(filepath: str) -> list[dict]:
    """Parse the MyPy error file and extract structured error information."""
    errors = []

    with open(filepath, 'r') as f:
        for line in f:
            # Parse: file.py:line: error: Message  [error-type]
            match = re.match(
                r'^(.*?):(\d+): error: (.*?)\s+\[([\w-]+)\]$',
                line.strip()
            )
            if match:
                filepath, lineno, message, error_type = match.groups()
                errors.append({
                    'file': filepath,
                    'line': int(lineno),
                    'message': message,
                    'type': error_type,
                    'raw': line.strip()
                })

    return errors


def categorize_errors(errors: list[dict]) -> dict:
    """Categorize errors by type and pattern."""
    categories = {
        'missing_stdlib_imports': [],
        'missing_internal_imports': [],
        'wrong_attr_names': [],
        'already_defined': [],
        'undefined_variables': [],
        'other': []
    }

    stdlib_modules = {
        'hashlib', 're', 'uuid', 'datetime', 'pathlib', 'typing',
        'json', 'os', 'sys', 'functools', 'collections', 'itertools'
    }

    for error in errors:
        msg = error['message']

        # Already defined errors
        if 'already defined' in msg.lower():
            categories['already_defined'].append(error)

        # Module attribute errors
        elif 'Module' in msg and 'has no attribute' in msg:
            categories['wrong_attr_names'].append(error)

        # Name not defined errors
        elif 'Name' in msg and 'is not defined' in msg:
            # Extract the undefined name
            match = re.search(r'Name "(\w+)" is not defined', msg)
            if match:
                name = match.group(1)
                # Check if it's a stdlib module
                if name.lower() in stdlib_modules or name in ['UUID', 'Path', 'cast', 'Any']:
                    categories['missing_stdlib_imports'].append(error)
                # Check if it's likely a variable scope issue
                elif name[0].islower() and '_' in name:
                    categories['undefined_variables'].append(error)
                else:
                    categories['missing_internal_imports'].append(error)
            else:
                categories['other'].append(error)

        else:
            categories['other'].append(error)

    return categories


def analyze_by_file(errors: list[dict]) -> dict:
    """Group errors by file and count them."""
    by_file = defaultdict(list)

    for error in errors:
        by_file[error['file']].append(error)

    # Sort by error count
    return dict(sorted(by_file.items(), key=lambda x: len(x[1]), reverse=True))


def print_report(errors: list[dict], categories: dict, by_file: dict):
    """Print a comprehensive analysis report."""
    print("=" * 80)
    print("MyPy Name-Defined Error Analysis Report")
    print("=" * 80)
    print()

    print(f"Total Errors: {len(errors)}")
    print()

    print("Error Distribution by Category:")
    print("-" * 80)
    for category, error_list in categories.items():
        if error_list:
            print(f"  {category:30s}: {len(error_list):4d} errors")
    print()

    print("Top 20 Files with Most Errors:")
    print("-" * 80)
    for i, (filepath, file_errors) in enumerate(list(by_file.items())[:20], 1):
        filename = Path(filepath).name
        print(f"  {i:2d}. {filename:50s}: {len(file_errors):3d} errors")
    print()

    # Detailed breakdown
    print("\n" + "=" * 80)
    print("Detailed Category Breakdowns")
    print("=" * 80)

    # Missing stdlib imports
    if categories['missing_stdlib_imports']:
        print("\n1. Missing Standard Library Imports:")
        print("-" * 80)
        stdlib_names = defaultdict(list)
        for error in categories['missing_stdlib_imports']:
            match = re.search(r'Name "(\w+)" is not defined', error['message'])
            if match:
                name = match.group(1)
                stdlib_names[name].append(error['file'])

        for name, files in sorted(stdlib_names.items()):
            unique_files = list(set(files))
            print(f"  {name:20s}: {len(files):3d} occurrences in {len(unique_files):2d} files")
            if len(unique_files) <= 5:
                for f in unique_files[:5]:
                    print(f"    - {Path(f).name}")

    # Wrong attribute names
    if categories['wrong_attr_names']:
        print("\n2. Wrong Attribute Names:")
        print("-" * 80)
        attr_errors = defaultdict(list)
        for error in categories['wrong_attr_names']:
            # Extract module and attribute
            match = re.search(r'Module "([^"]+)" has no attribute "([^"]+)"', error['message'])
            if match:
                module, attr = match.groups()
                attr_errors[(module, attr)].append(error['file'])

        for (module, attr), files in sorted(attr_errors.items())[:15]:
            mod_name = Path(module).stem if '/' in module else module
            print(f"  {mod_name}.{attr}")
            print(f"    Files: {', '.join([Path(f).name for f in list(set(files))[:3]])}")

    # Missing internal imports
    if categories['missing_internal_imports']:
        print("\n3. Missing Internal Imports:")
        print("-" * 80)
        internal_names = defaultdict(list)
        for error in categories['missing_internal_imports']:
            match = re.search(r'Name "(\w+)" is not defined', error['message'])
            if match:
                name = match.group(1)
                internal_names[name].append(error['file'])

        for name, files in sorted(internal_names.items())[:20]:
            unique_files = list(set(files))
            print(f"  {name:40s}: {len(files):3d} occurrences in {len(unique_files):2d} files")

    # Variable scope issues
    if categories['undefined_variables']:
        print("\n4. Undefined Variables (likely scope issues):")
        print("-" * 80)
        for error in categories['undefined_variables'][:10]:
            print(f"  {Path(error['file']).name}:{error['line']}")
            print(f"    {error['message']}")


if __name__ == '__main__':
    error_file = '/tmp/name_errors_v2.txt'

    print("Parsing error file...")
    errors = parse_error_file(error_file)

    print(f"Found {len(errors)} errors")
    print("Categorizing...")

    categories = categorize_errors(errors)
    by_file = analyze_by_file(errors)

    print_report(errors, categories, by_file)
