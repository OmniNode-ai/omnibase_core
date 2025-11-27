#!/usr/bin/env python3
"""
Validate documentation links in markdown files.

Checks for:
- Broken internal links (relative paths)
- Missing referenced files
- Correct file name casing
- Broken cross-references

Usage:
    poetry run python scripts/validate-doc-links.py
    poetry run python scripts/validate-doc-links.py --fix-case
"""

import argparse
import re
import sys
from pathlib import Path


class DocLinkValidator:
    """Validates internal links in documentation."""

    def __init__(self, docs_root: Path, fix_case: bool = False):
        """Initialize validator.

        Args:
            docs_root: Root directory for documentation
            fix_case: Whether to suggest case fixes
        """
        self.docs_root = docs_root
        self.fix_case = fix_case
        self.errors: list[str] = []
        self.warnings: list[str] = []

        # Pattern to match markdown links: [text](path)
        self.link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    def validate_all_docs(self) -> bool:
        """Validate all markdown files in docs directory.

        Returns:
            True if all validations pass, False otherwise
        """
        print(f"🔍 Validating documentation links in {self.docs_root}")
        print("=" * 70)

        # Find all markdown files
        md_files = list(self.docs_root.rglob("*.md"))
        md_files.append(Path("CLAUDE.md"))  # Include root CLAUDE.md

        total_links = 0
        broken_links = 0

        for md_file in md_files:
            if not md_file.exists():
                continue

            links = self._extract_links(md_file)
            total_links += len(links)

            for link_text, link_path, line_num in links:
                if not self._validate_link(md_file, link_path, line_num):
                    broken_links += 1

        # Print summary
        print("\n" + "=" * 70)
        print("📊 Validation Summary:")
        print(f"   Files checked: {len(md_files)}")
        print(f"   Links validated: {total_links}")
        print(f"   Errors: {len(self.errors)}")
        print(f"   Warnings: {len(self.warnings)}")

        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors:
                print(f"   {error}")

        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"   {warning}")

        if not self.errors and not self.warnings:
            print("\n✅ All documentation links are valid!")
            return True
        elif self.errors:
            print(f"\n❌ Found {len(self.errors)} broken link(s)")
            return False
        else:
            print(f"\n⚠️  Found {len(self.warnings)} warning(s)")
            return True

    def _extract_links(self, md_file: Path) -> list[tuple[str, str, int]]:
        """Extract all markdown links from file.

        Args:
            md_file: Markdown file to parse

        Returns:
            List of (link_text, link_path, line_number) tuples
        """
        links = []

        try:
            content = md_file.read_text(encoding="utf-8")
            in_code_block = False

            for line_num, line in enumerate(content.split("\n"), 1):
                # Track code fence boundaries
                if line.strip().startswith("```"):
                    in_code_block = not in_code_block
                    continue

                # Skip lines inside code blocks
                if in_code_block:
                    continue

                for match in self.link_pattern.finditer(line):
                    link_text = match.group(1)
                    link_path = match.group(2)

                    # Skip external links (http/https)
                    if link_path.startswith(("http://", "https://", "mailto:", "#")):
                        continue

                    # Remove anchor fragments
                    link_path = link_path.split("#")[0]

                    # Skip empty paths (pure anchors)
                    if not link_path:
                        continue

                    links.append((link_text, link_path, line_num))

        except Exception as e:
            self.warnings.append(f"Error reading {md_file}: {e}")

        return links

    def _validate_link(self, source_file: Path, link_path: str, line_num: int) -> bool:
        """Validate a single link.

        Args:
            source_file: File containing the link
            link_path: Relative path from link
            line_num: Line number of link

        Returns:
            True if link is valid, False otherwise
        """
        # Resolve relative path
        source_dir = source_file.parent
        target_path = (source_dir / link_path).resolve()

        # Check if target exists
        if not target_path.exists():
            # Try case-insensitive search
            if self.fix_case:
                alternatives = self._find_case_alternatives(target_path)
                if alternatives:
                    alt_str = ", ".join(
                        str(a.relative_to(Path.cwd())) for a in alternatives
                    )
                    self.warnings.append(
                        f"{source_file}:{line_num} - Broken link '{link_path}' "
                        f"(possible case issue, found: {alt_str})"
                    )
                    return False

            self.errors.append(
                f"{source_file}:{line_num} - Broken link '{link_path}' "
                f"(target not found: {target_path})"
            )
            return False

        # Check if it's a file (not directory)
        if target_path.is_dir():
            self.warnings.append(
                f"{source_file}:{line_num} - Link '{link_path}' points to directory "
                f"(should point to specific file)"
            )
            return True  # Warning, not error

        return True

    def _find_case_alternatives(self, target_path: Path) -> list[Path]:
        """Find files with same name but different case.

        Args:
            target_path: Path to search for

        Returns:
            List of alternative paths with different casing
        """
        alternatives = []
        target_name_lower = target_path.name.lower()

        # Search in parent directory
        if target_path.parent.exists():
            for file in target_path.parent.iterdir():
                if (
                    file.name.lower() == target_name_lower
                    and file.name != target_path.name
                ):
                    alternatives.append(file)

        return alternatives


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate documentation links",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--fix-case",
        action="store_true",
        help="Suggest case fixes for broken links",
    )
    parser.add_argument(
        "--docs-root",
        type=Path,
        default=Path("docs"),
        help="Root directory for documentation (default: docs)",
    )

    args = parser.parse_args()

    # Validate docs directory exists
    if not args.docs_root.exists():
        print(f"❌ Documentation directory not found: {args.docs_root}")
        return 1

    # Run validation
    validator = DocLinkValidator(args.docs_root, fix_case=args.fix_case)
    success = validator.validate_all_docs()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
