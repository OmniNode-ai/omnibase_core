"""Tests for omnibase_core.backends module.

This package contains backend tests organized by type:
- cache/: Cache backend tests (Redis URL sanitization, in-memory cache)
- metrics/: Metrics backend tests (Prometheus, in-memory metrics)

Note: This __init__.py is required for pytest test discovery
in subdirectories. Tests are intentionally organized in
subdirectories by backend type rather than in this root directory.
"""
