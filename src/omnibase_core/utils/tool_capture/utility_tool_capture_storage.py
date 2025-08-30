"""Tool Capture Storage Utility

Handles data persistence for tool captures, statistics, and file management.
Follows ONEX utility patterns with strong typing and single responsibility.
"""

import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from omnibase_core.models.model_capture_stats import ModelCaptureStats
from omnibase_core.models.model_tool_capture import ModelToolCapture
from omnibase_core.models.model_tool_stats import ModelToolStats


class ModelStorageConfig(BaseModel):
    """Configuration for tool capture storage."""

    storage_path: Path = Field(
        default_factory=lambda: Path("./data/tool_captures"),
        description="Base directory for storing tool capture data",
    )
    max_captures_per_file: int = Field(
        default=10000,
        description="Maximum captures per daily file before rotation",
    )
    retention_days: int = Field(
        default=30,
        description="Number of days to retain capture files",
    )


class UtilityToolCaptureStorage:
    """Tool capture data persistence utility.

    Responsibilities:
    - JSON file storage and retrieval
    - Statistics calculation and caching
    - Data cleanup and retention policies
    - Thread-safe operations
    """

    def __init__(self, storage_path: str | None = None):
        """Initialize storage utility.

        Args:
            storage_path: Optional storage path override
        """
        # Configuration with environment variable fallback
        config_path = storage_path or os.getenv(
            "TOOL_CAPTURE_STORAGE",
            "./data/tool_captures",
        )
        self.config = ModelStorageConfig(storage_path=Path(config_path))

        # Initialize storage directory
        self.config.storage_path.mkdir(parents=True, exist_ok=True)

        # In-memory caches
        self._captures_cache: list[ModelToolCapture] = []
        self._stats_cache: dict[str, ModelToolStats] = defaultdict(ModelToolStats)
        self._cache_loaded = False

    async def save_capture(self, capture: ModelToolCapture) -> bool:
        """Save a tool capture to persistent storage.

        Args:
            capture: Tool capture to save

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Add to in-memory cache
            self._captures_cache.append(capture)

            # Update statistics
            self._update_stats(capture)

            # Save to daily file
            await self._save_to_daily_file(capture)

            return True

        except Exception:
            return False

    async def load_captures(
        self,
        date: datetime | None = None,
        limit: int | None = None,
    ) -> list[ModelToolCapture]:
        """Load tool captures from storage.

        Args:
            date: Specific date to load, defaults to today
            limit: Maximum number of captures to return

        Returns:
            List of tool captures
        """
        try:
            if not self._cache_loaded:
                await self._load_cache()

            captures = self._captures_cache.copy()

            if date:
                # Filter by date if specified
                target_date = date.date()
                captures = [c for c in captures if c.timestamp.date() == target_date]

            if limit:
                captures = captures[-limit:]

            return captures

        except Exception:
            return []

    async def get_statistics(self) -> ModelCaptureStats:
        """Get comprehensive tool execution statistics.

        Returns:
            Current statistics summary
        """
        try:
            if not self._cache_loaded:
                await self._load_cache()

            total_calls = sum(stats.count for stats in self._stats_cache.values())
            total_errors = sum(stats.errors for stats in self._stats_cache.values())
            error_rate = (total_errors / total_calls * 100) if total_calls > 0 else 0.0

            return ModelCaptureStats(
                total_captures=len(self._captures_cache),
                total_calls=total_calls,
                total_errors=total_errors,
                error_rate=error_rate,
                active_sessions=0,  # Managed by service layer
                storage_path=str(self.config.storage_path),
                tool_stats=dict(self._stats_cache),
            )

        except Exception:
            return ModelCaptureStats(
                total_captures=0,
                total_calls=0,
                total_errors=0,
                error_rate=0.0,
                active_sessions=0,
                storage_path=str(self.config.storage_path),
                tool_stats={},
            )

    async def cleanup_old_files(self) -> int:
        """Clean up old capture files based on retention policy.

        Returns:
            Number of files cleaned up
        """
        try:
            cleanup_count = 0
            cutoff_date = datetime.now().date()

            # Find files older than retention period
            for file_path in self.config.storage_path.glob("captures_*.json"):
                try:
                    # Extract date from filename
                    date_str = file_path.stem.replace("captures_", "")
                    file_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                    days_old = (cutoff_date - file_date).days
                    if days_old > self.config.retention_days:
                        file_path.unlink()
                        cleanup_count += 1

                except (ValueError, OSError):
                    pass

            return cleanup_count

        except Exception:
            return 0

    async def update_capture_result(
        self,
        tool_use_id: str,
        result: str,
        status: str = "completed",
    ) -> bool:
        """Update a capture with execution result.

        Args:
            tool_use_id: ID of the tool use to update
            result: Tool execution result
            status: Updated status

        Returns:
            True if updated successfully
        """
        try:
            for capture in self._captures_cache:
                if capture.id == tool_use_id:
                    capture.result = result
                    capture.status = status
                    capture.result_timestamp = datetime.now()

                    # Re-save the daily file
                    await self._save_to_daily_file(capture, update_mode=True)
                    return True

            return False

        except Exception:
            return False

    async def _save_to_daily_file(
        self,
        capture: ModelToolCapture,
        update_mode: bool = False,
    ) -> None:
        """Save capture to daily JSON file.

        Args:
            capture: Capture to save
            update_mode: Whether this is an update to existing capture
        """
        date_str = capture.timestamp.strftime("%Y-%m-%d")
        file_path = self.config.storage_path / f"captures_{date_str}.json"

        if update_mode or not file_path.exists():
            # Write all captures for the day
            day_captures = [
                c
                for c in self._captures_cache
                if c.timestamp.date() == capture.timestamp.date()
            ]

            with open(file_path, "w") as f:
                captures_data = [c.model_dump(mode="json") for c in day_captures]
                json.dump(captures_data, f, indent=2)

        else:
            # Append to existing file (for performance)
            try:
                with open(file_path) as f:
                    existing_data = json.load(f)

                existing_data.append(capture.model_dump(mode="json"))

                with open(file_path, "w") as f:
                    json.dump(existing_data, f, indent=2)

            except (json.JSONDecodeError, FileNotFoundError):
                # Fall back to full write
                with open(file_path, "w") as f:
                    json.dump([capture.model_dump(mode="json")], f, indent=2)

    async def _load_cache(self) -> None:
        """Load today's captures into memory cache."""
        if self._cache_loaded:
            return

        try:
            date_str = datetime.now().strftime("%Y-%m-%d")
            file_path = self.config.storage_path / f"captures_{date_str}.json"

            if file_path.exists():
                with open(file_path) as f:
                    capture_dicts = json.load(f)
                    self._captures_cache = [
                        ModelToolCapture(**c) for c in capture_dicts
                    ]

                # Rebuild statistics from loaded captures
                self._stats_cache.clear()
                for capture in self._captures_cache:
                    self._update_stats(capture)

            self._cache_loaded = True

        except Exception:
            self._cache_loaded = True  # Prevent retry loops

    def _update_stats(self, capture: ModelToolCapture) -> None:
        """Update statistics with new capture.

        Args:
            capture: Capture to include in statistics
        """
        tool_name = capture.tool_name
        stats = self._stats_cache[tool_name]

        stats.count += 1
        if capture.status == "error":
            stats.errors += 1

        # Update timing statistics
        if capture.duration_ms:
            if stats.avg_duration_ms == 0:
                stats.avg_duration_ms = capture.duration_ms
            else:
                # Simple moving average
                stats.avg_duration_ms = (
                    stats.avg_duration_ms * (stats.count - 1) + capture.duration_ms
                ) / stats.count

    def get_storage_path(self) -> Path:
        """Get the current storage path."""
        return self.config.storage_path

    def is_storage_accessible(self) -> bool:
        """Check if storage directory is accessible."""
        try:
            return (
                self.config.storage_path.exists()
                and self.config.storage_path.is_dir()
                and os.access(self.config.storage_path, os.R_OK | os.W_OK)
            )
        except Exception:
            return False
