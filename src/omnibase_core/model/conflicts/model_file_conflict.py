"""
Model for file-level conflict detection and resolution.

This model represents file conflicts, lock states, and resolution
strategies for coordinating multi-agent file access and preventing
simultaneous modifications.
"""

import hashlib
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field


class ConflictType(str, Enum):
    """Types of file conflicts."""

    SIMULTANEOUS_EDIT = "simultaneous_edit"
    LOCK_CONTENTION = "lock_contention"
    MERGE_CONFLICT = "merge_conflict"
    DIRECTORY_CONFLICT = "directory_conflict"
    PERMISSION_CONFLICT = "permission_conflict"
    DEPENDENCY_CONFLICT = "dependency_conflict"


class ConflictSeverity(str, Enum):
    """Severity levels for conflicts."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConflictStatus(str, Enum):
    """Status of conflict resolution."""

    DETECTED = "detected"
    ANALYZING = "analyzing"
    RESOLVING = "resolving"
    RESOLVED = "resolved"
    FAILED = "failed"
    ESCALATED = "escalated"


class LockType(str, Enum):
    """Types of file locks."""

    READ_LOCK = "read_lock"
    WRITE_LOCK = "write_lock"
    EXCLUSIVE_LOCK = "exclusive_lock"
    SHARED_LOCK = "shared_lock"


class LockStatus(str, Enum):
    """Status of file locks."""

    ACTIVE = "active"
    PENDING = "pending"
    EXPIRED = "expired"
    RELEASED = "released"
    REVOKED = "revoked"


class ResolutionStrategy(str, Enum):
    """Strategies for conflict resolution."""

    FIRST_WRITER_WINS = "first_writer_wins"
    LAST_WRITER_WINS = "last_writer_wins"
    PRIORITY_BASED = "priority_based"
    MERGE_AUTOMATIC = "merge_automatic"
    MERGE_MANUAL = "merge_manual"
    QUEUE_SEQUENTIAL = "queue_sequential"
    AGENT_COORDINATION = "agent_coordination"


class ModelFileChange(BaseModel):
    """Model for tracking file changes."""

    file_path: str = Field(description="Absolute path to the file")
    change_type: str = Field(
        description="Type of change (create, modify, delete, rename)"
    )
    agent_id: str = Field(description="ID of the agent making the change")
    ticket_id: str = Field(description="ID of the ticket this change is for")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When the change was made"
    )
    content_hash: Optional[str] = Field(
        default=None, description="Hash of the file content"
    )
    line_ranges: List[tuple] = Field(
        default_factory=list,
        description="List of (start_line, end_line) tuples for changes",
    )
    change_summary: Optional[str] = Field(
        default=None, description="Summary of what was changed"
    )
    metadata: Optional[Dict[str, str]] = Field(
        default=None, description="Additional metadata about the change"
    )

    def calculate_content_hash(self, content: str) -> str:
        """Calculate hash for file content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()


