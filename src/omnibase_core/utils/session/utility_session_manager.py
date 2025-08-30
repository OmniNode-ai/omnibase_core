"""Session Management Utility

Handles Claude Code session identification and management.
Follows ONEX utility patterns with strong typing and single responsibility.
"""

import hashlib
import socket
from typing import Optional

from omnibase_core.model.hook_events.model_onex_hook_event import \
    ModelOnexHookEvent
from omnibase_core.utils.session.model_session_info import ModelSessionInfo


class UtilitySessionManager:
    """Session management utility for Claude Code events.

    Responsibilities:
    - Session ID generation using hostname:working_directory pattern
    - Working directory extraction from various event data sources
    - Session information standardization
    - Consistency with causal graph service patterns
    """

    def __init__(self) -> None:
        """Initialize session manager."""
        self.hostname = socket.gethostname()

    def extract_working_directory(
        self, hook_event: ModelOnexHookEvent
    ) -> Optional[str]:
        """Extract working directory from hook event data.

        Args:
            hook_event: Hook event containing potential working directory information

        Returns:
            Working directory path if found, None otherwise
        """
        # Get working directory from unified ModelOnexHookEvent
        working_dir = getattr(hook_event, "working_directory", None)
        if working_dir:
            return str(working_dir)

        # Fallback to cwd field if working_directory is not set
        cwd = getattr(hook_event, "cwd", None)
        if cwd:
            return str(cwd)

        return None

    def generate_session_id(self, working_directory: Optional[str]) -> str:
        """Generate consistent session ID from hostname and working directory.

        Args:
            working_directory: Working directory path for session identification

        Returns:
            MD5 hash-based session ID for consistency with causal graph service
        """
        if working_directory:
            # Create session key like causal graph service: hostname:directory
            session_key = f"{self.hostname}:{working_directory}"

            # Generate consistent session ID from the key (use hash for consistency)
            session_id = hashlib.md5(session_key.encode()).hexdigest()
            return session_id

        # Fallback for events without working directory
        return "unknown-session"

    def get_or_generate_session_info(
        self, hook_event: ModelOnexHookEvent
    ) -> ModelSessionInfo:
        """Get session information from event or generate new session data.

        Args:
            hook_event: Hook event to extract session information from

        Returns:
            Complete session information model
        """
        # Get existing session ID from unified ModelOnexHookEvent
        existing_session_id = getattr(hook_event, "session_id", None)

        # Extract working directory
        working_directory = self.extract_working_directory(hook_event)

        # Generate session ID if needed
        if existing_session_id:
            session_id = existing_session_id
            session_key = (
                f"{self.hostname}:{working_directory}"
                if working_directory
                else "unknown"
            )
        else:
            session_id = self.generate_session_id(working_directory)
            session_key = (
                f"{self.hostname}:{working_directory}"
                if working_directory
                else "unknown"
            )

        return ModelSessionInfo(
            session_id=session_id,
            working_directory=working_directory,
            hostname=self.hostname,
            session_key=session_key,
        )
