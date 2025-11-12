#!/usr/bin/env python3
"""
Fix no-redef errors by removing duplicate imports.

This script fixes MyPy [no-redef] errors caused by importing the same symbol
from multiple locations.
"""

import re
import sys
from pathlib import Path


def fix_duplicate_imports(file_path: Path) -> bool:
    """Fix duplicate imports in a file."""
    content = file_path.read_text()
    original_content = content

    # Pattern 1: Remove ModelOnexError from error_codes import when already imported
    # from model_onex_error
    if "from omnibase_core.errors.model_onex_error import ModelOnexError" in content:
        # Remove ModelOnexError from error_codes imports
        content = re.sub(
            r"from omnibase_core\.errors\.error_codes import \(\s*"
            r"([^)]*?)\s*ModelOnexError,?\s*([^)]*?)\s*\)",
            lambda m: (
                f"from omnibase_core.errors.error_codes import \n{m.group(1).strip()}{m.group(2).strip()}\n)"
                if m.group(1).strip() or m.group(2).strip()
                else ""
            ),
            content,
            flags=re.MULTILINE | re.DOTALL,
        )

        # Also handle single-line imports
        content = re.sub(
            r"from omnibase_core\.errors\.error_codes import ([^,\n]*,\s*)?ModelOnexError(,\s*[^\n]*)?",
            lambda m: f'from omnibase_core.errors.error_codes import {m.group(1) or ""}{m.group(2) or ""}'.strip.rstrip(
                "import "
            ).rstrip(
                ","
            ),
            content,
        )

    # Pattern 2: Remove ModelSchemaValue from imports when already imported
    if (
        "from omnibase_core.models.common.model_schema_value import ModelSchemaValue"
        in content
    ):
        content = re.sub(
            r"from omnibase_core\.models\.core\.model_schema import \(\s*"
            r"([^)]*?)\s*ModelSchemaValue,?\s*([^)]*?)\s*\)",
            lambda m: (
                f"from omnibase_core.models.core.model_schema import (\n{m.group(1).strip()}{m.group(2).strip()}\n)"
                if m.group(1).strip() or m.group(2).strip()
                else ""
            ),
            content,
            flags=re.MULTILINE | re.DOTALL,
        )

        # Single-line version
        content = re.sub(
            r"from omnibase_core\.models\.core\.model_schema import ([^,\n]*,\s*)?ModelSchemaValue(,\s*[^\n]*)?",
            lambda m: f'from omnibase_core.models.core.model_schema import {m.group(1) or ""}{m.group(2) or ""}'.strip()
            .rstrip("import ")
            .rstrip(","),
            content,
        )

    # Clean up empty imports
    content = re.sub(r"from [^\n]+ import \(\s*\)", "", content)
    content = re.sub(r"from [^\n]+ import\s*$", "", content, flags=re.MULTILINE)

    if content != original_content:
        file_path.write_text(content)
        return True
    return False


def main():
    """Main entry point."""
    # Files with ModelOnexError duplicate imports
    model_onex_error_files = [
        "src/omnibase_core/models/operations/model_workflow_instance_metadata.py",
        "src/omnibase_core/models/operations/model_event_metadata.py",
        "src/omnibase_core/models/operations/model_effect_parameter_value.py",
        "src/omnibase_core/models/core/model_multi_doc_generation_result.py",
        "src/omnibase_core/models/core/model_item_summary.py",
        "src/omnibase_core/models/core/model_generic_collection_summary.py",
        "src/omnibase_core/models/operations/model_operation_parameters_base.py",
        "src/omnibase_core/models/core/model_custom_properties.py",
        "src/omnibase_core/models/operations/model_computation_input_data.py",
        "src/omnibase_core/models/core/model_typed_accessor.py",
        "src/omnibase_core/models/operations/model_system_metadata.py",
        "src/omnibase_core/models/operations/model_execution_metadata.py",
        "src/omnibase_core/models/core/model_configuration_base.py",
        "src/omnibase_core/models/operations/model_operation_payload.py",
        "src/omnibase_core/models/infrastructure/model_conflict_resolver.py",
        "src/omnibase_core/models/core/model_validation_error_factory.py",
        "src/omnibase_core/mixins/mixin_registry_injection.py",
        "src/omnibase_core/mixins/mixin_fail_fast.py",
        "src/omnibase_core/decorators/error_handling.py",
        "src/omnibase_core/models/core/model_state_contract.py",
        "src/omnibase_core/models/security/model_signature_chain.py",
        "src/omnibase_core/infrastructure/node_base.py",
        "src/omnibase_core/mixins/mixin_contract_state_reducer.py",
        "src/omnibase_core/infrastructure/node_core_base.py",
        "src/omnibase_core/container/container_service_resolver.py",
        "src/omnibase_core/infrastructure/node_reducer.py",
        "src/omnibase_core/infrastructure/node_effect.py",
        "src/omnibase_core/infrastructure/node_compute.py",
        "src/omnibase_core/infrastructure/node_orchestrator.py",
        "src/omnibase_core/models/configuration/model_metadata_block.py",
        "src/omnibase_core/mixins/mixin_event_bus.py",
    ]

    root = Path("/Volumes/PRO-G40/Code/omnibase_core")
    fixed_count = 0

    for file_path in model_onex_error_files:
        full_path = root / file_path
        if full_path.exists():
            if fix_duplicate_imports(full_path):
                print(f"✓ Fixed: {file_path}")
                fixed_count += 1
        else:
            print(f"✗ Not found: {file_path}")

    print(f"\n✓ Fixed {fixed_count} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
