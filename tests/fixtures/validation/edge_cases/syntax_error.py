#!/usr/bin/env python3
"""File with syntax errors for testing edge cases."""

from typing import Dict


class ModelUserData:
    """Model with syntax errors."""

    def __init__(self, user_id: str:  # Syntax error here
        self.user_id = user_id

    def process_data(self) -> Dict[str, str]
        # Missing colon here
        return {"id": self.user_id}
