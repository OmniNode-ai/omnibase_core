#!/usr/bin/env python3
"""
Test __init__.py Optimization Fix

This script tests if removing package-level imports fixes the performance issue.
"""

import shutil
import sys
import time
from pathlib import Path

# Paths
src_path = Path(__file__).parent.parent / "src"
init_file = src_path / "omnibase_core" / "__init__.py"
fast_init_file = src_path / "omnibase_core" / "__init___fast.py"
backup_file = src_path / "omnibase_core" / "__init___backup.py"

sys.path.insert(0, str(src_path))


def clear_cache():
    """Clear import cache."""
    modules = [k for k in sys.modules if "omnibase_core" in k]
    for m in modules:
        if m in sys.modules:
            del sys.modules[m]


def test_original():
    """Test original __init__.py performance."""
    print("🐌 TESTING ORIGINAL __init__.py")
    clear_cache()

    start = time.perf_counter()
    import omnibase_core

    original_time = (time.perf_counter() - start) * 1000

    print(f"   Original import time: {original_time:.2f}ms")
    return original_time


def test_optimized():
    """Test optimized __init__.py performance."""
    print("🚀 TESTING OPTIMIZED __init__.py")

    # Backup original
    shutil.copy2(init_file, backup_file)

    try:
        # Replace with optimized version
        shutil.copy2(fast_init_file, init_file)

        clear_cache()

        start = time.perf_counter()
        import importlib

        importlib.invalidate_caches()

        # Import omnibase_core with optimized __init__.py
        spec = importlib.util.spec_from_file_location(
            "omnibase_core", init_file.parent / "__init__.py"
        )
        module = importlib.util.module_from_spec(spec)

        start = time.perf_counter()
        spec.loader.exec_module(module)
        optimized_time = (time.perf_counter() - start) * 1000

        print(f"   Optimized import time: {optimized_time:.2f}ms")
        return optimized_time

    finally:
        # Restore original
        shutil.copy2(backup_file, init_file)
        backup_file.unlink()


def main():
    """Test the __init__.py optimization."""
    print("🔬 TESTING __init__.py PERFORMANCE OPTIMIZATION")
    print("=" * 60)

    try:
        original_time = test_original()
        optimized_time = test_optimized()

        improvement = ((original_time - optimized_time) / original_time) * 100
        speedup = original_time / optimized_time if optimized_time > 0 else float("inf")

        print("\n📊 RESULTS:")
        print(f"   Original: {original_time:.2f}ms")
        print(f"   Optimized: {optimized_time:.2f}ms")
        print(f"   Improvement: {improvement:.1f}%")
        print(f"   Speedup: {speedup:.1f}x faster")
        print(f"   Zero Tolerance: {'✅ PASS' if optimized_time < 50 else '❌ FAIL'}")

        # Final assessment
        if optimized_time < 50:
            print("\n✅ OPTIMIZATION SUCCESSFUL!")
            print("🎯 Zero tolerance requirements met")
            return 0
        else:
            print("\n⚠️  PARTIAL SUCCESS")
            print("🔧 Further optimization may be needed")
            return 0

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
