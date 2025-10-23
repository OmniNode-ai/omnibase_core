#!/usr/bin/env python3
"""
Fix simple enum naming violations (single enum files with wrong name).
"""

import re
import subprocess
from pathlib import Path
from typing import Dict

# Map of incorrect class names to correct class names for simple renames
SIMPLE_RENAMES: dict[str, str] = {
    "EnumGitHubRunnerOS": "EnumGithubRunnerOs",
    "EnumIOType": "EnumIoType",
    "EnumRSDTriggerType": "EnumRsdTriggerType",
    "EnumGitHubActionEvent": "EnumGithubActionEvent",
    "EnumMCPStatus": "EnumMcpStatus",
    "EnumDocumentFreshnessErrorCodes": "EnumDocumentFreshnessErrors",
    "EnumType": "EnumTaskTypes",
}


def find_all_occurrences(src_dir: Path, old_name: str) -> list[Path]:
    """Find all files containing the old enum name."""
    result = subprocess.run(
        ["grep", "-r", "-l", old_name, str(src_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []

    return [Path(line) for line in result.stdout.strip().split("\n") if line]


def replace_in_file(file_path: Path, old_name: str, new_name: str) -> bool:
    """Replace old enum name with new name in file."""
    try:
        content = file_path.read_text()

        # Only replace if it's a whole word (not part of another identifier)
        pattern = r"\b" + re.escape(old_name) + r"\b"
        new_content = re.sub(pattern, new_name, content)

        if new_content != content:
            file_path.write_text(new_content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main fixing function."""
    src_dir = Path(__file__).parent.parent / "src" / "omnibase_core"
    tests_dir = Path(__file__).parent.parent / "tests"

    print("Fixing simple enum naming violations (single-enum files)...")
    print()

    total_files_changed = 0

    for old_name, new_name in SIMPLE_RENAMES.items():
        print(f"Fixing: {old_name} → {new_name}")

        # Find all occurrences in src and tests
        src_files = find_all_occurrences(src_dir, old_name)
        test_files = find_all_occurrences(tests_dir, old_name)
        all_files = src_files + test_files

        print(f"  Found in {len(all_files)} files")

        files_changed = 0
        for file_path in all_files:
            # Skip .pyc files
            if file_path.suffix == ".pyc":
                continue

            if replace_in_file(file_path, old_name, new_name):
                files_changed += 1
                print(f"    ✓ {file_path}")

        total_files_changed += files_changed
        print(f"  Changed {files_changed} files")
        print()

    print(f"Total files changed: {total_files_changed}")
    print()
    print("Simple renames complete!")


if __name__ == "__main__":
    main()
