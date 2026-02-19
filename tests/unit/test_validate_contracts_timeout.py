# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import importlib.util
from pathlib import Path

import pytest


def import_module_from_path(path: Path):
    spec = importlib.util.spec_from_file_location(
        "validate_contracts_module",
        str(path),
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def test_setup_timeout_handler_uses_constant_message():
    """Test that timeout utilities provide consistent error messages."""
    # Import the timeout utils module used by the validation script
    timeout_utils_path = Path("scripts/validation/timeout_utils.py").resolve()
    timeout_utils = import_module_from_path(timeout_utils_path)

    # Verify that timeout error messages are defined as constants
    assert hasattr(timeout_utils, "TIMEOUT_ERROR_MESSAGES")
    assert isinstance(timeout_utils.TIMEOUT_ERROR_MESSAGES, dict)

    # Check that validation-specific messages exist
    assert "validation" in timeout_utils.TIMEOUT_ERROR_MESSAGES
    assert "file_discovery" in timeout_utils.TIMEOUT_ERROR_MESSAGES

    # Test timeout context manager with constant message
    with pytest.raises(timeout_utils.TimeoutError) as ei:
        with timeout_utils.timeout_context("validation", duration=0.001):
            import time

            time.sleep(0.1)  # Sleep longer than timeout

    # Verify the error message comes from the constants
    error_msg = str(ei.value)
    expected_msg = timeout_utils.TIMEOUT_ERROR_MESSAGES["validation"]
    assert expected_msg in error_msg


def test_legacy_setup_timeout_handler_compatibility():
    """Test that legacy setup_timeout_handler function exists for compatibility."""
    module_path = Path("scripts/validation/validate-contracts.py").resolve()
    module = import_module_from_path(module_path)

    # Verify the legacy function exists and doesn't crash
    assert hasattr(module, "setup_timeout_handler")
    module.setup_timeout_handler()  # Should not raise any exceptions
