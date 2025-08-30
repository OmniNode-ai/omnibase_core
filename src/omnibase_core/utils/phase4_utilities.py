"""
Phase 4 Production Readiness Utilities.

Utility functions supporting 24/7 Pydantic AI agent automation operations including
time calculations, risk assessments, scheduling helpers, and monitoring utilities.
"""

import hashlib
import statistics
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple

from omnibase_core.model.automation.model_operational_window import \
    ModelOperationalWindow
from omnibase_core.model.automation.model_work_item_validation import \
    ModelWorkItemValidation
from omnibase_core.model.classification.enum_work_complexity import \
    EnumWorkComplexity
from omnibase_core.model.classification.enum_work_priority import \
    EnumWorkPriority
from omnibase_core.model.classification.enum_work_type import EnumWorkType
from omnibase_core.model.monitoring.enum_alert_severity import \
    EnumAlertSeverity
from omnibase_core.model.monitoring.enum_incident_severity import \
    EnumIncidentSeverity


class Phase4TimeUtilities:
    """Time and scheduling utilities for Phase 4 operations."""

    @staticmethod
    def get_current_window(
        windows: List[ModelOperationalWindow],
    ) -> Optional[ModelOperationalWindow]:
        """
        Determine the currently active operational window.

        Args:
            windows: List of operational windows

        Returns:
            Currently active window or None
        """
        current_time = datetime.now().time()

        for window in windows:
            if not window.enabled:
                continue

            # Handle windows that cross midnight
            if window.start_time > window.end_time:
                if current_time >= window.start_time or current_time < window.end_time:
                    return window
            else:
                if window.start_time <= current_time < window.end_time:
                    return window

        return None

    @staticmethod
    def calculate_window_duration(window: ModelOperationalWindow) -> timedelta:
        """
        Calculate the duration of an operational window.

        Args:
            window: Operational window

        Returns:
            Duration of the window
        """
        start_dt = datetime.combine(datetime.today(), window.start_time)
        end_dt = datetime.combine(datetime.today(), window.end_time)

        # Handle windows that cross midnight
        if window.end_time < window.start_time:
            end_dt += timedelta(days=1)

        return end_dt - start_dt

    @staticmethod
    def time_until_window(window: ModelOperationalWindow) -> timedelta:
        """
        Calculate time until a window starts.

        Args:
            window: Operational window

        Returns:
            Time until window starts
        """
        now = datetime.now()
        window_start = datetime.combine(now.date(), window.start_time)

        # If window already started today, calculate for tomorrow
        if window_start <= now:
            window_start += timedelta(days=1)

        return window_start - now

    @staticmethod
    def is_overnight_window(window_name: str) -> bool:
        """
        Check if a window is an overnight window.

        Args:
            window_name: Name of the window

        Returns:
            True if overnight window
        """
        overnight_windows = ["window_1_prime", "window_2_night"]
        return window_name in overnight_windows

    @staticmethod
    def is_business_hours() -> bool:
        """
        Check if current time is during business hours.

        Returns:
            True if business hours (9 AM - 5 PM weekdays)
        """
        now = datetime.now()

        # Check if weekend
        if now.weekday() >= 5:  # Saturday or Sunday
            return False

        # Check time
        return time(9, 0) <= now.time() <= time(17, 0)


