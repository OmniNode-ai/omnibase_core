#!/usr/bin/env python3
"""
Cross-platform timeout compatibility test.
Verifies timeout functionality works on both Windows and Unix systems.
"""

import sys
import threading
import time
from pathlib import Path

# Add validation directory to path to import timeout_utils
sys.path.insert(0, str(Path(__file__).parent))

from timeout_utils import (
    DEFAULT_TIMEOUTS,
    TIMEOUT_ERROR_MESSAGES,
    CrossPlatformTimeout,
    UnixSignalTimeout,
    get_platform_info,
    timeout_context,
    with_timeout,
)
from timeout_utils import TimeoutError as CustomTimeoutError


def test_cross_platform_timeout():
    """Test CrossPlatformTimeout works on all platforms."""
    print("Testing CrossPlatformTimeout...")

    # Test timeout occurs
    try:
        with CrossPlatformTimeout(1, "Test timeout"):
            time.sleep(2)
        assert False, "Should have timed out"
    except CustomTimeoutError as e:
        assert str(e) == "Test timeout"
        print("  ✅ Timeout correctly raised")

    # Test normal completion
    try:
        with CrossPlatformTimeout(2, "Test timeout"):
            time.sleep(0.5)
        print("  ✅ Normal completion works")
    except CustomTimeoutError:
        assert False, "Should not have timed out"


def test_unix_signal_timeout():
    """Test UnixSignalTimeout (falls back to threading on Windows)."""
    print("Testing UnixSignalTimeout...")

    # Test timeout occurs
    try:
        with UnixSignalTimeout(1, "Unix test timeout"):
            time.sleep(2)
        assert False, "Should have timed out"
    except CustomTimeoutError as e:
        assert str(e) == "Unix test timeout"
        print("  ✅ Unix timeout correctly raised")

    # Test normal completion
    try:
        with UnixSignalTimeout(2, "Unix test timeout"):
            time.sleep(0.5)
        print("  ✅ Unix normal completion works")
    except CustomTimeoutError:
        assert False, "Should not have timed out"


def test_timeout_context():
    """Test timeout_context convenience function."""
    print("Testing timeout_context...")

    # Test with predefined operation
    try:
        with timeout_context("validation", 1):
            time.sleep(2)
        assert False, "Should have timed out"
    except CustomTimeoutError as e:
        expected_msg = TIMEOUT_ERROR_MESSAGES["validation"]
        assert str(e) == expected_msg
        print("  ✅ Predefined operation timeout works")

    # Test with custom duration
    try:
        with timeout_context("general", 1):
            time.sleep(0.5)
        print("  ✅ Custom duration works")
    except CustomTimeoutError:
        assert False, "Should not have timed out"


def test_cleanup_function():
    """Test cleanup function is called on timeout."""
    print("Testing cleanup function...")

    cleanup_called = threading.Event()

    def cleanup():
        cleanup_called.set()

    try:
        with timeout_context("general", 1, cleanup_func=cleanup):
            time.sleep(2)
        assert False, "Should have timed out"
    except CustomTimeoutError:
        # Give cleanup function time to execute
        assert cleanup_called.wait(timeout=1), (
            "Cleanup function should have been called"
        )
        print("  ✅ Cleanup function called on timeout")


def test_with_timeout_decorator():
    """Test @with_timeout decorator."""
    print("Testing @with_timeout decorator...")

    @with_timeout(1, "Decorator timeout")
    def slow_function():
        time.sleep(2)
        return "completed"

    @with_timeout(2, "Decorator timeout")
    def fast_function():
        time.sleep(0.5)
        return "completed"

    # Test timeout
    try:
        slow_function()
        assert False, "Should have timed out"
    except CustomTimeoutError as e:
        assert str(e) == "Decorator timeout"
        print("  ✅ Decorator timeout works")

    # Test normal completion
    try:
        result = fast_function()
        assert result == "completed"
        print("  ✅ Decorator normal completion works")
    except CustomTimeoutError:
        assert False, "Should not have timed out"


