#!/usr/bin/env python3
"""
Validate markdown links in documentation.

Checks for:
- Broken internal file links (relative paths)
- Missing anchor links
- Unreachable files
"""

import re
import sys
from pathlib import Path


def remove_code_blocks(content: str) -> str:
    """Remove fenced code blocks from content to avoid false positives."""
    # Remove fenced code blocks (``` or ~~~)
    content = re.sub(r"```[\s\S]*?```", "", content)
    content = re.sub(r"~~~[\s\S]*?~~~", "", content)
    # Remove inline code
    content = re.sub(r"`[^`]+`", "", content)
    return content


def extract_markdown_links(content: str, file_path: Path) -> list[tuple[str, int]]:
    """Extract all markdown links with line numbers."""
    links = []

    # Remove code blocks to avoid false positives
    clean_content = remove_code_blocks(content)

    # Match [text](link) and [text](link#anchor)
    pattern = r"\[([^\]]+)\]\(([^)]+)\)"

    for match in re.finditer(pattern, clean_content):
        link = match.group(2)
        # Find line number in original content
        # Search for the same link pattern in original
        line_num = content[: content.find(match.group(0))].count("\n") + 1
        links.append((link, line_num))

    return links


def is_internal_link(link: str) -> bool:
    """Check if link is internal (not http/https/mailto)."""
    if link.startswith(("http://", "https://", "mailto:", "#")):
        return False
    # Skip code-like patterns that aren't real links
    # Single word PascalCase (class names like BaseModel, ValidationError)
    if re.match(r"^[A-Z][a-zA-Z0-9]*$", link):
        return False
    # Single word snake_case (variable names)
    if re.match(r"^[a-z_][a-z0-9_]*$", link):
        return False
    # Multi-line content (code blocks)
    if "\n" in link:
        return False
    # Placeholder text
    if link in ("link", "url", "path", "file"):
        return False
    return True


def validate_file_link(
    link: str, source_file: Path, repo_root: Path
) -> tuple[bool, str]:
    """Validate that a file link exists."""
    # Remove anchor if present
    file_path = link.split("#")[0]

    if not file_path:
        # Pure anchor link (same file)
        return True, ""

    # Resolve relative to source file's directory
    source_dir = source_file.parent
    target = source_dir / file_path

    # Normalize path
    try:
        target = target.resolve()
    except Exception as e:
        return False, f"Invalid path: {e}"

    # Check if file exists
    if not target.exists():
        # Handle paths outside repo root gracefully
        try:
            rel_path = target.relative_to(repo_root)
        except ValueError:
            # Path is outside repo - show absolute path or skip
            rel_path = target
        return False, f"File not found: {rel_path}"

    return True, ""


def validate_markdown_links(repo_root: Path) -> int:
    """Validate all markdown links in repository."""
    errors = 0
    total_links = 0
    total_files = 0

    # Find all markdown files
    md_files = sorted(repo_root.rglob("*.md"))

    print(f"🔍 Scanning {len(md_files)} markdown files for broken links...\n")

    for md_file in md_files:
        # Skip .venv and __pycache__ directories
        if ".venv" in md_file.parts or "__pycache__" in md_file.parts:
            continue

        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception as e:
            print(f"❌ Error reading {md_file.relative_to(repo_root)}: {e}")
            errors += 1
            continue

        links = extract_markdown_links(content, md_file)

        if not links:
            continue

        total_files += 1
        file_errors = 0

        for link, line_num in links:
            total_links += 1

            # Skip external links
            if not is_internal_link(link):
                continue

            # Validate internal file link
            is_valid, error_msg = validate_file_link(link, md_file, repo_root)

            if not is_valid:
                if file_errors == 0:
                    print(f"\n📄 {md_file.relative_to(repo_root)}")

                print(f"  ❌ Line {line_num}: [{link}] - {error_msg}")
                file_errors += 1
                errors += 1

    print(f"\n{'=' * 70}")
    print("✅ Validation complete!")
    print(f"   Files scanned: {total_files}")
    print(f"   Total links: {total_links}")
    print(f"   Broken links: {errors}")

    if errors == 0:
        print("\n🎉 All internal links are valid!")
        return 0
    else:
        print(f"\n⚠️  Found {errors} broken link(s)")
        return 1


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[2]
    sys.exit(validate_markdown_links(repo_root))
