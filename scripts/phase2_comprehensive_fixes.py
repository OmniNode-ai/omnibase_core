#!/usr/bin/env python3
"""
Phase 2: Comprehensive fixes for remaining arg-type errors.
Handles Path, UUID, logging, and type conversion issues.
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

ROOT_DIR = Path(__file__).parent.parent / "src" / "omnibase_core"


def apply_regex_replacement(
    filepath: Path, patterns: list[tuple[str, str]], desc: str
) -> int:
    """Apply multiple regex replacements to a file."""
    if not filepath.exists():
        return 0

    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    original = content
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  ✅ {desc}")
        return 1
    return 0


def main():
    """Main execution."""
    print("🚀 Phase 2: Comprehensive arg-type fixes\n")
    fixes_applied = 0

    # Fix 1: Path(str | None) errors - Add None checks
    print("\n📝 Fixing Path(str | None) errors...")
    path_files = [
        "infrastructure/node_effect.py",
        "mixins/mixin_node_id_from_contract.py",
        "mixins/mixin_introspect_from_contract.py",
        "mixins/mixin_node_setup.py",
    ]
    for file_rel in path_files:
        filepath = ROOT_DIR / file_rel
        if not filepath.exists():
            continue

        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        original = content
        # Pattern: Path(variable) where variable is str | None
        # Replace with: Path(variable or ".")
        content = re.sub(
            r"Path\((\w+)\)(\s*#.*)?$",
            r'Path(\1 or ".")\2',
            content,
            flags=re.MULTILINE,
        )

        if content != original:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  ✅ Fixed Path None checks in {file_rel}")
            fixes_applied += 1

    # Fix 2: emit_log_event_sync MixinLogData → str conversions
    print("\n📝 Fixing emit_log_event_sync signature issues...")
    filepath = ROOT_DIR / "mixins" / "mixin_event_bus.py"
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    original = content
    # The emit_log_event_sync signature is: (level, message, correlation_id, ...)
    # But MixinLogData is being passed as message
    # We need to pass message string and use data param for MixinLogData

    # Fix _log_info
    content = re.sub(
        r"emit_log_event\(\s*LogLevel\.INFO,\s*MixinLogData\(([^)]+)\),?\s*\)",
        r'emit_log_event(LogLevel.INFO, msg, uuid4(), data={"pattern": pattern, "node_name": self.get_node_name()})',
        content,
    )

    # Fix _log_warn
    content = re.sub(
        r"emit_log_event\(\s*LogLevel\.WARNING,\s*MixinLogData\(([^)]+)\),?\s*\)",
        r'emit_log_event(LogLevel.WARNING, msg, uuid4(), data={"pattern": pattern, "node_name": self.get_node_name()})',
        content,
    )

    # Fix _log_error
    content = re.sub(
        r"emit_log_event\(\s*LogLevel\.ERROR,\s*MixinLogData\(\s*pattern=pattern,\s*node_name=self\.get_node_name\(\),\s*error=[^)]+\),?\s*\)",
        r'emit_log_event(LogLevel.ERROR, msg, uuid4(), data={"pattern": pattern, "node_name": self.get_node_name(), "error": None if error is None else repr(error)})',
        content,
    )

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        # Need to add uuid4 import
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        if "from uuid import uuid4" not in content:
            content = content.replace(
                "from pydantic import BaseModel, ConfigDict, Field, StrictStr",
                "from pydantic import BaseModel, ConfigDict, Field, StrictStr\nfrom uuid import UUID, uuid4",
            )
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        print("  ✅ Fixed emit_log_event_sync calls in mixin_event_bus.py")
        fixes_applied += 3

    # Fix 3: ModelLogContext node_id conversions (Any | str → UUID | None)
    print("\n📝 Fixing ModelLogContext node_id conversions...")
    log_context_files = [
        "mixins/mixin_event_handler.py",
        "mixins/mixin_introspection_publisher.py",
        "logging/emit.py",
    ]
    for file_rel in log_context_files:
        filepath = ROOT_DIR / file_rel
        if not filepath.exists():
            continue

        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        original = content
        # Pattern: node_id=variable where variable is str or Any
        # Replace with: node_id=UUID(variable) if isinstance(variable, str) else variable
        content = re.sub(
            r"node_id=([a-zA-Z_][a-zA-Z0-9_]*),",
            r"node_id=UUID(\1) if isinstance(\1, str) else \1,",
            content,
        )

        if content != original:
            # Ensure UUID is imported
            if "from uuid import UUID" not in content:
                content = re.sub(
                    r"(from uuid import [^\n]+)",
                    (
                        r"\1, UUID"
                        if "from uuid import" in content
                        else "from uuid import UUID\n\1"
                    ),
                    content,
                )
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  ✅ Fixed ModelLogContext node_id in {file_rel}")
            fixes_applied += 1

    # Fix 4: str → UUID for node_id in various events
    print("\n📝 Fixing event node_id str → UUID...")
    event_files = [
        ("mixins/mixin_event_listener.py", [(924, "node_id"), (995, "node_id")]),
        ("mixins/mixin_event_bus.py", [(255, "node_id")]),
        (
            "models/discovery/model_introspection_response_event.py",
            [(143, "node_id"), (183, "node_id"), (227, "node_id")],
        ),
    ]
    for file_rel, line_fixes in event_files:
        filepath = ROOT_DIR / file_rel
        if not filepath.exists():
            continue

        with open(filepath, encoding="utf-8") as f:
            lines = f.readlines()

        modified = False
        for line_num, field_name in line_fixes:
            if line_num > len(lines):
                continue
            line_idx = line_num - 1
            line = lines[line_idx]

            # Fix node_id=var to node_id=UUID(var) if isinstance(var, str) else var
            if f"{field_name}=" in line and "UUID(" not in line:
                # Extract the variable name
                match = re.search(rf"{field_name}=([a-zA-Z_][a-zA-Z0-9_\.]*)", line)
                if match:
                    var_name = match.group(1)
                    lines[line_idx] = line.replace(
                        f"{field_name}={var_name}",
                        f"{field_name}=UUID({var_name}) if isinstance({var_name}, str) else {var_name}",
                    )
                    modified = True

        if modified:
            with open(filepath, "w", encoding="utf-8") as f:
                f.writelines(lines)
            print(f"  ✅ Fixed node_id conversions in {file_rel}")
            fixes_applied += len(line_fixes)

    # Fix 5: getattr default value str → UUID
    print("\n📝 Fixing getattr default values...")
    filepath = ROOT_DIR / "mixins" / "mixin_node_executor.py"
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    original = content
    # Pattern: getattr(..., "str_default") where UUID is expected
    # Common pattern: getattr(obj, attr, "uuid_string")
    content = re.sub(
        r'getattr\(([^,]+),\s*([^,]+),\s*"([a-f0-9\-]{36})"\)',
        r'getattr(\1, \2, UUID("\3"))',
        content,
    )
    # Pattern: getattr(..., "unknown") where UUID is expected
    content = re.sub(
        r'getattr\(([^,]+),\s*"correlation_id",\s*"([^"]+)"\)',
        r'getattr(\1, "correlation_id", None)',
        content,
    )

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print("  ✅ Fixed getattr defaults in mixin_node_executor.py")
        fixes_applied += 1

    # Fix 6: UUID | None → UUID with fallback
    print("\n📝 Fixing UUID | None → UUID conversions...")
    uuid_none_files = [
        (
            "infrastructure/node_effect.py",
            [
                (404, "ModelTransaction", "transaction_id"),
                (451, "operation_id", "operation_id"),
            ],
        ),
    ]
    for file_rel, line_fixes in uuid_none_files:
        filepath = ROOT_DIR / file_rel
        if not filepath.exists():
            continue

        with open(filepath, encoding="utf-8") as f:
            lines = f.readlines()

        modified = False
        for line_num, context, field_name in line_fixes:
            if line_num > len(lines):
                continue
            line_idx = line_num - 1
            line = lines[line_idx]

            # Add "or uuid4()" for Optional UUID fields
            if field_name in line and "or uuid4()" not in line:
                match = re.search(rf"{field_name}=([a-zA-Z_][a-zA-Z0-9_\.]*)", line)
                if match:
                    var_name = match.group(1)
                    lines[line_idx] = line.replace(
                        f"{field_name}={var_name}",
                        f"{field_name}={var_name} or uuid4()",
                    )
                    modified = True

        if modified:
            with open(filepath, "w", encoding="utf-8") as f:
                f.writelines(lines)
            print(f"  ✅ Fixed UUID | None conversions in {file_rel}")
            fixes_applied += 1

    print(f"\n✅ Phase 2 applied {fixes_applied} fixes")
    print("🎉 Phase 2 complete!")


if __name__ == "__main__":
    main()
