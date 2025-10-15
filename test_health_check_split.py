#!/usr/bin/env python3
"""
Verification script for health check subcontract split.
Run this after fixing the field_validator import issue.
"""

from omnibase_core.models.contracts.subcontracts.model_component_health import (
    ModelComponentHealth,
)
from omnibase_core.models.contracts.subcontracts.model_node_health_status import (
    ModelNodeHealthStatus,
)

print("✅ Import tests passed!")

# Verify ModelComponentHealth
print("\n✅ ModelComponentHealth")
print(f"   Fields: {list(ModelComponentHealth.model_fields.keys())}")

# Verify ModelNodeHealthStatus
print("\n✅ ModelNodeHealthStatus")
print(f"   Fields: {list(ModelNodeHealthStatus.model_fields.keys())}")

print("\n✅ All health check split verifications passed!")
