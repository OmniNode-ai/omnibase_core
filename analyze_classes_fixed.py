#!/usr/bin/env python3
"""
Script to analyze classes and enums in omnibase_core codebase
"""
import os
import re
from collections import defaultdict
from pathlib import Path

def extract_classes_from_file(file_path):
    """Extract class definitions from a Python file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find class definitions
        class_pattern = r'^class\s+(\w+)(?:\([^)]*\))?:'
        matches = re.findall(class_pattern, content, re.MULTILINE)
        return matches
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []

def find_files_in_directories(base_dirs, exclude_patterns=None):
    """Find all Python files in specified directories"""
    if exclude_patterns is None:
        exclude_patterns = ['archive', '__pycache__', 'tests']

    files = []
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
                    files.append(os.path.join(root, filename))

    return sorted(files)

def main():
    """Main analysis function"""
    # Define target directories
    target_dirs = [
        '/root/repo/src/omnibase_core/models',
        '/root/repo/src/omnibase_core/enums',
        '/root/repo/python/src/server/models'
    ]

    # Find all Python files
    all_files = []
    for base_dir in target_dirs:
        if os.path.exists(base_dir):
            files = find_files_in_directories([base_dir])
            all_files.extend(files)
            print(f"Found {len(files)} files in {base_dir}")

    print(f"\nTotal files to analyze: {len(all_files)}")

    # Extract classes from all files
    all_classes = {}  # file_path -> [class_names]
    class_to_files = defaultdict(list)

    for file_path in all_files:
        classes = extract_classes_from_file(file_path)
        all_classes[file_path] = classes

        for class_name in classes:
            class_to_files[class_name].append(file_path)

    # Find duplicates
    duplicates = {name: files for name, files in class_to_files.items() if len(files) > 1}

    print(f"\n=== DUPLICATE CLASS NAMES ===")
    print(f"Found {len(duplicates)} duplicate class names:")

    for class_name, files in duplicates.items():
        print(f"\nClass: {class_name}")
        for file_path in files:
            print(f"  - {file_path}")

    # Find classes with similar names (but different)
    print(f"\n=== POTENTIALLY SIMILAR CLASS NAMES ===")
    class_names = list(class_to_files.keys())
    similar_groups = defaultdict(list)

    # Group by base name (removing prefixes like "Model", "Enum")
    for name in class_names:
        base_name = name
        # Remove common prefixes
        for prefix in ['Model', 'Enum']:
            if base_name.startswith(prefix):
                base_name = base_name[len(prefix):]
                break

        if base_name:  # Only add if there's something left
            similar_groups[base_name.lower()].append(name)

    # Show groups with multiple items that are actually different classes
    similar_count = 0
    for base_name, names in similar_groups.items():
        if len(names) > 1:
            # Check if they're actually duplicates or just similar
            unique_names = set(names)
            if len(unique_names) > 1:
                print(f"\nBase name '{base_name}': {sorted(unique_names)}")
                similar_count += 1

    # Show summary statistics
    print(f"\n=== SUMMARY STATISTICS ===")
    print(f"Total files analyzed: {len(all_files)}")
    print(f"Total classes found: {len(class_to_files)}")
    print(f"Duplicate class names: {len(duplicates)}")
    print(f"Similar class name groups: {similar_count}")

    # Show distribution by directory
    dir_stats = defaultdict(int)
    for file_path, classes in all_classes.items():
        if '/models/' in file_path:
            dir_stats['omnibase_core/models'] += len(classes)
        elif '/enums/' in file_path:
            dir_stats['omnibase_core/enums'] += len(classes)
        elif 'server/models' in file_path:
            dir_stats['server/models'] += len(classes)

    print(f"\nClasses by directory:")
    for dir_name, count in dir_stats.items():
        print(f"  {dir_name}: {count}")

    return duplicates, similar_groups, class_to_files

if __name__ == "__main__":
    main()