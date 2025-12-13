"""
Unit tests for declarative node purity linter - Legacy mixin import detection.

AST-based detection of forbidden legacy mixin imports in pure/declarative nodes.
Pure nodes (NodeCompute, NodeReducer) must only use approved mixins
that are compatible with the declarative architecture.

FORBIDDEN MIXINS in declarative nodes:
- MixinEventBus - Event bus access violates declarative purity
- MixinEventDrivenNode - Event-driven patterns not compatible
- MixinEventHandler - Event handling not allowed
- MixinEventListener - Event listening not allowed
- MixinServiceRegistry - Service registry access violates declarative purity

ALLOWED MIXINS in declarative nodes:
- MixinFSMExecution - FSM is core to reducers
- MixinWorkflowExecution - Workflow is core to orchestrators
- MixinContractMetadata - Contract metadata is allowed
- MixinNodeLifecycle - Lifecycle is allowed
- MixinDiscoveryResponder - Discovery is allowed

Ticket: OMN-203
"""

from __future__ import annotations

import ast
import importlib.util
import sys
import textwrap
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest


def _load_check_node_purity_module() -> ModuleType:
    """Load the check_node_purity module without modifying sys.path.

    Uses importlib.util to load the script module directly from its file path.
    This avoids mutating global sys.path state, which is problematic for:
    - Parallel test execution (pytest-xdist)
    - Test isolation
    - Cleanup reliability

    Note: The module is registered in sys.modules because dataclasses requires
    the module to be findable via sys.modules[cls.__module__] during class
    decoration. This is a minimal and safe modification compared to sys.path
    manipulation.

    Returns:
        The loaded check_node_purity module.

    Raises:
        FileNotFoundError: If the script file doesn't exist.
        ImportError: If the module cannot be loaded.
    """
    script_path = (
        Path(__file__).parent.parent.parent.parent / "scripts" / "check_node_purity.py"
    )
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    spec = importlib.util.spec_from_file_location("check_node_purity", script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create module spec for: {script_path}")

    module = importlib.util.module_from_spec(spec)
    # Register in sys.modules before exec_module - required for dataclasses
    # to resolve the module's __dict__ during class decoration
    sys.modules["check_node_purity"] = module
    spec.loader.exec_module(module)
    return module


# Load module at module level for efficiency (loaded once per test session)
_purity_module = _load_check_node_purity_module()

# Extract the classes/enums we need from the loaded module
NodeTypeFinder = _purity_module.NodeTypeFinder
PurityAnalyzer = _purity_module.PurityAnalyzer
Severity = _purity_module.Severity
ViolationType = _purity_module.ViolationType

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def analyze_source() -> Callable[[str], PurityAnalyzer]:
    """Factory fixture to analyze source code directly using two-pass approach."""

    def _analyze(source_code: str) -> PurityAnalyzer:
        source = textwrap.dedent(source_code).strip()
        source_lines = source.splitlines()
        tree = ast.parse(source)

        # First pass: Find node classes and determine if file contains pure nodes
        finder = NodeTypeFinder()
        finder.visit(tree)

        # Second pass: Analyze for purity violations
        analyzer = PurityAnalyzer(
            file_path=Path("test.py"),
            source_lines=source_lines,
            node_type=finder.node_type,
            node_class_name=finder.node_class_name,
            is_pure_node=finder.is_pure_node,
        )
        analyzer.visit(tree)
        return analyzer

    return _analyze


# ==============================================================================
# LEGACY MIXIN DETECTION TESTS
# ==============================================================================


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestLegacyMixinDetection:
    """Test detection of forbidden legacy mixin imports in declarative nodes."""

    # -------------------------------------------------------------------------
    # FORBIDDEN MIXIN TESTS - These should be detected as violations
    # -------------------------------------------------------------------------

    def test_detects_event_bus_mixin_import(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that MixinEventBus import is detected as violation.

        MixinEventBus provides direct event bus access which violates
        declarative purity. Declarative nodes should receive events
        through their input contract, not by subscribing directly.
        """
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.mixins.mixin_event_bus import MixinEventBus

        class NodeMyReducer(NodeCoreBase, MixinEventBus):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node, "Reducer should be classified as pure node"
        assert any(
            v.violation_type == ViolationType.LEGACY_MIXIN_IMPORT
            and "MixinEventBus" in v.message
            for v in analyzer.violations
        ), "MixinEventBus should be detected as forbidden mixin"

    def test_detects_event_driven_node_mixin_import(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that MixinEventDrivenNode import is detected as violation.

        MixinEventDrivenNode enables event-driven patterns which are
        incompatible with the declarative node architecture.
        """
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.mixins.mixin_event_driven_node import MixinEventDrivenNode

        class NodeMyReducer(NodeCoreBase, MixinEventDrivenNode):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        assert any(
            v.violation_type == ViolationType.LEGACY_MIXIN_IMPORT
            and "MixinEventDrivenNode" in v.message
            for v in analyzer.violations
        ), "MixinEventDrivenNode should be detected as forbidden mixin"

    def test_detects_event_handler_mixin_import(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that MixinEventHandler import is detected as violation.

        MixinEventHandler provides event handling capabilities which
        violate declarative purity constraints.
        """
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.mixins.mixin_event_handler import MixinEventHandler

        class NodeMyReducer(NodeCoreBase, MixinEventHandler):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        assert any(
            v.violation_type == ViolationType.LEGACY_MIXIN_IMPORT
            and "MixinEventHandler" in v.message
            for v in analyzer.violations
        ), "MixinEventHandler should be detected as forbidden mixin"

    def test_detects_event_listener_mixin_import(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that MixinEventListener import is detected as violation.

        MixinEventListener provides event listening capabilities which
        violate declarative purity constraints.
        """
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.mixins.mixin_event_listener import MixinEventListener

        class NodeMyReducer(NodeCoreBase, MixinEventListener):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        assert any(
            v.violation_type == ViolationType.LEGACY_MIXIN_IMPORT
            and "MixinEventListener" in v.message
            for v in analyzer.violations
        ), "MixinEventListener should be detected as forbidden mixin"

    def test_detects_service_registry_mixin_import(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that MixinServiceRegistry import is detected as violation.

        MixinServiceRegistry provides direct service registry access which
        violates declarative purity. Declarative nodes should use
        container-based dependency injection.
        """
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.mixins.mixin_service_registry import MixinServiceRegistry

        class NodeMyReducer(NodeCoreBase, MixinServiceRegistry):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        assert any(
            v.violation_type == ViolationType.LEGACY_MIXIN_IMPORT
            and "MixinServiceRegistry" in v.message
            for v in analyzer.violations
        ), "MixinServiceRegistry should be detected as forbidden mixin"

    # -------------------------------------------------------------------------
    # ALLOWED MIXIN TESTS - These should NOT be detected as violations
    # -------------------------------------------------------------------------

    def test_allows_fsm_execution_mixin(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that MixinFSMExecution is allowed (core to reducers).

        MixinFSMExecution provides FSM execution capabilities which
        are essential for reducer nodes and allowed in declarative context.
        """
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.mixins.mixin_fsm_execution import MixinFSMExecution

        class NodeMyReducer(NodeCoreBase, MixinFSMExecution):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        legacy_mixin_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.LEGACY_MIXIN_IMPORT
        ]
        assert len(legacy_mixin_violations) == 0, (
            "MixinFSMExecution should be allowed in declarative nodes"
        )

    def test_allows_workflow_execution_mixin(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that MixinWorkflowExecution is allowed (core to orchestrators).

        MixinWorkflowExecution provides workflow execution capabilities which
        are essential for orchestrator nodes and allowed in declarative context.
        """
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.mixins.mixin_workflow_execution import MixinWorkflowExecution

        class NodeMyReducer(NodeCoreBase, MixinWorkflowExecution):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        legacy_mixin_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.LEGACY_MIXIN_IMPORT
        ]
        assert len(legacy_mixin_violations) == 0, (
            "MixinWorkflowExecution should be allowed in declarative nodes"
        )

    def test_allows_contract_metadata_mixin(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that MixinContractMetadata is allowed.

        MixinContractMetadata provides contract metadata capabilities which
        are compatible with declarative architecture.
        """
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.mixins.mixin_contract_metadata import MixinContractMetadata

        class NodeMyReducer(NodeCoreBase, MixinContractMetadata):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        legacy_mixin_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.LEGACY_MIXIN_IMPORT
        ]
        assert len(legacy_mixin_violations) == 0, (
            "MixinContractMetadata should be allowed in declarative nodes"
        )

    def test_allows_node_lifecycle_mixin(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that MixinNodeLifecycle is allowed.

        MixinNodeLifecycle provides lifecycle management which is
        compatible with declarative architecture.
        """
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.mixins.mixin_node_lifecycle import MixinNodeLifecycle

        class NodeMyReducer(NodeCoreBase, MixinNodeLifecycle):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        legacy_mixin_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.LEGACY_MIXIN_IMPORT
        ]
        assert len(legacy_mixin_violations) == 0, (
            "MixinNodeLifecycle should be allowed in declarative nodes"
        )

    def test_allows_discovery_responder_mixin(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that MixinDiscoveryResponder is allowed.

        MixinDiscoveryResponder provides discovery capabilities which are
        compatible with declarative architecture.
        """
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.mixins.mixin_discovery_responder import MixinDiscoveryResponder

        class NodeMyReducer(NodeCoreBase, MixinDiscoveryResponder):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        legacy_mixin_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.LEGACY_MIXIN_IMPORT
        ]
        assert len(legacy_mixin_violations) == 0, (
            "MixinDiscoveryResponder should be allowed in declarative nodes"
        )

    # -------------------------------------------------------------------------
    # EDGE CASE TESTS
    # -------------------------------------------------------------------------

    def test_detects_multiple_forbidden_mixins(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that multiple forbidden mixin imports are all detected."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.mixins.mixin_event_bus import MixinEventBus
        from omnibase_core.mixins.mixin_event_handler import MixinEventHandler

        class NodeMyReducer(NodeCoreBase, MixinEventBus, MixinEventHandler):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        legacy_mixin_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.LEGACY_MIXIN_IMPORT
        ]
        # Should detect both forbidden mixins
        assert len(legacy_mixin_violations) >= 2, (
            "Both forbidden mixins should be detected"
        )

        violation_messages = " ".join(v.message for v in legacy_mixin_violations)
        assert "MixinEventBus" in violation_messages
        assert "MixinEventHandler" in violation_messages

    def test_detects_forbidden_mixin_mixed_with_allowed(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that forbidden mixin is detected even when mixed with allowed mixins."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.mixins.mixin_fsm_execution import MixinFSMExecution
        from omnibase_core.mixins.mixin_event_bus import MixinEventBus
        from omnibase_core.mixins.mixin_node_lifecycle import MixinNodeLifecycle

        class NodeMyReducer(NodeCoreBase, MixinFSMExecution, MixinEventBus, MixinNodeLifecycle):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        legacy_mixin_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.LEGACY_MIXIN_IMPORT
        ]
        # Should only detect MixinEventBus
        assert len(legacy_mixin_violations) == 1, (
            "Only forbidden mixin should be detected"
        )
        assert "MixinEventBus" in legacy_mixin_violations[0].message

    def test_forbidden_mixin_not_flagged_in_effect_nodes(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that forbidden mixins are NOT flagged in Effect nodes.

        Effect nodes are allowed to have side effects and can use
        any mixin they need for I/O operations.
        """
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.mixins.mixin_event_bus import MixinEventBus

        class NodeMyEffect(NodeCoreBase, MixinEventBus):
            pass
        """
        analyzer = analyze_source(source)

        # Effect nodes are NOT pure nodes
        assert analyzer.is_pure_node is False
        assert analyzer.node_type == "effect"
        # No violations should be recorded for effect nodes
        assert len(analyzer.violations) == 0

    def test_forbidden_mixin_not_flagged_in_orchestrator_nodes(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that forbidden mixins are NOT flagged in Orchestrator nodes.

        Orchestrator nodes coordinate workflows and may need event bus
        access for coordination purposes.
        """
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.mixins.mixin_event_bus import MixinEventBus

        class NodeMyOrchestrator(NodeCoreBase, MixinEventBus):
            pass
        """
        analyzer = analyze_source(source)

        # Orchestrator nodes are NOT pure nodes
        assert analyzer.is_pure_node is False
        assert analyzer.node_type == "orchestrator"
        # No violations should be recorded for orchestrator nodes
        assert len(analyzer.violations) == 0

    def test_detects_forbidden_mixin_in_compute_node(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that forbidden mixins are detected in Compute nodes.

        Compute nodes are pure nodes and should not use event-related mixins.
        """
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.mixins.mixin_event_bus import MixinEventBus

        class NodeMyCompute(NodeCoreBase, MixinEventBus):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        assert analyzer.node_type == "compute"
        assert any(
            v.violation_type == ViolationType.LEGACY_MIXIN_IMPORT
            and "MixinEventBus" in v.message
            for v in analyzer.violations
        ), "MixinEventBus should be detected in compute nodes"

    def test_detects_mixin_import_without_inheritance(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that forbidden mixin import is detected even without class inheritance.

        The import itself suggests intent to use the forbidden functionality.
        """
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.mixins.mixin_event_bus import MixinEventBus

        class NodeMyReducer(NodeCoreBase):
            def __init__(self, container):
                super().__init__(container)
                # Even without inheritance, the import suggests forbidden usage
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        assert any(
            v.violation_type == ViolationType.LEGACY_MIXIN_IMPORT
            and "MixinEventBus" in v.message
            for v in analyzer.violations
        ), "MixinEventBus import should be detected even without inheritance"


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestLegacyMixinViolationDetails:
    """Test violation details for legacy mixin detection."""

    def test_violation_has_correct_severity(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that legacy mixin violations have ERROR severity."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.mixins.mixin_event_bus import MixinEventBus

        class NodeMyReducer(NodeCoreBase, MixinEventBus):
            pass
        """
        analyzer = analyze_source(source)

        legacy_mixin_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.LEGACY_MIXIN_IMPORT
        ]
        assert len(legacy_mixin_violations) >= 1
        assert all(v.severity == Severity.ERROR for v in legacy_mixin_violations), (
            "Legacy mixin violations should have ERROR severity"
        )

    def test_violation_includes_suggestion(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that legacy mixin violations include helpful suggestions."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.mixins.mixin_event_bus import MixinEventBus

        class NodeMyReducer(NodeCoreBase, MixinEventBus):
            pass
        """
        analyzer = analyze_source(source)

        legacy_mixin_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.LEGACY_MIXIN_IMPORT
        ]
        assert len(legacy_mixin_violations) >= 1
        for violation in legacy_mixin_violations:
            assert len(violation.suggestion) > 0, "Violation should have a suggestion"
            # Suggestion should guide toward declarative patterns
            assert any(
                keyword in violation.suggestion.lower()
                for keyword in ["declarative", "contract", "effect", "remove"]
            ), f"Suggestion should mention alternatives: {violation.suggestion}"

    def test_violation_includes_line_number(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that legacy mixin violations include line numbers."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.mixins.mixin_event_bus import MixinEventBus

        class NodeMyReducer(NodeCoreBase, MixinEventBus):
            pass
        """
        analyzer = analyze_source(source)

        legacy_mixin_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.LEGACY_MIXIN_IMPORT
        ]
        assert len(legacy_mixin_violations) >= 1
        for violation in legacy_mixin_violations:
            assert violation.line_number > 0, "Violation should have line number"


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestLegacyMixinImportStyles:
    """Test detection of various import styles for legacy mixins."""

    def test_detects_direct_import(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test detection via 'from ... import MixinEventBus'."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.mixins.mixin_event_bus import MixinEventBus

        class NodeMyReducer(NodeCoreBase, MixinEventBus):
            pass
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.LEGACY_MIXIN_IMPORT
            for v in analyzer.violations
        )

    def test_detects_module_import(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test detection via 'import omnibase_core.mixins.mixin_event_bus'."""
        source = """
        import omnibase_core.mixins.mixin_event_bus
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyReducer(NodeCoreBase, omnibase_core.mixins.mixin_event_bus.MixinEventBus):
            pass
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.LEGACY_MIXIN_IMPORT
            for v in analyzer.violations
        ), "Module import style should be detected"

    def test_detects_aliased_import(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test detection via 'from ... import MixinEventBus as EventMixin'."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.mixins.mixin_event_bus import MixinEventBus as EventMixin

        class NodeMyReducer(NodeCoreBase, EventMixin):
            pass
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.LEGACY_MIXIN_IMPORT
            for v in analyzer.violations
        ), "Aliased import should be detected"


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestLegacyMixinInheritanceDetection:
    """Test detection of legacy mixin usage in class inheritance."""

    def test_detects_mixin_in_class_bases(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that mixin in class bases is detected."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.mixins.mixin_event_bus import MixinEventBus

        class NodeMyReducer(NodeCoreBase, MixinEventBus):
            def process(self):
                pass
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.LEGACY_MIXIN_IMPORT
            for v in analyzer.violations
        )

    def test_detects_mixin_in_nested_class(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that mixin usage in nested class is detected."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.mixins.mixin_event_bus import MixinEventBus

        class NodeMyReducer(NodeCoreBase):
            class InnerHelper(MixinEventBus):
                pass
        """
        analyzer = analyze_source(source)

        # The import itself should be flagged
        assert any(
            v.violation_type == ViolationType.LEGACY_MIXIN_IMPORT
            for v in analyzer.violations
        ), "Forbidden mixin import should be detected even if used in nested class"


# ==============================================================================
# ANY/DICT[ANY] IMPORT BLOCKING TESTS (OMN-203)
# ==============================================================================
#
# Tests for blocking typing.Any and Dict[str, Any] in declarative nodes
# (NodeCompute, NodeReducer). Implementation complete.
# ==============================================================================


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestAnyImportBlockingInDeclarativeNodes:
    """
    TDD tests for blocking 'from typing import Any' in declarative nodes.

    Declarative nodes (COMPUTE, REDUCER) should use strongly-typed models
    instead of Any to maintain type safety guarantees.

    Ticket: OMN-203
    """

    def test_detects_typing_any_import_in_compute_node(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that 'from typing import Any' is detected in COMPUTE nodes."""
        source = """
        from typing import Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node is True, (
            "Compute node should be classified as pure"
        )
        assert analyzer.node_type == "compute"
        assert any(
            v.violation_type == ViolationType.ANY_IMPORT for v in analyzer.violations
        ), "Expected ANY_IMPORT violation for 'from typing import Any'"

    def test_detects_typing_any_import_in_reducer_node(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that 'from typing import Any' is detected in REDUCER nodes."""
        source = """
        from typing import Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyReducer(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node is True, (
            "Reducer node should be classified as pure"
        )
        assert analyzer.node_type == "reducer"
        assert any(
            v.violation_type == ViolationType.ANY_IMPORT for v in analyzer.violations
        ), "Expected ANY_IMPORT violation for 'from typing import Any'"

    def test_detects_any_import_with_multiple_typing_imports(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that Any is detected when imported with other typing constructs."""
        source = """
        from typing import Dict, List, Any, Optional, Union
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.ANY_IMPORT for v in analyzer.violations
        ), "Expected ANY_IMPORT violation even with multiple imports"

    def test_detects_typing_module_any_attribute_access(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that 'typing.Any' attribute access in type hints is detected."""
        source = """
        import typing
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            def process(self, data: typing.Any) -> typing.Any:
                return data
        """
        analyzer = analyze_source(source)

        # Either ANY_IMPORT for the import or ANY_TYPE_HINT for usage should be detected
        assert any(
            v.violation_type in (ViolationType.ANY_IMPORT, ViolationType.ANY_TYPE_HINT)
            for v in analyzer.violations
        ), "Expected violation for typing.Any usage"

    def test_allows_any_import_in_effect_node(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that Any import is ALLOWED in EFFECT nodes (not declarative)."""
        source = """
        from typing import Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeApiEffect(NodeCoreBase):
            def fetch(self, data: Any) -> Any:
                return data
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node is False, "Effect node should NOT be pure"
        assert analyzer.node_type == "effect"
        # Effect nodes should have NO Any violations
        any_violations = [
            v
            for v in analyzer.violations
            if v.violation_type
            in (ViolationType.ANY_IMPORT, ViolationType.ANY_TYPE_HINT)
        ]
        assert len(any_violations) == 0, (
            "Effect nodes should NOT have Any violations (not declarative)"
        )

    def test_allows_any_import_in_orchestrator_node(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that Any import is ALLOWED in ORCHESTRATOR nodes (not declarative)."""
        source = """
        from typing import Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeWorkflowOrchestrator(NodeCoreBase):
            def orchestrate(self, data: Any) -> Any:
                return data
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node is False, "Orchestrator node should NOT be pure"
        assert analyzer.node_type == "orchestrator"
        # Orchestrator nodes should have NO Any violations
        any_violations = [
            v
            for v in analyzer.violations
            if v.violation_type
            in (ViolationType.ANY_IMPORT, ViolationType.ANY_TYPE_HINT)
        ]
        assert len(any_violations) == 0, (
            "Orchestrator nodes should NOT have Any violations (not declarative)"
        )


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestDictAnyTypeHintBlockingInDeclarativeNodes:
    """
    TDD tests for blocking Dict[str, Any] and dict[str, Any] in declarative nodes.

    Declarative nodes should use TypedDict or Pydantic models instead of
    Dict[str, Any] to maintain type safety guarantees.

    Ticket: OMN-203
    """

    def test_detects_typing_dict_str_any_in_function_param(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that Dict[str, Any] from typing module is detected in parameters."""
        source = """
        from typing import Dict, Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            def process(self, data: Dict[str, Any]) -> str:
                return str(data)
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node is True
        assert any(
            v.violation_type == ViolationType.DICT_ANY_TYPE_HINT
            for v in analyzer.violations
        ), "Expected DICT_ANY_TYPE_HINT violation for Dict[str, Any]"

    def test_detects_typing_dict_str_any_in_return_type(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that Dict[str, Any] in return types is detected."""
        source = """
        from typing import Dict, Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            def get_config(self) -> Dict[str, Any]:
                return {}
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.DICT_ANY_TYPE_HINT
            for v in analyzer.violations
        ), "Expected DICT_ANY_TYPE_HINT violation in return type"

    def test_detects_lowercase_dict_str_any(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that dict[str, Any] (builtin lowercase) is detected."""
        source = """
        from typing import Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            def process(self, data: dict[str, Any]) -> dict[str, Any]:
                return data
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.DICT_ANY_TYPE_HINT
            for v in analyzer.violations
        ), "Expected DICT_ANY_TYPE_HINT violation for dict[str, Any]"

    def test_detects_dict_any_in_class_attribute(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that Dict[str, Any] in class attributes is detected."""
        source = """
        from typing import Dict, Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            metadata: Dict[str, Any]
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.DICT_ANY_TYPE_HINT
            for v in analyzer.violations
        ), "Expected DICT_ANY_TYPE_HINT violation in class attribute"

    def test_detects_nested_dict_any_in_list(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that List[Dict[str, Any]] is detected."""
        source = """
        from typing import Dict, Any, List
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            def process(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
                return items
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.DICT_ANY_TYPE_HINT
            for v in analyzer.violations
        ), "Expected DICT_ANY_TYPE_HINT violation for nested Dict[str, Any]"

    def test_detects_optional_dict_any(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that Optional[Dict[str, Any]] is detected."""
        source = """
        from typing import Dict, Any, Optional
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            def process(self, data: Optional[Dict[str, Any]] = None) -> None:
                pass
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type == ViolationType.DICT_ANY_TYPE_HINT
            for v in analyzer.violations
        ), "Expected DICT_ANY_TYPE_HINT violation for Optional[Dict[str, Any]]"

    def test_allows_dict_str_any_in_effect_node(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that Dict[str, Any] is ALLOWED in EFFECT nodes."""
        source = """
        from typing import Dict, Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeApiEffect(NodeCoreBase):
            def fetch(self, config: Dict[str, Any]) -> Dict[str, Any]:
                return {}
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node is False
        dict_any_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.DICT_ANY_TYPE_HINT
        ]
        assert len(dict_any_violations) == 0, "Effect nodes should allow Dict[str, Any]"


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestAllowDictAnyDecoratorExclusion:
    """
    TDD tests for @allow_dict_any decorator exclusion.

    Functions or classes decorated with @allow_dict_any should be excluded
    from Dict[str, Any] checks while still flagging the Any import.

    Ticket: OMN-203
    """

    def test_allow_dict_any_decorator_excludes_function(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that @allow_dict_any on a function excludes it from checks."""
        source = """
        from typing import Dict, Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.decorators import allow_dict_any

        class NodeMyCompute(NodeCoreBase):
            @allow_dict_any("Required for JSON serialization")
            def serialize(self, data: Dict[str, Any]) -> Dict[str, Any]:
                return data
        """
        analyzer = analyze_source(source)

        # The function with @allow_dict_any should NOT produce DICT_ANY violations
        dict_any_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.DICT_ANY_TYPE_HINT
        ]
        assert len(dict_any_violations) == 0, (
            "@allow_dict_any should exclude function from DICT_ANY checks"
        )

    def test_allow_dict_any_decorator_excludes_class(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that @allow_dict_any on a class excludes all methods."""
        source = """
        from typing import Dict, Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.decorators import allow_dict_any

        @allow_dict_any("JSON handler class")
        class NodeMyCompute(NodeCoreBase):
            def serialize(self, data: Dict[str, Any]) -> Dict[str, Any]:
                return data

            def deserialize(self, data: Dict[str, Any]) -> Dict[str, Any]:
                return data
        """
        analyzer = analyze_source(source)

        dict_any_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.DICT_ANY_TYPE_HINT
        ]
        assert len(dict_any_violations) == 0, (
            "@allow_dict_any on class should exclude all methods"
        )

    def test_allow_dict_any_does_not_affect_other_functions(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that @allow_dict_any only affects decorated function."""
        source = """
        from typing import Dict, Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.decorators import allow_dict_any

        class NodeMyCompute(NodeCoreBase):
            @allow_dict_any("Allowed")
            def serialize(self, data: Dict[str, Any]) -> Dict[str, Any]:
                return data

            def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
                return data
        """
        analyzer = analyze_source(source)

        dict_any_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.DICT_ANY_TYPE_HINT
        ]
        # process() is not decorated, so it should have violations
        assert len(dict_any_violations) >= 1, (
            "Non-decorated function should still have DICT_ANY violations"
        )

    def test_allow_dict_str_any_decorator_variant(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that @allow_dict_str_any decorator also works."""
        source = """
        from typing import Dict, Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.decorators import allow_dict_str_any

        class NodeMyCompute(NodeCoreBase):
            @allow_dict_str_any("JSON interface requirement")
            def serialize(self, data: Dict[str, Any]) -> Dict[str, Any]:
                return data
        """
        analyzer = analyze_source(source)

        dict_any_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.DICT_ANY_TYPE_HINT
        ]
        assert len(dict_any_violations) == 0, (
            "@allow_dict_str_any should exclude function from DICT_ANY checks"
        )


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestAnyTypeHintDetectionInDeclarativeNodes:
    """
    TDD tests for detecting Any in various type hint positions.

    Beyond just imports, Any usage in actual type hints should also be detected
    in declarative nodes.

    Ticket: OMN-203
    """

    def test_detects_any_in_parameter_type(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that Any in parameter types is detected."""
        source = """
        from typing import Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            def process(self, data: Any) -> str:
                return str(data)
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type in (ViolationType.ANY_IMPORT, ViolationType.ANY_TYPE_HINT)
            for v in analyzer.violations
        ), "Expected violation for Any parameter type"

    def test_detects_any_in_return_type(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that Any in return types is detected."""
        source = """
        from typing import Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            def process(self, data: str) -> Any:
                return data
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type in (ViolationType.ANY_IMPORT, ViolationType.ANY_TYPE_HINT)
            for v in analyzer.violations
        ), "Expected violation for Any return type"

    def test_detects_list_any_type_hint(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that List[Any] is detected."""
        source = """
        from typing import List, Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            items: List[Any]
        """
        analyzer = analyze_source(source)

        # Should detect either the import or the type hint usage
        assert any(
            v.violation_type in (ViolationType.ANY_IMPORT, ViolationType.ANY_TYPE_HINT)
            for v in analyzer.violations
        ), "Expected violation for List[Any]"

    def test_detects_union_with_any(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that Union containing Any is detected."""
        source = """
        from typing import Union, Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            def process(self, data: Union[str, Any]) -> Union[int, Any]:
                return 0
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type in (ViolationType.ANY_IMPORT, ViolationType.ANY_TYPE_HINT)
            for v in analyzer.violations
        ), "Expected violation for Union containing Any"

    def test_detects_callable_with_any(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that Callable with Any arguments is detected."""
        source = """
        from typing import Callable, Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            callback: Callable[[Any], Any]
        """
        analyzer = analyze_source(source)

        assert any(
            v.violation_type in (ViolationType.ANY_IMPORT, ViolationType.ANY_TYPE_HINT)
            for v in analyzer.violations
        ), "Expected violation for Callable with Any"


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestOnexExcludeCommentForAnyDictAny:
    """
    TDD tests for ONEX_EXCLUDE comment-based exclusions for Any/Dict[Any].

    Lines with ONEX_EXCLUDE: dict_str_any or ONEX_EXCLUDE: any comments
    should be excluded from checks.

    Ticket: OMN-203
    """

    def test_onex_exclude_dict_str_any_excludes_line(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that ONEX_EXCLUDE: dict_str_any comment excludes line."""
        source = """
        from typing import Dict, Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            # ONEX_EXCLUDE: dict_str_any - Required for external API compatibility
            def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
                return data
        """
        analyzer = analyze_source(source)

        dict_any_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.DICT_ANY_TYPE_HINT
        ]
        assert len(dict_any_violations) == 0, (
            "ONEX_EXCLUDE: dict_str_any should exclude line from checks"
        )

    def test_onex_exclude_any_excludes_line(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that ONEX_EXCLUDE: any comment excludes line."""
        source = """
        from typing import Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            # ONEX_EXCLUDE: any - Generic interface requirement
            def process(self, data: Any) -> Any:
                return data
        """
        analyzer = analyze_source(source)

        any_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.ANY_TYPE_HINT
        ]
        assert len(any_violations) == 0, (
            "ONEX_EXCLUDE: any should exclude line from type hint checks"
        )

    def test_onex_exclude_only_affects_annotated_function(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that ONEX_EXCLUDE only affects the specific function."""
        source = """
        from typing import Dict, Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            # ONEX_EXCLUDE: dict_str_any
            def excluded_method(self, data: Dict[str, Any]) -> Dict[str, Any]:
                return data

            def not_excluded_method(self, data: Dict[str, Any]) -> Dict[str, Any]:
                return data
        """
        analyzer = analyze_source(source)

        dict_any_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.DICT_ANY_TYPE_HINT
        ]
        # not_excluded_method should still have violations
        assert len(dict_any_violations) >= 1, (
            "ONEX_EXCLUDE should only affect annotated function"
        )


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestAnyDictAnyViolationMessageQuality:
    """
    TDD tests for violation message quality.

    Violation messages should be helpful and actionable, suggesting
    alternatives like TypedDict or Pydantic models.

    Ticket: OMN-203
    """

    def test_any_import_violation_has_helpful_suggestion(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that Any import violations include helpful suggestions."""
        source = """
        from typing import Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        any_violations = [
            v
            for v in analyzer.violations
            if v.violation_type
            in (ViolationType.ANY_IMPORT, ViolationType.ANY_TYPE_HINT)
        ]

        if any_violations:
            violation = any_violations[0]
            assert len(violation.suggestion) > 0, "Violation should have suggestion"
            # Suggestion should mention typed alternatives
            suggestion_lower = violation.suggestion.lower()
            assert any(
                keyword in suggestion_lower
                for keyword in [
                    "typed",
                    "model",
                    "specific",
                    "concrete",
                    "generic",
                    "pydantic",
                ]
            ), f"Suggestion should mention typed alternatives: {violation.suggestion}"

    def test_dict_any_violation_suggests_typeddict_or_pydantic(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that Dict[Any] violations suggest TypedDict or Pydantic."""
        source = """
        from typing import Dict, Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            metadata: Dict[str, Any]
        """
        analyzer = analyze_source(source)

        dict_any_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.DICT_ANY_TYPE_HINT
        ]

        if dict_any_violations:
            violation = dict_any_violations[0]
            assert len(violation.suggestion) > 0, "Violation should have suggestion"
            # Suggestion should mention TypedDict or Pydantic
            suggestion_lower = violation.suggestion.lower()
            assert any(
                keyword in suggestion_lower
                for keyword in ["typeddict", "pydantic", "model", "typed"]
            ), (
                f"Suggestion should mention TypedDict or Pydantic: {violation.suggestion}"
            )

    def test_violations_include_accurate_line_numbers(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that violations include accurate line numbers."""
        source = """
        from typing import Dict, Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            def process(self, data: Dict[str, Any]) -> str:
                return str(data)
        """
        analyzer = analyze_source(source)

        for violation in analyzer.violations:
            assert violation.line_number > 0, "Violation should have line number"

    def test_any_dict_any_violations_are_error_severity(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that Any/Dict[Any] violations are ERROR severity."""
        source = """
        from typing import Dict, Any
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            metadata: Dict[str, Any]
        """
        analyzer = analyze_source(source)

        relevant_violations = [
            v
            for v in analyzer.violations
            if v.violation_type
            in (
                ViolationType.ANY_IMPORT,
                ViolationType.ANY_TYPE_HINT,
                ViolationType.DICT_ANY_TYPE_HINT,
            )
        ]

        for violation in relevant_violations:
            assert violation.severity == Severity.ERROR, (
                "Any/Dict[Any] violations should be ERROR severity"
            )


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestTypeCheckingBlockExclusion:
    """
    TDD tests for TYPE_CHECKING block handling.

    Imports inside TYPE_CHECKING blocks may be handled differently since they
    don't affect runtime behavior.

    Ticket: OMN-203
    """

    def test_type_checking_block_any_import_handling(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test handling of Any import inside TYPE_CHECKING block.

        This is a design decision - TYPE_CHECKING imports may or may not be
        allowed since they only affect static type checking, not runtime.
        """
        source = """
        from typing import TYPE_CHECKING
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        if TYPE_CHECKING:
            from typing import Any

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        # Document the expected behavior - TYPE_CHECKING imports should be allowed
        # since they don't affect runtime
        any_import_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.ANY_IMPORT
        ]
        # Design decision: TYPE_CHECKING block imports should be allowed
        assert len(any_import_violations) == 0, (
            "TYPE_CHECKING block imports should be allowed (no runtime impact)"
        )


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestMixedValidAndInvalidTypeHints:
    """
    TDD tests for files with both valid and invalid type hints.

    Only the invalid type hints should be flagged.

    Ticket: OMN-203
    """

    def test_only_invalid_type_hints_are_flagged(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that only invalid type hints are flagged, not valid ones."""
        source = """
        from typing import Dict, Any, List, Optional
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            # Valid type hints - should NOT be flagged
            items: List[str]
            config: Dict[str, str]

            # Invalid type hints - SHOULD be flagged
            metadata: Dict[str, Any]
            cache: Dict[str, Any]

            def valid_method(self, data: str) -> Optional[str]:
                return data

            def invalid_method(self, data: Any) -> Dict[str, Any]:
                return {}
        """
        analyzer = analyze_source(source)

        # Should have violations for invalid_method and the class attributes
        violations = [
            v
            for v in analyzer.violations
            if v.violation_type
            in (
                ViolationType.ANY_IMPORT,
                ViolationType.ANY_TYPE_HINT,
                ViolationType.DICT_ANY_TYPE_HINT,
            )
        ]
        # At minimum: ANY_IMPORT + metadata + cache + invalid_method return
        # The exact count depends on implementation details
        assert len(violations) >= 3, (
            f"Should detect multiple Any/Dict[Any] violations, found {len(violations)}"
        )


# ==============================================================================
# EVENT BUS COMPONENT DETECTION TESTS (OMN-203)
# ==============================================================================
#
# Tests for blocking event bus component imports in declarative nodes
# (NodeCompute, NodeReducer). Implementation complete.
#
# Event Bus Components Blocked:
# - omnibase_core.events.* - All event system imports
# - omnibase_core.models.event_bus.* - Event bus models
# - omnibase_core.models.events.* - Event models
# - ProtocolEventBus, ModelEventEnvelope, ModelEventBusConfig
# ==============================================================================


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestEventBusComponentDetection:
    """Test detection of forbidden event bus imports in declarative nodes.

    Event Bus Components to Block:
    - omnibase_core.events.* - All event system imports
    - omnibase_core.models.event_bus.* - Event bus models
    - omnibase_core.models.events.* - Event models
    - ProtocolEventBus - Event bus protocol
    - ModelEventEnvelope - Event envelope model
    - ModelEventBusConfig - Event bus configuration

    Why Block These:
    - Declarative nodes should be pure functions/state machines
    - Event bus introduces side effects and external communication
    - Effects (I/O, events) should go through EFFECT nodes
    """

    def test_detects_events_module_import(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that omnibase_core.events module imports are detected."""
        source = """
        from omnibase_core.events import SomeEvent
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node, "Compute node should be classified as pure"
        assert any(
            v.violation_type == ViolationType.EVENT_BUS_IMPORT
            for v in analyzer.violations
        ), f"Expected EVENT_BUS_IMPORT violation, got: {analyzer.violations}"

    def test_detects_protocol_event_bus_import(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that ProtocolEventBus import is detected as violation.

        ProtocolEventBus is the event bus protocol interface. Declarative nodes
        should not import this as they should not interact with the event bus.
        """
        source = """
        from omnibase_core.protocols.event_bus import ProtocolEventBus
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            def __init__(self, container):
                super().__init__(container)
                self.event_bus: ProtocolEventBus = container.get_service("ProtocolEventBus")
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        assert any(
            v.violation_type == ViolationType.EVENT_BUS_IMPORT
            for v in analyzer.violations
        ), f"Expected EVENT_BUS_IMPORT violation, got: {analyzer.violations}"

    def test_detects_model_event_envelope_import(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that ModelEventEnvelope import is detected as violation.

        ModelEventEnvelope is used to wrap events for the event bus. Declarative
        nodes should not use this as they should not publish events directly.
        """
        source = """
        from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            async def process(self, input_data):
                envelope = ModelEventEnvelope(payload=input_data)
                return envelope
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        assert any(
            v.violation_type == ViolationType.EVENT_BUS_IMPORT
            for v in analyzer.violations
        ), f"Expected EVENT_BUS_IMPORT violation, got: {analyzer.violations}"

    def test_detects_models_event_bus_import(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that omnibase_core.models.event_bus imports are detected."""
        source = """
        from omnibase_core.models.event_bus import ModelEventBusInputState
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyReducer(NodeCoreBase):
            def __init__(self, container):
                super().__init__(container)
                self.state = ModelEventBusInputState()
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        assert any(
            v.violation_type == ViolationType.EVENT_BUS_IMPORT
            for v in analyzer.violations
        ), f"Expected EVENT_BUS_IMPORT violation, got: {analyzer.violations}"

    def test_detects_models_events_import(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that omnibase_core.models.events imports are detected."""
        source = """
        from omnibase_core.models.events import ModelEventConfig
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        assert any(
            v.violation_type == ViolationType.EVENT_BUS_IMPORT
            for v in analyzer.violations
        ), f"Expected EVENT_BUS_IMPORT violation, got: {analyzer.violations}"

    def test_detects_model_event_bus_config_import(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that ModelEventBusConfig import is detected as violation."""
        source = """
        from omnibase_core.models.event_bus.model_event_bus_config import ModelEventBusConfig
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyReducer(NodeCoreBase):
            def __init__(self, container):
                super().__init__(container)
                self.config = ModelEventBusConfig()
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        assert any(
            v.violation_type == ViolationType.EVENT_BUS_IMPORT
            for v in analyzer.violations
        ), f"Expected EVENT_BUS_IMPORT violation, got: {analyzer.violations}"

    def test_effect_node_allows_event_bus(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that EFFECT nodes CAN import event bus (not checked).

        Effect nodes are explicitly allowed to have side effects including
        event bus interaction for external communication.
        """
        source = """
        from omnibase_core.protocols.event_bus import ProtocolEventBus
        from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyEffect(NodeCoreBase):
            def __init__(self, container):
                super().__init__(container)
                self.event_bus: ProtocolEventBus = container.get_service("ProtocolEventBus")

            async def publish(self, data):
                envelope = ModelEventEnvelope(payload=data)
                await self.event_bus.publish(envelope)
        """
        analyzer = analyze_source(source)

        # EFFECT nodes are NOT pure nodes
        assert analyzer.is_pure_node is False
        assert analyzer.node_type == "effect"
        # EFFECT nodes should have NO violations for event bus imports
        event_bus_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.EVENT_BUS_IMPORT
        ]
        assert len(event_bus_violations) == 0, (
            f"EFFECT nodes should allow event bus imports, got: {event_bus_violations}"
        )

    def test_orchestrator_node_allows_event_bus(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that ORCHESTRATOR nodes CAN import event bus (not checked).

        Orchestrator nodes coordinate workflows and may need event bus
        access for coordination purposes.
        """
        source = """
        from omnibase_core.protocols.event_bus import ProtocolEventBus
        from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyOrchestrator(NodeCoreBase):
            def __init__(self, container):
                super().__init__(container)
                self.event_bus: ProtocolEventBus = container.get_service("ProtocolEventBus")
        """
        analyzer = analyze_source(source)

        # ORCHESTRATOR nodes are NOT pure nodes
        assert analyzer.is_pure_node is False
        assert analyzer.node_type == "orchestrator"
        # ORCHESTRATOR nodes should have NO violations for event bus imports
        event_bus_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.EVENT_BUS_IMPORT
        ]
        assert len(event_bus_violations) == 0, (
            f"ORCHESTRATOR nodes should allow event bus imports, got: {event_bus_violations}"
        )


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestEventBusImportVariations:
    """Test detection of various import syntax patterns for event bus components."""

    def test_detects_protocol_from_protocols_init(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test detection of ProtocolEventBus from protocols.__init__."""
        source = """
        from omnibase_core.protocols import ProtocolEventBus
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        assert any(
            v.violation_type == ViolationType.EVENT_BUS_IMPORT
            for v in analyzer.violations
        ), f"Expected EVENT_BUS_IMPORT violation, got: {analyzer.violations}"

    def test_detects_protocol_from_full_path(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test detection of ProtocolEventBus from full module path."""
        source = """
        from omnibase_core.protocols.event_bus.protocol_event_bus import ProtocolEventBus
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        assert any(
            v.violation_type == ViolationType.EVENT_BUS_IMPORT
            for v in analyzer.violations
        ), f"Expected EVENT_BUS_IMPORT violation, got: {analyzer.violations}"

    def test_detects_protocol_with_alias(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test detection of ProtocolEventBus imported with alias."""
        source = """
        from omnibase_core.protocols.event_bus import ProtocolEventBus as EventBusProtocol
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        assert any(
            v.violation_type == ViolationType.EVENT_BUS_IMPORT
            for v in analyzer.violations
        ), f"Expected EVENT_BUS_IMPORT violation, got: {analyzer.violations}"

    def test_detects_module_import_events(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test detection of 'import omnibase_core.events' style import."""
        source = """
        import omnibase_core.events
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        assert any(
            v.violation_type == ViolationType.EVENT_BUS_IMPORT
            for v in analyzer.violations
        ), f"Expected EVENT_BUS_IMPORT violation, got: {analyzer.violations}"

    def test_detects_wildcard_import_events(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test detection of 'from omnibase_core.events import *' style import."""
        source = """
        from omnibase_core.events import *
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        assert any(
            v.violation_type == ViolationType.EVENT_BUS_IMPORT
            for v in analyzer.violations
        ), f"Expected EVENT_BUS_IMPORT violation, got: {analyzer.violations}"

    def test_detects_submodule_import(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test detection of 'from omnibase_core.events.submodule import X' style."""
        source = """
        from omnibase_core.events.some_submodule import EventHandler
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        assert any(
            v.violation_type == ViolationType.EVENT_BUS_IMPORT
            for v in analyzer.violations
        ), f"Expected EVENT_BUS_IMPORT violation, got: {analyzer.violations}"


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestEventBusCleanCode:
    """Test that clean code without event bus imports produces no violations."""

    def test_clean_compute_node_no_violations(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that a clean NodeCompute subclass has no event bus violations."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.models.compute.model_compute_input import ModelComputeInput
        from omnibase_core.models.compute.model_compute_output import ModelComputeOutput

        class NodeMyCompute(NodeCoreBase):
            async def process(self, input_data: ModelComputeInput) -> ModelComputeOutput:
                # Pure computation - no event bus usage
                result = str(input_data).upper()
                return ModelComputeOutput(result=result)
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        event_bus_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.EVENT_BUS_IMPORT
        ]
        assert len(event_bus_violations) == 0

    def test_clean_reducer_node_no_violations(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that a clean NodeReducer subclass has no event bus violations."""
        source = """
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase
        from omnibase_core.models.reducer.model_reducer_input import ModelReducerInput
        from omnibase_core.models.reducer.model_reducer_output import ModelReducerOutput

        class NodeMyReducer(NodeCoreBase):
            async def process(self, input_data: ModelReducerInput) -> ModelReducerOutput:
                # Pure FSM-driven state management - no event bus usage
                return ModelReducerOutput(result=input_data.data)
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        event_bus_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.EVENT_BUS_IMPORT
        ]
        assert len(event_bus_violations) == 0

    def test_non_node_class_no_violations(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that non-node classes with event bus imports are not flagged."""
        source = """
        from omnibase_core.protocols.event_bus import ProtocolEventBus
        from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope

        class EventBusHelper:
            '''Utility class that uses event bus - not a node'''
            def __init__(self, event_bus: ProtocolEventBus):
                self.event_bus = event_bus

            async def publish(self, data):
                envelope = ModelEventEnvelope(payload=data)
                await self.event_bus.publish(envelope)
        """
        analyzer = analyze_source(source)

        # Non-node classes should not be checked
        assert analyzer.is_pure_node is False


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestEventBusMultipleViolations:
    """Test handling of multiple event bus violations in a single file."""

    def test_multiple_event_bus_imports(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that multiple forbidden event bus imports are all detected."""
        source = """
        from omnibase_core.events import SomeEvent
        from omnibase_core.protocols.event_bus import ProtocolEventBus
        from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        event_bus_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.EVENT_BUS_IMPORT
        ]
        # Should detect all three forbidden imports
        assert len(event_bus_violations) >= 3, (
            f"Expected at least 3 violations, got: {event_bus_violations}"
        )

    def test_multiple_declarative_nodes_same_file(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that violations are reported for files with multiple declarative nodes."""
        source = """
        from omnibase_core.events import SomeEvent
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass

        class NodeMyReducer(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        # File-level imports affect all declarative nodes
        assert analyzer.is_pure_node
        event_bus_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.EVENT_BUS_IMPORT
        ]
        assert len(event_bus_violations) > 0, (
            f"Expected violations, got: {event_bus_violations}"
        )


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestEventBusViolationDetails:
    """Test violation details for event bus detection."""

    def test_violation_has_correct_severity(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that event bus violations have ERROR severity."""
        source = """
        from omnibase_core.protocols.event_bus import ProtocolEventBus
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        event_bus_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.EVENT_BUS_IMPORT
        ]
        assert len(event_bus_violations) >= 1
        assert all(v.severity == Severity.ERROR for v in event_bus_violations), (
            "Event bus violations should have ERROR severity"
        )

    def test_violation_includes_line_number(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that event bus violations include line numbers."""
        source = """
        from omnibase_core.protocols.event_bus import ProtocolEventBus
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        event_bus_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.EVENT_BUS_IMPORT
        ]
        assert len(event_bus_violations) >= 1
        for violation in event_bus_violations:
            assert violation.line_number > 0, "Violation should have line number"

    def test_violation_includes_suggestion(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test that event bus violations include helpful suggestions."""
        source = """
        from omnibase_core.protocols.event_bus import ProtocolEventBus
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        event_bus_violations = [
            v
            for v in analyzer.violations
            if v.violation_type == ViolationType.EVENT_BUS_IMPORT
        ]
        assert len(event_bus_violations) >= 1
        for violation in event_bus_violations:
            assert len(violation.suggestion) > 0, "Violation should have suggestion"
            # Suggestion should guide toward EFFECT nodes
            assert any(
                keyword in violation.suggestion.lower()
                for keyword in ["effect", "node", "intent", "remove"]
            ), f"Suggestion should mention alternatives: {violation.suggestion}"


@pytest.mark.unit
@pytest.mark.timeout(30)
class TestEventBusSpecificModels:
    """Test detection of specific event bus model imports."""

    def test_detects_model_event_bus_input_state(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test detection of ModelEventBusInputState import."""
        source = """
        from omnibase_core.models.event_bus.model_event_bus_input_state import ModelEventBusInputState
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        assert any(
            v.violation_type == ViolationType.EVENT_BUS_IMPORT
            for v in analyzer.violations
        )

    def test_detects_model_event_bus_output_state(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test detection of ModelEventBusOutputState import."""
        source = """
        from omnibase_core.models.event_bus.model_event_bus_output_state import ModelEventBusOutputState
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        assert any(
            v.violation_type == ViolationType.EVENT_BUS_IMPORT
            for v in analyzer.violations
        )

    def test_detects_model_event_config(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test detection of ModelEventConfig import."""
        source = """
        from omnibase_core.models.events.model_event_config import ModelEventConfig
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyReducer(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        assert any(
            v.violation_type == ViolationType.EVENT_BUS_IMPORT
            for v in analyzer.violations
        )

    def test_detects_model_event_publish_intent(
        self, analyze_source: Callable[[str], PurityAnalyzer]
    ) -> None:
        """Test detection of ModelEventPublishIntent import."""
        source = """
        from omnibase_core.models.events.model_event_publish_intent import ModelEventPublishIntent
        from omnibase_core.infrastructure.node_core_base import NodeCoreBase

        class NodeMyCompute(NodeCoreBase):
            pass
        """
        analyzer = analyze_source(source)

        assert analyzer.is_pure_node
        assert any(
            v.violation_type == ViolationType.EVENT_BUS_IMPORT
            for v in analyzer.violations
        )
