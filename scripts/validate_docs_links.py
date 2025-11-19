#!/usr/bin/env python3
"""
Validate all documentation cross-references and links.

Checks:
1. Internal markdown links exist
2. Relative paths are correct
3. Anchor links point to valid sections
4. Files referenced actually exist
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

# Base directory
BASE_DIR = Path(__file__).parent.parent
DOCS_DIR = BASE_DIR / "docs"

# Markdown link pattern: [text](path) or [text](path#anchor)
MD_LINK_PATTERN = re.compile(r'\[([^\]]+)\]\(([^)]+\.md[^)]*)\)')

# Heading anchor pattern (for validating #section-name links)
HEADING_PATTERN = re.compile(r'^#{1,6}\s+(.+)$', re.MULTILINE)


def normalize_anchor(heading: str) -> str:
    """Convert heading text to GitHub-style anchor."""
    # GitHub anchor rules:
    # 1. Lowercase
    # 2. Replace spaces with hyphens
    # 3. Remove special characters except hyphens
    # 4. Remove leading/trailing hyphens
    anchor = heading.lower()
    anchor = re.sub(r'[^\w\s-]', '', anchor)
    anchor = re.sub(r'\s+', '-', anchor)
    anchor = anchor.strip('-')
    return anchor


def extract_headings(file_path: Path) -> Set[str]:
    """Extract all heading anchors from a markdown file."""
    try:
        content = file_path.read_text(encoding='utf-8')
        headings = HEADING_PATTERN.findall(content)
        return {normalize_anchor(h) for h in headings}
    except Exception as e:
        print(f"⚠️  Error reading {file_path}: {e}")
        return set()


def find_all_md_files() -> List[Path]:
    """Find all markdown files in the repository."""
    md_files = []

    # Docs directory
    md_files.extend(DOCS_DIR.rglob("*.md"))

    # Root markdown files
    for root_md in ["README.md", "CLAUDE.md", "CONTRIBUTING.md", "CHANGELOG.md"]:
        root_path = BASE_DIR / root_md
        if root_path.exists():
            md_files.append(root_path)

    return sorted(md_files)


def extract_links(file_path: Path) -> List[Tuple[int, str, str]]:
    """Extract all markdown links from a file.

    Returns:
        List of (line_number, link_text, link_path) tuples
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        links = []
        for line_num, line in enumerate(lines, start=1):
            for match in MD_LINK_PATTERN.finditer(line):
                link_text = match.group(1)
                link_path = match.group(2)
                links.append((line_num, link_text, link_path))

        return links
    except Exception as e:
        print(f"⚠️  Error reading {file_path}: {e}")
        return []


def resolve_link_path(source_file: Path, link_path: str) -> Tuple[Path, str]:
    """Resolve a link path relative to source file.

    Returns:
        (resolved_file_path, anchor)
    """
    # Split anchor if present
    if '#' in link_path:
        file_part, anchor = link_path.split('#', 1)
    else:
        file_part, anchor = link_path, ""

    # Skip external links
    if file_part.startswith(('http://', 'https://', 'mailto:')):
        return None, ""

    # Resolve relative path
    if file_part.startswith('/'):
        # Absolute from repo root
        resolved = BASE_DIR / file_part.lstrip('/')
    else:
        # Relative to source file
        resolved = (source_file.parent / file_part).resolve()

    return resolved, anchor


