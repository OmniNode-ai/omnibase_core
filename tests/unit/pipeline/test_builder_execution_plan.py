# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for BuilderExecutionPlan."""

import pytest

from omnibase_core.enums.enum_handler_type_category import EnumHandlerTypeCategory
from omnibase_core.models.pipeline import ModelPipelineHook
from omnibase_core.pipeline.builder_execution_plan import BuilderExecutionPlan
from omnibase_core.pipeline.exceptions import (
    DependencyCycleError,
    HookTypeMismatchError,
    UnknownDependencyError,
)
from omnibase_core.pipeline.registry_hook import RegistryHook


def create_frozen_registry(*hooks: ModelPipelineHook) -> RegistryHook:
    """Helper to create a frozen registry with hooks."""
    registry = RegistryHook()
    for hook in hooks:
        registry.register(hook)
    registry.freeze()
    return registry


@pytest.mark.unit
class TestBuilderExecutionPlanHookTypingValidation:
    """Test hook typing validation per the matrix."""

    @pytest.mark.unit
    def test_generic_hook_validates_for_compute(self) -> None:
        """Generic hook (None category) passes for COMPUTE contract."""
        hook = ModelPipelineHook(
            hook_name="generic",
            phase="execute",
            handler_type_category=None,
            callable_ref="module.func",
        )
        registry = create_frozen_registry(hook)
        builder = BuilderExecutionPlan(
            registry=registry,
            contract_category=EnumHandlerTypeCategory.COMPUTE,
            enforce_hook_typing=True,
        )
        plan, warnings = builder.build()
        assert len(warnings) == 0
        assert plan.total_hooks == 1

    @pytest.mark.unit
    def test_generic_hook_validates_for_effect(self) -> None:
        """Generic hook (None category) passes for EFFECT contract."""
        hook = ModelPipelineHook(
            hook_name="generic",
            phase="execute",
            handler_type_category=None,
            callable_ref="module.func",
        )
        registry = create_frozen_registry(hook)
        builder = BuilderExecutionPlan(
            registry=registry,
            contract_category=EnumHandlerTypeCategory.EFFECT,
            enforce_hook_typing=True,
        )
        _plan, warnings = builder.build()
        assert len(warnings) == 0

    @pytest.mark.unit
    def test_typed_compute_hook_passes_on_compute_contract(self) -> None:
        """COMPUTE hook passes on COMPUTE contract."""
        hook = ModelPipelineHook(
            hook_name="compute-hook",
            phase="execute",
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            callable_ref="module.func",
        )
        registry = create_frozen_registry(hook)
        builder = BuilderExecutionPlan(
            registry=registry,
            contract_category=EnumHandlerTypeCategory.COMPUTE,
            enforce_hook_typing=True,
        )
        _plan, warnings = builder.build()
        assert len(warnings) == 0

    @pytest.mark.unit
    def test_typed_compute_hook_fails_on_effect_contract_when_enforced(self) -> None:
        """COMPUTE hook on EFFECT contract raises error when enforced."""
        hook = ModelPipelineHook(
            hook_name="compute-hook",
            phase="execute",
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            callable_ref="module.func",
        )
        registry = create_frozen_registry(hook)
        builder = BuilderExecutionPlan(
            registry=registry,
            contract_category=EnumHandlerTypeCategory.EFFECT,
            enforce_hook_typing=True,
        )
        with pytest.raises(HookTypeMismatchError) as exc_info:
            builder.build()
        assert "compute-hook" in str(exc_info.value)

    @pytest.mark.unit
    def test_typed_compute_hook_warns_on_effect_contract_when_not_enforced(
        self,
    ) -> None:
        """COMPUTE hook on EFFECT contract produces warning when not enforced."""
        hook = ModelPipelineHook(
            hook_name="compute-hook",
            phase="execute",
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            callable_ref="module.func",
        )
        registry = create_frozen_registry(hook)
        builder = BuilderExecutionPlan(
            registry=registry,
            contract_category=EnumHandlerTypeCategory.EFFECT,
            enforce_hook_typing=False,
        )
        _plan, warnings = builder.build()
        assert len(warnings) == 1
        assert warnings[0].code == "HOOK_TYPE_MISMATCH"
        assert "compute-hook" in warnings[0].context.get("hook_name", "")

    @pytest.mark.unit
    def test_typed_effect_hook_fails_on_compute_contract_when_enforced(self) -> None:
        """EFFECT hook on COMPUTE contract raises error when enforced."""
        hook = ModelPipelineHook(
            hook_name="effect-hook",
            phase="execute",
            handler_type_category=EnumHandlerTypeCategory.EFFECT,
            callable_ref="module.func",
        )
        registry = create_frozen_registry(hook)
        builder = BuilderExecutionPlan(
            registry=registry,
            contract_category=EnumHandlerTypeCategory.COMPUTE,
            enforce_hook_typing=True,
        )
        with pytest.raises(HookTypeMismatchError):
            builder.build()

    @pytest.mark.unit
    def test_nondeterministic_compute_exact_match_only(self) -> None:
        """NONDETERMINISTIC_COMPUTE requires exact match."""
        hook = ModelPipelineHook(
            hook_name="nondeterministic",
            phase="execute",
            handler_type_category=EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE,
            callable_ref="module.func",
        )
        registry = create_frozen_registry(hook)

        # Match - should pass
        builder = BuilderExecutionPlan(
            registry=registry,
            contract_category=EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE,
            enforce_hook_typing=True,
        )
        _plan, warnings = builder.build()
        assert len(warnings) == 0

        # Mismatch with COMPUTE - should fail
        builder2 = BuilderExecutionPlan(
            registry=registry,
            contract_category=EnumHandlerTypeCategory.COMPUTE,
            enforce_hook_typing=True,
        )
        with pytest.raises(HookTypeMismatchError):
            builder2.build()


