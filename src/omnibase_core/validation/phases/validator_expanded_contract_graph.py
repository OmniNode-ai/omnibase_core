"""
Expanded Contract Graph Validator for Multi-Contract Validation.

Validates relationships across multiple expanded contracts. This validator
performs cross-contract analysis that cannot be done on individual contracts,
including:

- Full cycle detection across the dependency graph
- Orphan handler reference detection
- Event consumer/producer matching

This is a separate class because it requires access to a contract
registry or collection, which may not be available in all contexts.

Related:
    - OMN-1128: Contract Validation Pipeline
    - ExpandedContractValidator: Single-contract validation
    - EnumContractValidationErrorCode: Error codes used

.. versionadded:: 0.4.0
"""

import logging
from collections import defaultdict

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_contract_validation_error_code import (
    EnumContractValidationErrorCode,
)
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.contracts.model_handler_contract import ModelHandlerContract

__all__ = [
    "ExpandedContractGraphValidator",
]

# Configure logger for this module
logger = logging.getLogger(__name__)


class ExpandedContractGraphValidator:  # naming-ok: validator class, not protocol
    """Validates relationships across multiple expanded contracts.

    This validator performs cross-contract analysis that cannot be done
    on individual contracts, including:

    - Full cycle detection across the dependency graph
    - Orphan handler reference detection
    - Event consumer/producer matching

    This is a separate class because it requires access to a contract
    registry or collection, which may not be available in all contexts.

    Example:
        >>> graph_validator = ExpandedContractGraphValidator()
        >>> result = graph_validator.validate_graph(contracts)
        >>> if not result.is_valid:
        ...     print("Cross-contract issues found")

    Note:
        This is an optional extension for Phase 3 validation. The primary
        ExpandedContractValidator handles single-contract validation.

    .. versionadded:: 0.4.0
    """

    def validate_graph(
        self,
        contracts: list[ModelHandlerContract],
    ) -> ModelValidationResult[None]:
        """Validate relationships across multiple contracts.

        Performs cross-contract validation including:
            - Cycle detection in the full dependency graph
            - Orphan handler reference detection
            - Event producer/consumer matching

        Args:
            contracts: List of expanded contracts to validate as a graph.

        Returns:
            ModelValidationResult with cross-contract validation issues.
        """
        result: ModelValidationResult[None] = ModelValidationResult(
            is_valid=True,
            summary="Graph validation started",
        )

        logger.debug(f"Starting graph validation for {len(contracts)} contracts")

        if not contracts:
            result.summary = "No contracts to validate"
            return result

        # Build handler ID set for orphan detection
        handler_ids = {c.handler_id for c in contracts}

        # Detect orphan handler references
        self._detect_orphan_references(contracts, handler_ids, result)

        # Detect cycles in the dependency graph
        self._detect_cycles(contracts, result)

        # Validate event producer/consumer matching
        self._validate_event_consumers(contracts, result)

        # Update summary
        if result.is_valid:
            result.summary = f"Graph validation passed for {len(contracts)} contracts"
        else:
            result.summary = (
                f"Graph validation failed with {result.error_level_count} errors"
            )

        return result

    def _detect_orphan_references(
        self,
        contracts: list[ModelHandlerContract],
        handler_ids: set[str],
        result: ModelValidationResult[None],
    ) -> None:
        """Detect handler references that don't exist in the graph.

        Args:
            contracts: List of contracts to check.
            handler_ids: Set of valid handler IDs in the graph.
            result: The validation result to append issues to.
        """
        for contract in contracts:
            if not contract.execution_constraints:
                continue

            all_deps = contract.execution_constraints.get_all_dependencies()
            for dep in all_deps:
                if dep.startswith("handler:"):
                    ref_id = dep.split(":", 1)[1]
                    if ref_id not in handler_ids:
                        result.add_error(
                            f"Handler '{contract.handler_id}' references non-existent "
                            f"handler '{ref_id}' in execution_constraints.",
                            code=EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_EXECUTION_GRAPH_ORPHAN.value,
                        )

    def _detect_cycles(
        self,
        contracts: list[ModelHandlerContract],
        result: ModelValidationResult[None],
    ) -> None:
        """Detect cycles in the handler dependency graph.

        Uses depth-first search with coloring to detect cycles.
        A cycle exists if we encounter a node that is currently being visited.

        Args:
            contracts: List of contracts to analyze.
            result: The validation result to append issues to.
        """
        # Build adjacency list for dependency graph
        # An edge from A to B means A must run AFTER B (B is in A's requires_before)
        # or B must run AFTER A (A is in B's requires_after)
        graph: dict[str, set[str]] = defaultdict(set)
        handler_map = {c.handler_id: c for c in contracts}

        for contract in contracts:
            if not contract.execution_constraints:
                continue

            # requires_before: this handler runs after these dependencies
            for dep in contract.execution_constraints.requires_before:
                if dep.startswith("handler:"):
                    ref_id = dep.split(":", 1)[1]
                    if ref_id in handler_map:
                        graph[contract.handler_id].add(ref_id)

            # requires_after: these handlers run after this handler
            for dep in contract.execution_constraints.requires_after:
                if dep.startswith("handler:"):
                    ref_id = dep.split(":", 1)[1]
                    if ref_id in handler_map:
                        graph[ref_id].add(contract.handler_id)

        # DFS with coloring: WHITE=unvisited, GRAY=visiting, BLACK=finished
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = dict.fromkeys(handler_map, WHITE)
        cycle_path: list[str] = []

        def dfs(node: str) -> bool:
            """Return True if cycle detected."""
            color[node] = GRAY
            cycle_path.append(node)

            for neighbor in graph.get(node, set()):
                if neighbor not in color:
                    continue
                if color[neighbor] == GRAY:
                    # Found cycle - extract the cycle from path
                    cycle_start = cycle_path.index(neighbor)
                    cycle = cycle_path[cycle_start:] + [neighbor]
                    result.add_error(
                        f"Circular dependency detected in execution graph: "
                        f"{' -> '.join(cycle)}",
                        code=EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_EXECUTION_GRAPH_CYCLE.value,
                    )
                    cycle_path.pop()
                    return True
                if color[neighbor] == WHITE:
                    if dfs(neighbor):
                        cycle_path.pop()
                        return True

            color[node] = BLACK
            cycle_path.pop()
            return False

        for handler_id in handler_map:
            if color[handler_id] == WHITE:
                dfs(handler_id)

    def _validate_event_consumers(
        self,
        contracts: list[ModelHandlerContract],
        result: ModelValidationResult[None],
    ) -> None:
        """Validate that produced events have consumers.

        Collects all event outputs (capability_outputs starting with 'event.')
        and checks that at least one handler is configured to consume them.

        Note: This is a warning rather than an error since events may be
        consumed by external systems not in the contract graph.

        Args:
            contracts: List of contracts to analyze.
            result: The validation result to append issues to.
        """
        # Collect event outputs
        event_outputs: set[str] = set()
        for contract in contracts:
            for output in contract.capability_outputs:
                if output.startswith("event."):
                    event_outputs.add(output)

        if not event_outputs:
            return

        # Collect event consumers (capability_inputs with event. prefix)
        consumed_events: set[str] = set()
        for contract in contracts:
            for dep in contract.capability_inputs:
                if dep.capability.startswith("event."):
                    consumed_events.add(dep.capability)

        # Find unmatched events
        unmatched = event_outputs - consumed_events
        if unmatched:
            result.add_issue(
                severity=EnumSeverity.WARNING,
                message=(
                    f"The following events are produced but have no consumers in the graph: "
                    f"{sorted(unmatched)}. These may be consumed by external systems."
                ),
                code=EnumContractValidationErrorCode.CONTRACT_VALIDATION_EXPANDED_EVENT_CONSUMER_MISSING.value,
                suggestion="Verify these events are consumed by external handlers or systems.",
            )
