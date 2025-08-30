#!/usr/bin/env python3
"""
Infrastructure Reducer Service Entry Point.

Starts the infrastructure reducer as a persistent service that responds to
discovery requests and manages infrastructure adapters.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parents[5] / "src"
sys.path.insert(0, str(src_path))

from omnibase_core.core.onex_container import ONEXContainer
from omnibase_core.tools.infrastructure.tool_infrastructure_reducer.v1_0_0.node import \
    ToolInfrastructureReducer


async def main():
    """Start the infrastructure reducer service."""
    print("🚀 Starting ONEX Infrastructure Reducer Service")

    # Create container (lightweight for now)
    container = ONEXContainer()

    try:
        # Initialize the infrastructure reducer
        reducer = ToolInfrastructureReducer(container)
        print("✅ Infrastructure Reducer initialized")

        # Start in service mode to enable discovery handlers
        print("🌐 Starting service mode to enable discovery handlers...")
        await reducer.start_service_mode()

    except KeyboardInterrupt:
        print("\n🛑 Shutting down gracefully...")
        if "reducer" in locals():
            await reducer.stop_service_mode()
    except Exception as e:
        print(f"❌ Failed to start infrastructure reducer: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
