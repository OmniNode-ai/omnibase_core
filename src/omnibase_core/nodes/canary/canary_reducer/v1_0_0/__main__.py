#!/usr/bin/env python3
"""
Infrastructure Reducer Service Entry Point.

Starts the infrastructure reducer as a persistent service that responds to
discovery requests and manages infrastructure adapters.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parents[5] / "src"
sys.path.insert(0, str(src_path))

from omnibase_core.core.onex_container import ModelONEXContainer

from .node import NodeCanaryReducer


async def main():
    """Start the infrastructure reducer service."""

    # Create container (lightweight for now)
    container = ModelONEXContainer()

    try:
        # Initialize the infrastructure reducer
        reducer = NodeCanaryReducer(container)

        # Start in service mode to enable discovery handlers
        await reducer.start_service_mode()

    except KeyboardInterrupt:
        if "reducer" in locals():
            await reducer.stop_service_mode()
    except Exception:
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
