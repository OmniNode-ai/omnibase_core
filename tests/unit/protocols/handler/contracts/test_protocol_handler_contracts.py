# Copyright (C) 2024 OmniNode
# SPDX-License-Identifier: AGPL-3.0-only
"""Comprehensive unit tests for handler contract protocols.

This module tests the 5 handler contract protocols:
1. ProtocolHandlerContract - Main handler contract interface
2. ProtocolHandlerBehaviorDescriptor - Behavior characteristics
3. ProtocolCapabilityDependency - Capability requirements
4. ProtocolExecutionConstraints - Execution constraints
5. ProtocolExecutionConstrainable - Mixin for constraint-bearing objects

Tests verify:
- @runtime_checkable allows isinstance() checks with duck-typed classes
- Consistency invariants are maintained (has_constraints <-> execution_constraints)
- Duck-typed classes satisfy protocols without explicit inheritance
- All protocols are properly @runtime_checkable

PR #347 Review Feedback: Added to validate protocol behavior and consistency.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from omnibase_core.protocols.handler.contracts import (
    ProtocolCapabilityDependency,
    ProtocolExecutionConstrainable,
    ProtocolExecutionConstraints,
    ProtocolHandlerBehaviorDescriptor,
    ProtocolHandlerContract,
)

if TYPE_CHECKING:
    from omnibase_core.protocols.validation import ProtocolValidationResult


# =============================================================================
# Duck-Typed Implementation Classes (No Explicit Inheritance)
# =============================================================================


class DuckTypedBehaviorDescriptor:
    """Duck-typed implementation of ProtocolHandlerBehaviorDescriptor.

    This class implements all required properties WITHOUT explicitly inheriting
    from the protocol. It demonstrates structural subtyping (duck typing).
    """

    def __init__(
        self,
        *,
        idempotent: bool = True,
        deterministic: bool = False,
        side_effects: list[str] | None = None,
        retry_safe: bool = True,
    ) -> None:
        self._idempotent = idempotent
        self._deterministic = deterministic
        self._side_effects = side_effects or []
        self._retry_safe = retry_safe

    @property
    def idempotent(self) -> bool:
        return self._idempotent

    @property
    def deterministic(self) -> bool:
        return self._deterministic

    @property
    def side_effects(self) -> list[str]:
        return self._side_effects

    @property
    def retry_safe(self) -> bool:
        return self._retry_safe


class DuckTypedCapabilityDependency:
    """Duck-typed implementation of ProtocolCapabilityDependency.

    Demonstrates structural subtyping without explicit protocol inheritance.
    """

    def __init__(
        self,
        capability_name: str,
        required: bool = True,
        version_constraint: str | None = None,
    ) -> None:
        self._capability_name = capability_name
        self._required = required
        self._version_constraint = version_constraint

    @property
    def capability_name(self) -> str:
        return self._capability_name

    @property
    def required(self) -> bool:
        return self._required

    @property
    def version_constraint(self) -> str | None:
        return self._version_constraint


class DuckTypedExecutionConstraints:
    """Duck-typed implementation of ProtocolExecutionConstraints.

    Provides execution constraint values without explicit protocol inheritance.
    """

    def __init__(
        self,
        *,
        max_retries: int = 3,
        timeout_seconds: float = 30.0,
        memory_limit_mb: int | None = 512,
        cpu_limit: float | None = 1.0,
        concurrency_limit: int | None = 10,
    ) -> None:
        self._max_retries = max_retries
        self._timeout_seconds = timeout_seconds
        self._memory_limit_mb = memory_limit_mb
        self._cpu_limit = cpu_limit
        self._concurrency_limit = concurrency_limit

    @property
    def max_retries(self) -> int:
        return self._max_retries

    @property
    def timeout_seconds(self) -> float:
        return self._timeout_seconds

    @property
    def memory_limit_mb(self) -> int | None:
        return self._memory_limit_mb

    @property
    def cpu_limit(self) -> float | None:
        return self._cpu_limit

    @property
    def concurrency_limit(self) -> int | None:
        return self._concurrency_limit


class DuckTypedConstrainable:
    """Duck-typed implementation of ProtocolExecutionConstrainable.

    Demonstrates the recommended implementation pattern where has_constraints()
    derives directly from execution_constraints to maintain consistency.
    """

    def __init__(
        self,
        constraints: ProtocolExecutionConstraints | None = None,
    ) -> None:
        self._constraints = constraints

    @property
    def execution_constraints(self) -> ProtocolExecutionConstraints | None:
        return self._constraints

    def has_constraints(self) -> bool:
        # Recommended pattern: derive from execution_constraints
        return self._constraints is not None


class DuckTypedConstrainableInconsistent:
    """Duck-typed implementation with INTENTIONALLY BROKEN consistency.

    This class violates the consistency invariant for testing purposes.
    It shows what happens when has_constraints() doesn't match execution_constraints.

    WARNING: This is an anti-pattern. Do NOT use in production code.
    """

    def __init__(
        self,
        constraints: ProtocolExecutionConstraints | None = None,
        override_has_constraints: bool | None = None,
    ) -> None:
        self._constraints = constraints
        self._override = override_has_constraints

    @property
    def execution_constraints(self) -> ProtocolExecutionConstraints | None:
        return self._constraints

    def has_constraints(self) -> bool:
        if self._override is not None:
            return self._override  # Intentionally inconsistent
        return self._constraints is not None


class MockValidationResult:
    """Mock validation result for testing."""

    def __init__(self, is_valid: bool = True, errors: list[str] | None = None) -> None:
        self.is_valid = is_valid
        self.errors = errors or []


class DuckTypedHandlerContract:
    """Duck-typed implementation of ProtocolHandlerContract.

    Complete implementation of all handler contract properties and methods
    without explicit protocol inheritance.
    """

    def __init__(
        self,
        handler_id: str = "test-handler-001",
        handler_name: str = "test-handler",
        handler_version: str = "1.0.0",
        descriptor: ProtocolHandlerBehaviorDescriptor | None = None,
        capability_inputs: list[ProtocolCapabilityDependency] | None = None,
        execution_constraints: ProtocolExecutionConstraints | None = None,
    ) -> None:
        self._handler_id = handler_id
        self._handler_name = handler_name
        self._handler_version = handler_version
        self._descriptor = descriptor or DuckTypedBehaviorDescriptor()
        self._capability_inputs = capability_inputs or []
        self._execution_constraints = execution_constraints

    @property
    def handler_id(self) -> str:
        return self._handler_id

    @property
    def handler_name(self) -> str:
        return self._handler_name

    @property
    def handler_version(self) -> str:
        return self._handler_version

    @property
    def descriptor(self) -> ProtocolHandlerBehaviorDescriptor:
        return self._descriptor

    @property
    def capability_inputs(self) -> list[ProtocolCapabilityDependency]:
        return self._capability_inputs

    @property
    def execution_constraints(self) -> ProtocolExecutionConstraints | None:
        return self._execution_constraints

    async def validate(self) -> ProtocolValidationResult:
        # Simple mock validation
        return MockValidationResult(is_valid=True)  # type: ignore[return-value]

    def to_yaml(self) -> str:
        return f"handler_id: {self._handler_id}\nhandler_name: {self._handler_name}"

    @classmethod
    def from_yaml(cls, content: str) -> DuckTypedHandlerContract:
        # Simple mock deserialization
        return cls()


# =============================================================================
# Test Classes
# =============================================================================


@pytest.mark.unit
class TestProtocolRuntimeCheckable:
    """Test that all protocols are @runtime_checkable and support isinstance()."""

    def test_protocol_handler_behavior_descriptor_is_runtime_checkable(self) -> None:
        """Verify ProtocolHandlerBehaviorDescriptor supports isinstance().

        The @runtime_checkable decorator allows isinstance() checks on Protocol
        classes. This test confirms duck-typed classes pass isinstance().
        """
        descriptor = DuckTypedBehaviorDescriptor()
        assert isinstance(descriptor, ProtocolHandlerBehaviorDescriptor)

    def test_protocol_capability_dependency_is_runtime_checkable(self) -> None:
        """Verify ProtocolCapabilityDependency supports isinstance()."""
        dependency = DuckTypedCapabilityDependency(
            capability_name="database.postgresql",
            required=True,
            version_constraint=">=14.0.0",
        )
        assert isinstance(dependency, ProtocolCapabilityDependency)

    def test_protocol_execution_constraints_is_runtime_checkable(self) -> None:
        """Verify ProtocolExecutionConstraints supports isinstance()."""
        constraints = DuckTypedExecutionConstraints()
        assert isinstance(constraints, ProtocolExecutionConstraints)

    def test_protocol_execution_constrainable_is_runtime_checkable(self) -> None:
        """Verify ProtocolExecutionConstrainable supports isinstance()."""
        constrainable = DuckTypedConstrainable()
        assert isinstance(constrainable, ProtocolExecutionConstrainable)

    def test_protocol_handler_contract_is_runtime_checkable(self) -> None:
        """Verify ProtocolHandlerContract supports isinstance()."""
        contract = DuckTypedHandlerContract()
        assert isinstance(contract, ProtocolHandlerContract)


@pytest.mark.unit
class TestProtocolDuckTyping:
    """Test that protocols work with pure duck-typed classes.

    Duck typing (structural subtyping) means classes don't need to explicitly
    inherit from protocols - they just need to implement the required interface.
    """

    def test_behavior_descriptor_duck_typing(self) -> None:
        """Duck-typed class satisfies ProtocolHandlerBehaviorDescriptor."""
        descriptor = DuckTypedBehaviorDescriptor(
            idempotent=False,
            deterministic=True,
            side_effects=["network", "database"],
            retry_safe=False,
        )

        # Access all properties defined by the protocol
        assert descriptor.idempotent is False
        assert descriptor.deterministic is True
        assert descriptor.side_effects == ["network", "database"]
        assert descriptor.retry_safe is False

        # Confirm protocol conformance via isinstance
        assert isinstance(descriptor, ProtocolHandlerBehaviorDescriptor)

    def test_capability_dependency_duck_typing(self) -> None:
        """Duck-typed class satisfies ProtocolCapabilityDependency."""
        required_dep = DuckTypedCapabilityDependency(
            capability_name="messaging.kafka",
            required=True,
            version_constraint=">=3.0.0",
        )
        optional_dep = DuckTypedCapabilityDependency(
            capability_name="cache.redis",
            required=False,
            version_constraint=None,
        )

        # Verify required dependency
        assert required_dep.capability_name == "messaging.kafka"
        assert required_dep.required is True
        assert required_dep.version_constraint == ">=3.0.0"
        assert isinstance(required_dep, ProtocolCapabilityDependency)

        # Verify optional dependency
        assert optional_dep.capability_name == "cache.redis"
        assert optional_dep.required is False
        assert optional_dep.version_constraint is None
        assert isinstance(optional_dep, ProtocolCapabilityDependency)

    def test_execution_constraints_duck_typing(self) -> None:
        """Duck-typed class satisfies ProtocolExecutionConstraints."""
        constraints = DuckTypedExecutionConstraints(
            max_retries=5,
            timeout_seconds=60.0,
            memory_limit_mb=1024,
            cpu_limit=2.0,
            concurrency_limit=20,
        )

        # Access all properties
        assert constraints.max_retries == 5
        assert constraints.timeout_seconds == 60.0
        assert constraints.memory_limit_mb == 1024
        assert constraints.cpu_limit == 2.0
        assert constraints.concurrency_limit == 20
        assert isinstance(constraints, ProtocolExecutionConstraints)

    def test_execution_constraints_with_none_limits(self) -> None:
        """Duck-typed constraints with None values for optional limits."""
        constraints = DuckTypedExecutionConstraints(
            max_retries=0,
            timeout_seconds=10.0,
            memory_limit_mb=None,
            cpu_limit=None,
            concurrency_limit=None,
        )

        assert constraints.max_retries == 0
        assert constraints.timeout_seconds == 10.0
        assert constraints.memory_limit_mb is None
        assert constraints.cpu_limit is None
        assert constraints.concurrency_limit is None
        assert isinstance(constraints, ProtocolExecutionConstraints)

    def test_handler_contract_duck_typing(self) -> None:
        """Duck-typed class satisfies ProtocolHandlerContract."""
        descriptor = DuckTypedBehaviorDescriptor(
            idempotent=True,
            deterministic=False,
            side_effects=["network"],
            retry_safe=True,
        )
        capability = DuckTypedCapabilityDependency(
            capability_name="database.postgresql",
            required=True,
        )
        constraints = DuckTypedExecutionConstraints(
            max_retries=3,
            timeout_seconds=30.0,
        )

        contract = DuckTypedHandlerContract(
            handler_id="http-handler-001",
            handler_name="http-rest-handler",
            handler_version="2.1.0",
            descriptor=descriptor,
            capability_inputs=[capability],
            execution_constraints=constraints,
        )

        # Verify all contract properties
        assert contract.handler_id == "http-handler-001"
        assert contract.handler_name == "http-rest-handler"
        assert contract.handler_version == "2.1.0"
        assert contract.descriptor.idempotent is True
        assert len(contract.capability_inputs) == 1
        assert contract.capability_inputs[0].capability_name == "database.postgresql"
        assert contract.execution_constraints is not None
        assert contract.execution_constraints.timeout_seconds == 30.0

        # Confirm protocol conformance
        assert isinstance(contract, ProtocolHandlerContract)


@pytest.mark.unit
class TestExecutionConstrainableConsistency:
    """Test the consistency invariant of ProtocolExecutionConstrainable.

    The invariant states:
    - has_constraints() returns True IFF execution_constraints is not None
    - has_constraints() returns False IFF execution_constraints is None
    """

    def test_has_constraints_true_implies_non_none_constraints(self) -> None:
        """Test: has_constraints() True implies execution_constraints is not None.

        This tests the forward direction of the consistency invariant.
        """
        constraints = DuckTypedExecutionConstraints()
        constrainable = DuckTypedConstrainable(constraints=constraints)

        # Verify invariant: True -> not None
        assert constrainable.has_constraints() is True
        assert constrainable.execution_constraints is not None

    def test_has_constraints_false_implies_none_constraints(self) -> None:
        """Test: has_constraints() False implies execution_constraints is None.

        This tests the reverse direction of the consistency invariant.
        """
        constrainable = DuckTypedConstrainable(constraints=None)

        # Verify invariant: False -> None
        assert constrainable.has_constraints() is False
        assert constrainable.execution_constraints is None

    def test_non_none_constraints_implies_has_constraints_true(self) -> None:
        """Test: execution_constraints not None implies has_constraints() True.

        This tests the converse of the first invariant direction.
        """
        constraints = DuckTypedExecutionConstraints(timeout_seconds=15.0)
        constrainable = DuckTypedConstrainable(constraints=constraints)

        # Verify: not None -> True
        assert constrainable.execution_constraints is not None
        assert constrainable.has_constraints() is True

    def test_none_constraints_implies_has_constraints_false(self) -> None:
        """Test: execution_constraints None implies has_constraints() False.

        This tests the converse of the second invariant direction.
        """
        constrainable = DuckTypedConstrainable(constraints=None)

        # Verify: None -> False
        assert constrainable.execution_constraints is None
        assert constrainable.has_constraints() is False

    def test_recommended_implementation_maintains_consistency(self) -> None:
        """Test that recommended implementation pattern maintains consistency.

        The recommended pattern derives has_constraints() from execution_constraints:
            def has_constraints(self) -> bool:
                return self.execution_constraints is not None

        This ensures the invariant cannot be violated.
        """
        # Test with constraints
        constraints = DuckTypedExecutionConstraints()
        with_constraints = DuckTypedConstrainable(constraints=constraints)
        assert (with_constraints.execution_constraints is not None) == (
            with_constraints.has_constraints()
        )

        # Test without constraints
        without_constraints = DuckTypedConstrainable(constraints=None)
        assert (without_constraints.execution_constraints is not None) == (
            without_constraints.has_constraints()
        )

    def test_inconsistent_implementation_violates_invariant(self) -> None:
        """Demonstrate how inconsistent implementations violate the invariant.

        This test uses an intentionally broken implementation to show what
        the consistency check would catch. This is an anti-pattern example.
        """
        # Case 1: has_constraints() returns True but constraints is None
        inconsistent_1 = DuckTypedConstrainableInconsistent(
            constraints=None,
            override_has_constraints=True,  # Violates invariant
        )
        # This violates: has_constraints() True -> constraints not None
        assert inconsistent_1.has_constraints() is True
        assert inconsistent_1.execution_constraints is None  # VIOLATION

        # Case 2: has_constraints() returns False but constraints is not None
        constraints = DuckTypedExecutionConstraints()
        inconsistent_2 = DuckTypedConstrainableInconsistent(
            constraints=constraints,
            override_has_constraints=False,  # Violates invariant
        )
        # This violates: has_constraints() False -> constraints is None
        assert inconsistent_2.has_constraints() is False
        assert inconsistent_2.execution_constraints is not None  # VIOLATION


@pytest.mark.unit
class TestProtocolPropertyAccess:
    """Test that protocol properties are accessible on duck-typed implementations."""

    def test_behavior_descriptor_property_types(self) -> None:
        """Verify property return types match protocol specification."""
        descriptor = DuckTypedBehaviorDescriptor()

        assert isinstance(descriptor.idempotent, bool)
        assert isinstance(descriptor.deterministic, bool)
        assert isinstance(descriptor.side_effects, list)
        assert isinstance(descriptor.retry_safe, bool)

    def test_capability_dependency_property_types(self) -> None:
        """Verify property return types match protocol specification."""
        dep = DuckTypedCapabilityDependency(
            capability_name="test.capability",
            required=True,
            version_constraint=">=1.0.0",
        )

        assert isinstance(dep.capability_name, str)
        assert isinstance(dep.required, bool)
        assert dep.version_constraint is None or isinstance(dep.version_constraint, str)

    def test_execution_constraints_property_types(self) -> None:
        """Verify property return types match protocol specification."""
        constraints = DuckTypedExecutionConstraints()

        assert isinstance(constraints.max_retries, int)
        assert isinstance(constraints.timeout_seconds, float)
        assert constraints.memory_limit_mb is None or isinstance(
            constraints.memory_limit_mb, int
        )
        assert constraints.cpu_limit is None or isinstance(constraints.cpu_limit, float)
        assert constraints.concurrency_limit is None or isinstance(
            constraints.concurrency_limit, int
        )

    def test_handler_contract_property_types(self) -> None:
        """Verify property return types match protocol specification."""
        contract = DuckTypedHandlerContract()

        assert isinstance(contract.handler_id, str)
        assert isinstance(contract.handler_name, str)
        assert isinstance(contract.handler_version, str)
        assert isinstance(contract.descriptor, ProtocolHandlerBehaviorDescriptor)
        assert isinstance(contract.capability_inputs, list)
        assert contract.execution_constraints is None or isinstance(
            contract.execution_constraints, ProtocolExecutionConstraints
        )


@pytest.mark.unit
class TestProtocolMethodAccess:
    """Test that protocol methods are callable on duck-typed implementations."""

    def test_constrainable_has_constraints_method(self) -> None:
        """Verify has_constraints() method is callable and returns bool."""
        with_constraints = DuckTypedConstrainable(
            constraints=DuckTypedExecutionConstraints()
        )
        without_constraints = DuckTypedConstrainable(constraints=None)

        result_with = with_constraints.has_constraints()
        result_without = without_constraints.has_constraints()

        assert isinstance(result_with, bool)
        assert isinstance(result_without, bool)
        assert result_with is True
        assert result_without is False

    @pytest.mark.asyncio
    async def test_handler_contract_validate_method(self) -> None:
        """Verify validate() async method is callable."""
        contract = DuckTypedHandlerContract()
        result = await contract.validate()

        # MockValidationResult has is_valid attribute
        assert hasattr(result, "is_valid")
        assert result.is_valid is True

    def test_handler_contract_to_yaml_method(self) -> None:
        """Verify to_yaml() method returns string."""
        contract = DuckTypedHandlerContract(
            handler_id="yaml-test-001",
            handler_name="yaml-test-handler",
        )
        yaml_output = contract.to_yaml()

        assert isinstance(yaml_output, str)
        assert "yaml-test-001" in yaml_output
        assert "yaml-test-handler" in yaml_output

    def test_handler_contract_from_yaml_classmethod(self) -> None:
        """Verify from_yaml() classmethod creates instance."""
        yaml_content = "handler_id: test\nhandler_name: test"
        contract = DuckTypedHandlerContract.from_yaml(yaml_content)

        assert isinstance(contract, DuckTypedHandlerContract)
        assert isinstance(contract, ProtocolHandlerContract)


@pytest.mark.unit
class TestProtocolIntegration:
    """Integration tests showing protocols working together."""

    def test_complete_handler_contract_with_all_components(self) -> None:
        """Test a complete handler contract with all protocol components."""
        # Create behavior descriptor
        descriptor = DuckTypedBehaviorDescriptor(
            idempotent=True,
            deterministic=True,
            side_effects=[],
            retry_safe=True,
        )

        # Create capability dependencies
        db_cap = DuckTypedCapabilityDependency(
            capability_name="database.postgresql",
            required=True,
            version_constraint=">=14.0.0",
        )
        cache_cap = DuckTypedCapabilityDependency(
            capability_name="cache.redis",
            required=False,
        )

        # Create execution constraints
        constraints = DuckTypedExecutionConstraints(
            max_retries=3,
            timeout_seconds=30.0,
            memory_limit_mb=512,
            cpu_limit=1.0,
            concurrency_limit=10,
        )

        # Assemble complete contract
        contract = DuckTypedHandlerContract(
            handler_id="urn:onex:handler:user-auth:v1",
            handler_name="user-authentication-handler",
            handler_version="1.2.3",
            descriptor=descriptor,
            capability_inputs=[db_cap, cache_cap],
            execution_constraints=constraints,
        )

        # Verify all components via protocol interfaces
        assert isinstance(contract, ProtocolHandlerContract)
        assert isinstance(contract.descriptor, ProtocolHandlerBehaviorDescriptor)
        assert all(
            isinstance(cap, ProtocolCapabilityDependency)
            for cap in contract.capability_inputs
        )
        assert isinstance(contract.execution_constraints, ProtocolExecutionConstraints)

        # Verify semantic properties
        assert contract.descriptor.retry_safe is True
        assert contract.descriptor.idempotent is True
        assert len(contract.capability_inputs) == 2
        assert contract.execution_constraints.max_retries == 3

    def test_handler_contract_without_constraints(self) -> None:
        """Test handler contract with no execution constraints."""
        contract = DuckTypedHandlerContract(
            handler_id="simple-handler",
            handler_name="simple",
            handler_version="1.0.0",
            execution_constraints=None,
        )

        assert isinstance(contract, ProtocolHandlerContract)
        assert contract.execution_constraints is None

    def test_constrainable_with_nested_constraints(self) -> None:
        """Test ProtocolExecutionConstrainable holding nested protocol."""
        constraints = DuckTypedExecutionConstraints(
            max_retries=5,
            timeout_seconds=120.0,
        )
        constrainable = DuckTypedConstrainable(constraints=constraints)

        # Verify constrainable protocol
        assert isinstance(constrainable, ProtocolExecutionConstrainable)
        assert constrainable.has_constraints() is True

        # Verify nested constraints protocol
        nested = constrainable.execution_constraints
        assert nested is not None
        assert isinstance(nested, ProtocolExecutionConstraints)
        assert nested.max_retries == 5
        assert nested.timeout_seconds == 120.0


@pytest.mark.unit
class TestProtocolEdgeCases:
    """Test edge cases and boundary conditions for protocols."""

    def test_behavior_descriptor_empty_side_effects(self) -> None:
        """Test behavior descriptor with no side effects (pure computation)."""
        descriptor = DuckTypedBehaviorDescriptor(
            idempotent=True,
            deterministic=True,
            side_effects=[],
            retry_safe=True,
        )

        assert descriptor.side_effects == []
        assert len(descriptor.side_effects) == 0
        assert isinstance(descriptor, ProtocolHandlerBehaviorDescriptor)

    def test_capability_dependency_no_version_constraint(self) -> None:
        """Test capability dependency with no version constraint (any version)."""
        dep = DuckTypedCapabilityDependency(
            capability_name="any.capability",
            required=True,
            version_constraint=None,
        )

        assert dep.version_constraint is None
        assert isinstance(dep, ProtocolCapabilityDependency)

    def test_execution_constraints_zero_retries(self) -> None:
        """Test constraints with zero retries (single attempt only)."""
        constraints = DuckTypedExecutionConstraints(
            max_retries=0,
            timeout_seconds=5.0,
        )

        assert constraints.max_retries == 0
        assert isinstance(constraints, ProtocolExecutionConstraints)

    def test_execution_constraints_all_optional_none(self) -> None:
        """Test constraints with all optional fields as None."""
        constraints = DuckTypedExecutionConstraints(
            max_retries=1,
            timeout_seconds=10.0,
            memory_limit_mb=None,
            cpu_limit=None,
            concurrency_limit=None,
        )

        assert constraints.memory_limit_mb is None
        assert constraints.cpu_limit is None
        assert constraints.concurrency_limit is None
        assert isinstance(constraints, ProtocolExecutionConstraints)

    def test_handler_contract_empty_capabilities(self) -> None:
        """Test handler contract with no capability dependencies."""
        contract = DuckTypedHandlerContract(
            handler_id="no-deps-handler",
            handler_name="standalone",
            handler_version="1.0.0",
            capability_inputs=[],
        )

        assert contract.capability_inputs == []
        assert len(contract.capability_inputs) == 0
        assert isinstance(contract, ProtocolHandlerContract)