@pytest.mark.unit
class TestBuilderExecutionPlanDependencyValidation:
    """Test dependency graph validation."""

    @pytest.mark.unit
    def test_unknown_dependency_id_raises_error(self) -> None:
        """Unknown dependency raises UnknownDependencyError."""
        hook = ModelPipelineHook(
            hook_name="dependent",
            phase="execute",
            dependencies=["nonexistent"],
            callable_ref="module.func",
        )
        registry = create_frozen_registry(hook)
        builder = BuilderExecutionPlan(registry=registry)
        with pytest.raises(UnknownDependencyError) as exc_info:
            builder.build()
        assert "nonexistent" in str(exc_info.value)
        # Context is nested under additional_context.context due to ModelOnexError structure
        additional = exc_info.value.context.get("additional_context", {})
        inner_context = additional.get("context", {}) if additional else {}
        assert inner_context.get("validation_kind") == "unknown_dependency"

    @pytest.mark.unit
    def test_dependency_cycle_raises_error(self) -> None:
        """Dependency cycle raises DependencyCycleError."""
        hook_a = ModelPipelineHook(
            hook_name="hook-a",
            phase="execute",
            dependencies=["hook-b"],
            callable_ref="module.a",
        )
        hook_b = ModelPipelineHook(
            hook_name="hook-b",
            phase="execute",
            dependencies=["hook-a"],
            callable_ref="module.b",
        )
        registry = create_frozen_registry(hook_a, hook_b)
        builder = BuilderExecutionPlan(registry=registry)
        with pytest.raises(DependencyCycleError) as exc_info:
            builder.build()
        # Context is nested under additional_context.context due to ModelOnexError structure
        additional = exc_info.value.context.get("additional_context", {})
        inner_context = additional.get("context", {}) if additional else {}
        assert inner_context.get("validation_kind") == "dependency_cycle"

    @pytest.mark.unit
    def test_valid_dependency_chain_resolves(self) -> None:
        """Valid dependency chain resolves in correct order."""
        hook_a = ModelPipelineHook(
            hook_name="hook-a",
            phase="execute",
            callable_ref="module.a",
            priority=100,
        )
        hook_b = ModelPipelineHook(
            hook_name="hook-b",
            phase="execute",
            dependencies=["hook-a"],
            callable_ref="module.b",
            priority=100,
        )
        hook_c = ModelPipelineHook(
            hook_name="hook-c",
            phase="execute",
            dependencies=["hook-b"],
            callable_ref="module.c",
            priority=100,
        )
        registry = create_frozen_registry(hook_a, hook_b, hook_c)
        builder = BuilderExecutionPlan(registry=registry)
        plan, _warnings = builder.build()

        hooks = plan.get_phase_hooks("execute")
        hook_names = [h.hook_name for h in hooks]
        # a before b before c
        assert hook_names.index("hook-a") < hook_names.index("hook-b")
        assert hook_names.index("hook-b") < hook_names.index("hook-c")


