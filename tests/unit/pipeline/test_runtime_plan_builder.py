# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for RuntimePlanBuilder."""
import pytest

from omnibase_core.enums.enum_handler_type_category import EnumHandlerTypeCategory
from omnibase_core.pipeline.exceptions import (
    DependencyCycleError,
    HookTypeMismatchError,
    UnknownDependencyError,
)
from omnibase_core.pipeline.hook_registry import HookRegistry
from omnibase_core.pipeline.models import (
    ModelPipelineHook,
)
from omnibase_core.pipeline.runtime_plan_builder import RuntimePlanBuilder


def create_frozen_registry(*hooks: ModelPipelineHook) -> HookRegistry:
    """Helper to create a frozen registry with hooks."""
    registry = HookRegistry()
    for hook in hooks:
        registry.register(hook)
    registry.freeze()
    return registry


@pytest.mark.unit
class TestHookTypingValidation:
    """Test hook typing validation per the matrix."""

    def test_generic_hook_validates_for_compute(self) -> None:
        """Generic hook (None category) passes for COMPUTE contract."""
        hook = ModelPipelineHook(
            hook_id="generic",
            phase="execute",
            handler_type_category=None,
            callable_ref="module.func",
        )
        registry = create_frozen_registry(hook)
        builder = RuntimePlanBuilder(
            registry=registry,
            contract_category=EnumHandlerTypeCategory.COMPUTE,
            enforce_hook_typing=True,
        )
        plan, warnings = builder.build()
        assert len(warnings) == 0
        assert plan.total_hooks == 1

    def test_generic_hook_validates_for_effect(self) -> None:
        """Generic hook (None category) passes for EFFECT contract."""
        hook = ModelPipelineHook(
            hook_id="generic",
            phase="execute",
            handler_type_category=None,
            callable_ref="module.func",
        )
        registry = create_frozen_registry(hook)
        builder = RuntimePlanBuilder(
            registry=registry,
            contract_category=EnumHandlerTypeCategory.EFFECT,
            enforce_hook_typing=True,
        )
        plan, warnings = builder.build()
        assert len(warnings) == 0

    def test_typed_compute_hook_passes_on_compute_contract(self) -> None:
        """COMPUTE hook passes on COMPUTE contract."""
        hook = ModelPipelineHook(
            hook_id="compute-hook",
            phase="execute",
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            callable_ref="module.func",
        )
        registry = create_frozen_registry(hook)
        builder = RuntimePlanBuilder(
            registry=registry,
            contract_category=EnumHandlerTypeCategory.COMPUTE,
            enforce_hook_typing=True,
        )
        plan, warnings = builder.build()
        assert len(warnings) == 0

    def test_typed_compute_hook_fails_on_effect_contract_when_enforced(self) -> None:
        """COMPUTE hook on EFFECT contract raises error when enforced."""
        hook = ModelPipelineHook(
            hook_id="compute-hook",
            phase="execute",
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            callable_ref="module.func",
        )
        registry = create_frozen_registry(hook)
        builder = RuntimePlanBuilder(
            registry=registry,
            contract_category=EnumHandlerTypeCategory.EFFECT,
            enforce_hook_typing=True,
        )
        with pytest.raises(HookTypeMismatchError) as exc_info:
            builder.build()
        assert "compute-hook" in str(exc_info.value)

    def test_typed_compute_hook_warns_on_effect_contract_when_not_enforced(
        self,
    ) -> None:
        """COMPUTE hook on EFFECT contract produces warning when not enforced."""
        hook = ModelPipelineHook(
            hook_id="compute-hook",
            phase="execute",
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            callable_ref="module.func",
        )
        registry = create_frozen_registry(hook)
        builder = RuntimePlanBuilder(
            registry=registry,
            contract_category=EnumHandlerTypeCategory.EFFECT,
            enforce_hook_typing=False,
        )
        plan, warnings = builder.build()
        assert len(warnings) == 1
        assert warnings[0].code == "HOOK_TYPE_MISMATCH"
        assert "compute-hook" in warnings[0].context.get("hook_id", "")

    def test_typed_effect_hook_fails_on_compute_contract_when_enforced(self) -> None:
        """EFFECT hook on COMPUTE contract raises error when enforced."""
        hook = ModelPipelineHook(
            hook_id="effect-hook",
            phase="execute",
            handler_type_category=EnumHandlerTypeCategory.EFFECT,
            callable_ref="module.func",
        )
        registry = create_frozen_registry(hook)
        builder = RuntimePlanBuilder(
            registry=registry,
            contract_category=EnumHandlerTypeCategory.COMPUTE,
            enforce_hook_typing=True,
        )
        with pytest.raises(HookTypeMismatchError):
            builder.build()

    def test_nondeterministic_compute_exact_match_only(self) -> None:
        """NONDETERMINISTIC_COMPUTE requires exact match."""
        hook = ModelPipelineHook(
            hook_id="nondeterministic",
            phase="execute",
            handler_type_category=EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE,
            callable_ref="module.func",
        )
        registry = create_frozen_registry(hook)

        # Match - should pass
        builder = RuntimePlanBuilder(
            registry=registry,
            contract_category=EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE,
            enforce_hook_typing=True,
        )
        plan, warnings = builder.build()
        assert len(warnings) == 0

        # Mismatch with COMPUTE - should fail
        builder2 = RuntimePlanBuilder(
            registry=registry,
            contract_category=EnumHandlerTypeCategory.COMPUTE,
            enforce_hook_typing=True,
        )
        with pytest.raises(HookTypeMismatchError):
            builder2.build()


