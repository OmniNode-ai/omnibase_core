#!/usr/bin/env python3
"""Fix EnumComputationType assignment issues."""

from pathlib import Path


def fix_numeric_computation():
    """Fix model_numeric_computation_output.py"""
    file_path = Path(
        "/Volumes/PRO-G40/Code/omnibase_core/src/omnibase_core/models/operations/model_numeric_computation_output.py"
    )
    content = file_path.read_text()

    # Replace TYPE_CHECKING import with direct import
    content = content.replace(
        "from typing import TYPE_CHECKING, Any\n\nfrom pydantic import Field\n\nfrom omnibase_core.models.operations.model_computation_output_base import (\n    ModelComputationOutputBase,\n)\n\nif TYPE_CHECKING:\n    from omnibase_core.enums.enum_computation_type import EnumComputationType",
        "from typing import Any\n\nfrom pydantic import Field\n\nfrom omnibase_core.enums.enum_computation_type import EnumComputationType\nfrom omnibase_core.models.operations.model_computation_output_base import (\n    ModelComputationOutputBase,\n)",
    )

    # Replace string default with enum
    content = content.replace(
        '    computation_type: "EnumComputationType" = Field(\n        default="numeric",',
        "    computation_type: EnumComputationType = Field(\n        default=EnumComputationType.NUMERIC,",
    )

    file_path.write_text(content)
    print(f"Fixed: {file_path}")


def fix_structured_computation():
    """Fix model_structured_computation_output.py"""
    file_path = Path(
        "/Volumes/PRO-G40/Code/omnibase_core/src/omnibase_core/models/operations/model_structured_computation_output.py"
    )
    content = file_path.read_text()

    # Replace TYPE_CHECKING import with direct import
    content = content.replace(
        "from typing import TYPE_CHECKING, Any\n\nfrom pydantic import Field\n\nfrom omnibase_core.models.operations.model_computation_output_base import (\n    ModelComputationOutputBase,\n)\n\nif TYPE_CHECKING:\n    from omnibase_core.enums.enum_computation_type import EnumComputationType",
        "from typing import Any\n\nfrom pydantic import Field\n\nfrom omnibase_core.enums.enum_computation_type import EnumComputationType\nfrom omnibase_core.models.operations.model_computation_output_base import (\n    ModelComputationOutputBase,\n)",
    )

    # Replace string default with enum
    content = content.replace(
        '    computation_type: "EnumComputationType" = Field(\n        default="structured",',
        "    computation_type: EnumComputationType = Field(\n        default=EnumComputationType.STRUCTURED,",
    )

    file_path.write_text(content)
    print(f"Fixed: {file_path}")


def fix_binary_computation():
    """Fix model_binary_computation_output.py"""
    file_path = Path(
        "/Volumes/PRO-G40/Code/omnibase_core/src/omnibase_core/models/operations/model_binary_computation_output.py"
    )
    content = file_path.read_text()

    # Replace TYPE_CHECKING import with direct import
    content = content.replace(
        "from typing import TYPE_CHECKING, Any\n\nfrom pydantic import Field\n\nfrom omnibase_core.models.operations.model_computation_output_base import (\n    ModelComputationOutputBase,\n)\n\nif TYPE_CHECKING:\n    from omnibase_core.enums.enum_computation_type import EnumComputationType",
        "from typing import Any\n\nfrom pydantic import Field\n\nfrom omnibase_core.enums.enum_computation_type import EnumComputationType\nfrom omnibase_core.models.operations.model_computation_output_base import (\n    ModelComputationOutputBase,\n)",
    )

    # Replace string default with enum
    content = content.replace(
        '    computation_type: "EnumComputationType" = Field(\n        default="binary",',
        "    computation_type: EnumComputationType = Field(\n        default=EnumComputationType.BINARY,",
    )

    file_path.write_text(content)
    print(f"Fixed: {file_path}")


def main():
    """Main entry point."""
    fix_numeric_computation()
    fix_structured_computation()
    fix_binary_computation()
    print("\nFixed 3 files")


if __name__ == "__main__":
    main()
