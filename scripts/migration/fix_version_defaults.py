#!/usr/bin/env python3
"""Fix missing default_factory on ModelSemVer fields."""

import re
from pathlib import Path


def fix_file(filepath: Path) -> int:
    """Fix a single file. Returns number of fixes made."""
    content = filepath.read_text(encoding="utf-8")
    original_content = content
    fixes = 0

    # Pattern 1: version: ModelSemVer = Field(\n        description=...
    # This pattern matches multi-line Field definitions without default_factory
    pattern1 = re.compile(
        r'(\s+)(\w*version\w*): ModelSemVer = Field\(\s*\n\s+description=("[^"]+"|\'[^\']+\')',
        re.MULTILINE,
    )

    def replace1(match):
        nonlocal fixes
        indent = match.group(1)
        field_name = match.group(2)
        description = match.group(3)
        fixes += 1
        return (
            f"{indent}{field_name}: ModelSemVer = Field(\n"
            f"{indent}    default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),\n"
            f"{indent}    description={description}"
        )

    content = pattern1.sub(replace1, content)

    # Pattern 2: version: ModelSemVer = Field(default=..., description=...)
    # Replace default=... with default_factory
    pattern2 = re.compile(
        r'(\s+)(\w*version\w*): ModelSemVer = Field\(default=\.\.\., description=("[^"]+"|\'[^\']+\')\)',
        re.MULTILINE,
    )

    def replace2(match):
        nonlocal fixes
        indent = match.group(1)
        field_name = match.group(2)
        description = match.group(3)
        fixes += 1
        return (
            f"{indent}{field_name}: ModelSemVer = Field(\n"
            f"{indent}    default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),\n"
            f"{indent}    description={description}\n"
            f"{indent})"
        )

    content = pattern2.sub(replace2, content)

    # Pattern 3: version: ModelSemVer = Field(description=...) - single line
    pattern3 = re.compile(
        r'(\s+)(\w*version\w*): ModelSemVer = Field\(description=("[^"]+"|\'[^\']+\')\)',
        re.MULTILINE,
    )

    def replace3(match):
        nonlocal fixes
        indent = match.group(1)
        field_name = match.group(2)
        description = match.group(3)
        fixes += 1
        return (
            f"{indent}{field_name}: ModelSemVer = Field(\n"
            f"{indent}    default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),\n"
            f"{indent}    description={description}\n"
            f"{indent})"
        )

    content = pattern3.sub(replace3, content)

    if content != original_content:
        filepath.write_text(content, encoding="utf-8")

    return fixes


def main():
    """Main entry point."""
    base_path = Path(__file__).parent / "src/omnibase_core/models"

    total_fixes = 0
    files_fixed = 0

    print("Scanning for files with ModelSemVer fields...")
    for filepath in base_path.rglob("*.py"):
        try:
            content = filepath.read_text(encoding="utf-8")
            # Quick check if file has ModelSemVer and Field
            if ": ModelSemVer = Field(" in content:
                # Check if it's missing default_factory
                if (
                    ": ModelSemVer = Field(default=..." in content
                    or ": ModelSemVer = Field(\n        description=" in content
                    or (
                        ": ModelSemVer = Field(description=" in content
                        and "default_factory" not in content
                    )
                ):

                    fixes = fix_file(filepath)
                    if fixes > 0:
                        rel_path = filepath.relative_to(Path(__file__).parent)
                        print(f"  ✓ {rel_path}: {fixes} fix(es)")
                        total_fixes += fixes
                        files_fixed += 1
        except Exception as e:
            print(f"  ✗ Error processing {filepath}: {e}")

    print(f"\n✓ Fixed {total_fixes} fields in {files_fixed} files")


if __name__ == "__main__":
    main()
