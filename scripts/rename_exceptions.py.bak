#!/usr/bin/env python3
"""
Script to rename exception classes per ONEX conventions.
Changes *Error suffix classes to Exception* prefix without Error suffix.
"""
import re
import subprocess
import tempfile
from pathlib import Path

# Mapping of old names to new names
RENAMES = {
    "ExceptionAuditError": "ExceptionAudit",
    "ExceptionConfigurationError": "ExceptionConfiguration",
    "ExceptionFileProcessingError": "ExceptionFileProcessing",
    "ExceptionInputValidationError": "ExceptionInputValidation",
    "ExceptionMigrationError": "ExceptionMigration",
    "ExceptionPathTraversalError": "ExceptionPathTraversal",
    "ExceptionProtocolParsingError": "ExceptionProtocolParsing",
    "ExceptionValidationFrameworkError": "ExceptionValidationFramework",
    "FailFastError": "ExceptionFailFast",
    "ContractViolationError": "ExceptionContractViolation",
    "DependencyFailedError": "ExceptionDependencyFailed",
}


def find_python_files():
    """Find all Python files in src/ and tests/."""
    src_path = Path("src")
    tests_path = Path("tests")

    files = []
    if src_path.exists():
        files.extend(src_path.rglob("*.py"))
    if tests_path.exists():
        files.extend(tests_path.rglob("*.py"))

    return files


def rename_in_file(file_path: Path) -> int:
    """Rename exception classes in a single file. Returns number of changes."""
    try:
        content = file_path.read_text()
        original = content
        changes = 0

        for old_name, new_name in RENAMES.items():
            # Use word boundaries to avoid partial matches
            pattern = r"\b" + re.escape(old_name) + r"\b"
            new_content = re.sub(pattern, new_name, content)
            if new_content != content:
                occurrences = content.count(old_name)
                changes += occurrences
                content = new_content

        if content != original:
            # Bug fix: Use atomic write to prevent data corruption on interrupt
            # Write to temp file first, then atomically replace original
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, dir=file_path.parent, suffix=".tmp"
            ) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            # Atomic replace (POSIX compliant)
            Path(tmp_path).replace(file_path)
            return changes

        return 0
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return 0


def main():
    """Main execution."""
    print("Finding Python files...")
    files = find_python_files()
    print(f"Found {len(files)} Python files")

    total_changes = 0
    files_changed = 0

    for file_path in files:
        changes = rename_in_file(file_path)
        if changes > 0:
            total_changes += changes
            files_changed += 1
            print(f"  {file_path}: {changes} changes")

    print(f"\nTotal: {total_changes} changes in {files_changed} files")
    print("\nRenamed classes:")
    for old, new in RENAMES.items():
        print(f"  {old} → {new}")


if __name__ == "__main__":
    main()
