"""
Prometheus metrics registry for Phase 4 Production Readiness.
Centralized metrics definitions for all monitoring components.
"""

from typing import cast

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    Info,
    Summary,
    generate_latest,
)

# =============================================================================
# AGENT METRICS
# =============================================================================

# Agent state and health
agents_active = Gauge(
    "onex_agents_active",
    "Number of active agents",
    ["window_id", "agent_type"],
)

agent_health_score = Gauge(
    "onex_agent_health_score",
    "Agent health score (0-100)",
    ["agent_id", "window_id"],
)

agent_queue_depth = Gauge(
    "onex_agent_queue_depth",
    "Current queue depth per agent",
    ["agent_id", "window_id"],
)

# Agent performance
tasks_completed = Counter(
    "onex_tasks_completed_total",
    "Total tasks completed",
    ["agent_id", "task_type", "window_id"],
)

tasks_failed = Counter(
    "onex_tasks_failed_total",
    "Total tasks failed",
    ["agent_id", "task_type", "error_type", "window_id"],
)

task_duration = Histogram(
    "onex_task_duration_seconds",
    "Task completion duration",
    ["task_type", "window_id"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600),
)

# Agent scaling
scaling_events = Counter(
    "onex_agent_scaling_events_total",
    "Agent scaling events",
    [
        "direction",
        "window_id",
        "trigger",
    ],  # direction: up/down, trigger: queue/schedule/manual
)

scaling_cooldown_active = Gauge(
    "onex_scaling_cooldown_active",
    "Whether scaling cooldown is active",
    ["window_id"],
)

# =============================================================================
# QUOTA METRICS
# =============================================================================

# Quota usage
quota_tokens_used = Counter(
    "onex_quota_tokens_used_total",
    "Total tokens consumed",
    ["window_id", "task_type"],
)

quota_remaining = Gauge(
    "onex_quota_tokens_remaining",
    "Remaining quota tokens",
    ["window_id", "quota_type"],  # quota_type: allocated/emergency
)

quota_usage_rate = Gauge(
    "onex_quota_usage_rate_per_minute",
    "Token usage rate per minute",
    ["window_id"],
)

# Cost tracking
api_cost_dollars = Counter(
    "onex_api_cost_dollars_total",
    "Total API cost in dollars",
    ["window_id", "model"],
)

cost_per_task = Summary(
    "onex_cost_per_task_dollars",
    "Cost per task in dollars",
    ["task_type", "window_id"],
)

# Quota optimization
quota_reallocation_events = Counter(
    "onex_quota_reallocation_events_total",
    "Quota reallocation events",
    ["source_window", "target_window", "reason"],
)

quota_efficiency_score = Gauge(
    "onex_quota_efficiency_score",
    "Quota usage efficiency score (0-100)",
    ["window_id"],
)

# =============================================================================
# WINDOW METRICS
# =============================================================================

# Window transitions
window_transitions = Counter(
    "onex_window_transitions_total",
    "Window transition events",
    ["from_window", "to_window"],
)

current_window = Info("onex_current_window", "Currently active window")

window_quota_allocation = Gauge(
    "onex_window_quota_allocation",
    "Quota allocated per window",
    ["window_id"],
)

# Window performance
window_task_throughput = Gauge(
    "onex_window_task_throughput_per_hour",
    "Tasks processed per hour in window",
    ["window_id"],
)

window_success_rate = Gauge(
    "onex_window_success_rate",
    "Task success rate per window",
    ["window_id"],
)

# =============================================================================
# SYSTEM HEALTH METRICS
# =============================================================================

# System availability
system_health_score = Gauge(
    "onex_system_health_score",
    "Overall system health score (0-100)",
)

service_availability = Gauge(
    "onex_service_availability",
    "Service availability status",
    ["service_name"],
)

# Performance metrics
api_latency = Histogram(
    "onex_api_latency_seconds",
    "API call latency",
    ["endpoint", "method"],
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

database_query_duration = Histogram(
    "onex_database_query_duration_seconds",
    "Database query duration",
    ["query_type"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1),
)

# Error tracking
system_errors = Counter(
    "onex_system_errors_total",
    "System errors by type",
    ["error_type", "severity", "component"],
)

# =============================================================================
# DISTRIBUTED LOCK METRICS
# =============================================================================

distributed_locks_acquired = Counter(
    "onex_distributed_locks_acquired_total",
    "Distributed locks acquired",
    ["lock_name", "component"],
)

distributed_locks_failed = Counter(
    "onex_distributed_locks_failed_total",
    "Failed lock acquisition attempts",
    ["lock_name", "component", "reason"],
)

distributed_lock_hold_duration = Histogram(
    "onex_distributed_lock_hold_duration_seconds",
    "Duration locks are held",
    ["lock_name"],
    buckets=(0.1, 0.5, 1, 5, 10, 30, 60, 300),
)

distributed_locks_active = Gauge(
    "onex_distributed_locks_active",
    "Currently held distributed locks",
    ["lock_name", "holder"],
)

# =============================================================================
# INCIDENT METRICS
# =============================================================================

incidents_created = Counter(
    "onex_incidents_created_total",
    "Incidents created",
    ["severity", "component"],
)

incidents_resolved = Counter(
    "onex_incidents_resolved_total",
    "Incidents resolved",
    ["severity", "resolution_type"],
)

incident_resolution_time = Histogram(
    "onex_incident_resolution_time_seconds",
    "Time to resolve incidents",
    ["severity"],
    buckets=(60, 300, 600, 1800, 3600, 7200, 14400),
)

# =============================================================================
# BUSINESS METRICS
# =============================================================================

development_velocity = Gauge(
    "onex_development_velocity_tickets_per_day",
    "Development velocity in tickets per day",
)

roi_score = Gauge("onex_roi_score", "Return on investment score")

automation_efficiency = Gauge(
    "onex_automation_efficiency_percentage",
    "Percentage of work automated successfully",
)


def get_metrics() -> str:
    """Generate current metrics in Prometheus format."""
    return cast("str", generate_latest())


def get_content_type() -> str:
    """Get Prometheus content type for HTTP response."""
    return cast("str", CONTENT_TYPE_LATEST)
