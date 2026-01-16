"""
Manifest Logger for Output Formatting.

Provides the ManifestLogger class which outputs execution manifests in
various formats including JSON, YAML, Markdown, and human-readable text.

.. versionadded:: 0.4.0
    Added as part of Manifest Generation & Observability (OMN-1113)
"""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.manifest.model_execution_manifest import (
    ModelExecutionManifest,
)
from omnibase_core.protocols.protocol_logger_like import ProtocolLoggerLike


class ManifestLogger:
    """
    Logs and outputs manifests in various formats.

    This class provides static methods to convert execution manifests
    into different output formats for display, storage, or analysis.

    Supported formats:
        - JSON: Machine-readable, full fidelity
        - YAML: Human-readable, full fidelity
        - Markdown: Documentation-friendly report
        - Text: Concise human-readable summary

    Example:
        >>> from omnibase_core.pipeline import ManifestLogger
        >>> # Convert to JSON
        >>> json_str = ManifestLogger.to_json(manifest)
        >>>
        >>> # Convert to Markdown report
        >>> md_report = ManifestLogger.to_markdown(manifest)
        >>>
        >>> # Get text summary
        >>> summary = ManifestLogger.to_text(manifest)

    Thread Safety:
        All methods are static and stateless. ManifestLogger can be safely
        used from multiple threads concurrently.

    .. versionadded:: 0.4.0
        Added as part of Manifest Generation & Observability (OMN-1113)
    """

    @staticmethod
    def to_json(manifest: ModelExecutionManifest, indent: int = 2) -> str:
        """
        Convert manifest to JSON string.

        Args:
            manifest: The manifest to convert
            indent: JSON indentation level (default 2)

        Returns:
            JSON string representation
        """
        return manifest.model_dump_json(indent=indent)

    @staticmethod
    def to_yaml(manifest: ModelExecutionManifest) -> str:
        """
        Convert manifest to YAML string.

        Args:
            manifest: The manifest to convert

        Returns:
            YAML string representation

        Raises:
            ModelOnexError: If PyYAML is not installed
        """
        try:
            import yaml
        except ImportError as e:
            raise ModelOnexError(
                message="PyYAML is required for YAML output. Install with: poetry add pyyaml",
                error_code=EnumCoreErrorCode.DEPENDENCY_UNAVAILABLE,
                dependency="pyyaml",
                operation="to_yaml",
            ) from e

        data = manifest.model_dump(mode="json")
        return yaml.safe_dump(data, default_flow_style=False, sort_keys=False)

    @staticmethod
    def to_dict(manifest: ModelExecutionManifest) -> dict[str, object]:
        """
        Convert manifest to dictionary.

        Args:
            manifest: The manifest to convert

        Returns:
            Dictionary representation
        """
        return manifest.model_dump(mode="json")

    @staticmethod
    def to_markdown(manifest: ModelExecutionManifest, verbose: bool = False) -> str:
        """
        Convert manifest to Markdown report.

        Args:
            manifest: The manifest to convert
            verbose: If True, include detailed traces

        Returns:
            Markdown formatted report
        """
        lines = [
            "# Execution Manifest",
            "",
            f"**Manifest ID**: `{manifest.manifest_id}`",
            f"**Created At**: {manifest.created_at.isoformat()}",
            f"**Status**: {'SUCCESS' if manifest.is_successful() else 'FAILED'}",
            f"**Duration**: {manifest.get_total_duration_ms():.1f}ms",
            "",
            "## Node Identity",
            "",
            f"- **Node ID**: `{manifest.node_identity.node_id}`",
            f"- **Node Kind**: {manifest.node_identity.node_kind.value}",
            f"- **Version**: {manifest.node_identity.get_version_string()}",
        ]

        if manifest.node_identity.namespace:
            lines.append(f"- **Namespace**: {manifest.node_identity.namespace}")

        lines.extend(
            [
                "",
                "## Contract Identity",
                "",
                f"- **Contract ID**: `{manifest.contract_identity.contract_id}`",
            ]
        )

        if manifest.contract_identity.contract_path:
            lines.append(f"- **Path**: `{manifest.contract_identity.contract_path}`")
        if manifest.contract_identity.profile_name:
            lines.append(f"- **Profile**: {manifest.contract_identity.profile_name}")

        # Activation Summary
        activation = manifest.activation_summary
        if activation.total_evaluated > 0:
            lines.extend(
                [
                    "",
                    "## Capability Activation",
                    "",
                    f"- **Activated**: {activation.get_activated_count()}",
                    f"- **Skipped**: {activation.get_skipped_count()}",
                    f"- **Total Evaluated**: {activation.total_evaluated}",
                    "",
                ]
            )

            if activation.activated_capabilities:
                lines.append("### Activated Capabilities")
                lines.append("")
                for cap in activation.activated_capabilities:
                    lines.append(f"- `{cap.capability_name}` - {cap.reason.value}")
                lines.append("")

        # Ordering Summary
        ordering = manifest.ordering_summary
        if ordering.resolved_order:
            lines.extend(
                [
                    "## Execution Order",
                    "",
                    f"**Policy**: {ordering.ordering_policy or 'default'}",
                    "",
                    "**Handler Order**:",
                    "",
                ]
            )
            for i, handler_id in enumerate(ordering.resolved_order, 1):
                lines.append(f"{i}. `{handler_id}`")
            lines.append("")

        # Hook Traces
        if manifest.hook_traces:
            lines.extend(
                [
                    "## Execution Trace",
                    "",
                    f"**Hooks Executed**: {manifest.get_hook_count()}",
                    "",
                    "| Handler | Phase | Status | Duration |",
                    "|---------|-------|--------|----------|",
                ]
            )

            for trace in manifest.hook_traces:
                status_icon = (
                    "✓" if trace.is_success() else "✗" if trace.is_failure() else "○"
                )
                lines.append(
                    f"| `{trace.handler_id}` | {trace.phase.value} | "
                    f"{status_icon} {trace.status.value} | {trace.duration_ms:.1f}ms |"
                )
            lines.append("")

        # Emissions Summary
        emissions = manifest.emissions_summary
        if not emissions.is_empty():
            lines.extend(
                [
                    "## Emissions",
                    "",
                ]
            )
            if emissions.has_events():
                lines.append(
                    f"- **Events**: {emissions.events_count} ({', '.join(emissions.event_types)})"
                )
            if emissions.has_intents():
                lines.append(
                    f"- **Intents**: {emissions.intents_count} ({', '.join(emissions.intent_types)})"
                )
            if emissions.has_projections():
                lines.append(f"- **Projections**: {emissions.projections_count}")
            if emissions.has_actions():
                lines.append(f"- **Actions**: {emissions.actions_count}")
            lines.append("")

        # Failures
        if manifest.has_failures():
            lines.extend(
                [
                    "## Failures",
                    "",
                ]
            )
            for failure in manifest.failures:
                lines.append(f"### [{failure.error_code}]")
                lines.append("")
                lines.append(f"**Message**: {failure.error_message}")
                if failure.handler_id:
                    lines.append(f"**Handler**: `{failure.handler_id}`")
                if failure.phase:
                    lines.append(f"**Phase**: {failure.phase.value}")
                lines.append("")

        # Verbose: Include detailed trace information
        if verbose and manifest.hook_traces:
            lines.extend(
                [
                    "## Detailed Traces",
                    "",
                ]
            )
            for trace in manifest.hook_traces:
                lines.append(f"### Handler: `{trace.handler_id}`")
                lines.append("")
                lines.append(f"- **Phase**: {trace.phase.value}")
                lines.append(f"- **Status**: {trace.status.value}")
                lines.append(f"- **Duration**: {trace.duration_ms:.3f}ms")
                if trace.started_at:
                    lines.append(f"- **Started**: {trace.started_at.isoformat()}")
                if trace.ended_at:
                    lines.append(f"- **Completed**: {trace.ended_at.isoformat()}")
                if trace.error_message:
                    lines.append(f"- **Error**: {trace.error_message}")
                lines.append("")

        return "\n".join(lines)

    @staticmethod
    def to_text(manifest: ModelExecutionManifest) -> str:
        """
        Convert manifest to concise text summary.

        Args:
            manifest: The manifest to convert

        Returns:
            Text summary
        """
        lines = [
            "=" * 60,
            "EXECUTION MANIFEST",
            "=" * 60,
            "",
            f"ID:       {manifest.manifest_id}",
            f"Status:   {'SUCCESS' if manifest.is_successful() else 'FAILED'}",
            f"Duration: {manifest.get_total_duration_ms():.1f}ms",
            "",
            f"Node:     {manifest.node_identity.get_qualified_id()}",
            f"Contract: {manifest.contract_identity.contract_id}",
            "",
        ]

        # Activation
        activation = manifest.activation_summary
        if activation.total_evaluated > 0:
            lines.append(
                f"Capabilities: {activation.get_activated_count()} activated, "
                f"{activation.get_skipped_count()} skipped"
            )

        # Hooks
        if manifest.hook_traces:
            successful = len(manifest.get_successful_hooks())
            failed = len(manifest.get_failed_hooks())
            lines.append(f"Hooks: {successful} succeeded, {failed} failed")

        # Emissions
        emissions = manifest.emissions_summary
        if not emissions.is_empty():
            lines.append(f"Emissions: {emissions.total_emissions()} total")

        # Failures
        if manifest.has_failures():
            lines.append("")
            lines.append("FAILURES:")
            for failure in manifest.failures:
                lines.append(f"  [{failure.error_code}] {failure.error_message}")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

    @staticmethod
    def log_summary(
        manifest: ModelExecutionManifest,
        logger: ProtocolLoggerLike,
    ) -> None:
        """
        Log manifest summary using structured logger.

        Uses duck typing - logger must have an info() method that accepts
        a message string and optional ``extra`` dict for structured metadata.
        The ``extra`` parameter is passed as a keyword argument containing
        manifest summary data for structured logging backends.

        Args:
            manifest: The manifest to log
            logger: Logger with ``info(message, *, extra=None)`` method

        Raises:
            ModelOnexError: If logger does not have the expected interface

        Example:
            >>> import logging
            >>> logger = logging.getLogger("pipeline")
            >>> ManifestLogger.log_summary(manifest, logger)
            # Logs: "Execution manifest generated"
            #
            # The ``extra`` dict passed to logger.info() contains manifest metadata
            # for structured logging backends (e.g., structlog, python-json-logger):
            #
            #   extra = {
            #       "manifest_id": "abc-123-def",
            #       "node_id": "compute-001",
            #       "contract_id": "my-contract",
            #       "hooks_executed": 3,
            #       "duration_ms": 45.2,
            #       "successful": True,
            #       "failures": 0,
            #       "events_emitted": 2,
            #       "intents_emitted": 1,
            #   }
            #
            # With JSON logging configured, output appears as:
            # {"message": "Execution manifest generated", "manifest_id": "abc-123-def", ...}
        """
        try:
            info_method = logger.info
        except AttributeError as e:
            raise ModelOnexError(
                message="Logger must have an info() method",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
                parameter="logger",
                expected_interface="ProtocolLoggerLike",
                operation="log_summary",
            ) from e

        try:
            info_method(
                "Execution manifest generated",
                extra={
                    "manifest_id": str(manifest.manifest_id),
                    "node_id": manifest.node_identity.node_id,
                    "contract_id": manifest.contract_identity.contract_id,
                    "hooks_executed": manifest.get_hook_count(),
                    "duration_ms": manifest.get_total_duration_ms(),
                    "successful": manifest.is_successful(),
                    "failures": manifest.get_failure_count(),
                    "events_emitted": manifest.emissions_summary.events_count,
                    "intents_emitted": manifest.emissions_summary.intents_count,
                },
            )
        except TypeError as e:
            raise ModelOnexError(
                message="Logger.info() method has incompatible signature",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
                parameter="logger",
                expected_interface="ProtocolLoggerLike.info(message, *, extra=None)",
                operation="log_summary",
            ) from e


# Export for use
__all__ = ["ManifestLogger"]
