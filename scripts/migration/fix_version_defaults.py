#!/usr/bin/env python3
"""Fix missing default_factory on ModelSemVer fields."""

import argparse
import re
import sys
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

    def replace1(match: re.Match[str]) -> str:
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

    def replace2(match: re.Match[str]) -> str:
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

    def replace3(match: re.Match[str]) -> str:
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


def find_project_root(start_path: Path) -> Path | None:
    """Find project root by looking for pyproject.toml or src/ directory.

    Args:
        start_path: Starting directory (usually script location)

    Returns:
        Project root path or None if not found
    """
    current = start_path.resolve()

    # Walk up directory tree (max 10 levels to avoid infinite loops)
    for _ in range(10):
        # Check for project markers
        if (current / "pyproject.toml").exists():
            return current
        if (current / "src" / "omnibase_core").exists():
            return current

        # Move up one level
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent

    return None


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fix missing default_factory on ModelSemVer fields"
    )
    parser.add_argument(
        "--base-path",
        type=Path,
        default=None,
        help="Base path to scan for Python files (default: auto-detect project root)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    # Determine base path
    if args.base_path:
        base_path = args.base_path.resolve()
    else:
        # Auto-detect: Find project root from script location
        script_dir = Path(__file__).parent
        project_root = find_project_root(script_dir)

        if project_root is None:
            print("❌ Error: Could not auto-detect project root")
            print("   Looked for: pyproject.toml or src/omnibase_core directory")
            print("   Please specify --base-path explicitly")
            return 1

        base_path = project_root / "src" / "omnibase_core" / "models"

        # Validate auto-detected path exists
        if not base_path.exists():
            print(f"❌ Error: Auto-detected path does not exist: {base_path}")
            print(f"   Project root found: {project_root}")
            print("   Please specify --base-path explicitly")
            return 1

    if not base_path.exists():
        print(f"❌ Error: Base path does not exist: {base_path}")
        return 1

    if args.verbose:
        print(f"Scanning base path: {base_path}")

    total_fixes = 0
    files_fixed = 0

    print("Scanning for files with ModelSemVer fields...")
    for filepath in base_path.rglob("*.py"):
        try:
            content = filepath.read_text(encoding="utf-8")
        except (OSError, PermissionError) as e:
            print(f"  ✗ Error reading {filepath}: {e}")
            continue
        except UnicodeDecodeError as e:
            print(f"  ✗ Error decoding {filepath} (not UTF-8): {e}")
            continue

        try:
            # Check if file has ModelSemVer fields that might need fixing
            if ": ModelSemVer = Field(" in content:
                # Always try to fix - the fix_file() function will detect which
                # specific fields need fixing via regex patterns. This avoids
                # the over-restrictive check where if ANY field has default_factory,
                # we skip ALL fields in the file.
                fixes = fix_file(filepath)
                if fixes > 0:
                    try:
                        rel_path = filepath.relative_to(base_path.parent.parent)
                    except ValueError:
                        # If relative path fails, use absolute path
                        rel_path = filepath
                    print(f"  ✓ {rel_path}: {fixes} fix(es)")
                    total_fixes += fixes
                    files_fixed += 1
        except re.error as e:
            print(f"  ✗ Regex error in {filepath}: {e}")
            continue
        except OSError as e:
            # File operation errors during fix_file()
            print(f"  ✗ File operation error in {filepath}: {e}")
            continue
        except ValueError as e:
            print(f"  ✗ Value error in {filepath}: {e}")
            continue
        except RuntimeError as e:
            # Unexpected processing errors
            print(f"  ✗ Runtime error processing {filepath}: {e}")
            continue

    print(f"\n✓ Fixed {total_fixes} fields in {files_fixed} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