class Phase4RiskUtilities:
    """Risk assessment utilities for Phase 4 operations."""

    @staticmethod
    def calculate_composite_risk(
        work_type: EnumWorkType,
        complexity: EnumWorkComplexity,
        priority: EnumWorkPriority,
        file_count: int = 0,
    ) -> float:
        """
        Calculate composite risk score for work item.

        Args:
            work_type: Type of work
            complexity: Complexity level
            priority: Priority level
            file_count: Number of files affected

        Returns:
            Risk score (0-10 scale)
        """
        # Base risk by work type
        type_risks = {
            EnumWorkType.DEPLOYMENT: 8.0,
            EnumWorkType.ARCHITECTURE: 7.0,
            EnumWorkType.FEATURE: 5.0,
            EnumWorkType.BUG_FIX: 4.0,
            EnumWorkType.REFACTORING: 3.5,
            EnumWorkType.TESTING: 2.0,
            EnumWorkType.DOCUMENTATION: 1.0,
            EnumWorkType.CODE_FORMATTING: 0.5,
            EnumWorkType.ANALYSIS: 3.0,
        }

        # Complexity multiplier
        complexity_factors = {
            EnumWorkComplexity.TRIVIAL: 0.5,
            EnumWorkComplexity.SIMPLE: 0.7,
            EnumWorkComplexity.MODERATE: 1.0,
            EnumWorkComplexity.COMPLEX: 1.5,
            EnumWorkComplexity.VERY_COMPLEX: 2.0,
        }

        # Priority adjustment
        priority_adjustments = {
            EnumWorkPriority.URGENT: 0.5,  # Add risk for urgent items
            EnumWorkPriority.HIGH: 0.3,
            EnumWorkPriority.MEDIUM: 0.0,
            EnumWorkPriority.LOW: -0.2,
            EnumWorkPriority.DEFERRED: -0.5,
        }

        base_risk = type_risks.get(work_type, 3.0)
        complexity_factor = complexity_factors.get(complexity, 1.0)
        priority_adjustment = priority_adjustments.get(priority, 0.0)

        # File count risk (more files = higher risk)
        file_risk = min(2.0, file_count * 0.2)

        # Calculate composite risk
        risk_score = (base_risk * complexity_factor) + priority_adjustment + file_risk

        return min(10.0, max(0.0, risk_score))

    @staticmethod
    def is_safe_for_automation(
        risk_score: float,
        confidence_score: float,
        require_high_confidence: bool = False,
    ) -> bool:
        """
        Determine if work is safe for automation.

        Args:
            risk_score: Risk score (0-10)
            confidence_score: Confidence in assessment (0-1)
            require_high_confidence: Whether to require high confidence

        Returns:
            True if safe for automation
        """
        # Risk thresholds
        max_risk = 3.0 if require_high_confidence else 4.0
        min_confidence = 0.8 if require_high_confidence else 0.6

        return risk_score <= max_risk and confidence_score >= min_confidence

    @staticmethod
    def calculate_failure_impact(
        work_type: EnumWorkType,
        affects_production: bool,
        affects_customers: bool,
        data_sensitive: bool,
    ) -> EnumIncidentSeverity:
        """
        Calculate potential failure impact severity.

        Args:
            work_type: Type of work
            affects_production: Whether it affects production
            affects_customers: Whether it affects customers
            data_sensitive: Whether it involves sensitive data

        Returns:
            Incident severity level
        """
        if affects_production and affects_customers:
            return EnumIncidentSeverity.CRITICAL
        elif affects_production or data_sensitive:
            return EnumIncidentSeverity.HIGH
        elif affects_customers:
            return EnumIncidentSeverity.MEDIUM
        elif work_type in [EnumWorkType.DEPLOYMENT, EnumWorkType.ARCHITECTURE]:
            return EnumIncidentSeverity.MEDIUM
        else:
            return EnumIncidentSeverity.LOW


