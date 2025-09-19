#!/usr/bin/env python3
"""File with syntax errors for testing edge cases."""

from typing import Dict


class ModelUserData:
    """Model with syntax errors."""

    def __init__(self, user_id: str):  # Fixed syntax error - removed extra colon
        self.user_id = user_id

    def process_data(self) -> Dict[str, str]:
        # Fixed missing colon
        return {"id": self.user_id}