class ModelFileLock(BaseModel):
    """Model for file locking mechanism."""

    lock_id: str = Field(description="Unique identifier for the lock")
    file_path: str = Field(description="Path to the locked file")
    lock_type: LockType = Field(description="Type of lock")
    status: LockStatus = Field(
        default=LockStatus.ACTIVE, description="Current status of the lock"
    )
    agent_id: str = Field(description="ID of the agent holding the lock")
    ticket_id: str = Field(description="ID of the ticket requiring the lock")
    acquired_at: datetime = Field(
        default_factory=datetime.now, description="When the lock was acquired"
    )
    expires_at: datetime = Field(description="When the lock expires")
    released_at: Optional[datetime] = Field(
        default=None, description="When the lock was released"
    )
    lock_reason: str = Field(description="Reason for acquiring the lock")
    priority: int = Field(
        default=1, description="Priority of the lock (higher = more important)"
    )
    can_share: bool = Field(
        default=False, description="Whether this lock can be shared with other agents"
    )
    waiting_agents: List[str] = Field(
        default_factory=list, description="List of agent IDs waiting for this lock"
    )
    metadata: Optional[Dict[str, str]] = Field(
        default=None, description="Additional lock metadata"
    )

    @property
    def is_active(self) -> bool:
        """Check if lock is currently active."""
        return self.status == LockStatus.ACTIVE and datetime.now() < self.expires_at

    @property
    def is_expired(self) -> bool:
        """Check if lock has expired."""
        return datetime.now() >= self.expires_at

    @property
    def duration_held(self) -> timedelta:
        """Get duration the lock has been held."""
        end_time = self.released_at or datetime.now()
        return end_time - self.acquired_at

    @property
    def time_remaining(self) -> timedelta:
        """Get time remaining before lock expires."""
        if self.is_expired:
            return timedelta(0)
        return self.expires_at - datetime.now()

    def extend_lock(self, additional_minutes: int) -> None:
        """Extend the lock duration."""
        self.expires_at += timedelta(minutes=additional_minutes)

    def release_lock(self) -> None:
        """Release the lock."""
        self.status = LockStatus.RELEASED
        self.released_at = datetime.now()

    def revoke_lock(self) -> None:
        """Revoke the lock forcibly."""
        self.status = LockStatus.REVOKED
        self.released_at = datetime.now()


class ModelFileConflict(BaseModel):
    """Model for file conflict detection and resolution."""

    conflict_id: str = Field(description="Unique identifier for the conflict")
    conflict_type: ConflictType = Field(description="Type of conflict detected")
    severity: ConflictSeverity = Field(description="Severity level of the conflict")
    status: ConflictStatus = Field(
        default=ConflictStatus.DETECTED,
        description="Current status of conflict resolution",
    )
    file_path: str = Field(description="Path to the conflicted file")
    conflicting_agents: List[str] = Field(
        description="List of agent IDs involved in the conflict"
    )
    conflicting_tickets: List[str] = Field(
        description="List of ticket IDs involved in the conflict"
    )
    conflicting_changes: List[ModelFileChange] = Field(
        default_factory=list, description="List of conflicting file changes"
    )
    detected_at: datetime = Field(
        default_factory=datetime.now, description="When the conflict was detected"
    )
    resolved_at: Optional[datetime] = Field(
        default=None, description="When the conflict was resolved"
    )
    resolution_strategy: Optional[ResolutionStrategy] = Field(
        default=None, description="Strategy used to resolve the conflict"
    )
    resolution_details: Optional[str] = Field(
        default=None, description="Details about how the conflict was resolved"
    )
    winner_agent: Optional[str] = Field(
        default=None, description="Agent that won the conflict resolution"
    )
    affected_lines: List[tuple] = Field(
        default_factory=list,
        description="List of (start_line, end_line) tuples for affected lines",
    )
    conflict_context: Optional[Dict[str, str]] = Field(
        default=None, description="Additional context about the conflict"
    )
    escalation_reason: Optional[str] = Field(
        default=None, description="Reason for escalating the conflict"
    )
    metadata: Optional[Dict[str, str]] = Field(
        default=None, description="Additional conflict metadata"
    )

    @property
    def is_resolved(self) -> bool:
        """Check if conflict is resolved."""
        return self.status == ConflictStatus.RESOLVED

    @property
    def is_active(self) -> bool:
        """Check if conflict is actively being resolved."""
        return self.status in [
            ConflictStatus.DETECTED,
            ConflictStatus.ANALYZING,
            ConflictStatus.RESOLVING,
        ]

    @property
    def resolution_time(self) -> Optional[timedelta]:
        """Get time taken to resolve the conflict."""
        if self.resolved_at:
            return self.resolved_at - self.detected_at
        return None

    @property
    def agent_count(self) -> int:
        """Get number of agents involved in conflict."""
        return len(self.conflicting_agents)

    def add_conflicting_change(self, change: ModelFileChange) -> None:
        """Add a conflicting change to the conflict."""
        self.conflicting_changes.append(change)

        if change.agent_id not in self.conflicting_agents:
            self.conflicting_agents.append(change.agent_id)

        if change.ticket_id not in self.conflicting_tickets:
            self.conflicting_tickets.append(change.ticket_id)

    def resolve_conflict(
        self,
        strategy: ResolutionStrategy,
        winner_agent: Optional[str] = None,
        details: Optional[str] = None,
    ) -> None:
        """Mark conflict as resolved."""
        self.status = ConflictStatus.RESOLVED
        self.resolved_at = datetime.now()
        self.resolution_strategy = strategy
        self.winner_agent = winner_agent
        self.resolution_details = details

    def escalate_conflict(self, reason: str) -> None:
        """Escalate conflict for manual resolution."""
        self.status = ConflictStatus.ESCALATED
        self.escalation_reason = reason

    def fail_resolution(self, reason: str) -> None:
        """Mark conflict resolution as failed."""
        self.status = ConflictStatus.FAILED
        self.escalation_reason = reason


