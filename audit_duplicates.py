#!/usr/bin/env python3
"""
Comprehensive duplicate model file analyzer.
Finds all duplicate filenames and compares their content.
"""

import hashlib
from pathlib import Path
from collections import defaultdict
from difflib import unified_diff

def get_file_hash(filepath: Path) -> str:
    """Get SHA256 hash of file content."""
    return hashlib.sha256(filepath.read_bytes()).hexdigest()

def find_duplicates(base_dir: Path) -> dict[str, list[Path]]:
    """Find all duplicate filenames under base_dir."""
    files_by_name: dict[str, list[Path]] = defaultdict(list)

    for pyfile in base_dir.rglob("*.py"):
        if "__pycache__" in str(pyfile) or "__init__.py" == pyfile.name:
            continue
        files_by_name[pyfile.name].append(pyfile)

    # Only keep duplicates
    return {name: paths for name, paths in files_by_name.items() if len(paths) > 1}

def compare_files(paths: list[Path]) -> dict:
    """Compare file contents and return analysis."""
    # Get hashes
    hashes = {path: get_file_hash(path) for path in paths}

    # Check if all identical
    unique_hashes = set(hashes.values())

    # Get file sizes
    sizes = {path: path.stat().st_size for path in paths}

    return {
        "paths": paths,
        "hashes": hashes,
        "unique_count": len(unique_hashes),
        "is_identical": len(unique_hashes) == 1,
        "sizes": sizes,
    }

def analyze_all_duplicates(base_dir: Path):
    """Main analysis function."""
    duplicates = find_duplicates(base_dir)

    # Sort by count (most duplicates first)
    sorted_duplicates = sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True)

    print(f"Found {len(sorted_duplicates)} duplicate filename sets\n")

    # Categorize
    identical = []
    similar = []
    different = []

    for filename, paths in sorted_duplicates:
        analysis = compare_files(paths)

        if analysis["is_identical"]:
            identical.append((filename, paths, analysis))
        else:
            # Check if files are similar (same size or nearly same)
            sizes = list(analysis["sizes"].values())
            max_size = max(sizes)
            min_size = min(sizes)

            # If size difference is < 20% or all files < 100 bytes, consider similar
            if max_size < 100 or (max_size - min_size) / max_size < 0.2:
                similar.append((filename, paths, analysis))
            else:
                different.append((filename, paths, analysis))

    # Print summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total duplicate sets: {len(sorted_duplicates)}")
    print(f"Identical files: {len(identical)}")
    print(f"Similar files: {len(similar)}")
    print(f"Different implementations: {len(different)}")
    print()

    # Print identical files
    print("=" * 80)
    print("IDENTICAL DUPLICATES (byte-for-byte identical)")
    print("=" * 80)
    for filename, paths, analysis in identical:
        print(f"\n{filename} ({len(paths)} copies):")
        for path in paths:
            rel_path = path.relative_to(base_dir.parent)
            print(f"  - {rel_path}")
        print(f"  Size: {analysis['sizes'][paths[0]]} bytes")

    # Print similar files
    print("\n" + "=" * 80)
    print("SIMILAR FILES (likely small differences)")
    print("=" * 80)
    for filename, paths, analysis in similar:
        print(f"\n{filename} ({len(paths)} copies):")
        for path in paths:
            rel_path = path.relative_to(base_dir.parent)
            size = analysis['sizes'][path]
            print(f"  - {rel_path} ({size} bytes)")

    # Print different files
    print("\n" + "=" * 80)
    print("DIFFERENT IMPLEMENTATIONS (significant differences)")
    print("=" * 80)
    for filename, paths, analysis in different:
        print(f"\n{filename} ({len(paths)} copies):")
        for path in paths:
            rel_path = path.relative_to(base_dir.parent)
            size = analysis['sizes'][path]
            print(f"  - {rel_path} ({size} bytes)")

if __name__ == "__main__":
    base_dir = Path("/home/user/omnibase_core/src/omnibase_core/models")
    analyze_all_duplicates(base_dir)
