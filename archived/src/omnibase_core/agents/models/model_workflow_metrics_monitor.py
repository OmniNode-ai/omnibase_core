"""
Workflow Metrics and Monitoring System for WorkflowOrchestratorAgent.

This module provides real-time metrics collection, performance monitoring,
alerting, and comprehensive analytics for workflow orchestration operations.
"""

import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field

from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.enum_workflow_status import EnumWorkflowStatus
from omnibase_core.models.core.model_generic_metadata import ModelGenericMetadata


class ModelWorkflowMetric(BaseModel):
    """Model for individual workflow metrics."""

    metric_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique metric identifier"
    )
    workflow_id: str = Field(..., description="Workflow instance identifier")
    metric_name: str = Field(..., description="Name of the metric")
    metric_value: float = Field(..., description="Numeric metric value")
    metric_unit: str = Field(
        ..., description="Unit of measurement (ms, bytes, count, etc.)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Metric collection timestamp"
    )
    metric_type: str = Field(
        ..., description="Type of metric (performance, resource, business, etc.)"
    )
    tags: Dict[str, str] = Field(
        default_factory=dict, description="Additional metric tags"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metric metadata"
    )


class ModelPerformanceAlert(BaseModel):
    """Model for performance alerts and thresholds."""

    alert_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique alert identifier"
    )
    alert_name: str = Field(..., description="Human-readable alert name")
    metric_name: str = Field(..., description="Name of the monitored metric")
    threshold_value: float = Field(..., description="Alert threshold value")
    comparison_operator: str = Field(
        ..., description="Comparison operator (>, <, >=, <=, ==)"
    )
    severity: str = Field(
        ..., description="Alert severity (LOW, MEDIUM, HIGH, CRITICAL)"
    )
    alert_enabled: bool = Field(default=True, description="Whether the alert is active")
    created_timestamp: datetime = Field(
        default_factory=datetime.now, description="Alert creation timestamp"
    )
    last_triggered: Optional[datetime] = Field(
        None, description="Last time alert was triggered"
    )
    trigger_count: int = Field(
        default=0, description="Number of times alert has been triggered"
    )
    description: str = Field(default="", description="Human-readable alert description")


class ModelWorkflowPerformanceReport(BaseModel):
    """Model for comprehensive workflow performance reports."""

    report_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique report identifier"
    )
    generated_timestamp: datetime = Field(
        default_factory=datetime.now, description="Report generation timestamp"
    )
    time_window_start: datetime = Field(
        ..., description="Start of reporting time window"
    )
    time_window_end: datetime = Field(..., description="End of reporting time window")
    total_workflows: int = Field(..., description="Total workflows in time window")
    successful_workflows: int = Field(
        ..., description="Successfully completed workflows"
    )
    failed_workflows: int = Field(..., description="Failed workflows")
    cancelled_workflows: int = Field(..., description="Cancelled workflows")
    avg_execution_time_ms: float = Field(
        ..., description="Average workflow execution time in milliseconds"
    )
    max_execution_time_ms: float = Field(
        ..., description="Maximum workflow execution time in milliseconds"
    )
    min_execution_time_ms: float = Field(
        ..., description="Minimum workflow execution time in milliseconds"
    )
    throughput_workflows_per_hour: float = Field(
        ..., description="Workflow throughput per hour"
    )
    error_rate_percent: float = Field(..., description="Error rate as percentage")
    resource_utilization: Dict[str, float] = Field(
        default_factory=dict, description="Resource utilization metrics"
    )
    performance_trends: Dict[str, List[float]] = Field(
        default_factory=dict, description="Performance trend data"
    )
    alert_summary: Dict[str, int] = Field(
        default_factory=dict, description="Summary of alerts triggered"
    )


