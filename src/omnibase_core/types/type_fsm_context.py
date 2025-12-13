"""FSM context type alias for flexible runtime state.

This type alias is used by ModelFSMStateSnapshot to represent FSM context data.
FSM contexts inherently need flexibility because they can contain arbitrary runtime
state that varies per FSM implementation (e.g., request IDs, retry counts, user data).

Design Decision:
    Using dict[str, Any] is intentional here because:
    1. FSM contexts are inherently flexible and vary per implementation
    2. The context can contain any runtime state needed by specific FSM workflows
    3. Type safety for context values is enforced at the FSM executor level
    4. This aligns with common FSM patterns in other frameworks

Note:
    This file is in /types/ directory which is excluded from dict[str, Any] validation.
    This is the recommended pattern for intentional flexible typing.
"""

from typing import Any

# Type alias for FSM context - flexible runtime state storage
# Intentionally uses dict[str, Any] for FSM workflow flexibility
FSMContextType = dict[str, Any]

__all__ = ["FSMContextType"]
