#!/usr/bin/env python3
"""
Phase 3: Final fixes for remaining arg-type errors.
"""

import re
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent / "src" / "omnibase_core"


def fix_file(filepath: Path, fixes_description: str, replacements: list[tuple[str, str]]) -> bool:
    """Apply multiple text replacements to a file."""
    if not filepath.exists():
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    for old, new in replacements:
        content = content.replace(old, new)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✅ {fixes_description}")
        return True
    return False


def main():
    """Main execution."""
    print("🚀 Phase 3: Final arg-type fixes\n")
    fixes_applied = 0

    # Fix 1: Path errors in mixin files (lines that weren't caught by regex)
    print("\n📝 Fixing remaining Path(str | None) errors...")
    path_fixes = [
        (
            "mixins/mixin_node_id_from_contract.py",
            "Path None check",
            [
                ('contract_path = Path(contract_path_str)',
                 'contract_path = Path(contract_path_str or ".")')
            ]
        ),
        (
            "mixins/mixin_introspect_from_contract.py",
            "Path None check",
            [
                ('contract_path = Path(contract_path_str)',
                 'contract_path = Path(contract_path_str or ".")')
            ]
        ),
        (
            "mixins/mixin_node_setup.py",
            "Path None check + str conversion",
            [
                ('contract_path = Path(contract_path_attr)',
                 'contract_path = Path(contract_path_attr or ".")'),
                ('load_state_contract_from_file(contract_path)',
                 'load_state_contract_from_file(str(contract_path))')
            ]
        ),
        (
            "infrastructure/node_effect.py",
            "Path None check",
            [
                ('base_path = Path(base_path_str)',
                 'base_path = Path(base_path_str or ".")')
            ]
        ),
    ]

    for file_rel, desc, replacements in path_fixes:
        filepath = ROOT_DIR / file_rel
        if fix_file(filepath, desc, replacements):
            fixes_applied += 1

    # Fix 2: emit.py node_id conversions that were missed
    print("\n📝 Fixing emit.py node_id conversions...")
    filepath = ROOT_DIR / "logging" / "emit.py"
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    modified = False
    for i, line in enumerate(lines):
        # Look for ModelLogContext lines with node_id that weren't converted
        if 'ModelLogContext(' in line and i + 3 < len(lines):
            for j in range(i, min(i + 10, len(lines))):
                if 'node_id=' in lines[j] and 'UUID(' not in lines[j]:
                    # Check if it's a direct assignment without conversion
                    match = re.search(r'node_id=([a-zA-Z_][a-zA-Z0-9_]*),', lines[j])
                    if match and match.group(1) not in ['None', 'uuid4()']:
                        var_name = match.group(1)
                        lines[j] = lines[j].replace(
                            f'node_id={var_name},',
                            f'node_id=UUID({var_name}) if isinstance({var_name}, (str, UUID)) else {var_name},'
                        )
                        modified = True

    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"  ✅ Fixed emit.py node_id conversions")
        fixes_applied += 1

    # Fix 3: UUID | None → UUID with uuid4() fallback
    print("\n📝 Fixing UUID | None → UUID with fallbacks...")
    filepath = ROOT_DIR / "infrastructure" / "node_effect.py"
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find the specific lines and add fallbacks
    for i, line in enumerate(lines):
        if 'ModelTransaction(' in line and i + 1 < len(lines):
            if 'transaction_id=' in lines[i] or 'transaction_id=' in lines[i + 1]:
                # Look for the transaction_id parameter
                for j in range(i, min(i + 5, len(lines))):
                    if 'transaction_id=' in lines[j] and 'or uuid4()' not in lines[j]:
                        lines[j] = re.sub(
                            r'transaction_id=([a-zA-Z_][a-zA-Z0-9_]*)',
                            r'transaction_id=\1 or uuid4()',
                            lines[j]
                        )

        if 'ModelEffectOutput(' in line:
            # Look ahead for operation_id
            for j in range(i, min(i + 10, len(lines))):
                if 'operation_id=' in lines[j] and 'or uuid4()' not in lines[j]:
                    lines[j] = re.sub(
                        r'operation_id=([a-zA-Z_][a-zA-Z0-9_]*)',
                        r'operation_id=\1 or uuid4()',
                        lines[j]
                    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"  ✅ Fixed UUID | None fallbacks in node_effect.py")
    fixes_applied += 1

    # Fix 4: model_tooldiscoveryrequest.py str | UUID → UUID
    print("\n📝 Fixing model_tooldiscoveryrequest.py UUID conversions...")
    filepath = ROOT_DIR / "models" / "discovery" / "model_tooldiscoveryrequest.py"
    fixes = [
        (
            'node_id=node_id,',
            'node_id=UUID(node_id) if isinstance(node_id, str) else node_id,'
        ),
        (
            'requester_id=requester_id,',
            'requester_id=UUID(requester_id) if isinstance(requester_id, str) else requester_id,'
        ),
    ]
    if fix_file(filepath, "UUID conversions in tool discovery", fixes):
        fixes_applied += 1

    # Fix 5: mixin_workflow_support.py source_node_id
    print("\n📝 Fixing mixin_workflow_support.py source_node_id...")
    filepath = ROOT_DIR / "mixins" / "mixin_workflow_support.py"
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix source_node_id that can be str | Any | None → str
    original = content
    content = re.sub(
        r'source_node_id=node_id,',
        'source_node_id=str(node_id),',
        content
    )

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✅ Fixed source_node_id in mixin_workflow_support.py")
        fixes_applied += 1

    # Fix 6: Optional/None → required value fixes
    print("\n📝 Fixing Optional → required conversions...")
    optional_fixes = [
        (
            "models/configuration/model_rest_api_connection_config.py",
            "retry_config fallback",
            [
                ('retry_config=retry_config,',
                 'retry_config=retry_config or ModelRequestRetryConfig(),')
            ]
        ),
        (
            "models/core/model_typedproperties.py",
            "filter None properties",
            [
                ('properties=properties,',
                 'properties={k: v for k, v in properties.items() if v is not None},')
            ]
        ),
    ]

    for file_rel, desc, replacements in optional_fixes:
        filepath = ROOT_DIR / file_rel
        if fix_file(filepath, desc, replacements):
            fixes_applied += 1

    print(f"\n✅ Phase 3 applied {fixes_applied} fixes")
    print("🎉 Phase 3 complete!")


if __name__ == "__main__":
    main()
