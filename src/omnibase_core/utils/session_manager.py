"""
Thread-safe Session Manager for ONEX MCP Server

Provides thread-safe session management with proper isolation.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from omnibase_core.core.core_errors import CoreErrorCode, OnexError
from omnibase_core.model.mcp.model_mcp_session import ModelMCPSession

logger = logging.getLogger(__name__)


class ModelSessionConfig(BaseModel):
    """Configuration for session management."""

    max_sessions: int = Field(default=1000, description="Maximum concurrent sessions")
    session_timeout: timedelta = Field(
        default_factory=lambda: timedelta(hours=24),
        description="Session timeout duration",
    )
    cleanup_interval: timedelta = Field(
        default_factory=lambda: timedelta(minutes=15),
        description="Interval for cleaning up expired sessions",
    )
    enable_cleanup: bool = Field(default=True, description="Enable automatic cleanup")


class ThreadSafeSessionManager:
    """Thread-safe session manager with proper isolation."""

    def __init__(self, config: Optional[ModelSessionConfig] = None):
        """Initialize the session manager."""
        self.config = config or ModelSessionConfig()
        self._sessions: dict[str, ModelMCPSession] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self.logger = logger

    async def start(self) -> None:
        """Start the session manager and cleanup task."""
        if self.config.enable_cleanup and not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            self.logger.info("Session manager started with automatic cleanup")

    async def stop(self) -> None:
        """Stop the session manager and cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            self.logger.info("Session manager stopped")

    async def create_session(self, session_id: Optional[str] = None) -> ModelMCPSession:
        """
        Create a new session with proper isolation.

        Args:
            session_id: Optional session ID. If not provided, generates a new one.

        Returns:
            The created session

        Raises:
            OnexError if max sessions reached or session already exists
        """
        async with self._lock:
            # Check max sessions
            if len(self._sessions) >= self.config.max_sessions:
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_ERROR,
                    message=f"Maximum sessions ({self.config.max_sessions}) reached",
                    source="SessionManager",
                    metadata={"current_sessions": len(self._sessions)},
                )

            # Generate session ID if not provided
            if not session_id:
                session_id = str(uuid4())

            # Check if session already exists
            if session_id in self._sessions:
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_ERROR,
                    message=f"Session {session_id} already exists",
                    source="SessionManager",
                )

            # Create new session
            session = ModelMCPSession(session_id=session_id)
            self._sessions[session_id] = session

            self.logger.info(f"Created session: {session_id}")
            return session

    async def get_session(self, session_id: str) -> Optional[ModelMCPSession]:
        """
        Get a session by ID with thread safety.

        Args:
            session_id: The session ID

        Returns:
            The session if found, None otherwise
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                # Update access time
                session.update_access_time()
                # Check if expired
                if self._is_session_expired(session):
                    del self._sessions[session_id]
                    self.logger.info(f"Session {session_id} expired and removed")
                    return None
            return session

    async def update_session(self, session_id: str, metadata: dict) -> bool:
        """
        Update session metadata safely.

        Args:
            session_id: The session ID
            metadata: Metadata to update

        Returns:
            True if updated, False if session not found
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.metadata.update(metadata)
                session.update_access_time()
                return True
            return False

    async def remove_session(self, session_id: str) -> bool:
        """
        Remove a session.

        Args:
            session_id: The session ID

        Returns:
            True if removed, False if not found
        """
        async with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                self.logger.info(f"Removed session: {session_id}")
                return True
            return False

    async def list_sessions(self) -> list[str]:
        """
        List all active session IDs.

        Returns:
            List of session IDs
        """
        async with self._lock:
            return list(self._sessions.keys())

    async def get_session_count(self) -> int:
        """
        Get the count of active sessions.

        Returns:
            Number of active sessions
        """
        async with self._lock:
            return len(self._sessions)

    @asynccontextmanager
    async def session_context(self, session_id: Optional[str] = None):
        """
        Context manager for session operations.

        Args:
            session_id: Optional session ID

        Yields:
            The session
        """
        # Create or get session
        if session_id:
            session = await self.get_session(session_id)
            if not session:
                session = await self.create_session(session_id)
        else:
            session = await self.create_session()

        try:
            yield session
        finally:
            # Update access time on exit
            await self.update_session(session.session_id, {})

    def _is_session_expired(self, session: ModelMCPSession) -> bool:
        """Check if a session has expired."""
        if not session.is_active:
            return True

        expiry_time = session.last_accessed + self.config.session_timeout
        return datetime.now() >= expiry_time

    async def _cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        async with self._lock:
            expired_sessions = []

            for session_id, session in self._sessions.items():
                if self._is_session_expired(session):
                    expired_sessions.append(session_id)

            for session_id in expired_sessions:
                del self._sessions[session_id]

            if expired_sessions:
                self.logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

            return len(expired_sessions)

    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired sessions."""
        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval.total_seconds())
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")


# Global instance
_session_manager: Optional[ThreadSafeSessionManager] = None


def get_session_manager() -> ThreadSafeSessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if not _session_manager:
        _session_manager = ThreadSafeSessionManager()
    return _session_manager
