"""Allow running as python -m omnibase_core.validation.cross_repo."""

from omnibase_core.validation.cross_repo.cli import main

if __name__ == "__main__":
    raise SystemExit(main())  # error-ok: Standard CLI entry point pattern