class Phase4MetricsUtilities:
    """Metrics calculation utilities for Phase 4 operations."""

    @staticmethod
    def calculate_efficiency_score(
        tasks_completed: int,
        tasks_failed: int,
        tokens_consumed: int,
        time_elapsed_hours: float,
    ) -> float:
        """
        Calculate efficiency score.

        Args:
            tasks_completed: Number of successful tasks
            tasks_failed: Number of failed tasks
            tokens_consumed: Total tokens consumed
            time_elapsed_hours: Time elapsed in hours

        Returns:
            Efficiency score (0-100)
        """
        if tasks_completed == 0:
            return 0.0

        # Success rate component (40%)
        total_tasks = tasks_completed + tasks_failed
        success_rate = (tasks_completed / total_tasks) * 40

        # Token efficiency component (30%)
        tokens_per_task = tokens_consumed / tasks_completed
        # Assume 5000 tokens per task is optimal
        token_efficiency = max(0, 30 - (tokens_per_task - 5000) / 1000)

        # Time efficiency component (30%)
        tasks_per_hour = tasks_completed / max(0.1, time_elapsed_hours)
        # Assume 2 tasks per hour is optimal
        time_efficiency = min(30, (tasks_per_hour / 2) * 30)

        return min(100, success_rate + token_efficiency + time_efficiency)

    @staticmethod
    def calculate_cost_metrics(
        tokens_consumed: int,
        tasks_completed: int,
        cost_per_million_tokens: float = 15.0,
    ) -> Dict[str, float]:
        """
        Calculate cost metrics.

        Args:
            tokens_consumed: Total tokens consumed
            tasks_completed: Number of tasks completed
            cost_per_million_tokens: Cost per million tokens

        Returns:
            Cost metrics dictionary
        """
        total_cost = (tokens_consumed / 1_000_000) * cost_per_million_tokens
        cost_per_task = (
            total_cost / max(1, tasks_completed) if tasks_completed > 0 else 0
        )

        return {
            "total_cost": total_cost,
            "cost_per_task": cost_per_task,
            "tokens_per_task": tokens_consumed / max(1, tasks_completed),
            "cost_per_thousand_tokens": cost_per_million_tokens / 1000,
        }

    @staticmethod
    def calculate_velocity_metrics(
        tasks_history: List[int],
        time_period_days: int = 7,
    ) -> Dict[str, float]:
        """
        Calculate velocity metrics.

        Args:
            tasks_history: List of daily task counts
            time_period_days: Time period for calculation

        Returns:
            Velocity metrics dictionary
        """
        if not tasks_history:
            return {
                "average_daily_velocity": 0,
                "velocity_trend": 0,
                "peak_velocity": 0,
                "velocity_consistency": 0,
            }

        # Use recent data
        recent_history = tasks_history[-time_period_days:]

        avg_velocity = statistics.mean(recent_history)
        peak_velocity = max(recent_history)

        # Calculate trend (positive = improving)
        if len(recent_history) >= 3:
            first_half = recent_history[: len(recent_history) // 2]
            second_half = recent_history[len(recent_history) // 2 :]
            trend = statistics.mean(second_half) - statistics.mean(first_half)
        else:
            trend = 0

        # Calculate consistency (lower is better)
        consistency = statistics.stdev(recent_history) if len(recent_history) > 1 else 0

        return {
            "average_daily_velocity": avg_velocity,
            "velocity_trend": trend,
            "peak_velocity": peak_velocity,
            "velocity_consistency": 100 - min(100, consistency * 10),
        }


class Phase4AlertUtilities:
    """Alert and incident utilities for Phase 4 operations."""

    @staticmethod
    def determine_alert_severity(
        metric_name: str,
        current_value: float,
        threshold: float,
        is_critical_system: bool = False,
    ) -> EnumAlertSeverity:
        """
        Determine alert severity based on metrics.

        Args:
            metric_name: Name of the metric
            current_value: Current metric value
            threshold: Threshold value
            is_critical_system: Whether this is a critical system

        Returns:
            Alert severity level
        """
        # Calculate how much over threshold
        if threshold > 0:
            deviation = abs(current_value - threshold) / threshold
        else:
            deviation = abs(current_value)

        # Critical metrics
        critical_metrics = [
            "api_availability",
            "database_connectivity",
            "quota_exhaustion",
        ]

        if metric_name in critical_metrics or is_critical_system:
            if deviation > 0.5:
                return EnumAlertSeverity.EMERGENCY
            elif deviation > 0.25:
                return EnumAlertSeverity.CRITICAL
            else:
                return EnumAlertSeverity.WARNING
        else:
            if deviation > 0.75:
                return EnumAlertSeverity.CRITICAL
            elif deviation > 0.5:
                return EnumAlertSeverity.WARNING
            elif deviation > 0.25:
                return EnumAlertSeverity.WARNING
            else:
                return EnumAlertSeverity.INFO

    @staticmethod
    def should_escalate(
        alert_count: int,
        time_window_minutes: int,
        severity: EnumAlertSeverity,
    ) -> bool:
        """
        Determine if alerts should be escalated.

        Args:
            alert_count: Number of alerts in window
            time_window_minutes: Time window in minutes
            severity: Alert severity

        Returns:
            True if should escalate
        """
        # Escalation thresholds by severity
        thresholds = {
            EnumAlertSeverity.EMERGENCY: 1,  # Escalate immediately
            EnumAlertSeverity.CRITICAL: 1,  # Escalate immediately
            EnumAlertSeverity.WARNING: 5,  # Escalate after 5 in window
            EnumAlertSeverity.INFO: 20,  # Rarely escalate
        }

        threshold = thresholds.get(severity, 10)

        # Adjust for time window (shorter window = more urgent)
        if time_window_minutes <= 5:
            threshold = max(1, threshold // 2)

        return alert_count >= threshold

    @staticmethod
    def calculate_incident_priority(
        severity: EnumIncidentSeverity,
        affected_users: int,
        business_impact: str,
        time_since_start_hours: float,
    ) -> int:
        """
        Calculate incident priority score.

        Args:
            severity: Incident severity
            affected_users: Number of affected users
            business_impact: Business impact level
            time_since_start_hours: Time since incident started

        Returns:
            Priority score (higher = more urgent)
        """
        # Base score by severity
        severity_scores = {
            EnumIncidentSeverity.EMERGENCY: 100,
            EnumIncidentSeverity.CRITICAL: 80,
            EnumIncidentSeverity.HIGH: 60,
            EnumIncidentSeverity.MEDIUM: 40,
            EnumIncidentSeverity.LOW: 20,
        }

        base_score = severity_scores.get(severity, 30)

        # User impact factor
        if affected_users > 1000:
            user_factor = 20
        elif affected_users > 100:
            user_factor = 15
        elif affected_users > 10:
            user_factor = 10
        else:
            user_factor = 5

        # Business impact factor
        impact_factors = {
            "critical": 20,
            "high": 15,
            "medium": 10,
            "low": 5,
            "minimal": 0,
        }
        business_factor = impact_factors.get(business_impact.lower(), 10)

        # Time factor (increases priority over time)
        time_factor = min(20, time_since_start_hours * 2)

        return int(base_score + user_factor + business_factor + time_factor)


class Phase4ValidationUtilities:
    """Validation utilities for Phase 4 operations."""

    @staticmethod
    def validate_schedule(
        windows: List[ModelOperationalWindow],
    ) -> Tuple[bool, List[str]]:
        """
        Validate operational schedule for conflicts and gaps.

        Args:
            windows: List of operational windows

        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []

        if not windows:
            issues.append("No operational windows defined")
            return False, issues

        # Check for overlaps
        for i, window1 in enumerate(windows):
            for window2 in windows[i + 1 :]:
                if Phase4ValidationUtilities._windows_overlap(window1, window2):
                    issues.append(f"Windows overlap: {window1.name} and {window2.name}")

        # Check quota allocation
        total_quota = sum(w.quota_percentage for w in windows)
        if total_quota > 100:
            issues.append(f"Total quota allocation exceeds 100%: {total_quota}%")
        elif total_quota < 95:
            issues.append(f"Total quota allocation is low: {total_quota}%")

        # Check agent allocation
        for window in windows:
            if window.min_agents > window.max_agents:
                issues.append(
                    f"Invalid agent range in {window.name}: min={window.min_agents}, max={window.max_agents}"
                )

        return len(issues) == 0, issues

    @staticmethod
    def _windows_overlap(
        window1: ModelOperationalWindow, window2: ModelOperationalWindow
    ) -> bool:
        """Check if two windows overlap."""

        # Convert to datetime for comparison
        def to_datetime(t: time) -> datetime:
            return datetime.combine(datetime.today(), t)

        start1 = to_datetime(window1.start_time)
        end1 = to_datetime(window1.end_time)
        start2 = to_datetime(window2.start_time)
        end2 = to_datetime(window2.end_time)

        # Handle windows crossing midnight
        if end1 < start1:
            end1 += timedelta(days=1)
        if end2 < start2:
            end2 += timedelta(days=1)

        # Check for overlap
        return not (end1 <= start2 or end2 <= start1)

    @staticmethod
    def validate_work_item(
        work_item: ModelWorkItemValidation,
    ) -> Tuple[bool, List[str]]:
        """
        Validate work item for automation.

        Args:
            work_item: Work item validation model

        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []

        # Validate title
        if len(work_item.title) < 5:
            issues.append("Title too short (minimum 5 characters)")
        elif len(work_item.title) > 200:
            issues.append("Title too long (maximum 200 characters)")

        # Validate file paths
        if work_item.file_paths:
            for path in work_item.file_paths:
                if not path or ".." in path:
                    issues.append(f"Invalid file path: {path}")

        # Validate work type
        if not work_item.work_type:
            issues.append("Work type cannot be empty")

        # Validate priority
        if not work_item.priority:
            issues.append("Priority cannot be empty")

        return len(issues) == 0, issues


class Phase4HashingUtilities:
    """Hashing and identification utilities for Phase 4 operations."""

    @staticmethod
    def generate_work_hash(
        title: str,
        work_type: str,
        file_paths: Optional[List[str]] = None,
    ) -> str:
        """
        Generate unique hash for work item.

        Args:
            title: Work item title
            work_type: Type of work
            file_paths: List of file paths

        Returns:
            Unique hash string
        """
        # Create hashable content
        content = f"{title}:{work_type}"
        if file_paths:
            content += ":" + ":".join(sorted(file_paths))

        # Generate hash
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    @staticmethod
    def generate_incident_id(
        severity: str,
        component: str,
        timestamp: datetime,
    ) -> str:
        """
        Generate unique incident ID.

        Args:
            severity: Incident severity
            component: Affected component
            timestamp: Incident timestamp

        Returns:
            Unique incident ID
        """
        # Create readable ID with hash
        date_str = timestamp.strftime("%Y%m%d")
        time_str = timestamp.strftime("%H%M%S")
        hash_input = f"{severity}:{component}:{timestamp.isoformat()}"
        hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:6]

        return f"INC-{date_str}-{time_str}-{hash_suffix}"

    @staticmethod
    def generate_session_id(agent_id: str, window_id: str) -> str:
        """
        Generate unique session ID for agent.

        Args:
            agent_id: Agent identifier
            window_id: Window identifier

        Returns:
            Unique session ID
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        hash_input = f"{agent_id}:{window_id}:{timestamp}"
        hash_suffix = hashlib.sha256(hash_input.encode()).hexdigest()[:8]

        return f"session_{timestamp}_{hash_suffix}"
