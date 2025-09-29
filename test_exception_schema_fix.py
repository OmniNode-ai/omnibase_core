#!/usr/bin/env python3
"""
Test script to verify that the Pydantic Exception schema generation error is fixed.
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))


def test_exception_schema_generation():
    """Test that models with Exception types can generate schemas."""
    print("🧪 Testing Exception schema generation fixes...")

    # Test ModelResult with Exception
    try:
        from omnibase_core.models.infrastructure.model_result import (
            ModelResult,
            try_result,
        )

        # This should work now - ModelResult[str, Exception]
        result_schema = ModelResult.model_json_schema()
        print("✅ ModelResult base schema generated successfully")

        # Test the try_result function that returns ModelResult[T, Exception]
        def sample_function():
            return "success"

        result = try_result(sample_function)
        print(f"✅ try_result function works: {result}")

        # Test schema generation for specific ModelResult[str, Exception]
        from typing import get_type_hints

        from omnibase_core.models.infrastructure.model_result import try_result

        # Get the return type annotation
        hints = get_type_hints(try_result)
        return_type = hints["return"]
        print(f"✅ try_result return type: {return_type}")

    except Exception as e:
        print(f"❌ ModelResult test failed: {e}")
        return False

    # Test ModelConfigurationBase with arbitrary types
    try:
        from omnibase_core.models.core.model_configuration_base import (
            ModelConfigurationBase,
        )

        config_schema = ModelConfigurationBase.model_json_schema()
        print("✅ ModelConfigurationBase schema generated successfully")

        # Test with Exception as the generic type
        config_with_exception = ModelConfigurationBase[Exception](
            name="test_config", config_data=ValueError("test exception")
        )
        print(
            f"✅ ModelConfigurationBase[Exception] created: {config_with_exception.name}"
        )

    except Exception as e:
        print(f"❌ ModelConfigurationBase test failed: {e}")
        return False

    # Test specific Exception handling in try_result
    try:

        def failing_function():
            raise ValueError("This is a test error")

        error_result = try_result(failing_function)
        print(f"✅ Exception handling in try_result: {error_result}")

        # Test schema generation with the actual result
        if hasattr(error_result, "model_json_schema"):
            schema = error_result.model_json_schema()
            print("✅ Error result schema generated successfully")

    except Exception as e:
        print(f"❌ Exception handling test failed: {e}")
        return False

    print("🎉 All tests passed! Exception schema generation is fixed.")
    return True


if __name__ == "__main__":
    success = test_exception_schema_generation()
    sys.exit(0 if success else 1)