class WorkflowMetricsMonitor:
    """
    Comprehensive workflow metrics and monitoring system.

    Provides real-time metrics collection, performance analysis, alerting,
    and detailed reporting for workflow orchestration operations.
    """

    def __init__(
        self, max_metric_history: int = 10000, alert_cooldown_seconds: int = 300
    ):
        """
        Initialize the workflow metrics monitor.

        Args:
            max_metric_history: Maximum number of metrics to retain in memory
            alert_cooldown_seconds: Minimum time between repeated alerts
        """
        # Metrics storage
        self._metrics: deque = deque(maxlen=max_metric_history)
        self._metrics_by_workflow: Dict[str, List[ModelWorkflowMetric]] = defaultdict(
            list
        )
        self._metrics_lock = threading.RLock()

        # Performance tracking
        self._workflow_start_times: Dict[str, datetime] = {}
        self._workflow_end_times: Dict[str, datetime] = {}
        self._execution_times: deque = deque(maxlen=1000)
        self._performance_lock = threading.RLock()

        # Alerting system
        self._alerts: Dict[str, ModelPerformanceAlert] = {}
        self._alert_history: deque = deque(maxlen=1000)
        self._alerts_lock = threading.RLock()
        self._alert_cooldown_seconds = alert_cooldown_seconds

        # Resource monitoring
        self._resource_usage: Dict[str, deque] = {
            "cpu_usage_percent": deque(maxlen=100),
            "memory_usage_mb": deque(maxlen=100),
            "network_io_mb": deque(maxlen=100),
            "disk_io_mb": deque(maxlen=100),
        }
        self._resource_lock = threading.RLock()

        # Aggregated statistics
        self._workflow_counts: Dict[str, int] = defaultdict(int)
        self._workflow_status_counts: Dict[EnumWorkflowStatus, int] = defaultdict(int)
        self._statistics_lock = threading.RLock()

        # Configuration
        self._max_metric_history = max_metric_history
        self._monitoring_enabled = True

        emit_log_event(
            level=LogLevel.INFO,
            message="Workflow metrics monitor initialized",
            context=ModelGenericMetadata.from_dict(
                {
                    "max_metric_history": max_metric_history,
                    "alert_cooldown_seconds": alert_cooldown_seconds,
                }
            ),
        )

    def record_workflow_started(
        self, workflow_id: str, workflow_metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record the start of a workflow execution.

        Args:
            workflow_id: Unique workflow identifier
            workflow_metadata: Additional workflow metadata
        """
        if not self._monitoring_enabled:
            return

        try:
            current_time = datetime.now()

            with self._performance_lock:
                self._workflow_start_times[workflow_id] = current_time

            # Record workflow start metric
            start_metric = ModelWorkflowMetric(
                workflow_id=workflow_id,
                metric_name="workflow_started",
                metric_value=1.0,
                metric_unit="count",
                timestamp=current_time,
                metric_type="lifecycle",
                tags={"action": "start"},
                metadata=workflow_metadata or {},
            )

            self._add_metric(start_metric)

            with self._statistics_lock:
                self._workflow_counts["started"] += 1

            emit_log_event(
                level=LogLevel.DEBUG,
                message="Workflow start recorded",
                context=ModelGenericMetadata.from_dict(
                    {"workflow_id": workflow_id, "start_time": current_time.isoformat()}
                ),
            )

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to record workflow start: {str(e)}",
                context=ModelGenericMetadata.from_dict(
                    {"workflow_id": workflow_id, "error": str(e)}
                ),
            )

    def record_workflow_completed(
        self,
        workflow_id: str,
        status: EnumWorkflowStatus,
        workflow_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[float]:
        """
        Record the completion of a workflow execution.

        Args:
            workflow_id: Unique workflow identifier
            status: Final workflow status
            workflow_metadata: Additional workflow metadata

        Returns:
            Optional[float]: Execution time in milliseconds if available
        """
        if not self._monitoring_enabled:
            return None

        try:
            current_time = datetime.now()
            execution_time_ms = None

            with self._performance_lock:
                self._workflow_end_times[workflow_id] = current_time

                # Calculate execution time if start time exists
                start_time = self._workflow_start_times.get(workflow_id)
                if start_time:
                    execution_time_ms = (
                        current_time - start_time
                    ).total_seconds() * 1000
                    self._execution_times.append(execution_time_ms)

                    # Clean up start time tracking
                    del self._workflow_start_times[workflow_id]

            # Record completion metric
            completion_metric = ModelWorkflowMetric(
                workflow_id=workflow_id,
                metric_name="workflow_completed",
                metric_value=1.0,
                metric_unit="count",
                timestamp=current_time,
                metric_type="lifecycle",
                tags={"action": "complete", "status": status.value},
                metadata={
                    **(workflow_metadata or {}),
                    "execution_time_ms": execution_time_ms,
                },
            )

            self._add_metric(completion_metric)

            # Record execution time metric if available
            if execution_time_ms is not None:
                execution_time_metric = ModelWorkflowMetric(
                    workflow_id=workflow_id,
                    metric_name="workflow_execution_time",
                    metric_value=execution_time_ms,
                    metric_unit="milliseconds",
                    timestamp=current_time,
                    metric_type="performance",
                    tags={"status": status.value},
                    metadata=workflow_metadata or {},
                )

                self._add_metric(execution_time_metric)

            # Update statistics
            with self._statistics_lock:
                self._workflow_counts["completed"] += 1
                self._workflow_status_counts[status] += 1

            # Check performance alerts
            self._check_performance_alerts(execution_time_ms)

            emit_log_event(
                level=LogLevel.DEBUG,
                message="Workflow completion recorded",
                context=ModelGenericMetadata.from_dict(
                    {
                        "workflow_id": workflow_id,
                        "status": status.value,
                        "execution_time_ms": execution_time_ms,
                    }
                ),
            )

            return execution_time_ms

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to record workflow completion: {str(e)}",
                context=ModelGenericMetadata.from_dict(
                    {"workflow_id": workflow_id, "error": str(e)}
                ),
            )
            return None

    def record_custom_metric(
        self,
        workflow_id: str,
        metric_name: str,
        metric_value: float,
        metric_unit: str = "count",
        metric_type: str = "custom",
        tags: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Record a custom workflow metric.

        Args:
            workflow_id: Unique workflow identifier
            metric_name: Name of the custom metric
            metric_value: Numeric metric value
            metric_unit: Unit of measurement
            metric_type: Type of metric
            tags: Additional metric tags
            metadata: Additional metric metadata

        Returns:
            bool: True if metric was recorded successfully
        """
        if not self._monitoring_enabled:
            return False

        try:
            custom_metric = ModelWorkflowMetric(
                workflow_id=workflow_id,
                metric_name=metric_name,
                metric_value=metric_value,
                metric_unit=metric_unit,
                metric_type=metric_type,
                tags=tags or {},
                metadata=metadata or {},
            )

            self._add_metric(custom_metric)

            emit_log_event(
                level=LogLevel.DEBUG,
                message="Custom metric recorded",
                context=ModelGenericMetadata.from_dict(
                    {
                        "workflow_id": workflow_id,
                        "metric_name": metric_name,
                        "metric_value": metric_value,
                        "metric_unit": metric_unit,
                    }
                ),
            )

            return True

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to record custom metric: {str(e)}",
                context=ModelGenericMetadata.from_dict(
                    {
                        "workflow_id": workflow_id,
                        "metric_name": metric_name,
                        "error": str(e),
                    }
                ),
            )
            return False

    def create_performance_alert(
        self,
        alert_name: str,
        metric_name: str,
        threshold_value: float,
        comparison_operator: str = ">",
        severity: str = "MEDIUM",
        description: str = "",
    ) -> str:
        """
        Create a new performance alert.

        Args:
            alert_name: Human-readable alert name
            metric_name: Name of the monitored metric
            threshold_value: Alert threshold value
            comparison_operator: Comparison operator (>, <, >=, <=, ==)
            severity: Alert severity (LOW, MEDIUM, HIGH, CRITICAL)
            description: Human-readable alert description

        Returns:
            str: Alert ID if created successfully
        """
        try:
            alert = ModelPerformanceAlert(
                alert_name=alert_name,
                metric_name=metric_name,
                threshold_value=threshold_value,
                comparison_operator=comparison_operator,
                severity=severity,
                description=description,
            )

            with self._alerts_lock:
                self._alerts[alert.alert_id] = alert

            emit_log_event(
                level=LogLevel.INFO,
                message="Performance alert created",
                context=ModelGenericMetadata.from_dict(
                    {
                        "alert_id": alert.alert_id,
                        "alert_name": alert_name,
                        "metric_name": metric_name,
                        "threshold_value": threshold_value,
                        "severity": severity,
                    }
                ),
            )

            return alert.alert_id

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to create performance alert: {str(e)}",
                context=ModelGenericMetadata.from_dict(
                    {"alert_name": alert_name, "error": str(e)}
                ),
            )
            return ""

    def get_workflow_metrics(
        self,
        workflow_id: Optional[str] = None,
        metric_name: Optional[str] = None,
        time_window_minutes: Optional[int] = None,
    ) -> List[ModelWorkflowMetric]:
        """
        Get workflow metrics based on filters.

        Args:
            workflow_id: Filter by specific workflow ID
            metric_name: Filter by specific metric name
            time_window_minutes: Filter by time window in minutes

        Returns:
            List[ModelWorkflowMetric]: Filtered metrics
        """
        try:
            with self._metrics_lock:
                metrics = list(self._metrics)

            # Apply filters
            if workflow_id:
                metrics = [m for m in metrics if m.workflow_id == workflow_id]

            if metric_name:
                metrics = [m for m in metrics if m.metric_name == metric_name]

            if time_window_minutes:
                cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
                metrics = [m for m in metrics if m.timestamp >= cutoff_time]

            return metrics

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to get workflow metrics: {str(e)}",
                context=ModelGenericMetadata.from_dict(
                    {"workflow_id": workflow_id, "error": str(e)}
                ),
            )
            return []

    def get_performance_summary(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """
        Get a comprehensive performance summary.

        Args:
            time_window_minutes: Time window for analysis in minutes

        Returns:
            Dict[str, Any]: Performance summary data
        """
        try:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(minutes=time_window_minutes)

            # Get metrics within time window
            recent_metrics = self.get_workflow_metrics(
                time_window_minutes=time_window_minutes
            )

            # Calculate execution time statistics
            execution_times = [
                m.metric_value
                for m in recent_metrics
                if m.metric_name == "workflow_execution_time"
            ]

            # Calculate workflow counts
            completed_workflows = len(
                [m for m in recent_metrics if m.metric_name == "workflow_completed"]
            )

            started_workflows = len(
                [m for m in recent_metrics if m.metric_name == "workflow_started"]
            )

            # Calculate status distribution
            status_distribution = defaultdict(int)
            for metric in recent_metrics:
                if metric.metric_name == "workflow_completed":
                    status = metric.tags.get("status", "unknown")
                    status_distribution[status] += 1

            # Calculate performance statistics
            avg_execution_time = (
                sum(execution_times) / len(execution_times) if execution_times else 0.0
            )
            max_execution_time = max(execution_times) if execution_times else 0.0
            min_execution_time = min(execution_times) if execution_times else 0.0

            # Calculate throughput (workflows per hour)
            throughput = (
                (completed_workflows / time_window_minutes) * 60
                if time_window_minutes > 0
                else 0.0
            )

            # Calculate error rate
            failed_workflows = status_distribution.get("failed", 0)
            error_rate = (failed_workflows / max(completed_workflows, 1)) * 100

            # Get active alerts
            active_alerts = self._get_active_alerts()

            summary = {
                "time_window": {
                    "start_time": cutoff_time.isoformat(),
                    "end_time": current_time.isoformat(),
                    "window_minutes": time_window_minutes,
                },
                "workflow_counts": {
                    "started": started_workflows,
                    "completed": completed_workflows,
                    "in_progress": started_workflows - completed_workflows,
                },
                "status_distribution": dict(status_distribution),
                "performance_metrics": {
                    "avg_execution_time_ms": round(avg_execution_time, 2),
                    "max_execution_time_ms": round(max_execution_time, 2),
                    "min_execution_time_ms": round(min_execution_time, 2),
                    "throughput_per_hour": round(throughput, 2),
                    "error_rate_percent": round(error_rate, 2),
                },
                "resource_utilization": self._get_resource_utilization_summary(),
                "active_alerts": len(active_alerts),
                "total_metrics_collected": len(recent_metrics),
            }

            return summary

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to generate performance summary: {str(e)}",
                context=ModelGenericMetadata.from_dict(
                    {"time_window_minutes": time_window_minutes, "error": str(e)}
                ),
            )
            return {"error": str(e)}

    def generate_performance_report(
        self, start_time: datetime, end_time: datetime
    ) -> ModelWorkflowPerformanceReport:
        """
        Generate a comprehensive performance report for a time period.

        Args:
            start_time: Start of reporting time window
            end_time: End of reporting time window

        Returns:
            ModelWorkflowPerformanceReport: Comprehensive performance report
        """
        try:
            # Get metrics within time window
            with self._metrics_lock:
                window_metrics = [
                    m for m in self._metrics if start_time <= m.timestamp <= end_time
                ]

            # Calculate workflow statistics
            completed_metrics = [
                m for m in window_metrics if m.metric_name == "workflow_completed"
            ]
            execution_time_metrics = [
                m for m in window_metrics if m.metric_name == "workflow_execution_time"
            ]

            total_workflows = len(completed_metrics)
            execution_times = [m.metric_value for m in execution_time_metrics]

            # Calculate status counts
            status_counts = defaultdict(int)
            for metric in completed_metrics:
                status = metric.tags.get("status", "unknown")
                status_counts[status] += 1

            successful_workflows = status_counts.get("completed", 0)
            failed_workflows = status_counts.get("failed", 0)
            cancelled_workflows = status_counts.get("cancelled", 0)

            # Calculate performance metrics
            avg_execution_time = (
                sum(execution_times) / len(execution_times) if execution_times else 0.0
            )
            max_execution_time = max(execution_times) if execution_times else 0.0
            min_execution_time = min(execution_times) if execution_times else 0.0

            # Calculate throughput
            time_window_hours = (end_time - start_time).total_seconds() / 3600
            throughput = (
                total_workflows / time_window_hours if time_window_hours > 0 else 0.0
            )

            # Calculate error rate
            error_rate = (failed_workflows / max(total_workflows, 1)) * 100

            # Get alert summary
            alert_summary = self._get_alert_summary_for_period(start_time, end_time)

            # Generate performance trends (simplified)
            performance_trends = {
                "execution_times": (
                    execution_times[-50:]
                    if len(execution_times) > 50
                    else execution_times
                ),
                "throughput_per_hour": [
                    throughput
                ],  # Simplified for this implementation
                "error_rates": [error_rate],  # Simplified for this implementation
            }

            # Create performance report
            report = ModelWorkflowPerformanceReport(
                time_window_start=start_time,
                time_window_end=end_time,
                total_workflows=total_workflows,
                successful_workflows=successful_workflows,
                failed_workflows=failed_workflows,
                cancelled_workflows=cancelled_workflows,
                avg_execution_time_ms=avg_execution_time,
                max_execution_time_ms=max_execution_time,
                min_execution_time_ms=min_execution_time,
                throughput_workflows_per_hour=throughput,
                error_rate_percent=error_rate,
                resource_utilization=self._get_resource_utilization_summary(),
                performance_trends=performance_trends,
                alert_summary=alert_summary,
            )

            emit_log_event(
                level=LogLevel.INFO,
                message="Performance report generated",
                context=ModelGenericMetadata.from_dict(
                    {
                        "report_id": report.report_id,
                        "time_window_hours": time_window_hours,
                        "total_workflows": total_workflows,
                    }
                ),
            )

            return report

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to generate performance report: {str(e)}",
                context=ModelGenericMetadata.from_dict(
                    {
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "error": str(e),
                    }
                ),
            )
            # Return empty report on error
            return ModelWorkflowPerformanceReport(
                time_window_start=start_time,
                time_window_end=end_time,
                total_workflows=0,
                successful_workflows=0,
                failed_workflows=0,
                cancelled_workflows=0,
                avg_execution_time_ms=0.0,
                max_execution_time_ms=0.0,
                min_execution_time_ms=0.0,
                throughput_workflows_per_hour=0.0,
                error_rate_percent=0.0,
            )

    def _add_metric(self, metric: ModelWorkflowMetric) -> None:
        """Add a metric to the storage system."""
        with self._metrics_lock:
            self._metrics.append(metric)
            self._metrics_by_workflow[metric.workflow_id].append(metric)

            # Limit per-workflow metrics to prevent memory bloat
            if len(self._metrics_by_workflow[metric.workflow_id]) > 100:
                self._metrics_by_workflow[metric.workflow_id] = (
                    self._metrics_by_workflow[metric.workflow_id][-100:]
                )

    def _check_performance_alerts(self, execution_time_ms: Optional[float]) -> None:
        """Check if any performance alerts should be triggered."""
        if execution_time_ms is None:
            return

        try:
            current_time = datetime.now()

            with self._alerts_lock:
                for alert in self._alerts.values():
                    if not alert.alert_enabled:
                        continue

                    # Check if alert cooldown period has passed
                    if (
                        alert.last_triggered
                        and (current_time - alert.last_triggered).total_seconds()
                        < self._alert_cooldown_seconds
                    ):
                        continue

                    # Check if alert condition is met (simplified for execution time)
                    if alert.metric_name == "workflow_execution_time":
                        should_trigger = self._evaluate_alert_condition(
                            execution_time_ms,
                            alert.threshold_value,
                            alert.comparison_operator,
                        )

                        if should_trigger:
                            self._trigger_alert(alert, execution_time_ms)

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to check performance alerts: {str(e)}",
                context=ModelGenericMetadata.from_dict({"error": str(e)}),
            )

    def _evaluate_alert_condition(
        self, value: float, threshold: float, operator: str
    ) -> bool:
        """Evaluate if an alert condition is met."""
        if operator == ">":
            return value > threshold
        elif operator == "<":
            return value < threshold
        elif operator == ">=":
            return value >= threshold
        elif operator == "<=":
            return value <= threshold
        elif operator == "==":
            return value == threshold
        else:
            return False

    def _trigger_alert(self, alert: ModelPerformanceAlert, metric_value: float) -> None:
        """Trigger a performance alert."""
        try:
            current_time = datetime.now()

            # Update alert state
            alert.last_triggered = current_time
            alert.trigger_count += 1

            # Log alert
            emit_log_event(
                level=(
                    LogLevel.WARNING
                    if alert.severity in ["LOW", "MEDIUM"]
                    else LogLevel.ERROR
                ),
                message=f"Performance alert triggered: {alert.alert_name}",
                context=ModelGenericMetadata.from_dict(
                    {
                        "alert_id": alert.alert_id,
                        "alert_name": alert.alert_name,
                        "metric_name": alert.metric_name,
                        "threshold_value": alert.threshold_value,
                        "actual_value": metric_value,
                        "severity": alert.severity,
                        "trigger_count": alert.trigger_count,
                    }
                ),
            )

            # Add to alert history
            alert_event = {
                "alert_id": alert.alert_id,
                "alert_name": alert.alert_name,
                "triggered_at": current_time.isoformat(),
                "metric_value": metric_value,
                "threshold_value": alert.threshold_value,
                "severity": alert.severity,
            }

            self._alert_history.append(alert_event)

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to trigger alert: {str(e)}",
                context=ModelGenericMetadata.from_dict(
                    {"alert_id": alert.alert_id, "error": str(e)}
                ),
            )

    def _get_active_alerts(self) -> List[ModelPerformanceAlert]:
        """Get list of active alerts."""
        with self._alerts_lock:
            return [alert for alert in self._alerts.values() if alert.alert_enabled]

    def _get_resource_utilization_summary(self) -> Dict[str, float]:
        """Get summary of resource utilization."""
        summary = {}

        with self._resource_lock:
            for resource_type, values in self._resource_usage.items():
                if values:
                    summary[resource_type] = {
                        "current": values[-1] if values else 0.0,
                        "average": sum(values) / len(values),
                        "max": max(values),
                        "min": min(values),
                    }
                else:
                    summary[resource_type] = {
                        "current": 0.0,
                        "average": 0.0,
                        "max": 0.0,
                        "min": 0.0,
                    }

        return summary

    def _get_alert_summary_for_period(
        self, start_time: datetime, end_time: datetime
    ) -> Dict[str, int]:
        """Get alert summary for a specific time period."""
        alert_summary = defaultdict(int)

        for alert_event in self._alert_history:
            event_time = datetime.fromisoformat(alert_event["triggered_at"])
            if start_time <= event_time <= end_time:
                severity = alert_event["severity"]
                alert_summary[severity] += 1

        return dict(alert_summary)

    def cleanup_old_metrics(self, retention_hours: int = 24) -> Dict[str, int]:
        """
        Clean up old metrics beyond retention period.

        Args:
            retention_hours: Number of hours to retain metrics

        Returns:
            Dict[str, int]: Cleanup statistics
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=retention_hours)

            metrics_removed = 0
            alerts_removed = 0

            # Clean up old metrics
            with self._metrics_lock:
                original_count = len(self._metrics)
                self._metrics = deque(
                    (m for m in self._metrics if m.timestamp >= cutoff_time),
                    maxlen=self._max_metric_history,
                )
                metrics_removed = original_count - len(self._metrics)

                # Clean up per-workflow metrics
                for workflow_id in list(self._metrics_by_workflow.keys()):
                    self._metrics_by_workflow[workflow_id] = [
                        m
                        for m in self._metrics_by_workflow[workflow_id]
                        if m.timestamp >= cutoff_time
                    ]

                    # Remove empty workflow metric lists
                    if not self._metrics_by_workflow[workflow_id]:
                        del self._metrics_by_workflow[workflow_id]

            # Clean up old alert history
            with self._alerts_lock:
                original_alert_count = len(self._alert_history)
                self._alert_history = deque(
                    (
                        a
                        for a in self._alert_history
                        if datetime.fromisoformat(a["triggered_at"]) >= cutoff_time
                    ),
                    maxlen=1000,
                )
                alerts_removed = original_alert_count - len(self._alert_history)

            cleanup_stats = {
                "metrics_removed": metrics_removed,
                "alert_events_removed": alerts_removed,
                "retention_hours": retention_hours,
            }

            emit_log_event(
                level=LogLevel.INFO,
                message="Metrics cleanup completed",
                metadata=ModelGenericMetadata.from_dict(cleanup_stats),
            )

            return cleanup_stats

        except Exception as e:
            emit_log_event(
                level=LogLevel.ERROR,
                message=f"Failed to cleanup old metrics: {str(e)}",
                context=ModelGenericMetadata.from_dict(
                    {"retention_hours": retention_hours, "error": str(e)}
                ),
            )
            return {"error": str(e)}