def test_error_message_constants():
    """Test that all error messages are properly defined."""
    print("Testing error message constants...")

    required_messages = [
        "validation",
        "file_discovery",
        "directory_scan",
        "file_processing",
        "general",
        "import_validation",
        "type_checking",
        "linting",
    ]

    for msg_type in required_messages:
        assert msg_type in TIMEOUT_ERROR_MESSAGES, (
            f"Missing error message for {msg_type}"
        )
        assert isinstance(TIMEOUT_ERROR_MESSAGES[msg_type], str), (
            f"Error message for {msg_type} must be string"
        )
        assert len(TIMEOUT_ERROR_MESSAGES[msg_type]) > 0, (
            f"Error message for {msg_type} cannot be empty"
        )

    print("  ✅ All required error messages are defined")


def test_default_timeouts():
    """Test that default timeout values are reasonable."""
    print("Testing default timeout values...")

    required_timeouts = [
        "file_discovery",
        "validation",
        "directory_scan",
        "import_check",
        "type_check",
        "linting",
    ]

    for timeout_type in required_timeouts:
        assert timeout_type in DEFAULT_TIMEOUTS, (
            f"Missing default timeout for {timeout_type}"
        )
        timeout_val = DEFAULT_TIMEOUTS[timeout_type]
        assert isinstance(timeout_val, int), (
            f"Timeout for {timeout_type} must be integer"
        )
        assert timeout_val > 0, f"Timeout for {timeout_type} must be positive"
        assert timeout_val <= 600, (
            f"Timeout for {timeout_type} should be reasonable (≤ 10 minutes)"
        )

    print("  ✅ All default timeouts are reasonable")


def test_platform_info():
    """Test platform information gathering."""
    print("Testing platform info...")

    info = get_platform_info()
    required_keys = [
        "platform",
        "os_name",
        "has_sigalrm",
        "threading_support",
        "python_version",
    ]

    for key in required_keys:
        assert key in info, f"Missing platform info key: {key}"

    # Verify data types
    assert isinstance(info["platform"], str)
    assert isinstance(info["os_name"], str)
    assert isinstance(info["has_sigalrm"], bool)
    assert isinstance(info["threading_support"], bool)

    print(f"  ✅ Platform info: {info['platform']} ({info['os_name']})")
    print(f"      SIGALRM support: {info['has_sigalrm']}")
    print(f"      Threading support: {info['threading_support']}")


def test_ruff_try003_compliance():
    """Test that we're using constants for exception messages."""
    print("Testing Ruff TRY003 compliance...")

    # Test that timeout_context uses constants
    try:
        with timeout_context("validation", 0.1):
            time.sleep(0.2)
    except CustomTimeoutError as e:
        expected = TIMEOUT_ERROR_MESSAGES["validation"]
        assert str(e) == expected, f"Expected '{expected}', got '{e!s}'"
        print("  ✅ timeout_context uses constants for error messages")

    # Test that CrossPlatformTimeout can use custom messages
    try:
        with CrossPlatformTimeout(0.1, TIMEOUT_ERROR_MESSAGES["file_discovery"]):
            time.sleep(0.2)
    except CustomTimeoutError as e:
        expected = TIMEOUT_ERROR_MESSAGES["file_discovery"]
        assert str(e) == expected
        print("  ✅ CrossPlatformTimeout accepts constant messages")


def run_all_tests():
    """Run all timeout compatibility tests."""
    print("🧪 Cross-Platform Timeout Compatibility Tests")
    print("=" * 50)

    # Show platform info first
    platform_info = get_platform_info()
    print(f"Platform: {platform_info['platform']}")
    print(f"OS: {platform_info['os_name']}")
    print(f"SIGALRM available: {platform_info['has_sigalrm']}")
    print(f"Threading support: {platform_info['threading_support']}")
    print()

    tests = [
        test_cross_platform_timeout,
        test_unix_signal_timeout,
        test_timeout_context,
        test_cleanup_function,
        test_with_timeout_decorator,
        test_error_message_constants,
        test_default_timeouts,
        test_platform_info,
        test_ruff_try003_compliance,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            failed += 1
        print()

    print(f"📊 Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("✅ All timeout compatibility tests PASSED!")
        print("🎉 Cross-platform timeout handling is working correctly!")
        return 0
    else:
        print("❌ Some tests FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
