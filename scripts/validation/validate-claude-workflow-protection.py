#!/usr/bin/env python3
"""
ONEX Claude Workflow File Protection Validator

This validation script prevents modifications to the Claude Code Review workflow file
for security reasons. The file .github/workflows/claude-code-review.yml should only
be modified by repository administrators.

Usage:
    python validate-claude-workflow-protection.py [--help]

Exit Codes:
    0: No violations found (file not modified or doesn't exist)
    1: Claude workflow file modifications detected (blocked)

This validator is part of the ONEX validation framework and can be used by
any repository that includes omnibase_core as a dependency.
"""

import argparse
import sys
from pathlib import Path


def check_claude_workflow_protection(repo_root: Path) -> bool:
    """
    Check if Claude workflow file modifications should be blocked.

    Args:
        repo_root: Path to repository root

    Returns:
        True if validation passes (no modifications to block), False if blocked
    """
    claude_workflow_path = (
        repo_root / ".github" / "workflows" / "claude-code-review.yml"
    )

    # If the file doesn't exist, no protection needed
    if not claude_workflow_path.exists():
        return True

    # Check if we're in a git repository and if the file is staged/modified
    git_dir = repo_root / ".git"
    if not git_dir.exists():
        # Not a git repository, allow operation
        return True

    try:
        import subprocess

        # Check if the Claude workflow file has been modified (staged or unstaged)
        result = subprocess.run(
            ["git", "status", "--porcelain", str(claude_workflow_path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

        # If git status shows any changes to the file, block them
        if result.stdout.strip():
            return False

        # Check if the file is in the staging area specifically
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

        # Check if claude-code-review.yml is in the staged changes
        staged_files = (
            result.stdout.strip().split("\n") if result.stdout.strip() else []
        )
        claude_workflow_relative = ".github/workflows/claude-code-review.yml"

        if claude_workflow_relative in staged_files:
            return False

    except (subprocess.SubprocessError, FileNotFoundError):
        # If git commands fail, allow operation (not a git repo or git not available)
        return True

    return True


def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(
        description="Validate Claude workflow file protection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to repository root (default: current directory)",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress output except for errors"
    )

    args = parser.parse_args()

    repo_root = Path(args.path).resolve()

    if not repo_root.exists():
        if not args.quiet:
            print(f"❌ ERROR: Path does not exist: {repo_root}")
        sys.exit(1)

    # Perform validation
    validation_passed = check_claude_workflow_protection(repo_root)

    if validation_passed:
        if not args.quiet:
            print("✅ Claude workflow protection: PASSED")
        sys.exit(0)
    else:
        print(
            "❌ BLOCKED - .github/workflows/claude-code-review.yml cannot be modified in PRs"
        )
        print("🔒 This file is protected for GitHub security requirements")
        print("📧 Please contact repository administrators for any necessary changes")
        print(
            "💡 To bypass this check (not recommended): use --no-verify with git commit"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
