"""
Declarative Node Error Hierarchy (OMN-177).

Re-exports canonical error classes for declarative node validation.
Each error class is defined in its own file per ONEX single-class-per-file convention.

MVP Classes:
- AdapterBindingError: Adapter cannot bind to contract structure
- PurityViolationError: Node contains I/O or impure code
- NodeExecutionError: Runtime execution failure in node
- UnsupportedCapabilityError: Contract demands unavailable capability

Error Invariants (MVP Requirements):
- All errors MUST include correlation_id for tracking
- Node errors MUST include node_id when applicable
- All errors SHOULD include operation when applicable
- Raw stack traces MUST NOT appear in error envelopes
- Structured fields for logging and observability

Usage:
    from omnibase_core.errors.error_declarative import (
        AdapterBindingError,
        PurityViolationError,
        NodeExecutionError,
        UnsupportedCapabilityError,
    )

    # Adapter binding error
    raise AdapterBindingError(
        "Cannot bind YAML adapter to contract",
        adapter_type="YamlContractAdapter",
        contract_path="nodes/compute/contract.yaml",
    )

    # Purity violation error
    raise PurityViolationError(
        "COMPUTE node accessed external state",
        node_id="node-compute-123",
        violation_type="external_state_access",
    )

    # Node execution error
    raise NodeExecutionError(
        "Execution failed during compute phase",
        node_id="node-compute-abc",
        execution_phase="compute",
    )

    # Unsupported capability error
    raise UnsupportedCapabilityError(
        "Node does not support streaming",
        capability="streaming",
        node_type="COMPUTE",
    )
"""

from omnibase_core.errors.exception_adapter_binding_error import AdapterBindingError
from omnibase_core.errors.exception_node_execution_error import NodeExecutionError
from omnibase_core.errors.exception_purity_violation_error import PurityViolationError
from omnibase_core.errors.exception_unsupported_capability_error import (
    UnsupportedCapabilityError,
)

__all__ = [
    "AdapterBindingError",
    "NodeExecutionError",
    "PurityViolationError",
    "UnsupportedCapabilityError",
]
