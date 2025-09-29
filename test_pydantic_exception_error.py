#!/usr/bin/env python3
"""
Test script to find models with Exception type fields that cause Pydantic schema generation errors.
"""

import importlib
import os
import sys
from pathlib import Path
from typing import Any

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))


def find_models_with_exception_fields():
    """Find and test models for Exception field schema generation errors."""
    models_dir = src_path / "omnibase_core" / "models"
    problematic_models = []
    working_models = []

    # Walk through all Python files in models directory
    for py_file in models_dir.glob("**/*.py"):
        if py_file.name.startswith("__"):
            continue

        relative_path = py_file.relative_to(src_path)
        module_name = str(relative_path).replace("/", ".").replace(".py", "")

        try:
            module = importlib.import_module(module_name)

            # Find BaseModel classes in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)

                if (
                    hasattr(attr, "__mro__")
                    and any("BaseModel" in str(base) for base in attr.__mro__)
                    and attr_name != "BaseModel"
                ):

                    try:
                        # Try to generate schema
                        schema = attr.model_json_schema()
                        working_models.append(f"{module_name}.{attr_name}")

                        # Check if any fields have Exception annotations
                        if hasattr(attr, "model_fields"):
                            for field_name, field_info in attr.model_fields.items():
                                field_annotation = getattr(
                                    field_info, "annotation", None
                                )
                                if field_annotation and "Exception" in str(
                                    field_annotation
                                ):
                                    print(
                                        f"Found Exception field in {module_name}.{attr_name}: {field_name} -> {field_annotation}"
                                    )

                    except Exception as e:
                        if "pydantic-core schema" in str(e) and "Exception" in str(e):
                            problematic_models.append(f"{module_name}.{attr_name}: {e}")
                            print(f"❌ FOUND THE PROBLEM: {module_name}.{attr_name}")
                            print(f"   Error: {e}")

                            # Try to find the problematic field
                            if hasattr(attr, "model_fields"):
                                for field_name, field_info in attr.model_fields.items():
                                    field_annotation = getattr(
                                        field_info, "annotation", None
                                    )
                                    if field_annotation and "Exception" in str(
                                        field_annotation
                                    ):
                                        print(
                                            f"   Problematic field: {field_name} -> {field_annotation}"
                                        )
                        else:
                            # Other error, skip
                            pass

        except Exception as e:
            # Import error or other issue, skip
            pass

    print(f"\n✅ Working models: {len(working_models)}")
    print(f"❌ Problematic models: {len(problematic_models)}")

    if problematic_models:
        print("\nProblematic models:")
        for model in problematic_models:
            print(f"  - {model}")

    return problematic_models


if __name__ == "__main__":
    find_models_with_exception_fields()