class ModelConflictResolution(BaseModel):
    """Model for conflict resolution outcomes."""

    resolution_id: str = Field(description="Unique identifier for the resolution")
    conflict_id: str = Field(description="ID of the conflict being resolved")
    strategy: ResolutionStrategy = Field(description="Strategy used for resolution")
    winner_agent: Optional[str] = Field(
        default=None, description="Agent that won the resolution"
    )
    actions_taken: List[str] = Field(
        default_factory=list,
        description="List of actions taken to resolve the conflict",
    )
    files_modified: List[str] = Field(
        default_factory=list, description="List of files modified during resolution"
    )
    backup_created: bool = Field(
        default=False, description="Whether a backup was created"
    )
    backup_path: Optional[str] = Field(
        default=None, description="Path to the backup file if created"
    )
    merge_required: bool = Field(
        default=False, description="Whether manual merge is required"
    )
    merge_conflicts: List[str] = Field(
        default_factory=list,
        description="List of merge conflicts that need manual resolution",
    )
    success: bool = Field(
        default=False, description="Whether the resolution was successful"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if resolution failed"
    )
    resolution_time: timedelta = Field(
        default=timedelta(), description="Time taken to resolve the conflict"
    )
    resolved_at: datetime = Field(
        default_factory=datetime.now, description="When the resolution was completed"
    )
    metadata: Optional[Dict[str, str]] = Field(
        default=None, description="Additional resolution metadata"
    )


class ModelFileMonitor(BaseModel):
    """Model for file monitoring state."""

    monitor_id: str = Field(description="Unique identifier for the monitor")
    file_path: str = Field(description="Path being monitored")
    watching_agents: Set[str] = Field(
        default_factory=set, description="Set of agent IDs watching this file"
    )
    last_modified: datetime = Field(
        default_factory=datetime.now, description="Last modification time of the file"
    )
    last_content_hash: Optional[str] = Field(
        default=None, description="Hash of the last known content"
    )
    change_history: List[ModelFileChange] = Field(
        default_factory=list, description="History of changes to this file"
    )
    active_locks: List[str] = Field(
        default_factory=list, description="List of active lock IDs for this file"
    )
    conflict_count: int = Field(
        default=0, description="Number of conflicts detected for this file"
    )
    last_conflict: Optional[datetime] = Field(
        default=None, description="When the last conflict was detected"
    )
    monitor_enabled: bool = Field(
        default=True, description="Whether monitoring is enabled for this file"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="When monitoring was started"
    )
    metadata: Optional[Dict[str, str]] = Field(
        default=None, description="Additional monitoring metadata"
    )

    @property
    def is_contested(self) -> bool:
        """Check if file is currently contested by multiple agents."""
        return len(self.watching_agents) > 1

    @property
    def has_active_locks(self) -> bool:
        """Check if file has any active locks."""
        return len(self.active_locks) > 0

    @property
    def recent_conflicts(self) -> bool:
        """Check if file has had recent conflicts."""
        if not self.last_conflict:
            return False
        return datetime.now() - self.last_conflict < timedelta(hours=1)

    def add_watcher(self, agent_id: str) -> None:
        """Add an agent as a watcher for this file."""
        self.watching_agents.add(agent_id)

    def remove_watcher(self, agent_id: str) -> None:
        """Remove an agent from watching this file."""
        self.watching_agents.discard(agent_id)

    def record_change(self, change: ModelFileChange) -> None:
        """Record a change to this file."""
        self.change_history.append(change)
        self.last_modified = change.timestamp
        if change.content_hash:
            self.last_content_hash = change.content_hash

    def add_lock(self, lock_id: str) -> None:
        """Add an active lock for this file."""
        if lock_id not in self.active_locks:
            self.active_locks.append(lock_id)

    def remove_lock(self, lock_id: str) -> None:
        """Remove a lock for this file."""
        if lock_id in self.active_locks:
            self.active_locks.remove(lock_id)

    def detect_conflict(self) -> None:
        """Record that a conflict was detected."""
        self.conflict_count += 1
        self.last_conflict = datetime.now()


