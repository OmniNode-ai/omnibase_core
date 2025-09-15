#!/usr/bin/env python3
"""
Test contract model lazy evaluation optimization
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from omnibase_core.core.contracts.model_contract_orchestrator import (
    ModelContractOrchestrator,
)
from omnibase_core.models.core.model_semver import ModelSemVer


def test_contract_optimization():
    """Test contract model lazy evaluation."""
    print("🚀 Testing Contract Model Optimization")

    try:
        # Create test contract
        contract = ModelContractOrchestrator(
            contract_version="1.0.0",
            node_name="test_orchestrator",
            main_tool_class="TestOrchestratorTool",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
            event_type={
                "events_produced": ["test.event"],
                "events_consumed": ["input.event"],
            },
        )

        print("✅ Contract created successfully")

        # Test lazy model_dump
        lazy_dump = contract.lazy_model_dump()
        result = lazy_dump()

        print("✅ Lazy model_dump working")
        print(f"  Result contains {len(result)} fields")

        # Test cache stats
        cache_stats = contract.get_lazy_cache_stats()
        print(f"✅ Cache stats: {cache_stats}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = test_contract_optimization()
    sys.exit(0 if success else 1)
