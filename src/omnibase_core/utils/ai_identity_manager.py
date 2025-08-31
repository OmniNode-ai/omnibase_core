"""
AI Identity Manager
Manages git identity for AI-generated commits
"""

import os
import subprocess
from collections.abc import Generator
from contextlib import contextmanager

from pydantic import BaseModel, Field


class ModelIdentityInfo(BaseModel):
    """Identity information model."""

    co_author_name: str | None = Field(default=None, description="Co-author name")
    co_author_email: str | None = Field(default=None, description="Co-author email")
    ai_generated: bool = Field(
        default=True,
        description="Whether content is AI-generated",
    )


class AIIdentityManager:
    """Manages git identity switching for AI commits"""

    # Default AI identity
    AI_NAME = os.getenv("AI_GIT_NAME", "CAIA")
    AI_EMAIL = os.getenv("AI_GIT_EMAIL", "caia@omninode.ai")

    @staticmethod
    def get_current_identity() -> tuple[str, str]:
        """Get current git user name and email"""
        try:
            name = subprocess.run(
                ["git", "config", "user.name"],
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip()

            email = subprocess.run(
                ["git", "config", "user.email"],
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip()

            return name, email
        except Exception:
            return "", ""

    @staticmethod
    def set_identity(name: str, email: str) -> bool:
        """Set git identity"""
        try:
            subprocess.run(["git", "config", "user.name", name], check=True)
            subprocess.run(["git", "config", "user.email", email], check=True)
            return True
        except Exception:
            return False

    @classmethod
    @contextmanager
    def ai_identity(
        cls,
        co_author: tuple[str, str] | None = None,
    ) -> Generator[ModelIdentityInfo, None, None]:
        """
        Context manager for AI identity

        Usage:
            with AIIdentityManager.ai_identity() as identity:
                # Git operations here will use AI identity
                subprocess.run(["git", "commit", "-m", "AI commit"])
        """
        # Save current identity
        original_name, original_email = cls.get_current_identity()

        try:
            # Switch to AI identity
            cls.set_identity(cls.AI_NAME, cls.AI_EMAIL)

            # Yield identity info for commit messages
            yield ModelIdentityInfo(
                co_author_name=co_author[0] if co_author else original_name,
                co_author_email=co_author[1] if co_author else original_email,
            )

        finally:
            # Always restore original identity
            if original_name and original_email:
                cls.set_identity(original_name, original_email)

    @classmethod
    def format_commit_message(
        cls,
        message: str,
        identity_info: ModelIdentityInfo,
        include_co_author: bool = True,
    ) -> str:
        """Format commit message with AI attribution"""

        formatted = f"{message}\n\n🤖 Generated with AI Workflow System"

        if include_co_author and identity_info.co_author_name:
            formatted += f"\n\nCo-authored-by: {identity_info.co_author_name} <{identity_info.co_author_email}>"

        return formatted

    @classmethod
    def create_ai_author_tag(cls) -> str:
        """Create author tag for PR descriptions"""
        return f"AI Assistant ({cls.AI_NAME}) <{cls.AI_EMAIL}>"
