#!/usr/bin/env python3
"""
Systematic fix for remaining import and type definition errors.

This script addresses the most common issues found after single-class-per-file extraction:
1. Missing imports for common types (Any, Dict, List, etc.)
2. Missing imports for pydantic components (Field, BaseModel)
3. Missing imports for omnibase_core models and enums
4. Incorrect import paths after class extraction
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Define the project root
PROJECT_ROOT = Path("/Volumes/PRO-G40/Code/omnibase_core")
SRC_DIR = PROJECT_ROOT / "src" / "omnibase_core"

# Common import patterns that need to be fixed
COMMON_TYPING_IMPORTS = {
    "Any": "from typing import Any",
    "Dict": "from typing import Dict",
    "List": "from typing import List",
    "Optional": "from typing import Optional",
    "Union": "from typing import Union",
    "Callable": "from typing import Callable",
    "TypeVar": "from typing import TypeVar",
    "Generic": "from typing import Generic",
    "Literal": "from typing import Literal",
}

COMMON_PYDANTIC_IMPORTS = {
    "BaseModel": "from pydantic import BaseModel",
    "Field": "from pydantic import Field",
    "ValidationInfo": "from pydantic import ValidationInfo",
    "field_validator": "from pydantic import field_validator",
    "model_validator": "from pydantic import model_validator",
}

STANDARD_LIBRARY_IMPORTS = {
    "json": "import json",
    "uuid": "import uuid",
    "datetime": "from datetime import datetime",
    "pathlib": "from pathlib import Path",
}

# Model to import mapping (simplified)
MODEL_IMPORTS = {
    "ModelBaseResult": "from omnibase_core.models.core.model_base_result import ModelBaseResult",
    "ModelWorkflow": "from omnibase_core.models.core.model_workflow import ModelWorkflow",
    "ModelNodeServiceConfig": "from omnibase_core.models.configuration.model_node_service_config import ModelNodeServiceConfig",
    "ModelSecretConfig": "from omnibase_core.models.configuration.model_secret_config import ModelSecretConfig",
    "ModelSecretManager": "from omnibase_core.models.security.model_secret_manager import ModelSecretManager",
    "ModelOnexEvent": "from omnibase_core.models.core.model_onex_event import ModelOnexEvent",
    "ModelDiscoveryFilters": "from omnibase_core.models.core.model_discovery_filters import ModelDiscoveryFilters",
    "ModelSemVer": "from omnibase_core.models.core.model_sem_ver import ModelSemVer",
    "ModelCustomFields": "from omnibase_core.models.core.model_custom_fields import ModelCustomFields",
    "ModelCoreErrorCode": "from omnibase_core.errors.error_codes import ModelCoreErrorCode",
    "ModelOnexError": "from omnibase_core.errors.error_codes import ModelOnexError",
    "ModelErrorContext": "from omnibase_core.models.common.model_error_context import ModelErrorContext",
    "ModelSchemaValue": "from omnibase_core.models.common.model_schema_value import ModelSchemaValue",
    "EnumCliValueType": "from omnibase_core.enums.enum_cli_value_type import EnumCliValueType",
}

# Constants to import mapping
CONSTANT_IMPORTS = {
    "TOOL_DISCOVERY_REQUEST": "from omnibase_core.constants.constants_contract_fields import TOOL_DISCOVERY_REQUEST",
    "NODE_INTROSPECTION_EVENT": "from omnibase_core.constants.constants_contract_fields import NODE_INTROSPECTION_EVENT",
}

# Utility functions mapping
UTILITY_IMPORTS = {
    "serialize_data_to_yaml": "from omnibase_core.utils.util_serialization import serialize_data_to_yaml",
}


def read_file(file_path: Path) -> str:
    """Read file content."""
    try:
        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ""


def write_file(file_path: Path, content: str) -> bool:
    """Write file content."""
    try:
        file_path.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"Error writing {file_path}: {e}")
        return False


def analyze_imports(
    content: str, file_path: Path
) -> Tuple[Set[str], Set[str], Set[str]]:
    """Analyze what imports are needed based on content."""
    needed_typing = set()
    needed_pydantic = set()
    needed_models = set()
    needed_constants = set()
    needed_utilities = set()
    needed_standard = set()

    lines = content.split("\n")

    for line in lines:
        # Skip comments and docstrings
        line = line.strip()
        if line.startswith("#") or line.startswith('"""') or line.startswith("'''"):
            continue

        # Check for typing usage
        for typo, import_stmt in COMMON_TYPING_IMPORTS.items():
            if typo in line and import_stmt not in content:
                needed_typing.add(typo)

        # Check for pydantic usage
        for pydantic_item, import_stmt in COMMON_PYDANTIC_IMPORTS.items():
            if pydantic_item in line and import_stmt not in content:
                needed_pydantic.add(pydantic_item)

        # Check for model usage
        for model, import_stmt in MODEL_IMPORTS.items():
            if model in line and import_stmt not in content:
                needed_models.add(model)

        # Check for constant usage
        for const, import_stmt in CONSTANT_IMPORTS.items():
            if const in line and import_stmt not in content:
                needed_constants.add(const)

        # Check for utility usage
        for util, import_stmt in UTILITY_IMPORTS.items():
            if util in line and import_stmt not in content:
                needed_utilities.add(util)

        # Check for standard library usage
        for std, import_stmt in STANDARD_LIBRARY_IMPORTS.items():
            if std in line and import_stmt not in content:
                needed_standard.add(std)

    return (
        needed_typing,
        needed_pydantic,
        needed_models,
        needed_constants,
        needed_utilities,
        needed_standard,
    )


