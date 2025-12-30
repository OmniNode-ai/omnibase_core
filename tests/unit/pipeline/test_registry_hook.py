# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for RegistryHook."""

import pytest

from omnibase_core.pipeline.exceptions import (
    DuplicateHookError,
    HookRegistryFrozenError,
)
from omnibase_core.pipeline.registry_hook import RegistryHook
from omnibase_core.pipeline.models import ModelPipelineHook, PipelinePhase


@pytest.mark.unit
class TestRegistryHookRegistration:
    """Test hook registration functionality."""

    @pytest.mark.unit
    def test_register_hook_success(self) -> None:
        """Test successful hook registration."""
        registry = RegistryHook()
        hook = ModelPipelineHook(
            hook_id="test-hook",
            phase="execute",
            callable_ref="module.path.func",
        )
        registry.register(hook)
        assert registry.get_hooks_by_phase("execute") == [hook]

    @pytest.mark.unit
    def test_register_multiple_hooks_same_phase(self) -> None:
        """Test registering multiple hooks in same phase."""
        registry = RegistryHook()
        hook1 = ModelPipelineHook(
            hook_id="hook-1",
            phase="before",
            callable_ref="module.func1",
        )
        hook2 = ModelPipelineHook(
            hook_id="hook-2",
            phase="before",
            callable_ref="module.func2",
        )
        registry.register(hook1)
        registry.register(hook2)
        hooks = registry.get_hooks_by_phase("before")
        assert len(hooks) == 2
        assert hook1 in hooks
        assert hook2 in hooks

    @pytest.mark.unit
    def test_register_hooks_different_phases(self) -> None:
        """Test registering hooks in different phases."""
        registry = RegistryHook()
        hook1 = ModelPipelineHook(
            hook_id="preflight-hook",
            phase="preflight",
            callable_ref="module.preflight",
        )
        hook2 = ModelPipelineHook(
            hook_id="finalize-hook",
            phase="finalize",
            callable_ref="module.finalize",
        )
        registry.register(hook1)
        registry.register(hook2)
        assert registry.get_hooks_by_phase("preflight") == [hook1]
        assert registry.get_hooks_by_phase("finalize") == [hook2]

    @pytest.mark.unit
    def test_get_hooks_empty_phase(self) -> None:
        """Test getting hooks from phase with no registrations."""
        registry = RegistryHook()
        assert registry.get_hooks_by_phase("execute") == []

    @pytest.mark.unit
    def test_get_all_hooks(self) -> None:
        """Test getting all registered hooks."""
        registry = RegistryHook()
        hook1 = ModelPipelineHook(
            hook_id="hook-1",
            phase="before",
            callable_ref="module.func1",
        )
        hook2 = ModelPipelineHook(
            hook_id="hook-2",
            phase="after",
            callable_ref="module.func2",
        )
        registry.register(hook1)
        registry.register(hook2)
        all_hooks = registry.get_all_hooks()
        assert len(all_hooks) == 2

    @pytest.mark.unit
    def test_get_hook_by_id(self) -> None:
        """Test getting a hook by its ID."""
        registry = RegistryHook()
        hook = ModelPipelineHook(
            hook_id="my-hook",
            phase="execute",
            callable_ref="module.func",
        )
        registry.register(hook)
        assert registry.get_hook_by_id("my-hook") == hook
        assert registry.get_hook_by_id("nonexistent") is None


@pytest.mark.unit
class TestRegistryHookDuplicateRejection:
    """Test duplicate hook ID rejection."""

    @pytest.mark.unit
    def test_duplicate_hook_id_raises_error(self) -> None:
        """Test that registering duplicate hook ID raises error."""
        registry = RegistryHook()
        hook1 = ModelPipelineHook(
            hook_id="duplicate-id",
            phase="before",
            callable_ref="module.func1",
        )
        hook2 = ModelPipelineHook(
            hook_id="duplicate-id",
            phase="after",
            callable_ref="module.func2",
        )
        registry.register(hook1)
        with pytest.raises(DuplicateHookError) as exc_info:
            registry.register(hook2)
        assert "duplicate-id" in str(exc_info.value)


@pytest.mark.unit
class TestRegistryHookFreeze:
    """Test freeze-after-init pattern."""

    @pytest.mark.unit
    def test_freeze_prevents_registration(self) -> None:
        """Test that freeze() prevents further registrations."""
        registry = RegistryHook()
        hook = ModelPipelineHook(
            hook_id="pre-freeze",
            phase="execute",
            callable_ref="module.func",
        )
        registry.register(hook)
        registry.freeze()

        new_hook = ModelPipelineHook(
            hook_id="post-freeze",
            phase="execute",
            callable_ref="module.func2",
        )
        with pytest.raises(HookRegistryFrozenError):
            registry.register(new_hook)

    @pytest.mark.unit
    def test_is_frozen_property(self) -> None:
        """Test is_frozen property."""
        registry = RegistryHook()
        assert not registry.is_frozen
        registry.freeze()
        assert registry.is_frozen

    @pytest.mark.unit
    def test_freeze_idempotent(self) -> None:
        """Test that calling freeze() multiple times is safe."""
        registry = RegistryHook()
        registry.freeze()
        registry.freeze()  # Should not raise
        assert registry.is_frozen

    @pytest.mark.unit
    def test_reads_allowed_after_freeze(self) -> None:
        """Test that read operations work after freeze."""
        registry = RegistryHook()
        hook = ModelPipelineHook(
            hook_id="hook",
            phase="execute",
            callable_ref="module.func",
        )
        registry.register(hook)
        registry.freeze()

        # All reads should work
        assert registry.get_hooks_by_phase("execute") == [hook]
        assert registry.get_all_hooks() == [hook]
        assert registry.get_hook_by_id("hook") == hook
        assert registry.is_frozen


@pytest.mark.unit
class TestRegistryHookThreadSafety:
    """Test thread safety invariants."""

    @pytest.mark.unit
    def test_frozen_registry_returns_copies(self) -> None:
        """Test that frozen registry returns copies, not internal state."""
        registry = RegistryHook()
        hook = ModelPipelineHook(
            hook_id="hook",
            phase="execute",
            callable_ref="module.func",
        )
        registry.register(hook)
        registry.freeze()

        # Get hooks twice - should be equal but not same object
        hooks1 = registry.get_hooks_by_phase("execute")
        hooks2 = registry.get_hooks_by_phase("execute")
        assert hooks1 == hooks2
        # Modifying returned list shouldn't affect registry
        hooks1.clear()
        assert registry.get_hooks_by_phase("execute") == [hook]