@pytest.mark.unit
class TestDependencyValidation:
    """Test dependency graph validation."""

    def test_unknown_dependency_id_raises_error(self) -> None:
        """Unknown dependency raises UnknownDependencyError."""
        hook = ModelPipelineHook(
            hook_id="dependent",
            phase="execute",
            dependencies=["nonexistent"],
            callable_ref="module.func",
        )
        registry = create_frozen_registry(hook)
        builder = RuntimePlanBuilder(registry=registry)
        with pytest.raises(UnknownDependencyError) as exc_info:
            builder.build()
        assert "nonexistent" in str(exc_info.value)
        # Context is nested under additional_context.context due to ModelOnexError structure
        additional = exc_info.value.context.get("additional_context", {})
        inner_context = additional.get("context", {}) if additional else {}
        assert inner_context.get("validation_kind") == "unknown_dependency"

    def test_dependency_cycle_raises_error(self) -> None:
        """Dependency cycle raises DependencyCycleError."""
        hook_a = ModelPipelineHook(
            hook_id="hook-a",
            phase="execute",
            dependencies=["hook-b"],
            callable_ref="module.a",
        )
        hook_b = ModelPipelineHook(
            hook_id="hook-b",
            phase="execute",
            dependencies=["hook-a"],
            callable_ref="module.b",
        )
        registry = create_frozen_registry(hook_a, hook_b)
        builder = RuntimePlanBuilder(registry=registry)
        with pytest.raises(DependencyCycleError) as exc_info:
            builder.build()
        # Context is nested under additional_context.context due to ModelOnexError structure
        additional = exc_info.value.context.get("additional_context", {})
        inner_context = additional.get("context", {}) if additional else {}
        assert inner_context.get("validation_kind") == "dependency_cycle"

    def test_valid_dependency_chain_resolves(self) -> None:
        """Valid dependency chain resolves in correct order."""
        hook_a = ModelPipelineHook(
            hook_id="hook-a",
            phase="execute",
            callable_ref="module.a",
            priority=100,
        )
        hook_b = ModelPipelineHook(
            hook_id="hook-b",
            phase="execute",
            dependencies=["hook-a"],
            callable_ref="module.b",
            priority=100,
        )
        hook_c = ModelPipelineHook(
            hook_id="hook-c",
            phase="execute",
            dependencies=["hook-b"],
            callable_ref="module.c",
            priority=100,
        )
        registry = create_frozen_registry(hook_a, hook_b, hook_c)
        builder = RuntimePlanBuilder(registry=registry)
        plan, warnings = builder.build()

        hooks = plan.get_phase_hooks("execute")
        hook_ids = [h.hook_id for h in hooks]
        # a before b before c
        assert hook_ids.index("hook-a") < hook_ids.index("hook-b")
        assert hook_ids.index("hook-b") < hook_ids.index("hook-c")


@pytest.mark.unit
class TestTopologicalSorting:
    """Test topological sorting with priority tie-breaker."""

    def test_priority_determines_order_no_dependencies(self) -> None:
        """Lower priority executes first when no dependencies."""
        hook_high = ModelPipelineHook(
            hook_id="high-priority",
            phase="before",
            priority=10,
            callable_ref="module.high",
        )
        hook_low = ModelPipelineHook(
            hook_id="low-priority",
            phase="before",
            priority=200,
            callable_ref="module.low",
        )
        registry = create_frozen_registry(hook_low, hook_high)  # Register in wrong order
        builder = RuntimePlanBuilder(registry=registry)
        plan, _ = builder.build()

        hooks = plan.get_phase_hooks("before")
        assert hooks[0].hook_id == "high-priority"  # Lower priority value = first
        assert hooks[1].hook_id == "low-priority"

    def test_dependencies_override_priority(self) -> None:
        """Dependencies take precedence over priority."""
        hook_dep = ModelPipelineHook(
            hook_id="dependency",
            phase="execute",
            priority=999,  # Low priority but no dependencies
            callable_ref="module.dep",
        )
        hook_main = ModelPipelineHook(
            hook_id="main",
            phase="execute",
            priority=1,  # High priority but depends on dep
            dependencies=["dependency"],
            callable_ref="module.main",
        )
        registry = create_frozen_registry(hook_main, hook_dep)
        builder = RuntimePlanBuilder(registry=registry)
        plan, _ = builder.build()

        hooks = plan.get_phase_hooks("execute")
        hook_ids = [h.hook_id for h in hooks]
        assert hook_ids.index("dependency") < hook_ids.index("main")

    def test_multiple_phases_sorted_independently(self) -> None:
        """Each phase is sorted independently."""
        before_hook = ModelPipelineHook(
            hook_id="before",
            phase="before",
            callable_ref="module.before",
        )
        execute_hook = ModelPipelineHook(
            hook_id="execute",
            phase="execute",
            callable_ref="module.execute",
        )
        registry = create_frozen_registry(before_hook, execute_hook)
        builder = RuntimePlanBuilder(registry=registry)
        plan, _ = builder.build()

        assert plan.get_phase_hooks("before") == [before_hook]
        assert plan.get_phase_hooks("execute") == [execute_hook]