@pytest.mark.unit
class TestBuilderExecutionPlanTopologicalSorting:
    """Test topological sorting with priority tie-breaker."""

    @pytest.mark.unit
    def test_priority_determines_order_no_dependencies(self) -> None:
        """Lower priority executes first when no dependencies."""
        hook_high = ModelPipelineHook(
            hook_name="high-priority",
            phase="before",
            priority=10,
            callable_ref="module.high",
        )
        hook_low = ModelPipelineHook(
            hook_name="low-priority",
            phase="before",
            priority=200,
            callable_ref="module.low",
        )
        registry = create_frozen_registry(
            hook_low, hook_high
        )  # Register in wrong order
        builder = BuilderExecutionPlan(registry=registry)
        plan, _ = builder.build()

        hooks = plan.get_phase_hooks("before")
        assert hooks[0].hook_name == "high-priority"  # Lower priority value = first
        assert hooks[1].hook_name == "low-priority"

    @pytest.mark.unit
    def test_dependencies_override_priority(self) -> None:
        """Dependencies take precedence over priority."""
        hook_dep = ModelPipelineHook(
            hook_name="dependency",
            phase="execute",
            priority=999,  # Low priority but no dependencies
            callable_ref="module.dep",
        )
        hook_main = ModelPipelineHook(
            hook_name="main",
            phase="execute",
            priority=1,  # High priority but depends on dep
            dependencies=["dependency"],
            callable_ref="module.main",
        )
        registry = create_frozen_registry(hook_main, hook_dep)
        builder = BuilderExecutionPlan(registry=registry)
        plan, _ = builder.build()

        hooks = plan.get_phase_hooks("execute")
        hook_names = [h.hook_name for h in hooks]
        assert hook_names.index("dependency") < hook_names.index("main")

    @pytest.mark.unit
    def test_multiple_phases_sorted_independently(self) -> None:
        """Each phase is sorted independently."""
        before_hook = ModelPipelineHook(
            hook_name="before",
            phase="before",
            callable_ref="module.before",
        )
        execute_hook = ModelPipelineHook(
            hook_name="execute",
            phase="execute",
            callable_ref="module.execute",
        )
        registry = create_frozen_registry(before_hook, execute_hook)
        builder = BuilderExecutionPlan(registry=registry)
        plan, _ = builder.build()

        assert plan.get_phase_hooks("before") == [before_hook]
        assert plan.get_phase_hooks("execute") == [execute_hook]


@pytest.mark.unit
class TestBuilderExecutionPlanEmptyRegistry:
    """Test behavior with empty registry."""

    @pytest.mark.unit
    def test_empty_registry_produces_empty_plan(self) -> None:
        """Empty registry produces empty plan with no warnings."""
        registry = RegistryHook()
        registry.freeze()
        builder = BuilderExecutionPlan(registry=registry)
        plan, warnings = builder.build()

        assert plan.total_hooks == 0
        assert len(warnings) == 0


@pytest.mark.unit
class TestBuilderExecutionPlanCrossPhaseDependencies:
    """Test cross-phase dependency handling."""

    @pytest.mark.unit
    def test_cross_phase_dependency_is_unknown(self) -> None:
        """Dependencies must be within same phase - cross-phase is unknown."""
        # Hook in 'before' phase depends on hook in 'execute' phase
        # This is invalid - dependencies are resolved per-phase
        before_hook = ModelPipelineHook(
            hook_name="before-hook",
            phase="before",
            dependencies=["execute-hook"],  # This is in a different phase
            callable_ref="module.before",
        )
        execute_hook = ModelPipelineHook(
            hook_name="execute-hook",
            phase="execute",
            callable_ref="module.execute",
        )
        registry = create_frozen_registry(before_hook, execute_hook)
        builder = BuilderExecutionPlan(registry=registry)

        # The 'execute-hook' won't be found in the 'before' phase
        with pytest.raises(UnknownDependencyError):
            builder.build()


@pytest.mark.unit
class TestBuilderExecutionPlanComplexDependencyGraphs:
    """Test complex dependency scenarios."""

    @pytest.mark.unit
    def test_diamond_dependency(self) -> None:
        """Diamond dependency pattern resolves correctly."""
        #     A
        #    / \
        #   B   C
        #    \ /
        #     D
        hook_a = ModelPipelineHook(
            hook_name="A",
            phase="execute",
            callable_ref="module.a",
            priority=1,
        )
        hook_b = ModelPipelineHook(
            hook_name="B",
            phase="execute",
            dependencies=["A"],
            callable_ref="module.b",
            priority=1,
        )
        hook_c = ModelPipelineHook(
            hook_name="C",
            phase="execute",
            dependencies=["A"],
            callable_ref="module.c",
            priority=2,
        )
        hook_d = ModelPipelineHook(
            hook_name="D",
            phase="execute",
            dependencies=["B", "C"],
            callable_ref="module.d",
            priority=1,
        )
        registry = create_frozen_registry(hook_d, hook_c, hook_b, hook_a)
        builder = BuilderExecutionPlan(registry=registry)
        plan, _ = builder.build()

        hooks = plan.get_phase_hooks("execute")
        hook_names = [h.hook_name for h in hooks]

        # A must be first
        assert hook_names[0] == "A"
        # D must be last
        assert hook_names[-1] == "D"
        # B and C must be after A and before D
        assert hook_names.index("B") > hook_names.index("A")
        assert hook_names.index("C") > hook_names.index("A")
        assert hook_names.index("B") < hook_names.index("D")
        assert hook_names.index("C") < hook_names.index("D")

    @pytest.mark.unit
    def test_longer_cycle_detected(self) -> None:
        """Longer dependency cycles are detected."""
        # A -> B -> C -> A
        hook_a = ModelPipelineHook(
            hook_name="A",
            phase="execute",
            dependencies=["C"],
            callable_ref="module.a",
        )
        hook_b = ModelPipelineHook(
            hook_name="B",
            phase="execute",
            dependencies=["A"],
            callable_ref="module.b",
        )
        hook_c = ModelPipelineHook(
            hook_name="C",
            phase="execute",
            dependencies=["B"],
            callable_ref="module.c",
        )
        registry = create_frozen_registry(hook_a, hook_b, hook_c)
        builder = BuilderExecutionPlan(registry=registry)

        with pytest.raises(DependencyCycleError):
            builder.build()