class ModelConflictStatistics(BaseModel):
    """Model for conflict detection statistics."""

    total_conflicts_detected: int = Field(
        default=0, description="Total number of conflicts detected"
    )
    conflicts_resolved: int = Field(
        default=0, description="Number of conflicts successfully resolved"
    )
    conflicts_escalated: int = Field(
        default=0, description="Number of conflicts escalated for manual resolution"
    )
    conflicts_failed: int = Field(
        default=0, description="Number of conflicts that failed to resolve"
    )
    average_resolution_time: Optional[float] = Field(
        default=None, description="Average time to resolve conflicts in seconds"
    )
    most_contested_files: List[str] = Field(
        default_factory=list, description="List of files with the most conflicts"
    )
    agent_conflict_counts: Dict[str, int] = Field(
        default_factory=dict, description="Conflict count per agent"
    )
    conflict_types_frequency: Dict[str, int] = Field(
        default_factory=dict, description="Frequency of different conflict types"
    )
    resolution_strategies_used: Dict[str, int] = Field(
        default_factory=dict, description="Frequency of resolution strategies used"
    )
    peak_conflict_times: List[str] = Field(
        default_factory=list, description="Times when conflicts are most frequent"
    )
    files_under_monitoring: int = Field(
        default=0, description="Number of files currently being monitored"
    )
    active_locks: int = Field(
        default=0, description="Number of currently active file locks"
    )
    last_updated: datetime = Field(
        default_factory=datetime.now, description="When statistics were last updated"
    )

    @property
    def resolution_success_rate(self) -> float:
        """Calculate conflict resolution success rate."""
        total_resolved = (
            self.conflicts_resolved + self.conflicts_failed + self.conflicts_escalated
        )
        if total_resolved == 0:
            return 100.0
        return (self.conflicts_resolved / total_resolved) * 100.0

    @property
    def conflict_frequency(self) -> float:
        """Calculate conflicts per day."""
        # This would need time-based data to be meaningful
        return float(self.total_conflicts_detected)

    def update_agent_conflict_count(self, agent_id: str) -> None:
        """Increment conflict count for an agent."""
        self.agent_conflict_counts[agent_id] = (
            self.agent_conflict_counts.get(agent_id, 0) + 1
        )

    def update_conflict_type_frequency(self, conflict_type: str) -> None:
        """Increment frequency for a conflict type."""
        self.conflict_types_frequency[conflict_type] = (
            self.conflict_types_frequency.get(conflict_type, 0) + 1
        )

    def update_resolution_strategy_frequency(self, strategy: str) -> None:
        """Increment frequency for a resolution strategy."""
        self.resolution_strategies_used[strategy] = (
            self.resolution_strategies_used.get(strategy, 0) + 1
        )

    def get_top_conflicted_agents(self, limit: int = 5) -> List[tuple]:
        """Get agents with the most conflicts."""
        sorted_agents = sorted(
            self.agent_conflict_counts.items(), key=lambda x: x[1], reverse=True
        )
        return sorted_agents[:limit]

    def get_most_common_conflict_types(self, limit: int = 5) -> List[tuple]:
        """Get most common conflict types."""
        sorted_types = sorted(
            self.conflict_types_frequency.items(), key=lambda x: x[1], reverse=True
        )
        return sorted_types[:limit]
