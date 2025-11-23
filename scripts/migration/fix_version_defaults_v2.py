#!/usr/bin/env python3
"""Fix missing default_factory on ModelSemVer fields - Version 2."""

import re
import sys
from pathlib import Path


def fix_file(filepath: Path) -> int:
    """Fix a single file. Returns number of fixes made."""
    content = filepath.read_text(encoding="utf-8")
    original_content = content
    fixes = 0

    # This pattern handles multi-line cases where the closing paren is on its own line
    # Example:
    #     version: ModelSemVer = Field(
    #         description="Model version (MUST be provided in YAML contract)",
    #     )
    lines = content.split("\n")
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this line has ": ModelSemVer = Field("
        if ": ModelSemVer = Field(" in line and "default_factory" not in line:
            # Get the indentation
            indent_match = re.match(r"^(\s+)", line)
            indent = indent_match.group(1) if indent_match else ""

            # Extract field name
            field_match = re.search(r"(\w+): ModelSemVer = Field\(", line)
            if not field_match:
                new_lines.append(line)
                i += 1
                continue

            field_name = field_match.group(1)

            # Check the next lines to find description and closing paren
            j = i + 1
            field_lines = [line]
            has_default_factory = False

            while j < len(lines):
                next_line = lines[j]
                field_lines.append(next_line)

                if "default_factory" in next_line:
                    has_default_factory = True
                    break

                # Check if we've found the closing paren
                if ")" in next_line and "=" not in next_line.split(")")[0]:
                    break

                j += 1

            # If already has default_factory, keep as is
            if has_default_factory:
                new_lines.extend(field_lines)
                i = j + 1
                continue

            # Check if this has default=... or description= pattern
            full_field = "\n".join(field_lines)

            # Extract description if present
            desc_match = re.search(
                r'description\s*=\s*(\([^)]+\)|"[^"]+"|\'[^\']+\')',
                full_field,
                re.DOTALL,
            )
            description = desc_match.group(1) if desc_match else '"Model version"'

            # Clean up description to remove extra whitespace and parentheses
            if description.startswith("("):
                description = description.strip("(").strip(")")
                description = " ".join(description.split())
                description = f'"{description}"'

            # Create new field definition
            new_field_lines = [
                f"{indent}{field_name}: ModelSemVer = Field(",
                f"{indent}    default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),",
                f"{indent}    description={description},",
                f"{indent})",
            ]

            new_lines.extend(new_field_lines)
            fixes += 1

            # Skip to after the closing paren
            i = j + 1
        else:
            new_lines.append(line)
            i += 1

    content = "\n".join(new_lines)

    if content != original_content:
        filepath.write_text(content, encoding="utf-8")

    return fixes


def find_project_root() -> Path:
    """Find the project root by looking for pyproject.toml.

    Returns:
        Path to the project root directory.

    Raises:
        FileNotFoundError: If project root cannot be found.
    """
    current = Path(__file__).resolve()

    # Walk up the directory tree looking for pyproject.toml
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent

    # If not found, raise a clear error
    raise FileNotFoundError(
        f"Could not find project root (pyproject.toml) starting from {current}. "
        "Ensure this script is run from within the omnibase_core repository."
    )


def resolve_base_path(project_root: Path) -> Path:
    """Resolve and validate the base path for models.

    Args:
        project_root: The project root directory.

    Returns:
        Path to the models directory.

    Raises:
        FileNotFoundError: If the models directory doesn't exist.
    """
    base_path = project_root / "src" / "omnibase_core" / "models"

    if not base_path.exists():
        raise FileNotFoundError(
            f"Models directory not found at {base_path}. "
            f"Expected directory structure: {project_root}/src/omnibase_core/models"
        )

    if not base_path.is_dir():
        raise NotADirectoryError(f"Path exists but is not a directory: {base_path}")

    return base_path


def main():
    """Main entry point."""
    try:
        # Find project root
        project_root = find_project_root()
        print(f"Project root: {project_root}")

        # Resolve and validate base path
        base_path = resolve_base_path(project_root)
        print(f"Models directory: {base_path}")

    except (FileNotFoundError, NotADirectoryError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    total_fixes = 0
    files_fixed = 0

    print("\nScanning for files with ModelSemVer fields (V2)...")

    try:
        python_files = list(base_path.rglob("*.py"))
        if not python_files:
            print(f"WARNING: No Python files found in {base_path}", file=sys.stderr)
            sys.exit(0)

    except Exception as e:
        print(f"ERROR: Failed to scan directory {base_path}: {e}", file=sys.stderr)
        sys.exit(1)

    for filepath in python_files:
        try:
            content = filepath.read_text(encoding="utf-8")
            # Quick check if file has ModelSemVer and Field
            if ": ModelSemVer = Field(" in content:
                # Check if any don't have default_factory
                lines = content.split("\n")
                needs_fix = False

                for i, line in enumerate(lines):
                    if ": ModelSemVer = Field(" in line:
                        # Check if the next few lines have default_factory
                        context = "\n".join(lines[i : min(i + 5, len(lines))])
                        if "default_factory" not in context:
                            needs_fix = True
                            break

                if needs_fix:
                    fixes = fix_file(filepath)
                    if fixes > 0:
                        # Safely compute relative path
                        try:
                            rel_path = filepath.relative_to(project_root)
                        except ValueError:
                            # If file is not relative to project root, use absolute path
                            rel_path = filepath

                        print(f"  ✓ {rel_path}: {fixes} fix(es)")
                        total_fixes += fixes
                        files_fixed += 1
        except Exception as e:
            print(f"  ✗ Error processing {filepath}: {e}", file=sys.stderr)

    print(f"\n✓ Fixed {total_fixes} fields in {files_fixed} files")


if __name__ == "__main__":
    main()