@pytest.mark.unit
class TestBuilderExecutionPlanContractCategoryNone:
    """Test behavior when contract_category is None."""

    @pytest.mark.unit
    def test_no_contract_category_skips_type_validation(self) -> None:
        """When contract_category is None, type validation is skipped."""
        hook = ModelPipelineHook(
            hook_name="typed-hook",
            phase="execute",
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            callable_ref="module.func",
        )
        registry = create_frozen_registry(hook)
        builder = BuilderExecutionPlan(
            registry=registry,
            contract_category=None,  # No contract category
            enforce_hook_typing=True,
        )
        plan, warnings = builder.build()

        # Should pass without warnings - no contract to validate against
        assert len(warnings) == 0
        assert plan.total_hooks == 1


@pytest.mark.unit
class TestBuilderExecutionPlanCycleLogging:
    """Test dependency cycle debug logging."""

    @pytest.mark.unit
    def test_cycle_detection_logs_dependency_graph(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Verify that dependency cycle detection logs the dependency graph.

        Note: Cycle detection logging uses emit_log_event which writes to stdout,
        so we use capsys instead of caplog to capture the output.
        """
        hook_a = ModelPipelineHook(
            hook_name="hook-a",
            phase="execute",
            dependencies=["hook-b"],
            callable_ref="module.a",
        )
        hook_b = ModelPipelineHook(
            hook_name="hook-b",
            phase="execute",
            dependencies=["hook-a"],
            callable_ref="module.b",
        )
        registry = create_frozen_registry(hook_a, hook_b)
        builder = BuilderExecutionPlan(registry=registry)

        with pytest.raises(DependencyCycleError):
            builder.build()

        # Capture stdout where emit_log_event writes
        captured = capsys.readouterr()
        log_text = captured.out

        # Verify log message was captured
        assert "Dependency cycle detected" in log_text, (
            "Expected cycle detection log not found"
        )
        assert "[DEBUG]" in log_text

        # Verify log content includes required information
        assert "phase 'execute'" in log_text
        assert "hook-a" in log_text
        assert "hook-b" in log_text
        assert "depends_on=" in log_text
        assert "in_degree=" in log_text
        assert "Hooks in cycle:" in log_text

    @pytest.mark.unit
    def test_cycle_detection_logs_longer_cycle(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Verify that longer cycles log all involved hooks.

        Note: Cycle detection logging uses emit_log_event which writes to stdout,
        so we use capsys instead of caplog to capture the output.
        """
        # A -> B -> C -> A
        hook_a = ModelPipelineHook(
            hook_name="A",
            phase="execute",
            dependencies=["C"],
            callable_ref="module.a",
        )
        hook_b = ModelPipelineHook(
            hook_name="B",
            phase="execute",
            dependencies=["A"],
            callable_ref="module.b",
        )
        hook_c = ModelPipelineHook(
            hook_name="C",
            phase="execute",
            dependencies=["B"],
            callable_ref="module.c",
        )
        registry = create_frozen_registry(hook_a, hook_b, hook_c)
        builder = BuilderExecutionPlan(registry=registry)

        with pytest.raises(DependencyCycleError):
            builder.build()

        # Capture stdout where emit_log_event writes
        captured = capsys.readouterr()
        log_text = captured.out

        # Verify log message was captured
        assert "Dependency cycle detected" in log_text

        # All three hooks should be mentioned in the graph
        assert "A:" in log_text
        assert "B:" in log_text
        assert "C:" in log_text

        # All should have in_degree > 0 since they're all in the cycle
        assert "in_degree=1" in log_text
