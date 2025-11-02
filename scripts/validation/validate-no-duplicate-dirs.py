#!/usr/bin/env python3
"""
ONEX Duplicate Directory Detection

Detects duplicate or conflicting directory structures that indicate
organizational drift. Prevents confusion between similar directory names
like validation/ and validators/, or model/ and models/.

Examples of problematic duplicates:
- validation/ and validators/ (use validation/)
- model/ and models/ (use models/)
- enum/ and enums/ (use enums/)
- mixin/ and mixins/ (use mixins/)
- node/ and nodes/ (use nodes/)
- service/ and services/ (use services/)

This enforces consistent directory naming across the ONEX framework.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path


class DuplicateDirectoryViolation:
    """Represents a duplicate directory violation."""

    def __init__(
        self,
        canonical: str,
        duplicate: str,
        canonical_paths: list[Path],
        duplicate_paths: list[Path],
    ):
        self.canonical = canonical
        self.duplicate = duplicate
        self.canonical_paths = canonical_paths
        self.duplicate_paths = duplicate_paths

    def __str__(self) -> str:
        result = f"🔴 Duplicate: '{self.duplicate}/' should be '{self.canonical}/'\n"
        result += f"   Canonical locations ({len(self.canonical_paths)}):\n"
        for path in sorted(self.canonical_paths)[:3]:  # Show first 3
            result += f"     • {path}\n"
        if len(self.canonical_paths) > 3:
            result += f"     ... and {len(self.canonical_paths) - 3} more\n"

        result += f"   Duplicate locations ({len(self.duplicate_paths)}):\n"
        for path in sorted(self.duplicate_paths):
            result += f"     ⚠️  {path}\n"

        return result


class DuplicateDirectoryValidator:
    """Validates for duplicate or conflicting directory structures."""

    # Canonical directory names (singular/plural conventions)
    CANONICAL_FORMS = {
        # Plural forms (standard)
        "models": ["model"],
        "enums": ["enum"],
        "errors": ["error"],
        "mixins": ["mixin"],
        "nodes": ["node"],
        "services": ["service"],
        "utils": ["util", "utilities", "utility"],
        "types": ["type"],
        "constants": ["constant", "consts", "const"],
        "decorators": ["decorator"],
        "primitives": ["primitive"],
        # Singular forms (standard)
        "validation": [],  # validation/ is canonical, validators/ can coexist
        "validators": [],  # validators/ is canonical, validation/ can coexist
        "protocol": ["protocols"],
        "container": ["containers"],
        "discovery": ["discoveries"],
        "infrastructure": ["infra"],
    }

    # Directories to exclude from checks
    EXCLUDED_DIRS = {
        "__pycache__",
        ".git",
        ".pytest_cache",
        "archived",
        "archive",
        "node_modules",
        ".venv",
        "venv",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
        "*.egg-info",
    }

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.violations: list[DuplicateDirectoryViolation] = []
        self.directory_map: dict[str, list[Path]] = defaultdict(list)

    def validate(self) -> bool:
        """
        Validate for duplicate directory structures.

        Returns:
            True if no duplicates found, False otherwise
        """
        # Collect all directories
        self._collect_directories()

        # Check for duplicates
        self._detect_duplicates()

        return len(self.violations) == 0

    def _collect_directories(self) -> None:
        """Collect all directories in the repository."""
        for item in self.repo_path.rglob("*"):
            if not item.is_dir():
                continue

            # Skip excluded directories
            if any(excluded in str(item) for excluded in self.EXCLUDED_DIRS):
                continue

            # Get just the directory name (not full path)
            dir_name = item.name

            # Only care about directories in our canonical forms
            if dir_name in self.CANONICAL_FORMS or any(
                dir_name in duplicates for duplicates in self.CANONICAL_FORMS.values()
            ):
                self.directory_map[dir_name].append(item)

    def _detect_duplicates(self) -> None:
        """Detect duplicate directory patterns."""
        # Check each canonical form
        for canonical, duplicates in self.CANONICAL_FORMS.items():
            canonical_paths = self.directory_map.get(canonical, [])

            # Check if any duplicate forms exist
            for duplicate in duplicates:
                duplicate_paths = self.directory_map.get(duplicate, [])

                if duplicate_paths and canonical_paths:
                    # We have both canonical and duplicate - violation!
                    self.violations.append(
                        DuplicateDirectoryViolation(
                            canonical=canonical,
                            duplicate=duplicate,
                            canonical_paths=canonical_paths,
                            duplicate_paths=duplicate_paths,
                        )
                    )

    def generate_report(self) -> str:
        """Generate a validation report."""
        if not self.violations:
            return "✅ No duplicate directories found!"

        report = "🚨 ONEX Duplicate Directory Violations\n"
        report += "=" * 60 + "\n\n"

        report += f"Found {len(self.violations)} duplicate directory pattern(s):\n\n"

        for violation in sorted(self.violations, key=lambda v: v.canonical):
            report += str(violation) + "\n"

        report += "📚 CANONICAL DIRECTORY NAMES:\n"
        report += "=" * 60 + "\n"
        report += "Standard forms to use:\n"
        for canonical in sorted(self.CANONICAL_FORMS.keys()):
            report += f"  ✅ {canonical}/\n"

        report += "\n💡 How to fix:\n"
        report += "  1. Consolidate files from duplicate into canonical directory\n"
        report += "  2. Update all imports to use canonical directory\n"
        report += "  3. Delete the duplicate directory\n"
        report += "  4. Run tests to verify everything works\n"

        return report


def main() -> int:
    """Main entry point for validation script."""
    parser = argparse.ArgumentParser(
        description="Detect duplicate directory patterns in ONEX codebase"
    )
    parser.add_argument(
        "repo_path",
        nargs="?",
        default=".",
        help="Path to repository root (default: current directory)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    repo_path = Path(args.repo_path).resolve()
    if not repo_path.exists():
        print(f"❌ Error: Repository path does not exist: {repo_path}")
        return 1

    validator = DuplicateDirectoryValidator(repo_path)
    is_valid = validator.validate()

    if is_valid:
        if args.verbose:
            print("✅ No duplicate directories found!")
        return 0
    else:
        report = validator.generate_report()
        print(report)
        print(
            f"\n❌ FAILURE: {len(validator.violations)} duplicate directory pattern(s) found!"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
