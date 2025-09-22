"""
Entry point for running omnibase_core validation as a module.

Usage:
    python -m omnibase_core.validation --help
    python -m omnibase_core.validation architecture
    python -m omnibase_core.validation union-usage --strict
    python -m omnibase_core.validation all
"""

from .cli import main

if __name__ == "__main__":
    exit(main())
