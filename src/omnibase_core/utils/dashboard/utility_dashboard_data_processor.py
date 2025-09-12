"""Dashboard Data Processor Utility

Handles data processing and transformation for dashboard display.
Follows ONEX utility patterns with strong typing and single responsibility.
"""

import asyncio
from typing import TYPE_CHECKING

from omnibase_core.models.model_dashboard_tool_capture import ModelDashboardToolCapture
from omnibase_core.models.model_dashboard_web_socket_event_data import (
    ModelDashboardWebSocketEventData,
)
from omnibase_core.services.omnimemory.graph.factories.factory_claude_code_event import (
    FactoryClaudeCodeEvent,
)
from omnibase_core.services.postgres_debug_knowledge_base import (
    ServicePostgresDebugKnowledgeBase,
)
from omnibase_core.utils.session.utility_session_manager import UtilitySessionManager

if TYPE_CHECKING:
    pass


class UtilityDashboardDataProcessor:
    """Dashboard data processing utility.

    Responsibilities:
    - Hook event processing and data extraction
    - Database storage coordination
    - Content extraction and formatting
    - Data transformation for dashboard display
    """

    def __init__(
        self,
        db_service: ServicePostgresDebugKnowledgeBase | None = None,
        session_manager: UtilitySessionManager | None = None,
    ):
        """Initialize data processor.

        Args:
            db_service: PostgreSQL database service for storage
            session_manager: Session management utility
        """
        self.db_service = db_service
        self.session_manager = session_manager or UtilitySessionManager()

    def extract_tool_name(self, hook_event: "ModelHookEvent") -> str:
        """Extract tool name from hook event, with fallbacks for different event types.

        Args:
            hook_event: Hook event to extract tool name from

        Returns:
            Tool name string, never None to satisfy database constraints
        """
        # Handle tool_name being None for non-tool events (like user messages)
        tool_name = hook_event.tool_name or ""

        # Ensure tool_name is never None to satisfy database constraint
        if not tool_name:
            if "proxy" in hook_event.topic:
                tool_name = "proxy-message"
            elif "user" in hook_event.topic or hook_event.event_type == "user-prompt":
                tool_name = "user-message"
            else:
                tool_name = "system-event"

        return tool_name

    def build_capture_data(
        self,
        hook_event: "ModelHookEvent",
    ) -> ModelDashboardToolCapture:
        """Build capture data structure for database storage.

        Args:
            hook_event: Hook event to process

        Returns:
            Structured capture data model
        """
        tool_name = self.extract_tool_name(hook_event)
        session_info = self.session_manager.get_or_generate_session_info(hook_event)

        # Use the factory's centralized extraction methods
        # This is now the single source of truth for content extraction
        message_content = FactoryClaudeCodeEvent.extract_display_content(hook_event)

        return ModelDashboardToolCapture(
            capture_id=f"{hook_event.timestamp}_{tool_name}_{hook_event.event_type}",
            tool_name=tool_name,
            event_type=hook_event.event_type,
            timestamp=hook_event.timestamp,
            session_id=session_info.session_id,
            working_directory=session_info.working_directory,
            # Map hook fields to database fields
            request=(
                {
                    "parameters_json": getattr(hook_event, "parameters_json", None),
                    "claude_message": message_content
                    or getattr(hook_event, "claude_message", None),
                }
                if getattr(hook_event, "parameters_json", None) or message_content
                else None
            ),
            response=(
                {
                    "result": getattr(hook_event, "result", None),
                    "success": getattr(hook_event, "success", None),
                    "duration_ms": getattr(hook_event, "duration_ms", None),
                    "result_size_bytes": getattr(hook_event, "result_size_bytes", None),
                }
                if getattr(hook_event, "result", None)
                else None
            ),
            error=(
                {
                    "error_message": getattr(hook_event, "error_message", None),
                    "error_type": getattr(hook_event, "error_type", None),
                }
                if getattr(hook_event, "error_message", None)
                else None
            ),
            metadata={
                "topic": hook_event.topic,
                "source": "proxy" if "proxy" in hook_event.topic else "hook",
            },
        )

    def build_websocket_event_data(
        self,
        hook_event: "ModelHookEvent",
        message_content: str | None = None,
    ) -> ModelDashboardWebSocketEventData:
        """Build event data structure for WebSocket broadcasting.

        Args:
            hook_event: Hook event to process
            message_content: Optional pre-extracted message content

        Returns:
            WebSocket event data model
        """
        # Convert hook event to dictionary for broadcasting
        # Use Pydantic's model_dump to properly serialize ModelOnexHookEvent
        event_dict = (
            hook_event.model_dump(mode="json")
            if hasattr(hook_event, "model_dump")
            else {}
        )

        # Ensure message content is included for display
        if not message_content:
            message_content = FactoryClaudeCodeEvent.extract_display_content(hook_event)

        if message_content:
            event_dict["claude_message"] = message_content
            # Also add to nested data if it exists
            if event_dict.get("data"):
                event_dict["data"]["claude_message"] = message_content

        return ModelDashboardWebSocketEventData(
            topic=hook_event.topic,
            timestamp=hook_event.timestamp,
            data=event_dict,
            event_type=hook_event.event_type,
            # Use the same extraction as storage path to avoid 'Unknown' tools in live updates
            tool_name=self.extract_tool_name(hook_event),
            source="proxy" if "proxy" in hook_event.topic else "hook",
        )

    async def process_and_store_hook_event(
        self,
        hook_event: "ModelHookEvent",
    ) -> ModelDashboardWebSocketEventData | None:
        """Process hook event and store in database.

        Args:
            hook_event: Hook event to process and store

        Returns:
            WebSocket event data model if processing successful, None otherwise
        """
        if not self.db_service:
            return None

        # Build capture data for storage
        capture_data = self.build_capture_data(hook_event)

        # Store asynchronously with proper error handling
        storage_task = asyncio.create_task(
            self.db_service.store_tool_capture(capture_data),
        )
        storage_task.add_done_callback(self._handle_storage_task_completion)

        # Build WebSocket event data for broadcasting
        message_content = FactoryClaudeCodeEvent.extract_display_content(hook_event)
        return self.build_websocket_event_data(hook_event, message_content)

    def _handle_storage_task_completion(self, task):
        """Handle completion of async storage task with proper error handling.

        Args:
            task: Completed asyncio task for database storage
        """
        try:
            # Check if task completed successfully
            if task.exception() is not None:
                task.exception()
                # Log error but don't fail the main hook processing
                # In production, you might want to add retry logic or alerting here
            else:
                # Task completed successfully
                pass
        except Exception:
            # Handle any errors in the callback itself
            pass
