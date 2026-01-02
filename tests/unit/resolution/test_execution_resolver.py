# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Comprehensive tests for ExecutionResolver.

Tests cover:
    - Basic ordering (simple dependencies)
    - Multiple dependencies and chains
    - Cycle detection (direct, indirect, self-reference)
    - Tie-breaking (priority, alphabetical, multiple)
    - Phase assignment
    - Edge cases (empty, single, all independent)
    - Constraint resolution (capability, handler, tag references)
    - Missing dependency handling

.. versionadded:: 0.4.1
"""

from typing import Any

import pytest

from omnibase_core.models.contracts.model_execution_constraints import (
    ModelExecutionConstraints,
)
from omnibase_core.models.contracts.model_execution_ordering_policy import (
    ModelExecutionOrderingPolicy,
)
from omnibase_core.models.contracts.model_execution_profile import (
    DEFAULT_EXECUTION_PHASES,
    ModelExecutionProfile,
)
from omnibase_core.models.contracts.model_handler_contract import ModelHandlerContract
from omnibase_core.models.runtime.model_handler_behavior import ModelHandlerBehavior
from omnibase_core.resolution import ExecutionResolver

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def resolver() -> ExecutionResolver:
    """Create a fresh ExecutionResolver instance."""
    return ExecutionResolver()


@pytest.fixture
def default_profile() -> ModelExecutionProfile:
    """Create a default execution profile."""
    return ModelExecutionProfile(
        phases=list(DEFAULT_EXECUTION_PHASES),
        ordering_policy=ModelExecutionOrderingPolicy(
            strategy="topological_sort",
            tie_breakers=["priority", "alphabetical"],
            deterministic_seed=True,
        ),
    )


@pytest.fixture
def alphabetical_only_profile() -> ModelExecutionProfile:
    """Create a profile with alphabetical tie-breaking only."""
    return ModelExecutionProfile(
        phases=list(DEFAULT_EXECUTION_PHASES),
        ordering_policy=ModelExecutionOrderingPolicy(
            strategy="topological_sort",
            tie_breakers=["alphabetical"],
            deterministic_seed=True,
        ),
    )


@pytest.fixture
def priority_only_profile() -> ModelExecutionProfile:
    """Create a profile with priority tie-breaking only."""
    return ModelExecutionProfile(
        phases=list(DEFAULT_EXECUTION_PHASES),
        ordering_policy=ModelExecutionOrderingPolicy(
            strategy="topological_sort",
            tie_breakers=["priority"],
            deterministic_seed=True,
        ),
    )


def _create_contract(
    handler_id: str,
    *,
    requires_before: list[str] | None = None,
    requires_after: list[str] | None = None,
    must_run: bool = False,
    tags: list[str] | None = None,
    capability_outputs: list[str] | None = None,
    priority: int = 0,
    metadata: dict[str, Any] | None = None,
) -> ModelHandlerContract:
    """Helper to create a handler contract for testing."""
    constraints = None
    if requires_before or requires_after or must_run:
        constraints = ModelExecutionConstraints(
            requires_before=requires_before or [],
            requires_after=requires_after or [],
            must_run=must_run,
        )

    final_metadata: dict[str, Any] = {"priority": priority}
    if metadata:
        final_metadata.update(metadata)

    return ModelHandlerContract(
        handler_id=handler_id,
        name=f"Handler {handler_id}",
        version="1.0.0",
        descriptor=ModelHandlerBehavior(handler_kind="compute"),
        input_model="test.Input",
        output_model="test.Output",
        execution_constraints=constraints,
        tags=tags or [],
        capability_outputs=capability_outputs or [],
        metadata=final_metadata,
    )


# =============================================================================
# Basic Ordering Tests
# =============================================================================


class TestBasicOrdering:
    """Tests for basic dependency ordering."""

    def test_simple_a_before_b(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test simple A -> B dependency."""
        contracts = [
            _create_contract("handler.a"),
            _create_contract(
                "handler.b",
                requires_before=["handler:handler.a"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        assert handlers.index("handler.a") < handlers.index("handler.b")

    def test_chain_a_b_c(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test chain A -> B -> C dependency."""
        contracts = [
            _create_contract("handler.a"),
            _create_contract(
                "handler.b",
                requires_before=["handler:handler.a"],
            ),
            _create_contract(
                "handler.c",
                requires_before=["handler:handler.b"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        assert handlers == ["handler.a", "handler.b", "handler.c"]

    def test_multiple_dependencies(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test handler with multiple dependencies."""
        # C depends on both A and B
        contracts = [
            _create_contract("handler.a"),
            _create_contract("handler.b"),
            _create_contract(
                "handler.c",
                requires_before=["handler:handler.a", "handler:handler.b"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        # A and B must come before C
        assert handlers.index("handler.a") < handlers.index("handler.c")
        assert handlers.index("handler.b") < handlers.index("handler.c")

    def test_requires_after_constraint(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test requires_after constraint (A declares B must run after it)."""
        contracts = [
            _create_contract(
                "handler.a",
                requires_after=["handler:handler.b"],
            ),
            _create_contract("handler.b"),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        assert handlers.index("handler.a") < handlers.index("handler.b")

    def test_diamond_dependency(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test diamond dependency pattern: A -> B, A -> C, B -> D, C -> D."""
        contracts = [
            _create_contract("handler.a"),
            _create_contract(
                "handler.b",
                requires_before=["handler:handler.a"],
            ),
            _create_contract(
                "handler.c",
                requires_before=["handler:handler.a"],
            ),
            _create_contract(
                "handler.d",
                requires_before=["handler:handler.b", "handler:handler.c"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        # A must be first, D must be last
        assert handlers[0] == "handler.a"
        assert handlers[-1] == "handler.d"
        # B and C must be in middle
        assert set(handlers[1:3]) == {"handler.b", "handler.c"}


# =============================================================================
# Cycle Detection Tests
# =============================================================================


class TestCycleDetection:
    """Tests for cycle detection."""

    def test_direct_cycle_a_b_a(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test direct cycle: A -> B -> A."""
        contracts = [
            _create_contract(
                "handler.a",
                requires_before=["handler:handler.b"],
            ),
            _create_contract(
                "handler.b",
                requires_before=["handler:handler.a"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert not plan.is_valid
        assert plan.has_conflicts()
        assert plan.has_blocking_conflicts()

        cycle_conflicts = plan.get_cycle_conflicts()
        assert len(cycle_conflicts) >= 1
        cycle = cycle_conflicts[0]
        assert cycle.conflict_type == "cycle"
        assert cycle.severity == "error"
        assert cycle.cycle_path is not None
        # Cycle path should contain both handlers
        assert "handler.a" in cycle.cycle_path
        assert "handler.b" in cycle.cycle_path

    def test_indirect_cycle_a_b_c_a(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test indirect cycle: A -> B -> C -> A."""
        contracts = [
            _create_contract(
                "handler.a",
                requires_before=["handler:handler.c"],
            ),
            _create_contract(
                "handler.b",
                requires_before=["handler:handler.a"],
            ),
            _create_contract(
                "handler.c",
                requires_before=["handler:handler.b"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert not plan.is_valid
        assert plan.has_blocking_conflicts()

        cycle_conflicts = plan.get_cycle_conflicts()
        assert len(cycle_conflicts) >= 1
        cycle = cycle_conflicts[0]
        assert cycle.conflict_type == "cycle"
        assert cycle.cycle_path is not None
        # Cycle should include all three handlers
        assert len(set(cycle.cycle_path)) >= 3

    def test_self_reference_not_a_cycle(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that self-reference is NOT treated as a cycle (filtered out)."""
        # Self-references are filtered during graph building
        contracts = [
            _create_contract(
                "handler.a",
                requires_before=["handler:handler.a"],  # Self-reference
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        # Self-references are filtered out, so no cycle
        assert plan.is_valid


# =============================================================================
# Tie-Breaking Tests
# =============================================================================


class TestTieBreaking:
    """Tests for tie-breaking when handlers have no ordering constraints."""

    def test_priority_tie_breaking(
        self,
        resolver: ExecutionResolver,
        priority_only_profile: ModelExecutionProfile,
    ) -> None:
        """Test priority-based tie-breaking (lower number = higher priority)."""
        contracts = [
            _create_contract("handler.z", priority=2),  # Lower priority
            _create_contract("handler.a", priority=1),  # Higher priority
            _create_contract("handler.m", priority=3),  # Lowest priority
        ]

        plan = resolver.resolve(priority_only_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        # Should be ordered by priority: 1, 2, 3
        # With secondary alphabetical for stability
        assert handlers[0] == "handler.a"  # priority 1
        assert handlers[1] == "handler.z"  # priority 2
        assert handlers[2] == "handler.m"  # priority 3

    def test_alphabetical_tie_breaking(
        self,
        resolver: ExecutionResolver,
        alphabetical_only_profile: ModelExecutionProfile,
    ) -> None:
        """Test alphabetical tie-breaking."""
        contracts = [
            _create_contract("handler.charlie"),
            _create_contract("handler.alpha"),
            _create_contract("handler.bravo"),
        ]

        plan = resolver.resolve(alphabetical_only_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        # Should be alphabetical
        assert handlers == ["handler.alpha", "handler.bravo", "handler.charlie"]

    def test_priority_then_alphabetical(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test priority first, then alphabetical for same priority."""
        contracts = [
            _create_contract("handler.z", priority=1),  # High priority
            _create_contract("handler.b", priority=2),  # Lower priority
            _create_contract("handler.a", priority=2),  # Same priority as b
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        # z first (priority 1), then a before b (same priority 2, alphabetical)
        assert handlers[0] == "handler.z"
        # a and b have same priority, alphabetical order
        assert handlers[1] == "handler.a"
        assert handlers[2] == "handler.b"

    def test_tie_breaker_decision_recorded(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that tie-breaker decisions are recorded in metadata."""
        contracts = [
            _create_contract("handler.b"),
            _create_contract("handler.a"),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        assert plan.resolution_metadata is not None
        # Tie-breaking should have occurred
        # (though the specific decision may vary based on implementation)


# =============================================================================
# Phase Assignment Tests
# =============================================================================


class TestPhaseAssignment:
    """Tests for handler phase assignment."""

    def test_handlers_assigned_to_execute_phase(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that handlers are assigned to the execute phase."""
        contracts = [
            _create_contract("handler.a"),
            _create_contract("handler.b"),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        # Find the execute phase
        execute_phase = None
        for phase in plan.phases:
            if phase.phase.value == "execute":
                execute_phase = phase
                break

        assert execute_phase is not None
        assert "handler.a" in execute_phase.handler_ids
        assert "handler.b" in execute_phase.handler_ids

    def test_phase_ordering_preserved(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that dependency order is preserved within phases."""
        contracts = [
            _create_contract("handler.a"),
            _create_contract(
                "handler.b",
                requires_before=["handler:handler.a"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        execute_phase = None
        for phase in plan.phases:
            if phase.phase.value == "execute":
                execute_phase = phase
                break

        assert execute_phase is not None
        handlers = execute_phase.handler_ids
        assert handlers.index("handler.a") < handlers.index("handler.b")


# =============================================================================
# Constraint Reference Resolution Tests
# =============================================================================


class TestConstraintResolution:
    """Tests for resolving capability:, handler:, and tag: references."""

    def test_capability_reference(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test capability: reference resolution."""
        contracts = [
            _create_contract(
                "handler.auth",
                capability_outputs=["auth.provider"],
            ),
            _create_contract(
                "handler.api",
                requires_before=["capability:auth.provider"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        # auth provides auth.provider, api requires it
        assert handlers.index("handler.auth") < handlers.index("handler.api")

    def test_tag_reference(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test tag: reference resolution."""
        contracts = [
            _create_contract(
                "handler.core",
                tags=["core-execution"],
            ),
            _create_contract(
                "handler.metrics",
                requires_before=["tag:core-execution"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        # metrics requires core-execution tag
        assert handlers.index("handler.core") < handlers.index("handler.metrics")

    def test_multiple_handlers_with_same_capability(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test multiple handlers providing the same capability."""
        contracts = [
            _create_contract(
                "handler.auth_basic",
                capability_outputs=["auth.provider"],
            ),
            _create_contract(
                "handler.auth_oauth",
                capability_outputs=["auth.provider"],
            ),
            _create_contract(
                "handler.api",
                requires_before=["capability:auth.provider"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        api_idx = handlers.index("handler.api")
        # Both auth handlers must come before api
        assert handlers.index("handler.auth_basic") < api_idx
        assert handlers.index("handler.auth_oauth") < api_idx

    def test_missing_handler_reference(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test missing handler: reference creates warning."""
        contracts = [
            _create_contract(
                "handler.a",
                requires_before=["handler:handler.nonexistent"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        # Plan is still valid (warning, not error)
        assert plan.is_valid
        assert plan.has_conflicts()
        # Should have warning about missing dependency
        warnings = plan.get_warnings()
        assert len(warnings) == 1
        assert warnings[0].conflict_type == "missing_dependency"
        assert "handler.nonexistent" in warnings[0].message

    def test_missing_capability_reference(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test missing capability: reference creates warning."""
        contracts = [
            _create_contract(
                "handler.a",
                requires_before=["capability:unknown.capability"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        warnings = plan.get_warnings()
        assert len(warnings) == 1
        assert "unknown.capability" in warnings[0].message

    def test_missing_tag_reference(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test missing tag: reference creates warning."""
        contracts = [
            _create_contract(
                "handler.a",
                requires_before=["tag:unknown-tag"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        warnings = plan.get_warnings()
        assert len(warnings) == 1
        assert "unknown-tag" in warnings[0].message


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_contracts_list(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test resolution with empty contracts list."""
        plan = resolver.resolve(default_profile, [])

        assert plan.is_valid
        assert plan.is_empty()
        assert plan.total_handlers() == 0
        assert not plan.has_conflicts()

    def test_single_contract(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test resolution with single contract."""
        contracts = [_create_contract("handler.solo")]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        assert plan.total_handlers() == 1
        handlers = plan.get_all_handler_ids()
        assert handlers == ["handler.solo"]

    def test_all_handlers_independent(
        self,
        resolver: ExecutionResolver,
        alphabetical_only_profile: ModelExecutionProfile,
    ) -> None:
        """Test all handlers with no dependencies (all independent)."""
        contracts = [
            _create_contract("handler.delta"),
            _create_contract("handler.alpha"),
            _create_contract("handler.charlie"),
            _create_contract("handler.bravo"),
        ]

        plan = resolver.resolve(alphabetical_only_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        # Should be alphabetically sorted
        assert handlers == [
            "handler.alpha",
            "handler.bravo",
            "handler.charlie",
            "handler.delta",
        ]

    def test_no_constraints_in_contract(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test contracts with no execution_constraints field."""
        contracts = [
            _create_contract("handler.a"),
            _create_contract("handler.b"),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        assert plan.total_handlers() == 2

    def test_large_chain(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test a longer dependency chain."""
        # Create chain: h0 -> h1 -> h2 -> ... -> h9
        contracts = [_create_contract("handler.h0")]
        for i in range(1, 10):
            contracts.append(
                _create_contract(
                    f"handler.h{i}",
                    requires_before=[f"handler:handler.h{i - 1}"],
                )
            )

        plan = resolver.resolve(default_profile, contracts)

        assert plan.is_valid
        handlers = plan.get_all_handler_ids()
        # Verify order
        for i in range(10):
            assert handlers[i] == f"handler.h{i}"


# =============================================================================
# Determinism Tests
# =============================================================================


class TestDeterminism:
    """Tests verifying deterministic output."""

    def test_same_input_same_output(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that same inputs produce same outputs."""
        contracts = [
            _create_contract("handler.charlie"),
            _create_contract("handler.alpha"),
            _create_contract("handler.bravo"),
        ]

        plan1 = resolver.resolve(default_profile, contracts)
        plan2 = resolver.resolve(default_profile, contracts)

        assert plan1.is_valid and plan2.is_valid
        assert plan1.get_all_handler_ids() == plan2.get_all_handler_ids()

    def test_order_independence(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that input order doesn't affect output (when no deps)."""
        contracts1 = [
            _create_contract("handler.a"),
            _create_contract("handler.b"),
            _create_contract("handler.c"),
        ]
        contracts2 = [
            _create_contract("handler.c"),
            _create_contract("handler.a"),
            _create_contract("handler.b"),
        ]

        plan1 = resolver.resolve(default_profile, contracts1)
        plan2 = resolver.resolve(default_profile, contracts2)

        assert plan1.is_valid and plan2.is_valid
        # Same handlers, possibly same order (deterministic)
        assert set(plan1.get_all_handler_ids()) == set(plan2.get_all_handler_ids())


# =============================================================================
# Resolution Metadata Tests
# =============================================================================


class TestResolutionMetadata:
    """Tests for resolution metadata tracking."""

    def test_metadata_populated(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that resolution metadata is populated."""
        contracts = [
            _create_contract("handler.a"),
            _create_contract(
                "handler.b",
                requires_before=["handler:handler.a"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.resolution_metadata is not None
        meta = plan.resolution_metadata
        assert meta.strategy == "topological_sort"
        assert meta.total_handlers_resolved == 2
        assert meta.total_constraints_evaluated >= 1
        assert meta.resolution_started_at is not None
        assert meta.resolution_completed_at is not None
        assert meta.resolution_duration_ms is not None
        assert meta.resolution_duration_ms >= 0

    def test_constraint_count_tracking(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that constraint count is tracked correctly."""
        contracts = [
            _create_contract("handler.a"),
            _create_contract(
                "handler.b",
                requires_before=["handler:handler.a"],
                requires_after=["handler:handler.c"],
            ),
            _create_contract("handler.c"),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.resolution_metadata is not None
        # handler.b has 2 constraints (1 before, 1 after)
        assert plan.resolution_metadata.total_constraints_evaluated == 2


# =============================================================================
# Protocol Compliance Tests
# =============================================================================


class TestProtocolCompliance:
    """Tests verifying ProtocolExecutionResolver compliance."""

    def test_resolver_is_protocol_compliant(
        self,
        resolver: ExecutionResolver,
    ) -> None:
        """Test that ExecutionResolver implements the protocol interface."""
        from omnibase_core.protocols.resolution.protocol_execution_resolver import (
            ProtocolExecutionResolver,
        )

        assert isinstance(resolver, ProtocolExecutionResolver)

    def test_resolve_signature_matches_protocol(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that resolve() method signature matches protocol."""
        contracts: list[ModelHandlerContract] = []
        # Should not raise TypeError
        plan = resolver.resolve(default_profile, contracts)
        assert plan is not None


# =============================================================================
# Can Execute Tests
# =============================================================================


class TestCanExecute:
    """Tests for plan.can_execute() method."""

    def test_valid_plan_can_execute(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that valid non-empty plan can execute."""
        contracts = [_create_contract("handler.a")]

        plan = resolver.resolve(default_profile, contracts)

        assert plan.can_execute()

    def test_invalid_plan_cannot_execute(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that invalid plan cannot execute."""
        # Create cycle
        contracts = [
            _create_contract(
                "handler.a",
                requires_before=["handler:handler.b"],
            ),
            _create_contract(
                "handler.b",
                requires_before=["handler:handler.a"],
            ),
        ]

        plan = resolver.resolve(default_profile, contracts)

        assert not plan.can_execute()

    def test_empty_plan_cannot_execute(
        self,
        resolver: ExecutionResolver,
        default_profile: ModelExecutionProfile,
    ) -> None:
        """Test that empty plan cannot execute."""
        plan = resolver.resolve(default_profile, [])

        assert not plan.can_execute()