def validate_links() -> Dict[str, List[Dict]]:
    """Validate all documentation links.

    Returns:
        Dictionary of issues categorized by type
    """
    issues = defaultdict(list)

    # Find all markdown files
    md_files = find_all_md_files()
    print(f"📊 Found {len(md_files)} markdown files\n")

    # Cache heading anchors for performance
    heading_cache = {}

    total_links = 0
    broken_links = 0

    # Process each file
    for source_file in md_files:
        links = extract_links(source_file)

        for line_num, link_text, link_path in links:
            total_links += 1

            # Resolve the link
            target_file, anchor = resolve_link_path(source_file, link_path)

            # Skip external links
            if target_file is None:
                continue

            # Check if target file exists
            if not target_file.exists():
                broken_links += 1
                issues['broken_file'].append({
                    'source': str(source_file.relative_to(BASE_DIR)),
                    'line': line_num,
                    'link_text': link_text,
                    'link_path': link_path,
                    'target': str(target_file.relative_to(BASE_DIR)) if BASE_DIR in target_file.parents else str(target_file),
                    'issue': 'File does not exist'
                })
                continue

            # Check if target is a directory instead of a file
            if target_file.is_dir():
                broken_links += 1
                issues['link_to_directory'].append({
                    'source': str(source_file.relative_to(BASE_DIR)),
                    'line': line_num,
                    'link_text': link_text,
                    'link_path': link_path,
                    'target': str(target_file.relative_to(BASE_DIR)),
                    'issue': 'Link points to directory instead of file'
                })
                continue

            # Check anchor if present
            if anchor:
                # Get headings from target file (with caching)
                if target_file not in heading_cache:
                    heading_cache[target_file] = extract_headings(target_file)

                headings = heading_cache[target_file]

                if anchor not in headings:
                    broken_links += 1
                    issues['broken_anchor'].append({
                        'source': str(source_file.relative_to(BASE_DIR)),
                        'line': line_num,
                        'link_text': link_text,
                        'link_path': link_path,
                        'target': str(target_file.relative_to(BASE_DIR)),
                        'anchor': anchor,
                        'issue': f'Anchor #{anchor} not found',
                        'available_anchors': sorted(headings)[:5]  # Show first 5 available
                    })

    print(f"✅ Total links checked: {total_links}")
    print(f"{'❌' if broken_links > 0 else '✅'} Broken links: {broken_links}\n")

    return dict(issues)


def print_report(issues: Dict[str, List[Dict]]):
    """Print validation report."""

    if not issues:
        print("🎉 All documentation links are valid!")
        return 0

    print("=" * 80)
    print("DOCUMENTATION LINK VALIDATION REPORT")
    print("=" * 80)
    print()

    # Broken file references
    if 'broken_file' in issues:
        print(f"🔴 BROKEN FILE REFERENCES ({len(issues['broken_file'])})")
        print("-" * 80)
        for issue in issues['broken_file']:
            print(f"\n📄 {issue['source']}:{issue['line']}")
            print(f"   Link: [{issue['link_text']}]({issue['link_path']})")
            print(f"   ❌ {issue['issue']}: {issue['target']}")
        print()

    # Links to directories
    if 'link_to_directory' in issues:
        print(f"🟡 LINKS TO DIRECTORIES ({len(issues['link_to_directory'])})")
        print("-" * 80)
        for issue in issues['link_to_directory']:
            print(f"\n📄 {issue['source']}:{issue['line']}")
            print(f"   Link: [{issue['link_text']}]({issue['link_path']})")
            print(f"   ❌ {issue['issue']}: {issue['target']}")
            print(f"   💡 Suggestion: Link to a specific file like {issue['target']}/README.md or {issue['target']}/index.md")
        print()

    # Broken anchor references
    if 'broken_anchor' in issues:
        print(f"🟠 BROKEN ANCHOR REFERENCES ({len(issues['broken_anchor'])})")
        print("-" * 80)
        for issue in issues['broken_anchor']:
            print(f"\n📄 {issue['source']}:{issue['line']}")
            print(f"   Link: [{issue['link_text']}]({issue['link_path']})")
            print(f"   ❌ {issue['issue']} in {issue['target']}")
            if issue.get('available_anchors'):
                print(f"   ℹ️  Available anchors (first 5): {', '.join(issue['available_anchors'])}")
        print()

    # Summary
    total_issues = sum(len(v) for v in issues.values())
    print("=" * 80)
    print(f"SUMMARY: {total_issues} issues found")
    print("=" * 80)

    return 1  # Exit code


def main():
    """Main entry point."""
    print("🔍 Validating documentation cross-references...\n")

    issues = validate_links()
    exit_code = print_report(issues)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
