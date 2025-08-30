#!/usr/bin/env python3
"""
UtilityTextProcessor - Text processing utilities for ONEX business logic.

This utility provides common text processing functions used by AI agents
and business logic implementations.
"""

import re


class UtilityTextProcessor:
    """
    Utility class for common text processing operations.

    Used by AI agents and business logic implementations to provide
    consistent text processing capabilities across the ONEX platform.
    """

    @staticmethod
    def validate_text_content(
        content: str | None,
    ) -> dict[str, bool | str | list[str]]:
        """
        Validate text content for basic quality standards.

        Args:
            content: Text content to validate

        Returns:
            Dict containing validation results:
            - valid: bool indicating if content passes validation
            - message: str describing validation result
            - issues: List[str] of specific issues found
        """
        if content is None:
            return {
                "valid": False,
                "message": "Content is None",
                "issues": ["null_content"],
            }

        if not isinstance(content, str):
            return {
                "valid": False,
                "message": "Content must be a string",
                "issues": ["invalid_type"],
            }

        if not content:
            return {
                "valid": False,
                "message": "Content is empty",
                "issues": ["empty_content"],
            }

        if not content.strip():
            return {
                "valid": False,
                "message": "Content contains only whitespace",
                "issues": ["whitespace_only"],
            }

        # Check for reasonable length (not just a single character)
        if len(content.strip()) < 2:
            return {
                "valid": False,
                "message": "Content is too short to be meaningful",
                "issues": ["too_short"],
            }

        return {"valid": True, "message": "Content validation passed", "issues": []}

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean text by removing extra whitespace and normalizing line endings.

        Args:
            text: Text to clean

        Returns:
            Cleaned text
        """
        if not isinstance(text, str):
            return ""

        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Remove excessive whitespace
        text = re.sub(r"\n\s*\n\s*\n", "\n\n", text)  # Max 2 consecutive newlines
        text = re.sub(r"[ \t]+", " ", text)  # Multiple spaces/tabs to single space
        return text.strip()

    @staticmethod
    def extract_keywords(text: str, min_length: int = 3) -> list[str]:
        """
        Extract keywords from text.

        Args:
            text: Text to extract keywords from
            min_length: Minimum length for keywords

        Returns:
            List of extracted keywords
        """
        if not isinstance(text, str):
            return []

        # Simple keyword extraction - split on non-alphanumeric and filter
        words = re.findall(r"\b[a-zA-Z]+\b", text.lower())
        keywords = [word for word in words if len(word) >= min_length]

        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for keyword in keywords:
            if keyword not in seen:
                seen.add(keyword)
                unique_keywords.append(keyword)

        return unique_keywords

    @staticmethod
    def count_words(text: str) -> int:
        """
        Count words in text.

        Args:
            text: Text to count words in

        Returns:
            Number of words
        """
        if not isinstance(text, str):
            return 0

        words = re.findall(r"\b\w+\b", text)
        return len(words)

    @staticmethod
    def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
        """
        Truncate text to maximum length with optional suffix.

        Args:
            text: Text to truncate
            max_length: Maximum length including suffix
            suffix: Suffix to add if truncated

        Returns:
            Truncated text
        """
        if not isinstance(text, str):
            return ""

        if len(text) <= max_length:
            return text

        truncate_length = max_length - len(suffix)
        if truncate_length <= 0:
            return suffix[:max_length]

        return text[:truncate_length] + suffix

    @staticmethod
    def analyze_text_metrics(text: str) -> dict[str, int | float | list[str]]:
        """
        Analyze text and return comprehensive metrics.

        Args:
            text: Text to analyze

        Returns:
            Dict containing text metrics
        """
        if not isinstance(text, str):
            return {
                "word_count": 0,
                "character_count": 0,
                "line_count": 0,
                "average_word_length": 0.0,
                "keywords": [],
                "validation": {
                    "valid": False,
                    "message": "Invalid input type",
                    "issues": ["invalid_type"],
                },
            }

        validation = UtilityTextProcessor.validate_text_content(text)
        word_count = UtilityTextProcessor.count_words(text)
        keywords = UtilityTextProcessor.extract_keywords(text)

        # Calculate average word length
        words = re.findall(r"\b\w+\b", text)
        avg_word_length = (
            sum(len(word) for word in words) / len(words) if words else 0.0
        )

        return {
            "word_count": word_count,
            "character_count": len(text),
            "line_count": len(text.split("\n")),
            "average_word_length": round(avg_word_length, 2),
            "keywords": keywords[:10],  # Limit to top 10 keywords
            "validation": validation,
        }
