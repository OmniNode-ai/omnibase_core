#!/usr/bin/env python3
"""Fix missing default_factory on ModelSemVer fields - Version 2."""

import re
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


def main():
    """Main entry point."""
    base_path = Path(__file__).parent / "src/omnibase_core/models"

    total_fixes = 0
    files_fixed = 0

    print("Scanning for files with ModelSemVer fields (V2)...")
    for filepath in base_path.rglob("*.py"):
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
                        rel_path = filepath.relative_to(Path(__file__).parent)
                        print(f"  ✓ {rel_path}: {fixes} fix(es)")
                        total_fixes += fixes
                        files_fixed += 1
        except Exception as e:
            print(f"  ✗ Error processing {filepath}: {e}")

    print(f"\n✓ Fixed {total_fixes} fields in {files_fixed} files")


if __name__ == "__main__":
    main()