def add_missing_imports(content: str, file_path: Path) -> str:
    """Add missing imports to a file."""
    # Analyze what imports are needed
    (
        needed_typing,
        needed_pydantic,
        needed_models,
        needed_constants,
        needed_utilities,
        needed_standard,
    ) = analyze_imports(content, file_path)

    if not any(
        [
            needed_typing,
            needed_pydantic,
            needed_models,
            needed_constants,
            needed_utilities,
            needed_standard,
        ]
    ):
        return content  # No imports needed

    lines = content.split("\n")
    new_lines = []

    # Find where to insert imports (after any existing imports or after __future__ imports)
    insert_position = 0
    future_import_found = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("from __future__ import"):
            future_import_found = True
            insert_position = i + 1
        elif stripped.startswith("from typing import") or stripped.startswith("import"):
            insert_position = i + 1
        elif stripped.startswith("from pydantic import"):
            insert_position = i + 1
        elif stripped.startswith("from omnibase_core"):
            insert_position = i + 1
        elif (
            stripped
            and not stripped.startswith("#")
            and not stripped.startswith('"""')
            and not stripped.startswith("'''")
        ):
            # We've reached the end of imports
            break

    # Insert the original lines up to insert_position
    new_lines.extend(lines[:insert_position])

    # Add empty line if needed
    if insert_position > 0 and new_lines[-1].strip():
        new_lines.append("")

    # Add typing imports
    if needed_typing:
        typing_imports = [COMMON_TYPING_IMPORTS[t] for t in sorted(needed_typing)]
        new_lines.append(
            "from typing import "
            + ", ".join(t.split("from typing import ")[1] for t in typing_imports)
        )

    # Add standard library imports
    if needed_standard:
        for std in sorted(needed_standard):
            new_lines.append(STANDARD_LIBRARY_IMPORTS[std])

    # Add pydantic imports
    if needed_pydantic:
        pydantic_imports = [COMMON_PYDANTIC_IMPORTS[p] for p in sorted(needed_pydantic)]
        for imp in pydantic_imports:
            new_lines.append(imp)

    # Add model imports
    if needed_models:
        for model in sorted(needed_models):
            new_lines.append(MODEL_IMPORTS[model])

    # Add constant imports
    if needed_constants:
        for const in sorted(needed_constants):
            new_lines.append(CONSTANT_IMPORTS[const])

    # Add utility imports
    if needed_utilities:
        for util in sorted(needed_utilities):
            new_lines.append(UTILITY_IMPORTS[util])

    # Add empty line if needed
    if new_lines[-1].strip():
        new_lines.append("")

    # Add the rest of the original lines
    new_lines.extend(lines[insert_position:])

    return "\n".join(new_lines)


def fix_future_import_position(content: str) -> str:
    """Ensure __future__ imports are at the very beginning."""
    lines = content.split("\n")

    # Find __future__ imports
    future_imports = []
    other_lines = []
    future_import_found = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("from __future__ import"):
            future_imports.append(line)
            future_import_found = True
        else:
            other_lines.append(line)

    if future_import_found:
        # Remove any empty lines at the beginning
        while other_lines and other_lines[0].strip() == "":
            other_lines.pop(0)

        # Combine future imports first, then the rest
        result = future_imports + [""] + other_lines
        return "\n".join(result)

    return content


def process_file(file_path: Path) -> bool:
    """Process a single file."""
    if not file_path.exists():
        return False

    print(f"Processing {file_path.relative_to(PROJECT_ROOT)}")

    # Read the file
    content = read_file(file_path)
    if not content:
        return False

    # Fix __future__ import position
    content = fix_future_import_position(content)

    # Add missing imports
    content = add_missing_imports(content, file_path)

    # Write back
    return write_file(file_path, content)


def process_python_files(directory: Path) -> List[Path]:
    """Process all Python files in a directory."""
    processed_files = []

    for py_file in directory.rglob("*.py"):
        if py_file.is_file():
            if process_file(py_file):
                processed_files.append(py_file)

    return processed_files


def main():
    """Main function."""
    print("Starting systematic import fix...")

    # Process all Python files in src directory
    processed = process_python_files(SRC_DIR)

    print(f"Processed {len(processed)} files")

    # Run mypy to check progress
    print("\nRunning mypy to check progress...")
    os.system(
        "cd /Volumes/PRO-G40/Code/omnibase_core && poetry run mypy src/omnibase_core/ --no-error-summary | head -20"
    )


if __name__ == "__main__":
    main()
