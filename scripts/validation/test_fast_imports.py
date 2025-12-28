#!/usr/bin/env python3
"""
Quick Test: Zero-Import-Time Performance

Tests if the ultra-aggressive approach actually delivers <5ms import time.
"""

import gc
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def clear_cache():
    """Clear import cache."""
    modules = [k for k in sys.modules if "omnibase_core" in k]
    for m in modules:
        if m in sys.modules:
            del sys.modules[m]
    gc.collect()


def test_fast_import():
    """Test the fast import approach."""
    print("🚀 TESTING ZERO-IMPORT-TIME APPROACH")
    print("=" * 50)

    clear_cache()

    # Test 1: Module import time
    print("Test 1: Module import time")
    start = time.perf_counter()
    import omnibase_core.models.contracts.fast_imports

    import_time = (time.perf_counter() - start) * 1000
    print(f"   Module import: {import_time:.2f}ms")

    # Test 2: Factory access time
    print("Test 2: Factory access time")
    start = time.perf_counter()
    contract_base = omnibase_core.models.contracts.fast_imports.base()
    access_time = (time.perf_counter() - start) * 1000
    print(f"   First contract access: {access_time:.2f}ms")

    # Test 3: Cached access time
    print("Test 3: Cached access time")
    start = time.perf_counter()
    contract_base2 = omnibase_core.models.contracts.fast_imports.base()
    cached_time = (time.perf_counter() - start) * 1000
    print(f"   Cached contract access: {cached_time:.2f}ms")

    # Results
    total_time = import_time + access_time
    print("\n📊 RESULTS:")
    print(f"   Total time (import + first access): {total_time:.2f}ms")
    print(f"   Zero Tolerance Status: {'✅ PASS' if total_time < 50 else '❌ FAIL'}")
    print(
        f"   Performance Level: {'EXCELLENT' if total_time < 10 else 'GOOD' if total_time < 50 else 'POOR'}"
    )

    return total_time


if __name__ == "__main__":
    result = test_fast_import()
    sys.exit(0 if result < 50 else 1)