@pytest.mark.unit
class TestEmptyRegistry:
    """Test behavior with empty registry."""

    def test_empty_registry_produces_empty_plan(self) -> None:
        """Empty registry produces empty plan with no warnings."""
        registry = HookRegistry()
        registry.freeze()
        builder = RuntimePlanBuilder(registry=registry)
        plan, warnings = builder.build()

        assert plan.total_hooks == 0
        assert len(warnings) == 0


@pytest.mark.unit
class TestCrossPhaseDepedencies:
    """Test cross-phase dependency handling."""

    def test_cross_phase_dependency_is_unknown(self) -> None:
        """Dependencies must be within same phase - cross-phase is unknown."""
        # Hook in 'before' phase depends on hook in 'execute' phase
        # This is invalid - dependencies are resolved per-phase
        before_hook = ModelPipelineHook(
            hook_id="before-hook",
            phase="before",
            dependencies=["execute-hook"],  # This is in a different phase
            callable_ref="module.before",
        )
        execute_hook = ModelPipelineHook(
            hook_id="execute-hook",
            phase="execute",
            callable_ref="module.execute",
        )
        registry = create_frozen_registry(before_hook, execute_hook)
        builder = RuntimePlanBuilder(registry=registry)

        # The 'execute-hook' won't be found in the 'before' phase
        with pytest.raises(UnknownDependencyError):
            builder.build()


@pytest.mark.unit
class TestComplexDependencyGraphs:
    """Test complex dependency scenarios."""

    def test_diamond_dependency(self) -> None:
        """Diamond dependency pattern resolves correctly."""
        #     A
        #    / \
        #   B   C
        #    \ /
        #     D
        hook_a = ModelPipelineHook(
            hook_id="A",
            phase="execute",
            callable_ref="module.a",
            priority=1,
        )
        hook_b = ModelPipelineHook(
            hook_id="B",
            phase="execute",
            dependencies=["A"],
            callable_ref="module.b",
            priority=1,
        )
        hook_c = ModelPipelineHook(
            hook_id="C",
            phase="execute",
            dependencies=["A"],
            callable_ref="module.c",
            priority=2,
        )
        hook_d = ModelPipelineHook(
            hook_id="D",
            phase="execute",
            dependencies=["B", "C"],
            callable_ref="module.d",
            priority=1,
        )
        registry = create_frozen_registry(hook_d, hook_c, hook_b, hook_a)
        builder = RuntimePlanBuilder(registry=registry)
        plan, _ = builder.build()

        hooks = plan.get_phase_hooks("execute")
        hook_ids = [h.hook_id for h in hooks]

        # A must be first
        assert hook_ids[0] == "A"
        # D must be last
        assert hook_ids[-1] == "D"
        # B and C must be after A and before D
        assert hook_ids.index("B") > hook_ids.index("A")
        assert hook_ids.index("C") > hook_ids.index("A")
        assert hook_ids.index("B") < hook_ids.index("D")
        assert hook_ids.index("C") < hook_ids.index("D")

    def test_longer_cycle_detected(self) -> None:
        """Longer dependency cycles are detected."""
        # A -> B -> C -> A
        hook_a = ModelPipelineHook(
            hook_id="A",
            phase="execute",
            dependencies=["C"],
            callable_ref="module.a",
        )
        hook_b = ModelPipelineHook(
            hook_id="B",
            phase="execute",
            dependencies=["A"],
            callable_ref="module.b",
        )
        hook_c = ModelPipelineHook(
            hook_id="C",
            phase="execute",
            dependencies=["B"],
            callable_ref="module.c",
        )
        registry = create_frozen_registry(hook_a, hook_b, hook_c)
        builder = RuntimePlanBuilder(registry=registry)

        with pytest.raises(DependencyCycleError):
            builder.build()


@pytest.mark.unit
class TestContractCategoryNone:
    """Test behavior when contract_category is None."""

    def test_no_contract_category_skips_type_validation(self) -> None:
        """When contract_category is None, type validation is skipped."""
        hook = ModelPipelineHook(
            hook_id="typed-hook",
            phase="execute",
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            callable_ref="module.func",
        )
        registry = create_frozen_registry(hook)
        builder = RuntimePlanBuilder(
            registry=registry,
            contract_category=None,  # No contract category
            enforce_hook_typing=True,
        )
        plan, warnings = builder.build()

        # Should pass without warnings - no contract to validate against
        assert len(warnings) == 0
        assert plan.total_hooks == 1
