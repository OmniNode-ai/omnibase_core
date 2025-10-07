#!/usr/bin/env python3
"""
Fix MyPy arg-type errors across the omnibase_core codebase.
Handles UUID, ModelSemVer, Path, and other type conversion issues.
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

# Root directory
ROOT_DIR = Path(__file__).parent.parent / "src" / "omnibase_core"

# Fixes to apply: (file_path, line_number, pattern, replacement, description)
FIXES: List[Tuple[str, int, str, str, str]] = [
    # UUID conversion fixes - mixin_workflow_support.py
    (
        "mixins/mixin_workflow_support.py",
        114,
        r"correlation_id=correlation_id,",
        "correlation_id=UUID(correlation_id) if isinstance(correlation_id, str) else correlation_id,",
        "Convert str to UUID for correlation_id",
    ),
    (
        "mixins/mixin_workflow_support.py",
        127,
        r"correlation_id=correlation_id,",
        "correlation_id=UUID(correlation_id) if isinstance(correlation_id, str) else correlation_id,",
        "Convert str to UUID for correlation_id in create_broadcast",
    ),
    (
        "mixins/mixin_workflow_support.py",
        156,
        r"correlation_id=correlation_id,",
        "correlation_id=UUID(correlation_id) if isinstance(correlation_id, str) else correlation_id,",
        "Convert str to UUID for correlation_id in emit_dag_start_event",
    ),
    (
        "mixins/mixin_workflow_support.py",
        169,
        r"correlation_id=correlation_id,",
        "correlation_id=UUID(correlation_id) if isinstance(correlation_id, str) else correlation_id,",
        "Convert str to UUID for correlation_id in envelope",
    ),
    # ModelSemVer conversion - model_event_bus_input_state.py
    (
        "models/service/model_event_bus_input_state.py",
        398,
        r"version=version,",
        "version=parse_semver_from_string(version) if isinstance(version, str) else version,",
        "Convert str to ModelSemVer",
    ),
    # ModelSemVer conversion - model_schema.py
    (
        "models/core/model_schema.py",
        502,
        r"schema_version=schema_version,",
        "schema_version=parse_semver_from_string(schema_version) if isinstance(schema_version, str) else schema_version,",
        "Convert str to ModelSemVer for schema_version",
    ),
]


def read_file_lines(filepath: Path) -> List[str]:
    """Read file and return lines."""
    with open(filepath, "r", encoding="utf-8") as f:
        return f.readlines()


def write_file_lines(filepath: Path, lines: List[str]) -> None:
    """Write lines to file."""
    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(lines)


def apply_line_fix(
    filepath: Path, line_num: int, pattern: str, replacement: str, description: str
) -> bool:
    """Apply a fix to a specific line in a file."""
    try:
        lines = read_file_lines(filepath)

        if line_num > len(lines):
            print(f"  ❌ Line {line_num} not found in {filepath}")
            return False

        # Line numbers are 1-based
        line_idx = line_num - 1
        original_line = lines[line_idx]

        # Try to match and replace
        new_line = re.sub(pattern, replacement, original_line)

        if new_line == original_line:
            print(f"  ⚠️  Pattern not found on line {line_num}: {pattern}")
            return False

        lines[line_idx] = new_line
        write_file_lines(filepath, lines)

        print(f"  ✅ Line {line_num}: {description}")
        return True

    except Exception as e:
        print(f"  ❌ Error fixing line {line_num}: {e}")
        return False


def fix_path_none_errors():
    """Fix 'str | None' to Path errors."""
    files_to_fix = [
        ("mixins/mixin_node_id_from_contract.py", 84),
        ("mixins/mixin_introspect_from_contract.py", 34),
        ("mixins/mixin_node_setup.py", 42),
        ("infrastructure/node_effect.py", 275),
    ]

    print("\n🔧 Fixing Path(str | None) errors...")
    for file_rel, line_num in files_to_fix:
        filepath = ROOT_DIR / file_rel
        if not filepath.exists():
            print(f"  ⚠️  File not found: {filepath}")
            continue

        lines = read_file_lines(filepath)
        line_idx = line_num - 1

        if line_idx >= len(lines):
            continue

        line = lines[line_idx]

        # Find Path(...) call and wrap the argument
        if "Path(" in line:
            # Replace Path(var) with Path(var) if var else Path(".")
            # This is a simple pattern - looking for Path(something)
            new_line = re.sub(r"Path\(([^)]+)\)", r'Path(\1 if \1 else ".")', line)

            if new_line != line:
                lines[line_idx] = new_line
                write_file_lines(filepath, lines)
                print(f"  ✅ {file_rel}:{line_num} - Added None check for Path")


def fix_uuid_node_id_errors():
    """Fix node_id str -> UUID conversion errors."""
    # Read the discovery files and fix str -> UUID issues
    files_patterns = [
        (
            "models/discovery/model_introspection_response_event.py",
            [(143, "node_id"), (183, "node_id"), (227, "node_id")],
        ),
        ("mixins/mixin_event_listener.py", [(990, "node_id")]),
    ]

    print("\n🔧 Fixing node_id str -> UUID conversion errors...")
    for file_rel, fixes in files_patterns:
        filepath = ROOT_DIR / file_rel
        if not filepath.exists():
            continue

        lines = read_file_lines(filepath)
        modified = False

        for line_num, field_name in fixes:
            line_idx = line_num - 1
            if line_idx >= len(lines):
                continue

            line = lines[line_idx]
            # Look for node_id=some_var pattern
            pattern = rf"({field_name}=)(\w+),"
            match = re.search(pattern, line)

            if match:
                var_name = match.group(2)
                # Add UUID conversion
                new_line = re.sub(
                    pattern,
                    rf"\1UUID({var_name}) if isinstance({var_name}, str) else {var_name},",
                    line,
                )
                lines[line_idx] = new_line
                modified = True
                print(f"  ✅ {file_rel}:{line_num} - Convert {field_name} str to UUID")

        if modified:
            write_file_lines(filepath, lines)


def fix_correlation_id_errors():
    """Fix correlation_id type conversion errors in various mixins."""
    files_to_fix = [
        "mixins/mixin_tool_execution.py",
        "mixins/mixin_service_registry.py",
    ]

    print("\n🔧 Fixing correlation_id str -> UUID conversion errors...")
    for file_rel in files_to_fix:
        filepath = ROOT_DIR / file_rel
        if not filepath.exists():
            continue

        content = filepath.read_text(encoding="utf-8")
        original = content

        # Fix correlation_id=var_name, patterns
        content = re.sub(
            r"correlation_id=(\w+),",
            lambda m: f"correlation_id=UUID({m.group(1)}) if isinstance({m.group(1)}, str) else {m.group(1)},",
            content,
        )

        if content != original:
            filepath.write_text(content, encoding="utf-8")
            print(f"  ✅ {file_rel} - Fixed correlation_id conversions")


def main():
    """Main execution."""
    print("🚀 Starting arg-type error fixes...")
    print(f"📁 Working directory: {ROOT_DIR}")

    # Apply individual fixes
    print("\n🔧 Applying targeted line fixes...")
    success_count = 0
    for file_rel, line_num, pattern, replacement, description in FIXES:
        filepath = ROOT_DIR / file_rel
        if not filepath.exists():
            print(f"  ⚠️  File not found: {filepath}")
            continue

        print(f"\n📝 {file_rel}")
        if apply_line_fix(filepath, line_num, pattern, replacement, description):
            success_count += 1

    # Apply pattern-based fixes
    fix_path_none_errors()
    fix_uuid_node_id_errors()
    fix_correlation_id_errors()

    print(f"\n✅ Fixed {success_count} targeted errors")
    print("🎉 Batch fixes complete!")


if __name__ == "__main__":
    main()
